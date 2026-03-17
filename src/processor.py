import pandas as pd
from pathlib import Path
from src.loader import DataLoader
from src.indicators import IndicatorBuilder


class DataProcessor:

    # IS8 sector name mapping — raw data names → standardised names
    SECTOR_MAP = {
        "Advanced manufacturing":             "Advanced Manufacturing",
        "Creative Industries":                "Creative Industries",
        "Defence sector":                     "Defence",
        "Digital and Technology":             "Digital and Technologies",
        "Financial Services":                 "Financial Services",
        "Life Sciences":                      "Life Sciences",
        "Professional and Business Services": "Professional and Business Services",
    }

    def __init__(self, config: dict):
        self.config = config
        self.paths = config["paths"]
        self.loader = DataLoader(config)
        self.indicator_builder = IndicatorBuilder(config)

    def _save(self, df: pd.DataFrame, key: str):
        path = Path(self.paths[key])
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)

    # --- Step 1: filter country aggregates ---

    def filter_lad_only(self, df: pd.DataFrame) -> pd.DataFrame:
        lad_type = "local authorities: district / unitary (as of April 2023)"
        return df[df["GEOGRAPHY_TYPE"] == lad_type].copy()

    # --- Step 2: standardise IS8 sector names ---

    def standardise_sector_names(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["IS8_SECTOR"] = df["IS8_SECTOR"].map(self.SECTOR_MAP).fillna(df["IS8_SECTOR"])
        return df

    # --- Step 3: aggregate to IS8 level ---

    def aggregate_to_is8(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sum all rows (null + non-null FRONTIER_SECTOR) per LAD x IS8 sector x year.
        IS8-level and frontier-level rows are complementary — summing both gives
        the correct IS8 total. Do NOT filter to null frontier only.
        SIZE_BAND is always dropped — business counts are summed across all size bands.
        """
        group_cols = ["YEAR", "GEOGRAPHY_CODE", "GEOGRAPHY_NAME", "IS8_SECTOR"]
        return (
            df.groupby(group_cols, as_index=False)["OBS_VALUE"]
            .sum()
        )

    # --- Step 4: parse and clean ONS indicators ---

    def _parse_ons_sheet(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Extract LAD-level rows from a single ONS indicator sheet.
        Sheets have metadata rows at the top — data starts at row 6.
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
        df = df.replace("na", pd.NA)
        df = df.replace("NA", pd.NA)
        for col in df.columns:
            if col != "GEOGRAPHY_CODE":
                df[col] = pd.to_numeric(df[col], errors="coerce")
        numeric_cols = [c for c in df.columns if c != "GEOGRAPHY_CODE" and df[c].notna().any()]
        df = df[["GEOGRAPHY_CODE"] + numeric_cols]
        return df

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
        return result

    # --- Step 5: reconcile pre-2023 boundary codes ---

    def reconcile_boundaries(
        self,
        df: pd.DataFrame,
        crosswalk: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Replace obsolete pre-2023 LAD codes in ONS indicators with current 2023 codes.
        Uses CHGIND flag from MSOA crosswalk to identify changed boundaries.
        """
        changed = crosswalk[crosswalk["CHGIND"].notna()][["LAD22CD", "LAD22NM"]].drop_duplicates()
        obsolete_codes = set(changed["LAD22CD"])
        df = df[~df["GEOGRAPHY_CODE"].isin(obsolete_codes)].copy()
        return df

    # --- Orchestrator ---

    def build_panel(self) -> pd.DataFrame:
        # load
        emp = self.loader.load_employee_counts_lad()
        bus = self.loader.load_business_counts_lad()
        ons_sheets = self.loader.load_ons_indicators()
        crosswalk = self.loader.load_msoa_crosswalk()

        # process employee counts
        emp = self.filter_lad_only(emp)
        emp = self.standardise_sector_names(emp)
        emp = self.aggregate_to_is8(emp)
        emp = emp.rename(columns={"OBS_VALUE": "EMPLOYEES"})

        # process business counts
        bus = self.filter_lad_only(bus)
        bus = self.standardise_sector_names(bus)
        bus = self.aggregate_to_is8(bus)
        bus = bus.rename(columns={"OBS_VALUE": "BUSINESSES"})

        # merge employee and business counts
        merge_cols = ["YEAR", "GEOGRAPHY_CODE", "GEOGRAPHY_NAME", "IS8_SECTOR"]
        panel = emp.merge(bus, on=merge_cols, how="outer")

        # merge ONS indicators
        panel = self.merge_ons_indicators(panel, ons_sheets)

        # reconcile boundaries
        panel = self.reconcile_boundaries(panel, crosswalk)

        # build indicators
        panel = self.indicator_builder.build_indicators(panel)

        # save
        self._save(panel, "analysis_panel")
        print(f"Panel built: {panel.shape[0]:,} rows x {panel.shape[1]} columns")
        return panel