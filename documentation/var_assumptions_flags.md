# Dataset Assumptions and Analytical Flags
*PP422 | LSE Growth Co-Lab | Last updated: March 2026*

This document captures: (1) methodological assumptions baked into the dataset construction, and (2) preprocessing flags that must be addressed before any regression or clustering analysis. It is a companion to the variable codebook and the pipeline source files.

---

## Part 1 — Dataset Construction Assumptions

### Geography

| Assumption | Detail | Implication |
|---|---|---|
| England-only panel | Scottish (S12) and Welsh (W06) LADs excluded via `england_only: true` config parameter. Baseline panel retains GB. | All findings are England-specific. Policy recommendations cannot generalise to devolved administrations. |
| LAD23 boundary codes | IS8 data uses April 2023 LAD codes. ONS indicators use LAD22 codes for some variables. | ~21 boundary-change LADs have their ONS indicator codes remapped before merging (`boundary_approach: 2`). Simple mean used for rate aggregation in absence of population weights — acknowledged approximation. |
| 296 English LADs | Post-boundary reconciliation and England filter. Isles of Scilly and City of London retained despite anomalous characteristics. | These two LADs are structural outliers and may appear as extreme observations in clustering and regression. |

### Temporal

| Assumption | Detail | Implication |
|---|---|---|
| Analysis window: 2016–2022 | Chosen to align employee and business count data availability. | Window straddles COVID-19 (2020). Recovery effects in 2021–2022 may reflect structural distortions, not long-run trends. Robustness check excluding 2020 is warranted. |
| X variables treated as time-invariant | All ONS indicators are single time-point snapshots (2019–2023). | Temporal mismatch with GD window (2016–2022). Implicit assumption: structural conditions are stable over the period. This is defensible but not trivially true. |
| Transport variables temporally stale | DfT data from 2019, referenced to 2011 boundaries. | Most outdated X variables in the dataset. Pre-COVID transport patterns may not reflect current accessibility. |
| ONS indicator reference years vary | Enterprise data: 2022. Broadband/4G: 2023. NVQ/GDHI: 2021. Transport: 2019. | 4-year spread across X variables all treated as contemporaneous. Document in limitations. |

### Benchmarking

| Assumption | Detail | Implication |
|---|---|---|
| England aggregate as LQ benchmark | LQ national denominator uses England aggregate row from raw ONS data, not sum of LAD rows. | Summing LAD rows would inflate denominators and produce LQ values systematically below 1. England-only consistent with panel geography. |
| β_national fixed per sector × dimension | National OLS slope computed once from full 2016–2022 England time series. | All LAD GD values are relative to the same fixed benchmark. A sector declining nationally gives a negative β_national — LADs declining slower will have positive GD. This is correct but requires careful interpretation. |

### IS8 Sectors

| Assumption | Detail | Implication |
|---|---|---|
| Defence excluded from all modelling | Confirmed structurally unreliable: lq_emp up to 120, gd_bus based on 14 national observations, p99 of lq_bus = 0. | All 24 regression models and clustering analysis run on 6 sectors only. |
| Clean Energy Industries absent | Entirely absent from all source files. | One IS8 sector cannot be modelled or mapped. Acknowledged as data gap. |
| 6 sectors modelled | Advanced Manufacturing, Creative Industries, Digital and Technologies, Financial Services, Life Sciences, Professional and Business Services. | |

### Enterprise Variables

| Assumption | Detail | Implication |
|---|---|---|
| Enterprise dynamics normalised by active stock | `enterprise_births`, `enterprise_deaths`, `enterprise_high_growth` divided by `enterprise_active` to produce rates. | Removes LAD size effect. Birth rate and death rate are theoretically interpretable as churn rates. High growth rate is the share of scaling firms. `enterprise_active` dropped after normalisation. |

### Growth Differential

| Assumption | Detail | Implication |
|---|---|---|
| Log-linear OLS slope as trajectory measure | β estimated from `log(y) ~ year` using all available non-zero years per LAD × sector. | More robust than CAGR — uses all data points, not just endpoints. Not comparable to CAGR in magnitude. |
| Minimum 4 valid years for slope estimate | LAD × sector combinations with fewer than 4 non-zero observations → GD = NaN. | ~13% null rate on gd_emp, ~17% on gd_bus. Concentrated in Life Sciences (small base) and Defence (excluded). |
| National β = 0 → GD undefined | If national slope is zero, subtraction produces a β_LAD that is not a differential — excluded as NaN. | Unlikely to occur for IS8 sectors at national level but coded defensively. |

### Related Variety

| Assumption | Detail | Implication |
|---|---|---|
| Cross-sector entropy as EEG proxy | Shannon entropy across IS8 sectors per LAD × year, weighted by business counts. | Approximation only. True EEG related variety requires SIC-level technological proximity weights. Acknowledge as limitation. Theoretical max = log(6) ≈ 1.79; observed max = 1.35. |

---

## Part 2 — Preprocessing Flags (Before Any Analysis)

These flags do not affect dataset construction but must be addressed before running regressions, clustering, or producing final outputs.

### Y Variables — Winsorisation Required

