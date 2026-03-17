# analysis_panel.parquet — Dataset Documentation

*Last updated: March 2026*

---

## Overview

`analysis_panel.parquet` is the main analysis-ready dataset for the PP422 project. It is a balanced panel covering **350 Local Authority Districts (LADs)** across Great Britain, **7 IS8 sectors**, and **7 years (2016–2022)**, for a total of **17,150 rows and 57 columns**.

It is built by running `main.py` from the project root, which calls `DataProcessor.build_panel()` in `src/processor.py` and `IndicatorBuilder.build_indicators()` in `src/indicators.py`. All file paths and parameters are read from `config.yml` — no hardcoded paths exist in any class.

---

## Source Data

| File | Format | Coverage | Role |
|---|---|---|---|
| `raw_data/employee_counts/Employee_counts_IS8_LADs.parquet` | Parquet | 2015–2024, GB | Employee counts by LAD × IS8 sector × year |
| `raw_data/business_counts/Business_counts_IS8_LADs.parquet` | Parquet | 2016–2025, GB | Business counts by LAD × IS8 sector × year × size band |
| `raw_data/local_indicators/ONS_local_indicators_package.xlsx` | Excel (54 sheets) | ~2021–2024, varies | Place-based contextual indicators |
| `raw_data/boundaries/MSOA_(2011)_to_MSOA_(2021)_to_Local_Authority_District_(2022)_Exact_Fit_Lookup_for_EW_(V2).csv` | CSV | England & Wales | Boundary crosswalk (see note below) |

---

## Build Pipeline

### Step 1 — Filter to LAD geography

Both parquet files contain rows at multiple geographic levels (LAD, region, country, Great Britain). Only rows where `GEOGRAPHY_TYPE == "local authorities: district / unitary (as of April 2023)"` are retained. Country-level rows are kept separately for use as national benchmarks in LQ computation.

### Step 2 — Filter to year range

Both datasets are filtered to 2016–2022. This is the intersection of meaningful coverage for both employee and business count series. Years outside this range are dropped before any further processing.

### Step 3 — Standardise IS8 sector names

Raw sector names in the parquet files differ slightly from the IS8 framework labels. A fixed mapping in `config.yml` (`sector_map`) corrects these:

| Raw name | Standardised name |
|---|---|
| `Advanced manufacturing` | `Advanced Manufacturing` |
| `Defence sector` | `Defence` |
| `Digital and Technology` | `Digital and Technologies` |

The remaining four sector names (`Creative Industries`, `Financial Services`, `Life Sciences`, `Professional and Business Services`) match directly and are left unchanged.

**Note on sector count:** The dataset contains **7 IS8 sectors**, not 8. `Clean Energy` and `Space` do not exist in the source data. The raw parquet files contain exactly these 7 sectors plus a `Total` aggregate row.

### Step 4 — Aggregate to IS8 level

Raw parquet files contain rows at two levels of granularity: IS8-level rows and frontier-level sub-sector rows. These are complementary parts of the same total, not duplicates. Both are summed together to produce the correct IS8 total per LAD × IS8 sector × year. The `SIZE_BAND` and `FRONTIER_SECTOR` columns are dropped at this stage by grouping on `["YEAR", "GEOGRAPHY_CODE", "GEOGRAPHY_NAME", "IS8_SECTOR"]`. `Total` rows are kept at this stage — they are needed for LQ computation in Step 6.

### Step 5 — Merge employee and business counts

The processed employee and business count tables are joined on `["YEAR", "GEOGRAPHY_CODE", "GEOGRAPHY_NAME", "IS8_SECTOR"]` using an inner join. A 100% match is expected and observed — both tables cover the same LADs, sectors, and years.

### Step 6 — Merge ONS indicators

ONS indicators are merged onto the panel by `GEOGRAPHY_CODE`. Each of the 54 Excel sheets is processed individually:

1. The header row is located by scanning for `"Area Code"`
2. Rows are filtered to LAD level using a regex match on geography codes (`^[EWS]\d{8}$`)
3. Value columns are converted to numeric; `"na"` and `"NA"` strings are replaced with `NaN`
4. Only the **first numeric value column** per sheet is retained, named after the sheet (lowercased, spaces replaced with underscores)
5. Each indicator is joined to the panel via a left merge on `GEOGRAPHY_CODE`

Four metadata sheets (`Notes`, `Voluntary TQV`, `Data dictionary`, `Data inclusivity`) are skipped automatically.

**Important assumption:** ONS indicators are single time-point snapshots (roughly 2021–2024). They are merged onto all rows in the panel regardless of year — they are treated as **time-invariant** place characteristics. This is a deliberate modelling assumption. Users should not interpret year-on-year variation in these columns as real change.

**Known null patterns in ONS columns:** Several education and health columns have high null rates (48–64%). This is expected — these are England-only indicators. Scotland (32 LADs) and Wales (22 LADs) will always be null for these columns. Some columns also have partial coverage within England due to data availability in the source file.

### Step 7 — Boundary reconciliation

