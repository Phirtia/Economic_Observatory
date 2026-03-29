import re
import time
import requests
import pandas as pd
import geopandas as gpd
from pathlib import Path


class UniversityBuilder:
    """
    Computes n_universities_lad — count of fee-cap registered HE providers
    per LAD, based on physical campus locations from HESA.

    Data sources:
      - HESA campus locations CSV: physical campus postcodes + coordinates
        per provider (one row per campus, multiple rows per provider)
      - OfS register XLSX: official list of registered HE providers with
        registration category (fee-cap vs approved)

    Method:
      1. Load HESA campus locations, filter to England
      2. Load OfS register, filter to fee-cap providers
      3. Spatial join campus coordinates to LAD boundaries
      4. Count distinct fee-cap providers per LAD (UKPRN deduplication)
      5. Return LAD-level count merged onto panel

    Notes:
      - Uses campus coordinates directly — no postcode geocoding needed
      - 7 boundary-edge campuses assigned via nearest-LAD fallback
      - Non-fee-cap providers (small private/online) excluded as they
        contribute minimally to local knowledge spillovers
      - 193 of 296 LADs have at least one fee-cap HE provider
    """

    # OfS registration category for traditional universities
    FEECAP_CATEGORY = "Approved (fee cap)"

    def __init__(self, config: dict):
        self.config = config
        self.base = Path(__file__).resolve().parent.parent

    def _p(self, key: str) -> Path:
        p = self.base / self.config["paths"][key]
        if not p.exists():
            raise FileNotFoundError(f"[UniversityBuilder] File not found for '{key}': {p}")
        return p

    def _load_hesa_campuses(self) -> gpd.GeoDataFrame:
        """
        Load HESA campus locations, filter to England with valid coordinates.
        Returns GeoDataFrame with one row per campus.
        """
        hesa = pd.read_csv(self._p("hesa_campuses"))
        eng = hesa[
            (hesa["CampusCountry"] == "England") &
            hesa["CampusLatitude"].notna() &
            hesa["CampusLongitude"].notna()
        ].copy()
        gdf = gpd.GeoDataFrame(
            eng,
            geometry=gpd.points_from_xy(eng["CampusLongitude"], eng["CampusLatitude"]),
            crs="EPSG:4326"
        )
        print(f"[UniversityBuilder] {len(gdf)} English campuses with coordinates loaded")
        return gdf

    def _load_feecap_ukprns(self) -> set:
        """
        Load OfS register and return set of UKPRNs for fee-cap providers only.
        """
        ofs = pd.read_excel(self._p("ofs_register"), skiprows=2)

        # column names use curly apostrophes — match by keyword
        cat_col  = next(c for c in ofs.columns if "category" in c.lower())
        ukprn_col = next(c for c in ofs.columns if "ukprn" in c.lower())

        feecap = ofs[ofs[cat_col].astype(str).str.strip() == self.FEECAP_CATEGORY]
        ukprns = set(feecap[ukprn_col].astype(str))
        print(f"[UniversityBuilder] {len(ukprns)} fee-cap providers identified from OfS register")
        return ukprns

    def _load_lad_boundaries(self) -> gpd.GeoDataFrame:
        lad = gpd.read_file(self._p("lad_boundaries"))
        lad = lad[lad["LAD23CD"].str.startswith("E")].copy()
        return lad.to_crs("EPSG:4326")

    def build(self, panel: pd.DataFrame) -> pd.DataFrame:
        """
        Add n_universities_feecap_lad column to the panel.
        Value is constant across all years and sectors for a given LAD
        (HE presence treated as time-invariant structural condition).
        """
        campuses  = self._load_hesa_campuses()
        feecap    = self._load_feecap_ukprns()
        lad       = self._load_lad_boundaries()

        # filter campuses to fee-cap providers only
        campuses["UKPRN"] = campuses["UKPRN"].astype(str)
        campuses = campuses[campuses["UKPRN"].isin(feecap)].copy()
        print(f"[UniversityBuilder] {len(campuses)} fee-cap campuses retained")

        # spatial join — within
        joined = gpd.sjoin(
            campuses,
            lad[["LAD23CD", "LAD23NM", "geometry"]],
            how="left",
            predicate="within"
        )

        # nearest fallback for boundary-edge campuses
        unmatched = joined[joined["LAD23CD"].isna()].drop(
            columns=["index_right", "LAD23CD", "LAD23NM"]
        )
        if len(unmatched) > 0:
            lad_proj = lad.to_crs("EPSG:27700")
            unmatched_proj = unmatched.to_crs("EPSG:27700")
            nearest = gpd.sjoin_nearest(
                unmatched_proj,
                lad_proj[["LAD23CD", "LAD23NM", "geometry"]],
                how="left"
            ).to_crs("EPSG:4326")
            joined = pd.concat(
                [joined[joined["LAD23CD"].notna()], nearest],
                ignore_index=True
            )
            print(f"[UniversityBuilder] {len(unmatched)} boundary campuses assigned via nearest LAD")

        # count distinct providers (UKPRN) per LAD
        lad_counts = (
            joined.groupby("LAD23CD")["UKPRN"]
            .nunique()
            .reset_index()
            .rename(columns={"UKPRN": "n_universities_feecap_lad"})
        )

        # ensure all 296 LADs present — fill missing with 0
        all_lads = lad[["LAD23CD"]].copy()
        lad_counts = all_lads.merge(lad_counts, on="LAD23CD", how="left").fillna(0)
        lad_counts["n_universities_feecap_lad"] = lad_counts["n_universities_feecap_lad"].astype(int)

        n_with = (lad_counts["n_universities_feecap_lad"] > 0).sum()
        print(f"[UniversityBuilder] {n_with} LADs with at least one fee-cap HE provider")

        # merge onto panel — LAD-level join (year/sector constant)
        panel = panel.copy()
        panel["GEOGRAPHY_CODE"] = panel["GEOGRAPHY_CODE"].astype(str)
        lad_counts["LAD23CD"] = lad_counts["LAD23CD"].astype(str)
        panel = panel.merge(
            lad_counts,
            left_on="GEOGRAPHY_CODE",
            right_on="LAD23CD",
            how="left"
        ).drop(columns=["LAD23CD"])

        print(f"[UniversityBuilder] n_universities_feecap_lad added to panel")
        return panel