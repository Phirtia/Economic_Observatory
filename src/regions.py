import pandas as pd
from pathlib import Path


class RegionMapper:
    """
    Maps candidate city regions to their constituent LAD codes.
    Handles English combined authorities via MSOA→CA lookup,
    and non-CA regions via LAD name matching against the panel.
    """

    # --- CA lookup regions (matched via CAUTH23NM in the CA lookup file) ---
    CA_NAME_MAP = {
        'South Yorkshire MCA':   'South Yorkshire',
        'West Midlands CA':      'West Midlands',
        'West Yorkshire CA':     'West Yorkshire',
        'Greater Manchester CA': 'Greater Manchester',
        'West of England CA':    'West of England',
        'Liverpool City Region': 'Liverpool City Region',
    }

    # --- Name-match regions (matched via GEOGRAPHY_NAME in the panel) ---
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
        'North East CA': [
            'Newcastle upon Tyne', 'Gateshead', 'Sunderland', 'South Tyneside',
            'North Tyneside', 'County Durham', 'Northumberland'
        ],
        'East Midlands CA': [
            'Derby', 'Nottingham', 'Leicester', 'Rutland'
        ],
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
        'Cambridge Sub-Region': [
            'Cambridge', 'South Cambridgeshire'
        ],
    }

    def __init__(self, config: dict, panel: pd.DataFrame):
        self.config = config
        self.panel = panel
        self.base = Path(__file__).resolve().parent.parent
        self._region_map = None

    def _load_ca_lookup(self) -> pd.DataFrame:
        path = self.base / self.config["paths"]["msoa_to_ca"]
        return pd.read_csv(path)[['CAUTH23NM', 'LAD23CD', 'LAD23NM']].drop_duplicates()

    def build(self) -> dict[str, list[str]]:
        """
        Build and return the full region → LAD code mapping.
        Returns a dict: {region_name: [LAD_CODE, ...]}
        """
        ca_lookup = self._load_ca_lookup()
        region_map = {}

        # --- CA lookup regions ---
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

        # --- Name-match regions ---
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