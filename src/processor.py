import pandas as pd
from pathlib import Path
from src.loader import DataLoader
from src.indicators import IndicatorBuilder


class DataProcessor:

    # Repeated geographic label columns in ONS file — keep first, drop rest
    GEO_LABEL_PATTERNS = [
        "county or unitary authority",
        "region",
        "nation",
        "country",
    ]

    def __init__(self, config: dict):
        self.config = config
        self.paths = config["paths"]
        self.params = config["parameters"]
        self.loader = DataLoader(config)
        self.indicator_builder = IndicatorBuilder(config)

    def _save(self, df: pd.DataFrame, key: str):
        path = Path(self.paths[key])
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)

    # --- Step 1: filter to LAD geography only ---

    def filter_lad_only(self, df: pd.DataFrame) -> pd.DataFrame:
        lad_type = "local authorities: district / unitary (as of April 2023)"
        return df[df["GEOGRAPHY_TYPE"] == lad_type].copy()

    # --- Step 2: filter to year range ---

    def filter_years(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only 2016–2022 to align employee and business count ranges."""
        y0 = self.params["growth_start_year_emp"]
        y1 = self.params["growth_end_year"]
        return df[(df["YEAR"] >= y0) & (df["YEAR"] <= y1)].copy()

    # --- Step 3: standardise IS8 sector names ---

    def standardise_sector_names(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        sector_map = self.config["parameters"]["sector_map"]
        df["IS8_SECTOR"] = df["IS8_SECTOR"].map(sector_map).fillna(df["IS8_SECTOR"])
        return df

    # --- Step 4: aggregate to IS8 level ---

    def aggregate_to_is8(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sum all rows per LAD x IS8 sector x year.
        SIZE_BAND and FRONTIER_SECTOR are dropped by grouping at IS8 level only.
        Total rows are kept here — needed for LQ computation in indicators.py.
        """
        group_cols = ["YEAR", "GEOGRAPHY_CODE", "GEOGRAPHY_NAME", "IS8_SECTOR"]
        return df.groupby(group_cols, as_index=False)["OBS_VALUE"].sum()

    # --- Step 5: optimise dtypes ---

    def optimise_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cast group key columns to category and numeric values to float32."""
        cat_cols = ["GEOGRAPHY_CODE", "GEOGRAPHY_NAME", "IS8_SECTOR"]
        for col in cat_cols:
            if col in df.columns:
                df[col] = df[col].astype("category")
        for col in ["EMPLOYEES", "BUSINESSES"]:
            if col in df.columns:
                df[col] = df[col].astype("float32")
        return df

    # --- Step 6: parse and clean ONS indicators ---

    def _parse_ons_sheet(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Extract LAD-level rows from a single ONS indicator sheet.
        Keeps only LAD-level rows using Area Code prefix heuristic.
        """
        df = df_raw.copy()
        df.columns = range(df.shape[1])
        header_row = None
        for i, row in df.iterrows():
            if any("Area Code" in str(v) for v in row.values):
                header_row = i
                break
        if header_row is None:
            return pd.DataFrame()
        df.columns = df.iloc[header_row]
        df = df.iloc[header_row + 1:].reset_index(drop=True)
        df = df.rename(columns={df.columns[0]: "GEOGRAPHY_CODE"})
        df = df[df["GEOGRAPHY_CODE"].astype(str).str.match(r"^[EWS]\d{8}$")]
        df = df.replace("na", pd.NA).replace("NA", pd.NA)
        for col in df.columns:
            if col != "GEOGRAPHY_CODE":
                df[col] = pd.to_numeric(df[col], errors="coerce")
        numeric_cols = [c for c in df.columns if c != "GEOGRAPHY_CODE" and df[c].notna().any()]
        return df[["GEOGRAPHY_CODE"] + numeric_cols]

    def _dedup_geo_label_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        The ONS file repeats geographic label columns once per indicator sheet
        (e.g. 'County or Unitary Authority [GVA per hour]',
              'County or Unitary Authority [Weekly pay]', ...).
        Keep the first occurrence of each pattern, drop all subsequent ones.
        """
        seen = set()
        drop_cols = []
        for col in df.columns:
            col_lower = str(col).lower()
            for pattern in self.GEO_LABEL_PATTERNS:
                if col_lower.startswith(pattern):
                    if pattern in seen:
                        drop_cols.append(col)
                    else:
                        seen.add(pattern)
                    break
        return df.drop(columns=drop_cols)

    def merge_ons_indicators(
        self,
        panel: pd.DataFrame,
        ons_sheets: dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        result = panel.copy()
        for sheet_name, df_raw in ons_sheets.items():
            df = self._parse_ons_sheet(df_raw)
            if df.empty or len(df.columns) < 2:
                continue
            col_name = sheet_name.lower().replace(" ", "_").replace("&", "and")
            val_cols = [c for c in df.columns if c != "GEOGRAPHY_CODE"]
            if not val_cols:
                continue
            df = df[["GEOGRAPHY_CODE", val_cols[0]]].copy()
            df = df.rename(columns={val_cols[0]: col_name})
            df["GEOGRAPHY_CODE"] = df["GEOGRAPHY_CODE"].astype(str)
            result = result.merge(df, on="GEOGRAPHY_CODE", how="left")
        result = self._dedup_geo_label_columns(result)
        result = result.dropna(axis=1, how="all")
        return result

    # --- Step 7: reconcile pre-2023 boundary codes ---

    def reconcile_boundaries(
        self,
        df: pd.DataFrame,
        crosswalk: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Drop LADs with obsolete pre-2023 boundary codes.
        Uses CHGIND flag from MSOA crosswalk to identify changed boundaries.
        """
        changed = crosswalk[crosswalk["CHGIND"].notna()][["LAD22CD", "LAD22NM"]].drop_duplicates()
        obsolete_codes = set(changed["LAD22CD"])
        return df[~df["GEOGRAPHY_CODE"].isin(obsolete_codes)].copy()

    # --- Orchestrator ---

    def build_panel(self) -> pd.DataFrame:
        # load
        emp = self.loader.load_employee_counts_lad()
        bus = self.loader.load_business_counts_lad()
        ons_sheets = self.loader.load_ons_indicators()
        crosswalk = self.loader.load_msoa_crosswalk()

        # process employee counts
        emp = self.filter_lad_only(emp)
        emp = self.filter_years(emp)
        emp = self.standardise_sector_names(emp)
        emp = self.aggregate_to_is8(emp)
        emp = emp.rename(columns={"OBS_VALUE": "EMPLOYEES"})

        # process business counts
        bus = self.filter_lad_only(bus)
        bus = self.filter_years(bus)
        bus = self.standardise_sector_names(bus)
        bus = self.aggregate_to_is8(bus)
        bus = bus.rename(columns={"OBS_VALUE": "BUSINESSES"})

        # inner join — 100% match expected
        merge_cols = ["YEAR", "GEOGRAPHY_CODE", "GEOGRAPHY_NAME", "IS8_SECTOR"]
        panel = emp.merge(bus, on=merge_cols, how="inner")

        # merge ONS indicators (dedup geo columns + drop all-NA inside)
        panel = self.merge_ons_indicators(panel, ons_sheets)

        # reconcile boundaries
        panel = self.reconcile_boundaries(panel, crosswalk)

        # build indicators (LQ, growth, density — removes Total rows internally)
        panel = self.indicator_builder.build_indicators(panel)

        # optimise dtypes
        panel = self.optimise_dtypes(panel)

        # save
        self._save(panel, "analysis_panel")
        print(f"Panel built: {panel.shape[0]:,} rows x {panel.shape[1]} columns")
        return panel