import re
import pandas as pd
from pathlib import Path
from src.loader import DataLoader
from src.indicators import IndicatorBuilder
from src.regions import RegionMapper


class DataProcessor:

    # Repeated geographic label columns in ONS file — keep first, drop rest
    GEO_LABEL_PATTERNS = [
        "county or unitary authority",
        "region",
        "nation",
        "country",
    ]

    # Count variables — should be summed when aggregating merged LADs
    # All other variables are treated as rates/percentages and averaged
    # Note: enterprise counts are normalised to rates in compute_enterprise_rates()
    # and are no longer present as raw counts in the final panel
    COUNT_VARIABLES = {
        "housing_net_additions",
    }

    def __init__(self, config: dict):
        self.config = config
        self.paths = config["paths"]
        self.params = config["parameters"]
        self.loader = DataLoader(config)
        self.indicator_builder = IndicatorBuilder(config)
        # 0 = keep obsolete LADs as-is (no reconciliation)
        # 1 = drop obsolete LADs (default, safe)
        # 2 = remap and aggregate using simple mean/sum
        self.boundary_approach = self.params.get("boundary_approach", 1)

    def _save(self, df: pd.DataFrame, key: str):
        path = Path(__file__).resolve().parent.parent / self.paths[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)

    # --- Step 1: filter to LAD geography only ---

    def filter_lad_only(self, df: pd.DataFrame) -> pd.DataFrame:
        lad_type = "local authorities: district / unitary (as of April 2023)"
        return df[df["GEOGRAPHY_TYPE"] == lad_type].copy()

    # --- Step 2: filter to year range ---

    def filter_years(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only configured year range (growth_start_year to growth_end_year)."""
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

    def _parse_ons_sheet(self, df_raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        """
        Extract LAD-level rows from a single ONS indicator sheet.
        Also extracts obsolete code → new code mappings from Notes column.
        Returns (parsed_df, code_map_fragment).
        """
        df = df_raw.copy()
        df.columns = range(df.shape[1])
        header_row = None
        for i, row in df.iterrows():
            if any("Area Code" in str(v) for v in row.values):
                header_row = i
                break
        if header_row is None:
            return pd.DataFrame(), {}

        df.columns = df.iloc[header_row]
        df = df.iloc[header_row + 1:].reset_index(drop=True)
        df = df.rename(columns={df.columns[0]: "GEOGRAPHY_CODE"})

        # restrict to LAD-level codes only (E06, E07, E08, E09 prefixes)
        df = df[df["GEOGRAPHY_CODE"].astype(str).str.match(r"^E0[6-9]\d{6}$")]

        df = df.replace("na", pd.NA).replace("NA", pd.NA)

        # extract obsolete code mappings from Notes column if present
        code_map = {}
        pattern = re.compile(r"replaced by ([EWS]\d{8})")
        notes_col = next((c for c in df.columns if str(c).strip().lower() == "notes"), None)
        if notes_col is not None:
            for _, row in df.iterrows():
                match = pattern.search(str(row.get(notes_col, "")))
                if match:
                    old_code = str(row["GEOGRAPHY_CODE"]).strip()
                    code_map[old_code] = match.group(1)

        for col in df.columns:
            if col != "GEOGRAPHY_CODE":
                df[col] = pd.to_numeric(df[col], errors="coerce")

        numeric_cols = [c for c in df.columns if c != "GEOGRAPHY_CODE" and df[c].notna().any()]
        return df[["GEOGRAPHY_CODE"] + numeric_cols], code_map

    def _dedup_geo_label_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        The ONS file repeats geographic label columns once per indicator sheet.
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

    # --- Step 7: merge ONS indicators ---

    def merge_ons_indicators(
        self,
        panel: pd.DataFrame,
        ons_sheets: dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Parse and merge all ONS indicator sheets onto the panel.
        Boundary remapping is applied to each ONS sheet before merging,
        so obsolete codes are resolved to LAD23 codes at join time.
        Two-pass approach:
          Pass 1 — collect full code_map across all sheets
          Pass 2 — remap each sheet and merge onto panel

        Boundary reconciliation approaches (controlled by boundary_approach):
          0 = keep obsolete codes as-is (no reconciliation)
          1 = drop rows with obsolete codes
          2 = remap obsolete codes and aggregate (mean for rates, sum for counts)
        """
        # pass 1: build full code_map
        full_code_map = {}
        parsed = {}
        for sheet_name, df_raw in ons_sheets.items():
            df, code_map = self._parse_ons_sheet(df_raw)
            full_code_map.update(code_map)
            parsed[sheet_name] = df
        print(f"[merge_ons_indicators] {len(full_code_map)} obsolete codes identified across sheets")

        # pass 2: remap and merge
        result = panel.copy()
        for sheet_name, df in parsed.items():
            if df.empty or len(df.columns) < 2:
                continue

            col_name = sheet_name.lower().replace(" ", "_").replace("&", "and")
            val_cols = [c for c in df.columns if c != "GEOGRAPHY_CODE"]
            if not val_cols:
                continue

            df = df[["GEOGRAPHY_CODE", val_cols[0]]].copy()
            df = df.rename(columns={val_cols[0]: col_name})
            df["GEOGRAPHY_CODE"] = df["GEOGRAPHY_CODE"].astype(str)

            if self.boundary_approach == 2:
                df["GEOGRAPHY_CODE"] = df["GEOGRAPHY_CODE"].replace(full_code_map)
                df = df.groupby("GEOGRAPHY_CODE", as_index=False)[col_name].mean()
            elif self.boundary_approach == 1:
                df = df[~df["GEOGRAPHY_CODE"].isin(full_code_map.keys())]

            result = result.merge(df, on="GEOGRAPHY_CODE", how="left")

        result = self._dedup_geo_label_columns(result)
        result = result.dropna(axis=1, how="all")
        return result

    # --- Step 8: compute enterprise rates ---

    def compute_enterprise_rates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalise enterprise dynamics by active enterprise stock to remove
        LAD size effect and produce theoretically meaningful churn rates.

        enterprise_birth_rate       = enterprise_births / enterprise_active
        enterprise_death_rate       = enterprise_deaths / enterprise_active
        enterprise_high_growth_rate = enterprise_high_growth / enterprise_active

        enterprise_active is then dropped after normalisation.
        Raw counts (births, deaths, high_growth) are dropped after rate computation.
        """
        df = df.copy()
        stock = df["enterprise_active"].replace(0, pd.NA)
        df["enterprise_birth_rate"]       = df["enterprise_births"]      / stock
        df["enterprise_death_rate"]       = df["enterprise_deaths"]      / stock
        df["enterprise_high_growth_rate"] = df["enterprise_high_growth"] / stock
        df = df.drop(columns=[
            "enterprise_births", "enterprise_deaths",
            "enterprise_high_growth", "enterprise_active"
        ])
        return df

    # --- Step 9: filter to England-only LADs ---

    def filter_england_only(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Restrict panel to English LADs only (GEOGRAPHY_CODE starting with 'E').
        Removes Scottish (S12) and Welsh (W06) LADs whose ONS indicator
        coverage is partial or absent for England-focused variables.
        Controlled by england_only parameter in config.
        """
        n_before = df["GEOGRAPHY_CODE"].nunique()
        df = df[df["GEOGRAPHY_CODE"].astype(str).str.startswith("E")].copy()
        n_after = df["GEOGRAPHY_CODE"].nunique()
        print(f"[filter_england_only] {n_before - n_after} non-England LADs removed, "
              f"{n_after} English LADs retained")
        return df

    # --- Step 10: rename and filter ONS columns to codebook names ---

    def apply_ons_column_map(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename ONS-derived columns to codebook variable names and drop
        all columns not in the ons_column_map. Excluded variables
        (reverse causality, wrong geography, etc.) are dropped here.
        """
        col_map = self.params["ons_column_map"]
        panel_key_cols = ["YEAR", "GEOGRAPHY_CODE", "GEOGRAPHY_NAME", "IS8_SECTOR",
                          "EMPLOYEES", "BUSINESSES"]

        df = df.rename(columns=col_map)

        retained_ons = list(col_map.values())
        keep_cols = [c for c in df.columns if c in panel_key_cols or c in retained_ons]
        dropped = [c for c in df.columns if c not in keep_cols]
        if dropped:
            print(f"[apply_ons_column_map] dropped {len(dropped)} excluded columns: {dropped}")
        return df[keep_cols]

    # --- Orchestrator ---

    def build_panel(self) -> pd.DataFrame:
        # load
        emp = self.loader.load_employee_counts_lad()
        bus = self.loader.load_business_counts_lad()
        ons_sheets = self.loader.load_ons_indicators()

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
        assert len(panel) == len(emp) == len(bus), \
            f"Unexpected row loss on inner join: emp={len(emp)}, bus={len(bus)}, panel={len(panel)}"

        # merge ONS indicators with boundary remap applied per sheet
        panel = self.merge_ons_indicators(panel, ons_sheets)

        # filter to England-only LADs (optional — controlled by config)
        if self.params.get("england_only", False):
            panel = self.filter_england_only(panel)

        # rename retained ONS columns to codebook names, drop excluded columns
        panel = self.apply_ons_column_map(panel)

        # compute enterprise rates (normalise by active stock, drop raw counts)
        panel = self.compute_enterprise_rates(panel)

        # add REGION and COUNTY_UA columns from ONS hierarchy
        region_mapper = RegionMapper(self.config, panel)
        panel = region_mapper.enrich_panel(panel)

        # build indicators (LQ, GD — removes Total rows internally)
        panel = self.indicator_builder.build_indicators(panel)

        # optimise dtypes
        panel = self.optimise_dtypes(panel)

        # save
        self._save(panel, "analysis_panel")
        print(f"Panel built: {panel.shape[0]:,} rows x {panel.shape[1]} columns")
        return panel