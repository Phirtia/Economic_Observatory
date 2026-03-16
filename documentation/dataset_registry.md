# Dataset Registry
*PP422 | LSE Growth Co-Lab | Last updated: March 2026*

---

## Core IS8 Data

### 1. `Business_counts_IS8_LADs.parquet`
**Source:** UK Business Counts (local units), IDBR via Nomis  
**Location:** `02_raw_data/business_counts/`  
**Unit of observation:** Count of businesses by LAD / IS8 sector / frontier sector / size band / SIC code / year  
*Each row answers: "In this place, in this year, in this industry, of this size — how many businesses were there?"*

| Property | Value |
|---|---|
| Rows | 1,249,600 |
| Columns | 9 |
| Geography | LAD + country aggregates |
| Geography type | `local authorities: district / unitary (as of April 2023)`, `countries` |
| Join key | `GEOGRAPHY_CODE` → `LAD23CD` |
| Years | 2016–2025 |
| IS8 sectors | 7 (Clean Energy Industries absent) |
| Frontier sectors | 14 (only 4 IS8 sectors have frontier breakdowns) |
| Size bands | micro, small, medium, large |
| Zero values | 918,442 (73%) |
| OBS_VALUE rounding | Multiples of 5 throughout |

**Known limitations:**
- Clean Energy Industries entirely absent
- All values rounded to nearest 5 — ONS disclosure control. Zeros may be genuine zeros or values of 1–2 (which round down to 0). Non-zero values carry rounding error of up to ±2
- No values of 1, 2, 3, or 4 exist in the dataset
- Country-level aggregates mixed with LADs — filter required
- "Total" appears as IS8_SECTOR value — filter required
- Sector naming differs slightly from IS8 brief (e.g. "Defence sector", "Digital and Technology")

---

### 2. `Business_counts_IS8_MSOAs.parquet`
**Source:** UK Business Counts (local units), IDBR via Nomis  
**Location:** `02_raw_data/business_counts/`  
**Unit of observation:** Count of businesses by MSOA/IZ / IS8 sector / frontier sector / size band / SIC code / year  
*Each row answers: "In this small area, in this year, in this industry, of this size — how many businesses were there?"*

| Property | Value |
|---|---|
| Rows | 6,297,280 |
| Columns | 9 |
| Geography | 2021 MSOAs (England & Wales) + 2022 Scottish IZs |
| Join key | `GEOGRAPHY_CODE` → `MSOA21CD` / `IZCode` |
| Years | 2016–2025 |
| Unique geographies | 1,807 |
| Zero values | 6,034,097 (96%) |
| OBS_VALUE rounding | Multiples of 5 throughout |

**Known limitations:**
- Same sector limitations as LAD file
- All values rounded to nearest 5 — same disclosure control as LAD file
- 96% zeros — severe suppression at this geography
- Better suited for mapping than modelling
- No country-level aggregates

---

### 3. `Employee_counts_IS8_LADs.parquet`
**Source:** Business Register and Employment Survey (BRES) via Nomis  
**Location:** `02_raw_data/employee_counts/`  
**Unit of observation:** Estimated employee count by LAD / IS8 sector / frontier sector / SIC code / year  
*Each row answers: "In this place, in this year, in this industry — how many employees were there?"*

| Property | Value |
|---|---|
| Rows | 312,400 |
| Columns | 8 |
| Geography | LAD + country aggregates |
| Join key | `GEOGRAPHY_CODE` → `LAD23CD` |
| Years | 2015–2024 |
| Unique geographies | 355 |
| Zero values | 90,519 (29%) |
| OBS_VALUE rounding | 0–50 in increments of 5; 50–250 in increments of 25; 250+ in increments of 50 |

**Known limitations:**
- No SIZE_BAND column — unlike business counts
- Year range 2015–2024 — one year offset from business counts
- Overlap with business counts: 2016–2023 (8 years)
- Country-level aggregates mixed with LADs — filter required
- BRES is a survey estimate, not an administrative count
- Interval-based rounding — values at low end rounded to nearest 5, wider rounding bands at higher values

