import pandas as pd
import numpy as np
from pathlib import Path
from src.loader import DataLoader
from src.processor import DataProcessor


class IndicatorBuilder:

    def __init__(self, config: dict):
        self.config = config
        self.paths = config["paths"]
        self.params = config["parameters"]

    def _save(self, df: pd.DataFrame, key: str):
        path = Path(self.paths[key])
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)

    # --- Location Quotient ---

    def compute_location_quotient(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        LQ = (IS8 emp in LAD / total emp in LAD) /
             (IS8 emp nationally / total emp nationally)
        Computed per LAD x IS8 sector x year.
        Uses EMPLOYEES column. Total employment derived from IS8_SECTOR == 'Total'.
        """
        df = df.copy()

        total = (
            df[df["IS8_SECTOR"] == "Total"]
            [["YEAR", "GEOGRAPHY_CODE", "EMPLOYEES"]]
            .rename(columns={"EMPLOYEES": "TOTAL_EMP"})
        )

        national = (
            df[df["IS8_SECTOR"] != "Total"]
            .groupby(["YEAR", "IS8_SECTOR"], as_index=False)["EMPLOYEES"]
            .sum()
            .rename(columns={"EMPLOYEES": "NAT_IS8_EMP"})
        )

        nat_total = (
            df[df["IS8_SECTOR"] == "Total"]
            .groupby("YEAR", as_index=False)["EMPLOYEES"]
            .sum()
            .rename(columns={"EMPLOYEES": "NAT_TOTAL_EMP"})
        )

        df = df[df["IS8_SECTOR"] != "Total"].copy()
        df = df.merge(total, on=["YEAR", "GEOGRAPHY_CODE"], how="left")
        df = df.merge(national, on=["YEAR", "IS8_SECTOR"], how="left")
        df = df.merge(nat_total, on="YEAR", how="left")

        df["lq_emp"] = (
            (df["EMPLOYEES"] / df["TOTAL_EMP"]) /
            (df["NAT_IS8_EMP"] / df["NAT_TOTAL_EMP"])
        )
        df = df.drop(columns=["TOTAL_EMP", "NAT_IS8_EMP", "NAT_TOTAL_EMP"])
        return df

    # --- Business count LQ ---

    def compute_lq_bus(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        LQ = (IS8 businesses in LAD / total businesses in LAD) /
             (IS8 businesses nationally / total businesses nationally)
        Computed per LAD x IS8 sector x year.
        Uses BUSINESSES column. Total businesses derived from IS8_SECTOR == 'Total'.
        """
        df = df.copy()

        total = (
            df[df["IS8_SECTOR"] == "Total"]
            [["YEAR", "GEOGRAPHY_CODE", "BUSINESSES"]]
            .rename(columns={"BUSINESSES": "TOTAL_BUS"})
        )

        national = (
            df[df["IS8_SECTOR"] != "Total"]
            .groupby(["YEAR", "IS8_SECTOR"], as_index=False)["BUSINESSES"]
            .sum()
            .rename(columns={"BUSINESSES": "NAT_IS8_BUS"})
        )

        nat_total = (
            df[df["IS8_SECTOR"] == "Total"]
            .groupby("YEAR", as_index=False)["BUSINESSES"]
            .sum()
            .rename(columns={"BUSINESSES": "NAT_TOTAL_BUS"})
        )

        df = df.merge(total, on=["YEAR", "GEOGRAPHY_CODE"], how="left")
        df = df.merge(national, on=["YEAR", "IS8_SECTOR"], how="left")
        df = df.merge(nat_total, on="YEAR", how="left")

        df["lq_bus"] = (
            (df["BUSINESSES"] / df["TOTAL_BUS"]) /
            (df["NAT_IS8_BUS"] / df["NAT_TOTAL_BUS"])
        )
        df = df.drop(columns=["TOTAL_BUS", "NAT_IS8_BUS", "NAT_TOTAL_BUS"])
        return df

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

    def compute_growth_rates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes point-to-point growth and CAGR for employment and business counts.
        Uses separate start years for employment and business counts from config.
        """
        df = df.copy()
        y0_emp = self.params["growth_start_year_emp"]
        y0_bus = self.params["growth_start_year_bus"]
        y1 = self.params["growth_end_year"]

        # employment growth
        emp_base = df[df["YEAR"] == y0_emp][
            ["GEOGRAPHY_CODE", "IS8_SECTOR", "EMPLOYEES"]
        ].rename(columns={"EMPLOYEES": "EMP_START"})
        emp_end = df[df["YEAR"] == y1][
            ["GEOGRAPHY_CODE", "IS8_SECTOR", "EMPLOYEES"]
        ].rename(columns={"EMPLOYEES": "EMP_END"})
        emp_growth = emp_base.merge(emp_end, on=["GEOGRAPHY_CODE", "IS8_SECTOR"], how="inner")
        n_emp = y1 - y0_emp
        emp_growth["growth_emp"] = (emp_growth["EMP_END"] - emp_growth["EMP_START"]) / emp_growth["EMP_START"]
        emp_growth["cagr_emp"] = (emp_growth["EMP_END"] / emp_growth["EMP_START"]) ** (1 / n_emp) - 1
        emp_growth = emp_growth.drop(columns=["EMP_START", "EMP_END"])

        # business count growth
        bus_base = df[df["YEAR"] == y0_bus][
            ["GEOGRAPHY_CODE", "IS8_SECTOR", "BUSINESSES"]
        ].rename(columns={"BUSINESSES": "BUS_START"})
        bus_end = df[df["YEAR"] == y1][
            ["GEOGRAPHY_CODE", "IS8_SECTOR", "BUSINESSES"]
        ].rename(columns={"BUSINESSES": "BUS_END"})
        bus_growth = bus_base.merge(bus_end, on=["GEOGRAPHY_CODE", "IS8_SECTOR"], how="inner")
        n_bus = y1 - y0_bus
        bus_growth["growth_bus"] = (bus_growth["BUS_END"] - bus_growth["BUS_START"]) / bus_growth["BUS_START"]
        bus_growth["cagr_bus"] = (bus_growth["BUS_END"] / bus_growth["BUS_START"]) ** (1 / n_bus) - 1
        bus_growth = bus_growth.drop(columns=["BUS_START", "BUS_END"])

        df = df.merge(emp_growth, on=["GEOGRAPHY_CODE", "IS8_SECTOR"], how="left")
        df = df.merge(bus_growth, on=["GEOGRAPHY_CODE", "IS8_SECTOR"], how="left")
        return df

    # --- Business density ---

    def compute_business_density(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        IS8 businesses per 1,000 working-age population.
        Requires working-age population column from ONS indicators.
        Column name TBC after ONS sheet parsing — placeholder uses 'working_age_pop'.
        """
        df = df.copy()
        if "working_age_pop" not in df.columns:
            df["business_density"] = np.nan
            return df
        df["business_density"] = df["BUSINESSES"] / (df["working_age_pop"] / 1000)
        return df

    # --- Related variety (placeholder) ---

    def compute_related_variety(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        SIC adjacency-based relatedness index per LAD.
        To be implemented in Step 6 after SIC adjacency approach is finalised.
        See Open Questions in workplan.
        """
        df = df.copy()
        df["related_variety"] = np.nan
        return df

    # --- Size distribution (placeholder) ---

    def compute_size_distribution(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Firm size distribution per LAD x IS8 sector.
        Requires SIZE_BAND data from business counts.
        To be implemented in Step 6.
        """
        df = df.copy()
        df["size_large_share"] = np.nan
        df["size_micro_share"] = np.nan
        return df

    # --- Orchestrator ---

    def build_indicators(self, panel: pd.DataFrame) -> pd.DataFrame:
        df = panel.copy()
        # both emp_share and lq_emp need Total rows — compute before removing them
        df = self.compute_lq_bus(df)
        df = self.compute_employment_share(df)
        df = self.compute_location_quotient(df)
        # now remove Total rows
        df = df[df["IS8_SECTOR"] != "Total"].copy()
        df = self.compute_growth_rates(df)
        df = self.compute_business_density(df)
        df = self.compute_related_variety(df)
        df = self.compute_size_distribution(df)
        self._save(df, "indicators_panel")
        print(f"Indicators built: {df.shape[0]:,} rows x {df.shape[1]} columns")
        return df