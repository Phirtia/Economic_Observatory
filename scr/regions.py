import pandas as pd
from pathlib import Path


class RegionMapper:
    """
    Maps candidate city regions to their constituent LAD codes.
    Handles English combined authorities via MSOA→CA lookup,
    Glasgow City Region via Scottish council areas,
    and Cardiff-Newport via LAD name matching.
    """

    GLASGOW_COUNCILS = [
        'Glasgow City', 'East Dunbartonshire', 'West Dunbartonshire',
        'North Lanarkshire', 'South Lanarkshire', 'East Renfrewshire',
        'Renfrewshire', 'Inverclyde'
    ]

    CARDIFF_NEWPORT = ['Cardiff', 'Newport']

    CA_NAME_MAP = {
        'South Yorkshire MCA':   'South Yorkshire',
        'West Midlands CA':      'West Midlands',
        'West Yorkshire CA':     'West Yorkshire',
        'Greater Manchester CA': 'Greater Manchester',
        'West of England CA':    'West of England',
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

        # English combined authorities
        for region, ca_name in self.CA_NAME_MAP.items():
            codes = ca_lookup[ca_lookup['CAUTH23NM'] == ca_name]['LAD23CD'].tolist()
            region_map[region] = codes

        # Glasgow City Region
        glasgow_codes = (
            self.panel[self.panel['GEOGRAPHY_NAME'].isin(self.GLASGOW_COUNCILS)]
            ['GEOGRAPHY_CODE'].unique().tolist()
        )
        region_map['Glasgow City Region'] = glasgow_codes

        # Cardiff-Newport
        cardiff_codes = (
            self.panel[self.panel['GEOGRAPHY_NAME'].isin(self.CARDIFF_NEWPORT)]
            ['GEOGRAPHY_CODE'].unique().tolist()
        )
        region_map['Cardiff-Newport'] = cardiff_codes

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