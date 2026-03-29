import pandas as pd
from pathlib import Path


class RegionMapper:
    """
    Two responsibilities:
    1. Enrich the panel with REGION and COUNTY_UA columns parsed directly
       from the ONS indicators file hierarchy (no external lookup needed).
    2. Map candidate city regions to their constituent LAD codes for
       Phase 2 analysis.

    CA regions are resolved via the MSOA→CA lookup file.
    Non-CA regions (incl. non-English) are resolved via LAD name matching.
    Note: non-English regions return empty lists when england_only: true.
    """

    # --- CA lookup regions (matched via CAUTH23NM in the CA lookup file) ---
    CA_NAME_MAP = {
        'South Yorkshire MCA':             'South Yorkshire',
        'West Midlands CA':                'West Midlands',
        'West Yorkshire CA':               'West Yorkshire',
        'Greater Manchester CA':           'Greater Manchester',
        'West of England CA':              'West of England',
        'Liverpool City Region':           'Liverpool City Region',
        'Cambridgeshire and Peterborough': 'Cambridgeshire and Peterborough',
        'Tees Valley CA':                  'Tees Valley',
    }

    # North East CA combines two separate CAs in the lookup:
    # 'North East' (4 LADs) + 'North of Tyne' (3 LADs)
    MULTI_CA_MAP = {
        'North East CA': ['North East', 'North of Tyne'],
    }

    # --- Name-match regions (matched via GEOGRAPHY_NAME in the panel) ---
    # Used for regions absent from the CA lookup or non-English geographies.
    # East Midlands CA absent from 2023 boundaries file — LAD list sourced manually.
    NAME_MATCH_REGIONS = {
        'London': [
            'Barking and Dagenham', 'Barnet', 'Bexley', 'Brent', 'Bromley',
            'Camden', 'City of London', 'Croydon', 'Ealing', 'Enfield',
            'Greenwich', 'Hackney', 'Hammersmith and Fulham', 'Haringey',
            'Harrow', 'Havering', 'Hillingdon', 'Hounslow', 'Islington',
            'Kensington and Chelsea', 'Kingston upon Thames', 'Lambeth',
            'Lewisham', 'Merton', 'Newham', 'Redbridge', 'Richmond upon Thames',
            'Southwark', 'Sutton', 'Tower Hamlets', 'Waltham Forest',
            'Wandsworth', 'Westminster'
        ],
        'East Midlands CA': [
            # Derby unitary
            'Derby',
            # Derbyshire districts
            'Amber Valley', 'Bolsover', 'Chesterfield', 'Derbyshire Dales',
            'Erewash', 'High Peak', 'North East Derbyshire', 'South Derbyshire',
            # Nottingham unitary
            'Nottingham',
            # Nottinghamshire districts
            'Ashfield', 'Bassetlaw', 'Broxtowe', 'Gedling', 'Mansfield',
            'Newark and Sherwood', 'Rushcliffe',
            # Leicester unitary
            'Leicester',
            # Leicestershire districts
            'Blaby', 'Charnwood', 'Harborough', 'Hinckley and Bosworth',
            'Melton', 'North West Leicestershire', 'Oadby and Wigston',
        ],
        # Non-English regions — return empty lists when england_only: true
        'Glasgow City Region': [
            'Glasgow City', 'East Dunbartonshire', 'West Dunbartonshire',
            'North Lanarkshire', 'South Lanarkshire', 'East Renfrewshire',
            'Renfrewshire', 'Inverclyde'
        ],
        'Cardiff-Newport': [
            'Cardiff', 'Newport'
        ],
        'Edinburgh City Region': [
            'City of Edinburgh', 'East Lothian', 'Midlothian', 'West Lothian'
        ],
    }

    def __init__(self, config: dict, panel: pd.DataFrame):
        self.config = config
        self.panel = panel
        self.base = Path(__file__).resolve().parent.parent
        self._region_map = None
        self._hierarchy = None

    # --- Panel enrichment ---

    def _build_hierarchy(self) -> pd.DataFrame:
        """
        Parse LAD → Region → County/UA hierarchy directly from the ONS
        indicators file (Weekly pay sheet), which contains the most complete
        geographic hierarchy at LAD level. Result is cached after first call.
        """
        if self._hierarchy is not None:
            return self._hierarchy

        path = self.base / self.config["paths"]["ons_indicators"]
        df = pd.read_excel(path, sheet_name="Weekly pay", header=None)

        # find header row
        header_row = None
        for i, row in df.iterrows():
            if any("Area Code" in str(v) for v in row.values):
                header_row = i
                break

        df.columns = df.iloc[header_row]
        df = df.iloc[header_row + 1:].reset_index(drop=True)
        df = df.rename(columns={df.columns[0]: "GEOGRAPHY_CODE"})

        # forward fill region and county/UA down the hierarchy, strip whitespace
        df["Region"] = df["Region"].ffill().str.strip()
        df["County or Unitary Authority"] = df["County or Unitary Authority"].ffill().str.strip()

        # filter to LAD-level rows only
        df = df[df["GEOGRAPHY_CODE"].astype(str).str.match(r"^E0[6-9]\d{6}$", na=False)].copy()

        self._hierarchy = df[["GEOGRAPHY_CODE", "Region", "County or Unitary Authority"]].rename(columns={
            "Region": "REGION",
            "County or Unitary Authority": "COUNTY_UA"
        })
        return self._hierarchy

    def enrich_panel(self, panel: pd.DataFrame) -> pd.DataFrame:
        """
        Add REGION and COUNTY_UA columns to the panel.
        Parsed directly from ONS indicators file — no external CSV needed.
        Non-English LADs (if present) will have NaN.
        """
        hierarchy = self._build_hierarchy()
        hierarchy["GEOGRAPHY_CODE"] = hierarchy["GEOGRAPHY_CODE"].astype(str)
        panel = panel.copy()
        panel["GEOGRAPHY_CODE"] = panel["GEOGRAPHY_CODE"].astype(str)
        panel = panel.merge(hierarchy, on="GEOGRAPHY_CODE", how="left")
        n_missing = panel[panel["GEOGRAPHY_CODE"].str.startswith("E")]["REGION"].isna().sum()
        if n_missing > 0:
            missing = panel[panel["REGION"].isna()]["GEOGRAPHY_NAME"].unique()
            print(f"[RegionMapper] WARNING — {len(missing)} LADs missing REGION: {missing}")
        else:
            print(f"[RegionMapper] REGION and COUNTY_UA added — all English LADs matched")
        return panel

    # --- CA lookup ---

    def _load_ca_lookup(self) -> pd.DataFrame:
        path = self.base / self.config["paths"]["msoa_to_ca"]
        return pd.read_csv(path)[['CAUTH23NM', 'LAD23CD', 'LAD23NM']].drop_duplicates()

    # --- Region → LAD code mapping ---

    def build(self) -> dict[str, list[str]]:
        """
        Build and return the full region → LAD code mapping.
        Returns a dict: {region_name: [LAD_CODE, ...]}
        """
        ca_lookup = self._load_ca_lookup()
        region_map = {}

        # single CA lookup regions
        ca_not_found = []
        for region, ca_name in self.CA_NAME_MAP.items():
            codes = ca_lookup[ca_lookup['CAUTH23NM'] == ca_name]['LAD23CD'].tolist()
            if codes:
                region_map[region] = codes
            else:
                ca_not_found.append(f"  {region} (looked up as '{ca_name}')")

        if ca_not_found:
            print(f"[RegionMapper] WARNING — not found in CA lookup (will be skipped):")
            for msg in ca_not_found:
                print(msg)

        # multi-CA regions (e.g. North East CA = North East + North of Tyne)
        for region, ca_names in self.MULTI_CA_MAP.items():
            codes = ca_lookup[ca_lookup['CAUTH23NM'].isin(ca_names)]['LAD23CD'].tolist()
            if not codes:
                print(f"[RegionMapper] WARNING — {region}: no LADs found for CAs {ca_names}")
            region_map[region] = codes

        # name-match regions
        for region, lad_names in self.NAME_MATCH_REGIONS.items():
            codes = (
                self.panel[self.panel['GEOGRAPHY_NAME'].isin(lad_names)]
                ['GEOGRAPHY_CODE'].unique().tolist()
            )
            matched = self.panel[self.panel['GEOGRAPHY_CODE'].isin(codes)]['GEOGRAPHY_NAME'].unique().tolist()
            missing = [n for n in lad_names if n not in matched]
            if missing:
                print(f"[RegionMapper] WARNING — {region}: LADs not found in panel: {missing}")
            region_map[region] = codes

        self._region_map = region_map
        return region_map

    def get(self) -> dict[str, list[str]]:
        """Return cached region map, building it if not yet built."""
        if self._region_map is None:
            self.build()
        return self._region_map

    def get_lad_names(self) -> dict[str, list[str]]:
        """Return region → LAD name mapping for display purposes."""
        region_map = self.get()
        return {
            region: self.panel[self.panel['GEOGRAPHY_CODE'].isin(codes)]
                        ['GEOGRAPHY_NAME'].unique().tolist()
            for region, codes in region_map.items()
        }

    def verify(self):
        """Print a summary of each region and its constituent LADs."""
        names = self.get_lad_names()
        for region, lad_names in names.items():
            print(f"{region} ({len(lad_names)} LADs): {lad_names}")