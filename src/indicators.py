import pandas as pd
import numpy as np
from pathlib import Path


class IndicatorBuilder:

    def __init__(self, config: dict):
        self.config = config
        self.params = config["parameters"]

    def _load_national_totals(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load GB-level employment and business totals per IS8 sector per year.
        Uses Great Britain country row as the national benchmark for LQ computation.
        """
        emp_path = Path(__file__).resolve().parent.parent / self.config["paths"]["employee_counts_lad"]
        bus_path = Path(__file__).resolve().parent.parent / self.config["paths"]["business_counts_lad"]
        sector_map = self.config["parameters"]["sector_map"]
        y0 = self.params["growth_start_year_emp"]
        y1 = self.params["growth_end_year"]

        # employment nationals
        emp = pd.read_parquet(emp_path)
        emp["IS8_SECTOR"] = emp["IS8_SECTOR"].map(sector_map).fillna(emp["IS8_SECTOR"])
        emp = emp[(emp["GEOGRAPHY_NAME"] == "Great Britain") & (emp["YEAR"] >= y0) & (emp["YEAR"] <= y1)]
        emp = emp.groupby(["YEAR", "IS8_SECTOR"], as_index=False)["OBS_VALUE"].sum()
        nat_emp_is8 = emp[emp["IS8_SECTOR"] != "Total"].rename(columns={"OBS_VALUE": "NAT_IS8_EMP"})
        nat_emp_total = emp[emp["IS8_SECTOR"] == "Total"][["YEAR", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "NAT_TOTAL_EMP"})

        # business nationals
        bus = pd.read_parquet(bus_path)
        bus["IS8_SECTOR"] = bus["IS8_SECTOR"].map(sector_map).fillna(bus["IS8_SECTOR"])
        bus = bus[(bus["GEOGRAPHY_NAME"] == "Great Britain") & (bus["YEAR"] >= y0) & (bus["YEAR"] <= y1)]
        bus = bus.groupby(["YEAR", "IS8_SECTOR"], as_index=False)["OBS_VALUE"].sum()
        nat_bus_is8 = bus[bus["IS8_SECTOR"] != "Total"].rename(columns={"OBS_VALUE": "NAT_IS8_BUS"})
        nat_bus_total = bus[bus["IS8_SECTOR"] == "Total"][["YEAR", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "NAT_TOTAL_BUS"})

        return (nat_emp_is8, nat_emp_total, nat_bus_is8, nat_bus_total)


    def compute_location_quotient(self, df: pd.DataFrame, nat_emp_is8: pd.DataFrame, nat_emp_total: pd.DataFrame) -> pd.DataFrame:
        """
        LQ = (IS8 emp in LAD / total emp in LAD) /
             (IS8 emp in GB / total emp in GB)
        Uses Great Britain country row as national benchmark.
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
        LQ = (IS8 businesses in LAD / total businesses in LAD) /
             (IS8 businesses in GB / total businesses in GB)
        Uses Great Britain country row as national benchmark.
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
        """
        IS8 employment as share of total LAD employment.
        Keeps Total rows intact for use by compute_location_quotient().
        """
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

    # --- Growth rates ---

    def _first_nonzero_base(
        self,
        df: pd.DataFrame,
        value_col: str,
        y0: int,
        y1: int
    ) -> pd.DataFrame:
        """
        For each LAD x IS8 sector, find the first year >= y0 where value_col > 0.
        Returns a dataframe with GEOGRAPHY_CODE, IS8_SECTOR, <value_col>_START, BASE_YEAR.
        Falls back to NaN if no non-zero value exists in [y0, y1-1].
        """
        candidates = (
            df[(df["YEAR"] >= y0) & (df["YEAR"] < y1) & (df[value_col] > 0)]
            .sort_values("YEAR")
            .groupby(["GEOGRAPHY_CODE", "IS8_SECTOR"], as_index=False)
            .first()[["GEOGRAPHY_CODE", "IS8_SECTOR", "YEAR", value_col]]
            .rename(columns={"YEAR": "BASE_YEAR", value_col: f"{value_col}_START"})
        )
        return candidates

    def compute_growth_rates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Log-diff growth from first non-zero year to end year, per LAD x IS8 sector.
        If y0 is zero, walks forward year by year until a non-zero value is found.
        CAGR is annualised using the actual number of years between base and end year.
        """
        df = df.copy()
        y0_emp = self.params["growth_start_year_emp"]
        y0_bus = self.params["growth_start_year_bus"]
        y1 = self.params["growth_end_year"]

        # employment growth
        emp_base = self._first_nonzero_base(df, "EMPLOYEES", y0_emp, y1)
        emp_end = df[df["YEAR"] == y1][
            ["GEOGRAPHY_CODE", "IS8_SECTOR", "EMPLOYEES"]
        ].rename(columns={"EMPLOYEES": "EMPLOYEES_END"})
        emp_growth = emp_base.merge(emp_end, on=["GEOGRAPHY_CODE", "IS8_SECTOR"], how="inner")
        emp_growth["n_emp"] = y1 - emp_growth["BASE_YEAR"]
        emp_growth["growth_emp"] = (emp_growth["EMPLOYEES_END"] - emp_growth["EMPLOYEES_START"]) / emp_growth["EMPLOYEES_START"]
        emp_growth["cagr_emp"] = (emp_growth["EMPLOYEES_END"] / emp_growth["EMPLOYEES_START"]) ** (1 / emp_growth["n_emp"]) - 1
        emp_growth = emp_growth[["GEOGRAPHY_CODE", "IS8_SECTOR", "growth_emp", "cagr_emp"]]

        # business count growth
        bus_base = self._first_nonzero_base(df, "BUSINESSES", y0_bus, y1)
        bus_end = df[df["YEAR"] == y1][
            ["GEOGRAPHY_CODE", "IS8_SECTOR", "BUSINESSES"]
        ].rename(columns={"BUSINESSES": "BUSINESSES_END"})
        bus_growth = bus_base.merge(bus_end, on=["GEOGRAPHY_CODE", "IS8_SECTOR"], how="inner")
        bus_growth["n_bus"] = y1 - bus_growth["BASE_YEAR"]
        bus_growth["growth_bus"] = (bus_growth["BUSINESSES_END"] - bus_growth["BUSINESSES_START"]) / bus_growth["BUSINESSES_START"]
        bus_growth["cagr_bus"] = (bus_growth["BUSINESSES_END"] / bus_growth["BUSINESSES_START"]) ** (1 / bus_growth["n_bus"]) - 1
        bus_growth = bus_growth[["GEOGRAPHY_CODE", "IS8_SECTOR", "growth_bus", "cagr_bus"]]

        df = df.merge(emp_growth, on=["GEOGRAPHY_CODE", "IS8_SECTOR"], how="left")
        df = df.merge(bus_growth, on=["GEOGRAPHY_CODE", "IS8_SECTOR"], how="left")
        return df


    # --- Related variety ---

    def compute_related_variety(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Within-sector SIC entropy per LAD x IS8 sector x year.
        Measures how diversified the IS8 sector is internally across SIC codes.
        Higher entropy = businesses spread across more SIC codes within the sector.
        Uses business counts as weights. Computed from raw business counts directly.
        """
        path = Path(__file__).resolve().parent.parent / self.config["paths"]["business_counts_lad"]
        sic_path = Path(__file__).resolve().parent.parent / self.config["paths"]["sic_lookup"]

        bus_raw = pd.read_parquet(path)
        sic = pd.read_csv(sic_path)

        # standardise sector names
        sector_map = self.config["parameters"]["sector_map"]
        bus_raw["IS8_SECTOR"] = bus_raw["IS8_SECTOR"].map(sector_map).fillna(bus_raw["IS8_SECTOR"])

        # filter to LAD level and year range
        lad_type = "local authorities: district / unitary (as of April 2023)"
        y0 = self.params["growth_start_year_emp"]
        y1 = self.params["growth_end_year"]
        bus_raw = bus_raw[bus_raw["GEOGRAPHY_TYPE"] == lad_type].copy()
        bus_raw = bus_raw[(bus_raw["YEAR"] >= y0) & (bus_raw["YEAR"] <= y1)]

        # aggregate to LAD x IS8 x SIC x year
        group_cols = ["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR", "INDUSTRY_CODE"]
        bus_sic = bus_raw.groupby(group_cols, as_index=False)["OBS_VALUE"].sum()

        # compute within-sector entropy
        sector_total = bus_sic.groupby(
            ["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"], as_index=False
        )["OBS_VALUE"].sum().rename(columns={"OBS_VALUE": "SECTOR_TOTAL"})

        bus_sic = bus_sic.merge(sector_total, on=["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"], how="left")
        bus_sic["p"] = bus_sic["OBS_VALUE"] / bus_sic["SECTOR_TOTAL"].replace(0, pd.NA)
        bus_sic["entropy"] = -bus_sic["p"] * np.log(bus_sic["p"].replace(0, pd.NA))

        related_variety = bus_sic.groupby(
            ["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"], as_index=False
        )["entropy"].sum().rename(columns={"entropy": "related_variety"})

        related_variety["GEOGRAPHY_CODE"] = related_variety["GEOGRAPHY_CODE"].astype(str)
        df = df.merge(related_variety, on=["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"], how="left")
        return df

    # --- Size distribution ---

    def compute_size_distribution(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Share of micro and large businesses out of total businesses per LAD x IS8 sector x year.
        Loads raw business counts directly to access SIZE_BAND before it is aggregated away.
        """
        path = Path(__file__).resolve().parent.parent / self.config["paths"]["business_counts_lad"]
        bus_raw = pd.read_parquet(path)

        # standardise sector names to match panel
        sector_map = self.config["parameters"]["sector_map"]
        bus_raw["IS8_SECTOR"] = bus_raw["IS8_SECTOR"].map(sector_map).fillna(bus_raw["IS8_SECTOR"])

        # filter to LAD level and year range
        lad_type = "local authorities: district / unitary (as of April 2023)"
        y0 = self.params["growth_start_year_emp"]
        y1 = self.params["growth_end_year"]
        bus_raw = bus_raw[bus_raw["GEOGRAPHY_TYPE"] == lad_type].copy()
        bus_raw = bus_raw[(bus_raw["YEAR"] >= y0) & (bus_raw["YEAR"] <= y1)]

        group_cols = ["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR", "SIZE_BAND"]
        bus_raw = bus_raw.groupby(group_cols, as_index=False)["OBS_VALUE"].sum()

        # pivot size bands into columns
        bus_pivot = bus_raw.pivot_table(
            index=["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"],
            columns="SIZE_BAND",
            values="OBS_VALUE",
            aggfunc="sum"
        ).reset_index()
        bus_pivot.columns.name = None

        # compute total and shares
        size_cols = ["large", "medium", "micro", "small"]
        bus_pivot["total_bus"] = bus_pivot[size_cols].sum(axis=1)
        bus_pivot["size_large_share"] = bus_pivot["large"] / bus_pivot["total_bus"].replace(0, pd.NA)
        bus_pivot["size_micro_share"] = bus_pivot["micro"] / bus_pivot["total_bus"].replace(0, pd.NA)

        keep = ["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR", "size_large_share", "size_micro_share"]
        bus_pivot = bus_pivot[keep]
        bus_pivot["GEOGRAPHY_CODE"] = bus_pivot["GEOGRAPHY_CODE"].astype(str)

        df = df.merge(bus_pivot, on=["YEAR", "GEOGRAPHY_CODE", "IS8_SECTOR"], how="left")
        return df

    # --- Orchestrator ---

    def build_indicators(self, panel: pd.DataFrame) -> pd.DataFrame:
        df = panel.copy()
        # both emp_share and lq_emp need Total rows — compute before removing them
        df = self.compute_lq_bus(df)
        df = self.compute_employment_share(df)
        df = self.compute_location_quotient(df)
        # remove Total rows
        df = df[df["IS8_SECTOR"] != "Total"].copy()
        df = self.compute_growth_rates(df)
        df = self.compute_related_variety(df)
        df = self.compute_size_distribution(df)
        print(f"Indicators built: {df.shape[0]:,} rows x {df.shape[1]} columns")
        return df