`reconcile_boundaries()` was designed to drop LADs with obsolete pre-2023 boundary codes using a `CHGIND` flag from the MSOA crosswalk. In practice, `CHGIND` is entirely null in the crosswalk file, so this step drops nothing. This is not a problem: the raw parquet files already use 2023 LAD boundaries throughout, so no reconciliation is needed. The 350 LADs in the panel represent the correct full GB coverage (296 England + 32 Scotland + 22 Wales).

### Step 8 — Build indicators

`IndicatorBuilder.build_indicators()` computes all derived indicators. National totals (GB-level) are loaded once from the raw parquet files and used as benchmarks for LQ computation. `Total` sector rows are removed after LQ and employment share computation.

See the **Indicators** section below for full definitions.

### Step 9 — Optimise dtypes

Key columns are cast to memory-efficient types: `GEOGRAPHY_CODE`, `GEOGRAPHY_NAME`, and `IS8_SECTOR` to `category`; `EMPLOYEES` and `BUSINESSES` to `float32`.

---

## Geographic Coverage

| Nation | LADs |
|---|---|
| England | 296 |
| Scotland | 32 |
| Wales | 22 |
| **Total** | **350** |

Geography codes follow the standard ONS format (`^[EWS]\d{8}$`). All 350 codes in the panel are valid. Boundaries use the **April 2023** LAD definition throughout.

---

## Sectors

| Sector |
|---|
| Advanced Manufacturing |
| Creative Industries |
| Defence |
| Digital and Technologies |
| Financial Services |
| Life Sciences |
| Professional and Business Services |

---

## Indicators

### Location Quotient — Employment (`lq_emp`)

```
LQ = (IS8 employment in LAD / total employment in LAD)
   / (IS8 employment in GB  / total employment in GB)
```

Values above 1 indicate the sector is more concentrated in the LAD than the national average. The GB row from the raw parquet is used as the national benchmark. No null values.

### Location Quotient — Businesses (`lq_bus`)

Same formula as `lq_emp` but using business counts instead of employment. No null values.

### Employment Share (`emp_share`)

IS8 sector employment as a share of total LAD employment. No null values.

### Employment Growth (`growth_emp`) and CAGR (`cagr_emp`)

Growth from the first non-zero year (≥ `growth_start_year_emp` in config) to `growth_end_year`, per LAD × sector. CAGR is annualised using the actual number of years between the base year and end year.

Null where a LAD × sector has zero employment throughout the entire period — the base year cannot be identified. **Null rate: ~12%.** Almost entirely concentrated in the Defence sector (279/350 LADs) and partially in Life Sciences (12/350 LADs). This reflects genuine absence of sector presence, not a data error.

### Business Count Growth (`growth_bus`) and CAGR (`cagr_bus`)

Same logic as employment growth but using business counts. **Null rate: ~17%.** Concentrated in Defence (347/350 LADs) and Life Sciences (59/350 LADs).

### Related Variety (`related_variety`)

Within-sector Shannon entropy per LAD × IS8 sector × year, computed from business counts across SIC codes within the sector. Higher values indicate the sector is more internally diversified across SIC codes. Computed directly from the raw business counts parquet (before aggregation) to preserve SIC-level granularity. No null values.

### Size Distribution (`size_large_share`, `size_micro_share`)

Share of large and micro businesses out of total businesses per LAD × IS8 sector × year. Computed from the raw business counts parquet using the `SIZE_BAND` column (which is aggregated away in the main panel). **Null rate: ~18–19%.** Concentrated in Defence (348/350 LADs) and Life Sciences (151/350 LADs), for the same reason as growth rates.

---

## Known Issues and Analytical Considerations

### Defence sector sparsity

Defence is structurally different from the other six sectors. It is heavily concentrated in a small number of LADs (West Berkshire, Stevenage, Gosport, Monmouthshire, Basildon, Telford and Wrekin, and a few others). Across the rest of GB:

- 80% of LADs have null employment growth (no Defence presence in the period)
- 99% of LADs have null business count growth
- Employment LQ values exceed 100 in the main clusters (vs. a max of ~3 in other sectors)

**Recommendation:** Do not pool Defence with the other six sectors in a cross-sector regression without controls. Consider running it as a standalone case study or including a Defence dummy and flagging the cluster LADs as influential outliers.

### ONS indicators are time-invariant

ONS indicators are merged as static values, not as a time series. Any model using both `YEAR` and ONS columns as covariates should account for this — year fixed effects will absorb no variation from ONS columns.

### `reconcile_boundaries()` is currently a no-op

The boundary reconciliation step was designed to handle pre-2023 LAD codes but the crosswalk file has no usable `CHGIND` flags. This is harmless because the source data already uses 2023 boundaries, but the method should either be removed or updated if the project later incorporates pre-2023 data sources.

### Employee counts are rounded

ONS employee count data is rounded to the nearest 100 (for counts ≥ 1,000) or nearest 50 (for smaller counts). This introduces measurement error in growth rates and LQ for small LAD × sector combinations. Treat growth estimates for cells with fewer than 500 employees with caution.
