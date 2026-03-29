import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats


class IndicatorBuilder:

    def __init__(self, config: dict):
        self.config = config
        self.params = config["parameters"]

    def _load_national_totals(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Load national employment and business totals per IS8 sector per year.
        Benchmark geography is driven by config:
          england_only: true  → England aggregate row
          england_only: false → Great Britain aggregate row
        """
        emp_path = Path(__file__).resolve().parent.parent / self.config["paths"]["employee_counts_lad"]
        bus_path = Path(__file__).resolve().parent.parent / self.config["paths"]["business_counts_lad"]
        sector_map = self.params["sector_map"]
        y0 = self.params["growth_start_year_emp"]
        y1 = self.params["growth_end_year"]
        benchmark = "England" if self.params.get("england_only", False) else "Great Britain"

        # employment nationals
        emp = pd.read_parquet(emp_path)
        emp["IS8_SECTOR"] = emp["IS8_SECTOR"].map(sector_map).fillna(emp["IS8_SECTOR"])
        emp = emp[(emp["GEOGRAPHY_NAME"] == benchmark) & (emp["YEAR"] >= y0) & (emp["YEAR"] <= y1)]
        emp = emp.groupby(["YEAR", "IS8_SECTOR"], as_index=False)["OBS_VALUE"].sum()
        nat_emp_is8 = emp[emp["IS8_SECTOR"] != "Total"].rename(columns={"OBS_VALUE": "NAT_IS8_EMP"})
        nat_emp_total = emp[emp["IS8_SECTOR"] == "Total"][["YEAR", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "NAT_TOTAL_EMP"})

        # business nationals — load once, reused by both LQ and GD
        bus = pd.read_parquet(bus_path)
        bus["IS8_SECTOR"] = bus["IS8_SECTOR"].map(sector_map).fillna(bus["IS8_SECTOR"])
        bus = bus[(bus["GEOGRAPHY_NAME"] == benchmark) & (bus["YEAR"] >= y0) & (bus["YEAR"] <= y1)]
        bus = bus.groupby(["YEAR", "IS8_SECTOR"], as_index=False)["OBS_VALUE"].sum()
        nat_bus_is8 = bus[bus["IS8_SECTOR"] != "Total"].rename(columns={"OBS_VALUE": "NAT_IS8_BUS"})
        nat_bus_total = bus[bus["IS8_SECTOR"] == "Total"][["YEAR", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "NAT_TOTAL_BUS"})

        print(f"[_load_national_totals] benchmark geography: {benchmark}")
        return nat_emp_is8, nat_emp_total, nat_bus_is8, nat_bus_total

    def _load_raw_business_counts(self) -> pd.DataFrame:
        """
        Load and filter raw business counts to LAD level and configured year range.
        Called once and reused by compute_within_sector_diversity() and
        compute_size_distribution() to avoid repeated file reads.
        """
        path = Path(__file__).resolve().parent.parent / self.config["paths"]["business_counts_lad"]
        bus_raw = pd.read_parquet(path)
        bus_raw["IS8_SECTOR"] = bus_raw["IS8_SECTOR"].map(
            self.params["sector_map"]
        ).fillna(bus_raw["IS8_SECTOR"])
        lad_type = "local authorities: district / unitary (as of April 2023)"
        y0 = self.params["growth_start_year_bus"]
        y1 = self.params["growth_end_year"]
        bus_raw = bus_raw[bus_raw["GEOGRAPHY_TYPE"] == lad_type].copy()
        bus_raw = bus_raw[(bus_raw["YEAR"] >= y0) & (bus_raw["YEAR"] <= y1)]
        return bus_raw

    # --- Location Quotient (employment) ---

    def compute_location_quotient(self, df: pd.DataFrame, nat_emp_is8: pd.DataFrame, nat_emp_total: pd.DataFrame) -> pd.DataFrame:
        """
        lq_emp = (IS8 emp in LAD / total emp in LAD) /
                 (IS8 emp nationally / total emp nationally)
        Total rows are consumed here and removed from output.
        """
        df = df.copy()
        total = (
            df[df["IS8_SECTOR"] == "Total"]
            [["YEAR", "GEOGRAPHY_CODE", "EMPLOYEES"]]
            .rename(columns={"EMPLOYEES": "TOTAL_EMP"})
        )
        df = df[df["IS8_SECTOR"] != "Total"].copy()
        df = df.merge(total, on=["YEAR", "GEOGRAPHY_CODE"], how="left")
        df = df.merge(nat_emp_is8[["YEAR", "IS8_SECTOR", "NAT_IS8_EMP"]], on=["YEAR", "IS8_SECTOR"], how="left")
        df = df.merge(nat_emp_total, on="YEAR", how="left")
        df["lq_emp"] = (df["EMPLOYEES"] / df["TOTAL_EMP"]) / (df["NAT_IS8_EMP"] / df["NAT_TOTAL_EMP"])
        df = df.drop(columns=["TOTAL_EMP", "NAT_IS8_EMP", "NAT_TOTAL_EMP"])
        return df

    # --- Location Quotient (business count) ---

    def compute_lq_bus(self, df: pd.DataFrame, nat_bus_is8: pd.DataFrame, nat_bus_total: pd.DataFrame) -> pd.DataFrame:
        """
        lq_bus = (IS8 businesses in LAD / total businesses in LAD) /
                 (IS8 businesses nationally / total businesses nationally)
        """
        df = df.copy()
        total = (
            df[df["IS8_SECTOR"] == "Total"]
            [["YEAR", "GEOGRAPHY_CODE", "BUSINESSES"]]
            .rename(columns={"BUSINESSES": "TOTAL_BUS"})
        )
        df = df.merge(total, on=["YEAR", "GEOGRAPHY_CODE"], how="left")
        df = df.merge(nat_bus_is8[["YEAR", "IS8_SECTOR", "NAT_IS8_BUS"]], on=["YEAR", "IS8_SECTOR"], how="left")
        df = df.merge(nat_bus_total, on="YEAR", how="left")
        df["lq_bus"] = (df["BUSINESSES"] / df["TOTAL_BUS"]) / (df["NAT_IS8_BUS"] / df["NAT_TOTAL_BUS"])
        df = df.drop(columns=["TOTAL_BUS", "NAT_IS8_BUS", "NAT_TOTAL_BUS"])
        return df

    # --- Employment share ---

    def compute_employment_share(self, df: pd.DataFrame) -> pd.DataFrame:
        """IS8 employment as share of total LAD employment."""
        df = df.copy()
        total = (
            df[df["IS8_SECTOR"] == "Total"]
            [["YEAR", "GEOGRAPHY_CODE", "EMPLOYEES"]]
            .rename(columns={"EMPLOYEES": "TOTAL_EMP"})
        )
        df = df.merge(total, on=["YEAR", "GEOGRAPHY_CODE"], how="left")
        df["emp_share"] = df["EMPLOYEES"] / df["TOTAL_EMP"]
        df = df.drop(columns=["TOTAL_EMP"])
        return df

    # --- Growth Differential ---

    def _ols_slope(self, years: np.ndarray, values: np.ndarray) -> float:
        """
        Fit log-linear OLS: log(values) ~ years.
        Returns slope coefficient (log points per year ≈ % per year).
        Returns NaN if fewer than 4 valid (non-zero, finite) observations.
        """
        mask = (values > 0) & np.isfinite(values)
        x, y = years[mask], values[mask]
        if len(x) < 4:
            return np.nan
        slope, _, _, _, _ = stats.linregress(x, np.log(y))
        return slope

    def _compute_national_slopes(self, nat_df: pd.DataFrame, value_col: str) -> dict:
        """
        Compute national log-linear OLS slope per IS8 sector.
        Returns dict: {sector: beta_national}
        beta_national is fixed across all LADs for a given sector x dimension.
        """
        slopes = {}
        for sector, grp in nat_df.groupby("IS8_SECTOR"):
            grp = grp.sort_values("YEAR")
            slopes[sector] = self._ols_slope(grp["YEAR"].values, grp[value_col].values)
        return slopes

    def compute_growth_differential(
        self,
        df: pd.DataFrame,
        nat_emp_is8: pd.DataFrame,
        nat_bus_is8: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Growth Differential (GD) = β_LAD − β_national

        β estimated via log-linear OLS: log(y_t) ~ α + β·t
        β_national is a single fixed value per sector × dimension,
        computed from the full national time series.

        gd_emp: employment growth differential
        gd_bus: business count growth differential

        Positive GD → LAD growing faster than national trend
        Negative GD → LAD growing slower (or declining faster)
        Units: log points per year ≈ percentage points per year

        n_years_emp / n_years_bus: number of valid observations used
        in LAD slope estimate. Estimates based on < 4 years → NaN.

        Edge case: national β = 0 → GD undefined, set to NaN.
        """
        df = df.copy()

        nat_slopes_emp = self._compute_national_slopes(nat_emp_is8, "NAT_IS8_EMP")
        nat_slopes_bus = self._compute_national_slopes(nat_bus_is8, "NAT_IS8_BUS")

        records = []
        for (geo, sector), grp in df.groupby(["GEOGRAPHY_CODE", "IS8_SECTOR"]):
            grp = grp.sort_values("YEAR")
            years = grp["YEAR"].values

            beta_emp = self._ols_slope(years, grp["EMPLOYEES"].values)
            beta_bus = self._ols_slope(years, grp["BUSINESSES"].values)

            nat_beta_emp = nat_slopes_emp.get(sector, np.nan)
            nat_beta_bus = nat_slopes_bus.get(sector, np.nan)

            gd_emp = (beta_emp - nat_beta_emp
                      if (not np.isnan(nat_beta_emp) and nat_beta_emp != 0)
                      else np.nan)
            gd_bus = (beta_bus - nat_beta_bus
                      if (not np.isnan(nat_beta_bus) and nat_beta_bus != 0)
                      else np.nan)

            n_emp = int(np.sum((grp["EMPLOYEES"].values > 0) & np.isfinite(grp["EMPLOYEES"].values)))
            n_bus = int(np.sum((grp["BUSINESSES"].values > 0) & np.isfinite(grp["BUSINESSES"].values)))

            records.append({
                "GEOGRAPHY_CODE": geo,
                "IS8_SECTOR": sector,
                "gd_emp": gd_emp,
                "gd_bus": gd_bus,
                "n_years_emp": n_emp,
                "n_years_bus": n_bus,
            })

        gd = pd.DataFrame(records)
        df = df.merge(gd, on=["GEOGRAPHY_CODE", "IS8_SECTOR"], how="left")
        return df

    # --- Related variety (cross-sector, EEG approximation) ---

    def compute_related_variety(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cross-sector Shannon entropy per LAD x year.

        EEG related variety: measures how diversified a LAD's business base
        is across IS8 sectors. Higher entropy = more evenly spread across
        sectors = more adjacent industries available for capability spillovers.

        Computed directly from panel (post-Total-row removal) using BUSINESSES.
        This is an approximation of the EEG concept — true related variety
        requires SIC-level technological proximity weights.

        Result is LAD x year level (same value replicated across all sectors
        within a LAD x year).
        """
        df = df.copy()

        sector_tots = (
            df.groupby(["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"], as_index=False)["BUSINESSES"]
            .sum()
        )
        lad_tots = (
            sector_tots.groupby(["YEAR", "GEOGRAPHY_CODE"], as_index=False)["BUSINESSES"]
            .sum()
            .rename(columns={"BUSINESSES": "LAD_TOTAL"})
        )
        sector_tots = sector_tots.merge(lad_tots, on=["YEAR", "GEOGRAPHY_CODE"])
        sector_tots["p"] = (sector_tots["BUSINESSES"] / sector_tots["LAD_TOTAL"].replace(0, pd.NA)).fillna(0).astype(float)
        sector_tots["entropy"] = np.where(
            sector_tots["p"] > 0,
            -sector_tots["p"] * np.log(sector_tots["p"]),
            0
        )
        rv = (
            sector_tots.groupby(["YEAR", "GEOGRAPHY_CODE"], as_index=False)["entropy"]
            .sum()
            .rename(columns={"entropy": "related_variety"})
        )
        df = df.merge(rv, on=["YEAR", "GEOGRAPHY_CODE"], how="left")
        return df

    # --- Within-sector diversity ---

    def compute_within_sector_diversity(self, df: pd.DataFrame, bus_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Within-sector Shannon entropy per LAD x IS8 sector x year.

        Measures internal SIC diversity within each IS8 sector per LAD.
        Higher entropy = businesses spread across more SIC codes within sector.
        Complements related_variety — captures sectoral complexity rather than
        cross-sector diversification.

        0·log(0) = 0 by convention (standard Shannon entropy treatment).

        bus_raw: pre-loaded raw business counts (passed from build_indicators
                 to avoid repeated file reads).
        """
        group_cols = ["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR", "INDUSTRY_CODE"]
        bus_sic = bus_raw.groupby(group_cols, as_index=False)["OBS_VALUE"].sum()

        sector_total = (
            bus_sic.groupby(["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"], as_index=False)["OBS_VALUE"]
            .sum()
            .rename(columns={"OBS_VALUE": "SECTOR_TOTAL"})
        )
        bus_sic = bus_sic.merge(sector_total, on=["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"], how="left")
        bus_sic["p"] = (bus_sic["OBS_VALUE"] / bus_sic["SECTOR_TOTAL"].replace(0, pd.NA)).fillna(0).astype(float)
        bus_sic["entropy"] = np.where(
            bus_sic["p"] > 0,
            -bus_sic["p"] * np.log(bus_sic["p"]),
            0
        )

        wsd = (
            bus_sic.groupby(["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"], as_index=False)["entropy"]
            .sum()
            .rename(columns={"entropy": "within_sector_diversity"})
        )
        wsd["GEOGRAPHY_CODE"] = wsd["GEOGRAPHY_CODE"].astype(str)
        df = df.merge(wsd, on=["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"], how="left")
        return df

    # --- Size distribution ---

    def compute_size_distribution(self, df: pd.DataFrame, bus_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Share of micro and large businesses per LAD x IS8 sector x year.

        bus_raw: pre-loaded raw business counts (passed from build_indicators
                 to avoid repeated file reads).
        """
        group_cols = ["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR", "SIZE_BAND"]
        bus = bus_raw.groupby(group_cols, as_index=False)["OBS_VALUE"].sum()

        bus_pivot = bus.pivot_table(
            index=["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"],
            columns="SIZE_BAND",
            values="OBS_VALUE",
            aggfunc="sum"
        ).reset_index()
        bus_pivot.columns.name = None

        size_cols = ["large", "medium", "micro", "small"]
        bus_pivot["total_bus"] = bus_pivot[size_cols].sum(axis=1)
        bus_pivot["size_large_share"] = bus_pivot["large"] / bus_pivot["total_bus"].replace(0, pd.NA)
        bus_pivot["size_micro_share"] = bus_pivot["micro"] / bus_pivot["total_bus"].replace(0, pd.NA)

        keep = ["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR", "size_large_share", "size_micro_share"]
        bus_pivot["GEOGRAPHY_CODE"] = bus_pivot["GEOGRAPHY_CODE"].astype(str)
        df = df.merge(bus_pivot[keep], on=["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"], how="left")
        return df

    # --- Orchestrator ---

    def build_indicators(self, panel: pd.DataFrame) -> pd.DataFrame:
        df = panel.copy()

        # load national totals once — used by LQ and GD methods
        nat_emp_is8, nat_emp_total, nat_bus_is8, nat_bus_total = self._load_national_totals()

        # load raw business counts once — used by within_sector_diversity and size_distribution
        bus_raw = self._load_raw_business_counts()

        # LQ and emp_share need Total rows — compute before removing them
        df = self.compute_lq_bus(df, nat_bus_is8, nat_bus_total)
        df = self.compute_employment_share(df)
        df = self.compute_location_quotient(df, nat_emp_is8, nat_emp_total)

        # remove Total rows — all subsequent methods operate at IS8 sector level
        df = df[df["IS8_SECTOR"] != "Total"].copy()

        # growth differential
        df = self.compute_growth_differential(df, nat_emp_is8, nat_bus_is8)

        # diversity measures
        df = self.compute_related_variety(df)
        df = self.compute_within_sector_diversity(df, bus_raw)

        # firm structure
        df = self.compute_size_distribution(df, bus_raw)

        print(f"Indicators built: {df.shape[0]:,} rows x {df.shape[1]} columns")
        return df