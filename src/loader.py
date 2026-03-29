import pandas as pd
import geopandas as gpd
import yaml
from pathlib import Path


def load_config(path: str = "config.yml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


class DataLoader:

    def __init__(self, config: dict):
        self.config = config
        self.paths = config["paths"]
        self.base = Path(__file__).resolve().parent.parent

    def _p(self, key: str) -> Path:
        if key not in self.paths:
            raise KeyError(f"[DataLoader] Path key '{key}' not found in config.yml")
        p = self.base / self.paths[key]
        if not p.exists():
            raise FileNotFoundError(f"[DataLoader] File not found for '{key}': {p}")
        return p

    # --- IS8 core data ---

    def load_business_counts_lad(self) -> pd.DataFrame:
        return pd.read_parquet(self._p("business_counts_lad"))

    def load_employee_counts_lad(self) -> pd.DataFrame:
        return pd.read_parquet(self._p("employee_counts_lad"))

    def load_business_counts_msoa(self) -> pd.DataFrame:
        return pd.read_parquet(self._p("business_counts_msoa"))

    def load_employee_counts_msoa(self) -> pd.DataFrame:
        return pd.read_parquet(self._p("employee_counts_msoa"))

    # --- Reference data ---

    def load_sic_lookup(self) -> pd.DataFrame:
        return pd.read_csv(self._p("sic_lookup"))

    def load_ons_indicators(self) -> dict[str, pd.DataFrame]:
        xl = pd.ExcelFile(self._p("ons_indicators"))
        skip = {"Notes", "Voluntary TQV", "Data dictionary", "Data inclusivity"}
        return {
            sheet: xl.parse(sheet)
            for sheet in xl.sheet_names
            if sheet not in skip
        }

    # --- Boundary files ---

    def load_lad_boundaries(self) -> gpd.GeoDataFrame:
        return gpd.read_file(self._p("lad_boundaries"))

    def load_msoa_boundaries(self) -> gpd.GeoDataFrame:
        return gpd.read_file(self._p("msoa_boundaries"))

    # --- Lookup tables ---

    def load_msoa_ca_lookup(self) -> pd.DataFrame:
        return pd.read_csv(self._p("msoa_to_ca"))