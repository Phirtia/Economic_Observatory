# The Data
*This version: 27 February 2026*

This data extract contains business and employee counts for the UK's Industrial Strategy 8 (IS-8) sectors and frontier industries (sub-sectors).

- **Business counts** are sourced from the [UK Business Counts (local units)](https://www.nomisweb.co.uk/datasets/idbrlu) dataset on Nomis. Data are recorded by *local unit* — individual, geographically identified workplaces — rather than by headquarters location. Business counts are drawn from administrative records, e.g. PAYE tax data and VAT registrations.
- **Employee counts** are sourced from the [Business Register and Employment Survey (BRES)](https://www.nomisweb.co.uk/datasets/newbres6pub) on Nomis, which estimates the number of employees by workplace.

Both datasets use the Standard Industrial Classification 2007 (SIC 2007). 

The IS-8 sectors and frontier industries are defined by the UK government's Industrial Strategy. (See the [official sector definitions](https://www.gov.uk/government/publications/industrial-strategy/industrial-strategy-sector-definitions-list).) The accompanying `IS-8_SIC_Lookup.csv` in this folder maps each SIC code to its IS-8 sector and frontier industry. The codes used here span a mix of 2-, 3-, 4-, and 5-digit SIC codes. A "Total" entry is also included for each geography and year, derived by summing across all 18 broad SIC sections (A–R).

If you want other employee or business count data, consider visiting the sources on Nomis directly. There you can download data at other geographies, for other or more detailed industry groups, and disaggregated in other ways (e.g. public vs private sector; full-time vs part-time). The data is accessible without logging in, but creating a free account gives access to the powerful API.

---

## Files

### `business_counts/`

Business counts by employment size band, IS-8 sector, geography, and year (2016–2025).

- **`Business_counts_IS8_LADs.parquet`** — Local authority districts and UK country aggregates (England, Wales, Scotland, Great Britain, England & Wales).
- **`Business_counts_IS8_MSOAs.parquet`** — Small area geographies: 2021 Census Middle Layer Super Output Areas (MSOAs) for England and Wales, and 2022 Intermediate Zones (IZs) for Scotland, each covering approximately 8,000 people.

Columns:

| Column | Description |
|---|---|
| `YEAR` | Reference year (2016–2025) |
| `SIZE_BAND` | Employment size band: `micro` (0–9), `small` (10–49), `medium` (50–249), `large` (250+) |
| `GEOGRAPHY_CODE` | ONS geography code |
| `GEOGRAPHY_NAME` | Geography name |
| `GEOGRAPHY_TYPE` | Geography type (LAD, MSOA, country, etc.) |
| `IS8_SECTOR` | IS-8 sector name, or `Total` for the economy-wide aggregate |
| `FRONTIER_SECTOR` | Frontier industry (sub-sector) where applicable, otherwise blank |
| `INDUSTRY_CODE` | SIC code (as string), or `Total` |
| `OBS_VALUE` | Count of local units |

### `employee_counts/`

Employee counts by IS-8 sector, geography, and year (2015–2024).

- **`Employee_counts_IS8_LADs.parquet`** — Local authority districts and UK country aggregates.
- **`Employee_counts_IS8_MSOAs.parquet`** — 2021 MSOAs (England & Wales) and 2022 IZs (Scotland).

Columns are the same as the business counts files, except there is no `SIZE_BAND` column. `OBS_VALUE` is the estimated number of employees.

### `boundaries/`

Geography boundary and lookup files.

- **`UK_Local_Authority_Districts_December_2023_Boundaries_UK_BGC_2537431731774104276.geojson`** — Boundaries for all UK local authorities (2023 definition).
- **`Middle_layer_Super_Output_Areas_December_2021_Boundaries_EW_BGC_V3_-4477917303172606123.geojson`** — 2021 MSOA boundaries for England and Wales.
- **`SG_IZ_2022.geojson`** — 2022 Intermediate Zone boundaries for Scotland, simplified to 100m tolerance (WGS84). Contains `IZCode`, `IZName`, and `TotPop2022`.
- **`MSOA_to_English_combined_authorities.csv`** — Lookup from 2021 MSOA to English combined authority (April 2023 definitions). Covers 1,941 MSOAs across 10 combined authority areas.
- **`IZ2022_to_council_area.csv`** — Lookup from all 1,334 Scottish 2022 Intermediate Zones to council area.
- **`MSOA_(2011)_to_MSOA_(2021)_to_Local_Authority_District_(2022)_Exact_Fit_Lookup_for_EW_(V2).csv`** — ONS best-fit lookup linking 2011 MSOAs to 2021 MSOAs and their parent LADs.

### `local_indicators/`

The industry data should be complemented by other local indicators. You should consider sourcing additional data relevant to your analysis, but as a starting point:

- **`ONS_local_indicators_package.xlsx`** — A set of ~50 indicators compiled by the ONS for the [Explore Local Statistics](https://www.ons.gov.uk/explore-local-statistics/) tool. The ONS offers a much wider range of local data beyond what is packaged here.
- **Census 2021 bulk download** — Available at https://www.nomisweb.co.uk/sources/census_2021_bulk

---

## Notes on UK statistical geography

### Boundary vintages

Statistical geographies in the UK are periodically revised. The table below shows which boundary vintage applies to each dataset and year range.

| Dataset | Years | MSOA/IZ boundary |
|---|---|---|
| Business counts | 2025 | 2021 MSOAs / 2022 IZs |
| Business counts | 2016–2024 | 2011 MSOAs / 2011 IZs |
| Employee counts (BRES) | 2023–2024 | 2021 MSOAs / 2022 IZs |
| Employee counts (BRES) | 2015–2022 | 2011 MSOAs / 2011 IZs |

In the MSOA/IZ files provided here, all years have been standardised onto current (2021/2022) boundaries. For England and Wales, the ONS exact-fit lookup provided a direct code-to-code mapping. For Scotland, a majority-OA-vote crosswalk was constructed via OA-level linkage between the 2011 and 2022 censuses. Data from zones that were merged in the boundary revision have been summed. Because BRES and business counts data are rounded for disclosure control, any small errors introduced by the crosswalk are negligible.

LAD-level data are unaffected — 2023 boundaries are used throughout.

### Defining your areas

The target areas in this dataset are UK city regions. You should be careful about how your area is defined, but allow some flexibility where administrative borders do not align perfectly with the economic geography you are trying to capture. Some inconsistency in geographic groupings is expected and acceptable.

The five English target areas are Combined Authorities with clear mappings to MSOAs and local authority districts:

1. **South Yorkshire MCA** — Barnsley, Doncaster, Rotherham, Sheffield
2. **West Midlands CA**
3. **West Yorkshire CA**
4. **Greater Manchester CA**
5. **West of England CA** — Bristol, Bath and North East Somerset, South Gloucestershire

Scotland and Wales do not follow the same combined authority structure.

6. **Glasgow City Region** — a voluntary grouping of eight council areas with no independent legal authority: Glasgow City, East Dunbartonshire, West Dunbartonshire, North Lanarkshire, South Lanarkshire, East Renfrewshire, Renfrewshire, Inverclyde. If the geographic extent proves challenging, consider restricting to areas in and around Glasgow City.
7. **Cardiff–Newport** — Cardiff and Newport LADs. You may incorporate adjacent authorities (e.g. Caerphilly) if relevant to your analysis.

You may wish to define your boundaries more tightly to exclude peripheral areas, or more loosely to capture functional economic relationships that cross administrative borders.