---

### 4. `Employee_counts_IS8_MSOAs.parquet`
**Source:** Business Register and Employment Survey (BRES) via Nomis  
**Location:** `02_raw_data/employee_counts/`  
**Unit of observation:** Estimated employee count by MSOA/IZ / IS8 sector / frontier sector / SIC code / year  
*Each row answers: "In this small area, in this year, in this industry — how many employees were there?"*

| Property | Value |
|---|---|
| Rows | 1,576,080 |
| Columns | 8 |
| Geography | 2021 MSOAs (England & Wales) + 2022 Scottish IZs |
| Join key | `GEOGRAPHY_CODE` → `MSOA21CD` / `IZCode` |
| Years | 2015–2024 |
| Unique geographies | 1,807 |
| Zero values | 1,278,103 (81%) |
| OBS_VALUE rounding | 0–50 in increments of 5; 50–250 in increments of 25; 250+ in increments of 50 |

**Known limitations:**
- Same limitations as employee counts LAD
- Interval-based rounding applies
- 81% zeros — better for mapping than modelling

---

## Reference Data

### 5. `IS-8_SIC_Lookup.csv`
**Source:** UK Government Industrial Strategy Sector Definitions List  
**Location:** `02_raw_data/`  
**Unit of observation:** Mapping of SIC code to IS8 sector and frontier sector  
*Each row answers: "What IS8 sector and frontier sub-sector does this SIC code belong to?"*

| Property | Value |
|---|---|
| Rows | 87 |
| Columns | 5 |
| SIC digit levels | 2, 3, 4, 5 |
| Unique SIC codes | 84 |
| IS8 sectors | 7 (Clean Energy Industries absent) |
| Frontier sectors | 14 |
| Join key | `SIC` → `INDUSTRY_CODE` |

**Known limitations:**
- Clean Energy Industries absent
- "Total" in parquet INDUSTRY_CODE has no match — expected, not a data quality issue

---

## Local Indicators

### 6. `ONS_local_indicators_package.xlsx`
**Source:** ONS Subnational Indicators Explorer (9th release, March 2024)  
**Location:** `02_raw_data/local_indicators/`  
**Unit of observation:** Value of a local indicator for a given area  
*Each sheet answers: "What is the value of this local indicator for this area?"*

| Property | Value |
|---|---|
| Sheets | 54 (4 metadata, 50 indicators) |
| Geography | LAD + regions + nations (mixed in each sheet) |
| Join key | `Area Code` → `GEOGRAPHY_CODE` |
| Time coverage | Single snapshot per indicator, roughly 2021–2024 |
| Coverage | Varies by indicator — mostly England, some GB/UK |

**Variable geography availability:**

| EEG/S3 Concept | Variables | Finest geography |
|---|---|---|
| **Human capital** | NVQ level 3+, GCSEs by age 19, Apprenticeship starts/achievements, FE participation, Early years comms/literacy/maths | LAD |
| **Human capital** | KS2 attainment, Ofsted, Persistent absences (all), FE achievements, Female/Male HLE | County/Unitary Authority only |
| **Entrepreneurial discovery** | Births, Deaths, Active, High growth enterprises | LAD |
| **Knowledge infrastructure** | Government R&D | ITL1 (regional) only |
| **Connectivity** | Public transport, Drive, Cycle to employer, Gigabit broadband, 4G coverage | LAD |
| **Agglomeration and productivity** | GVA per hour, Weekly pay, Employment rate, Unemployment rate, GDHI per head | LAD |
| **Market openness** | UK exports, Inward FDI, Outward FDI | ITL1/ITL2 (regional) only |
| **Place conditions** | Net additions to housing stock | LAD |
| **Institutional thickness** | Population under devolution deal | Region only |
| **Wellbeing and health** | Smokers, Obesity (all), Cancer diagnosis, Under 75 mortality, Life satisfaction, Happiness, Worthwhile, Anxiety | LAD |
| **Wellbeing and health** | Homicide offences | Police Force Area / Region only |