Right-tail (and in some cases left-tail) extreme values driven by small-base LADs. Winsorise at the stated percentiles per sector before regression. Panel stores true values — winsorisation applied at analysis stage only.

| Variable | Sector | Tail | Threshold | Observed max | p99 |
|---|---|---|---|---|---|
| `lq_emp` | Life Sciences | Right | 99th percentile | 14.8 | ~10 | 21 (1.0%) |
| `lq_emp` | Advanced Manufacturing | Right | 99th percentile | 13.3 | ~8 | 21 (1.0%) |
| `lq_emp` | Financial Services | Right | 99th percentile | 11.0 | ~6 | 21 (1.0%) |
| `lq_bus` | Life Sciences | Right | 99th percentile | 9.7 | 5.2 | 21 (1.0%) |
| `lq_bus` | Financial Services | Right | 99th percentile | 7.8 | 3.3 | 21 (1.0%) |
| `gd_emp` | Life Sciences | Both | 1st–99th percentile | -0.595 / +0.721 | ±0.33–0.41 | 28 (1.5%) |
| `gd_bus` | Life Sciences | Both | 1st–99th percentile | -0.310 / +0.198 | ±0.17–0.26 | 28 (1.7%) |
| `gd_emp` | Financial Services | Left | Monitor (p1=-0.167) | -0.220 | — | — |
| `gd_emp` | Advanced Manufacturing | Left | Monitor (p1=-0.151) | -0.249 | — | — |

### X Variables — Standardisation Required

All X variables must be z-scored (zero mean, unit variance) before entering any regularised regression (Elastic Net, Ridge, LASSO). Without standardisation, penalisation is applied unevenly based on variable magnitude rather than explanatory power.

### X Variables — Skewness

| Variable | Issue | Suggested treatment |
|---|---|---|
| `lq_emp`, `lq_bus` | Mechanically right-skewed (bounded at 0, unbounded above) | Log transformation theoretically correct if used as X in any model |
| `enterprise_birth_rate`, `enterprise_death_rate` | Moderately right-skewed | Log transformation worth considering |

### X Variables — Low Variance (Monitor in Regression)

These variables have very low variance and may contribute little to regularised models. They will likely be shrunk toward zero by regularisation — monitor coefficient magnitudes.

| Variable | Issue |
|---|---|
| `coverage_4g` | Mean 99.5%, near-zero variation across LADs |
| `size_large_share` | Mean 0.004, max 0.125 — large firms are rare |
| `enterprise_high_growth_rate` | Mean 0.004, max 0.018 — high growth firms are rare |

### X Variables — Expected Collinearity (Let Regularisation Handle)

These variable groups are likely correlated. Do not pre-drop — allow regularised regression to distribute coefficients. Document collinearity in limitations.

| Group | Variables |
|---|---|
| Human capital | `nvq_level3`, `gcse_age19`, `apprenticeship_starts`, `apprenticeship_achievements`, `fe_participation` |
| Transport accessibility | `transport_to_employer`, `drive_to_employer`, `cycle_to_employer` |
| Enterprise churn | `enterprise_birth_rate`, `enterprise_death_rate` |

### X Variables — Directional Ambiguity (Document Expected Sign Before Regression)

| Variable | Ambiguity |
|---|---|
| `unemployment_rate` | Higher unemployment = labour flexibility (positive for IS8 attraction) OR economic weakness (negative signal). Theoretical direction unclear. |
| `enterprise_death_rate` | Creative destruction (positive signal — Schumpeterian churn) OR ecosystem fragility (negative signal). |

### Missing Data

| Variable | Null rate | Cause | Action |
|---|---|---|---|
| `unemployment_rate` | 5.7% (17 LADs) | ONS modelled estimate suppression — small/anomalous LADs (City of London, Isles of Scilly, some unitaries) | Accept as NaN. Document in limitations. Do not impute. |
| `nvq_level3` | 0.7% | Isles of Scilly, City of London suppression | Accept as NaN. |
| `gd_emp` | 13.3% | n_years < 4 — sparse sector presence | Accept as NaN. Concentrated in Life Sciences and zero-activity LADs. |
| `gd_bus` | 17.5% | n_years < 4 — sparser than employment | Accept as NaN. Additional 4% vs gd_emp concentrated in Life Sciences and Defence. |

### Structural Limitations to Acknowledge in Write-Up

1. **No causal identification** — all findings are correlational. X gaps identify associated conditions, not causes.
2. **University/research intensity absent** — key EEG variable not available at LAD level. Source: HESA. Most significant theoretical gap.
3. **Government R&D absent at LAD level** — available at ITL1 only. Second most significant EEG gap.
4. **Related variety is an approximation** — cross-sector entropy proxies the EEG concept but lacks SIC-level proximity weights.
5. **COVID window** — 2016–2022 straddles COVID. Effects may persist into 2021–2022 recovery data.
6. **Transport data temporally stale** — DfT 2019, 2011 boundaries. Pre-COVID patterns may not reflect current accessibility.
7. **ONS employment counts rounded to nearest 5** — disclosure control introduces minor measurement error in small LADs.
8. **Boundary reconciliation approximation** — ~21 merged LADs use simple mean aggregation for ONS indicator rates. Population-weighted average not possible without working-age population data.