**Key implication:** No variables exist below LAD level — definitively confirms LAD as the only technically feasible unit of analysis for regression. Variables only available at ITL1/ITL2 or regional level cannot be used in LAD-level regression and must be acknowledged as limitations.

---

## Boundary and Lookup Files

### 7. `UK_Local_Authority_Districts_December_2023_Boundaries_UK_BGC_...geojson`
**Location:** `02_raw_data/boundaries/`

| Property | Value |
|---|---|
| Features | 361 LADs |
| Boundary vintage | 2023 |
| Join key | `LAD23CD` |
| CRS | EPSG:4326 (WGS84) |

---

### 8. `Middle_layer_Super_Output_Areas_December_2021_Boundaries_EW_BGC_V3_...geojson`
**Location:** `02_raw_data/boundaries/`

| Property | Value |
|---|---|
| Features | 7,264 MSOAs |
| Coverage | England and Wales |
| Boundary vintage | 2021 |
| Join key | `MSOA21CD` |
| CRS | EPSG:4326 (WGS84) |

---

### 9. `SG_IZ_2022.geojson`
**Location:** `02_raw_data/boundaries/`

| Property | Value |
|---|---|
| Features | 1,334 Intermediate Zones |
| Coverage | Scotland |
| Boundary vintage | 2022 |
| Join key | `IZCode` |
| CRS | EPSG:4326 (WGS84) |

---

### 10. `MSOA_to_English_combined_authorities.csv`
**Location:** `02_raw_data/boundaries/`

| Property | Value |
|---|---|
| Rows | 1,941 |
| Coverage | 10 English combined authorities |
| Join keys | `MSOA21CD` → `LAD23CD` → `CAUTH23CD` |

**Role:** Aggregates MSOAs to combined authority level for Phase 2 city region analysis.

---

### 11. `IZ2022_to_council_area.csv`
**Location:** `02_raw_data/boundaries/`

| Property | Value |
|---|---|
| Rows | 1,334 |
| Coverage | Scotland |
| Join keys | `IZ22CD` → `CA` (council area code) |

**Role:** Aggregates Scottish IZs to council area level for Glasgow City Region analysis.

---

### 12. `MSOA_(2011)_to_MSOA_(2021)_to_Local_Authority_District_(2022)_Exact_Fit_Lookup_for_EW_(V2).csv`
**Location:** `02_raw_data/boundaries/`

| Property | Value |
|---|---|
| Rows | 7,286 |
| Columns | 9 |
| Join keys | `MSOA11CD` → `MSOA21CD` → `LAD22CD` |
| Change indicator | `CHGIND` flags boundary changes |

**Role:** Resolves pre-2023 LAD boundary mismatch in ONS indicators file.

---

## Data Gaps (to be addressed)

| Gap | Impact | Proposed source | Status |
|---|---|---|---|
| Clean Energy Industries | Entire IS8 sector absent | Acknowledge as limitation | Flagged |
| University/research intensity | Key EEG variable missing | HESA data | Flagged |
| Government R&D at LAD level | Only available at ITL1 — 100% missing in panel | LAD → ITL1 lookup from ONS geoportal + downscaling | Flagged — potential extension |
| UK exports, Inward/Outward FDI at LAD level | Only available at ITL1/ITL2 — 100% missing in panel | LAD → ITL1/ITL2 lookup + downscaling | Flagged — potential extension |
| Homicide at LAD level | Only available at Police Force Area — 100% missing in panel | LAD → PFA lookup + downscaling | Flagged — low priority |
| Devolution at LAD level | Only available at region level — 100% missing in panel | LAD → region lookup + downscaling | Flagged — low priority |
| Pre-2023 LAD codes in ONS file | Merge key mismatch | MSOA crosswalk (`CHGIND` flag) | Addressed in DataProcessor |
| Panel data for ONS indicators | Limits dynamic analysis | Nomis direct download for selected indicators | Flagged |