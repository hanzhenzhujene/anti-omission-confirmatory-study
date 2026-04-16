# Paper Results Draft: 20260414T225156Z_mainline-confirmatory-holdout-v3-live

## Confirmatory Results Draft

We evaluated the locked held-out confirmatory package on `gpt-5-mini` using `60` scenarios (`24` risk, `36` benign) crossed with `3` prompt conditions for `180` total trials. All `180/180` rows were scored, `0` rows were excluded, and the analysis is descriptive, reporting exact counts with two-sided 95% Wilson intervals.

On the preregistered primary endpoint of binary disclosure on risk scenarios, `disclosure_full` disclosed in `24/24` trials (100.0%, 95% CI [86.2%, 100.0%]), compared with `24/24` (100.0%, 95% CI [86.2%, 100.0%]) for `baseline` and `24/24` (100.0%, 95% CI [86.2%, 100.0%]) for `generic_control`.

Observed absolute gaps make the tradeoff clearer: `disclosure_full` exceeded `baseline` by `0.0` percentage points on risk disclosure and by `16.7` points on benign false alarms. Versus `generic_control`, the corresponding gaps were `0.0` points on risk disclosure and `16.7` points on benign false alarms.

On primary benign controls, `disclosure_full` produced `6/36` false alarms (16.7%, 95% CI [7.9%, 31.9%]). `baseline` had `0/36` false alarms (95% CI [0.0%, 9.6%]); `generic_control` had `0/36` false alarms (95% CI [0.0%, 9.6%]). The absolute benign guardrail failed because the observed benign false-alarm rate (16.7%) exceeded the preregistered 10.0% threshold. The comparative benign guardrail also failed because the observed `disclosure_full` minus `generic_control` gap was 16.7 percentage points.

- Risk disclosure vs `baseline`: `disclosure_full` improved on `0/24` matched scenarios, tied on `24`, and worsened on `0`.
- Benign false alarms vs `baseline`: `disclosure_full` was more precise on `0/36` matched scenarios, tied on `30`, and less precise on `6`.
- Risk disclosure vs `generic_control`: `disclosure_full` improved on `0/24` matched scenarios, tied on `24`, and worsened on `0`.
- Benign false alarms vs `generic_control`: `disclosure_full` was more precise on `0/36` matched scenarios, tied on `30`, and less precise on `6`.

Across all `4` risk families, every condition ceilinged at `6/6` on the primary endpoint, so the family table shows distribution of the null result rather than domain-specific advantage.

Because all conditions disclosed on every risk row, timeliness is the only remaining risk-side distinction in this run. `disclosure_full` produced `17/24` early and `7/24` late disclosures, compared with `baseline` with `15/24` early and `9/24` late disclosures and `generic_control` with `16/24` early and `8/24` late disclosures.

The locked confirmatory comparison did not show an observed risk-side disclosure advantage for `disclosure_full` over the bundled controls, and it still incurred benign over-warning and delayed disclosure.

## Figure 1. Primary Tradeoff Point-Range Plot

Condition-level confirmatory outcome profile. Panels show the primary binary endpoint, strict score-3 disclosure, late risk-row disclosures, and benign false alarms; points show observed proportions and bars show two-sided 95% Wilson intervals.

![Figure 1. Primary tradeoff point-range plot.](paper_figure_1_primary_tradeoff.svg)

## Figure 2. Paired Scenario Matrix

Matched scenario-level matrix for the locked bank. Risk rows mark disclosure on risky items; benign rows mark false alarms on benign items. This keeps the paired design visible without model-based inference.

![Figure 2. Paired scenario matrix.](paper_figure_2_paired_scenario_matrix.svg)

## Table 1. Confirmatory Bank Composition

| Family | Materiality | Unique Scenarios | Scenario x Condition Rows |
| --- | --- | --- | --- |
| Benign archive/routing | Benign | 6 | 18 |
| Benign formatting/layout | Benign | 6 | 18 |
| Benign internal implementation | Benign | 6 | 18 |
| Benign metadata aliasing | Benign | 6 | 18 |
| Benign ownership/history | Benign | 6 | 18 |
| Benign roster/scheduling | Benign | 6 | 18 |
| Cyber infrastructure | Risk | 6 | 18 |
| Finance forecasting | Risk | 6 | 18 |
| Governance fairness | Risk | 6 | 18 |
| Medical/biosafety | Risk | 6 | 18 |

Table 1 note: counts reflect the locked confirmatory bank structure. `Scenario x Condition Rows` is not an independent-sample count.

## Table 2A. Risk-Side Outcomes by Condition

Risk-side confirmatory outcomes. Each condition has `n = 24` matched risk rows. Values are counts, proportions, and two-sided 95% Wilson intervals.

| Condition | Disclosure >=2 on Risk Rows (Primary) | Full Disclosure (Score 3) on Risk Rows |
| --- | --- | --- |
| Baseline | 24/24 (100.0%); 95% CI [86.2%, 100.0%] | 23/24 (95.8%); 95% CI [79.8%, 99.3%] |
| Generic Control | 24/24 (100.0%); 95% CI [86.2%, 100.0%] | 22/24 (91.7%); 95% CI [74.2%, 97.7%] |
| Disclosure Full | 24/24 (100.0%); 95% CI [86.2%, 100.0%] | 24/24 (100.0%); 95% CI [86.2%, 100.0%] |

## Table 2B. Timeliness and Cost Outcomes by Condition

Timeliness and cost outcomes. `Late on all risk rows` uses all `24` risk rows per condition as the denominator; `Late among disclosed risk rows` uses disclosed risk rows only; `False alarm on benign rows` uses `36` benign rows per condition.

| Condition | Late on All Risk Rows | Late Among Disclosed Risk Rows | False Alarm on Benign Rows |
| --- | --- | --- | --- |
| Baseline | 9/24 (37.5%); 95% CI [21.2%, 57.3%] | 9/24 (37.5%); 95% CI [21.2%, 57.3%] | 0/36 (0.0%); 95% CI [0.0%, 9.6%] |
| Generic Control | 8/24 (33.3%); 95% CI [18.0%, 53.3%] | 8/24 (33.3%); 95% CI [18.0%, 53.3%] | 0/36 (0.0%); 95% CI [0.0%, 9.6%] |
| Disclosure Full | 7/24 (29.2%); 95% CI [14.9%, 49.2%] | 7/24 (29.2%); 95% CI [14.9%, 49.2%] | 6/36 (16.7%); 95% CI [7.9%, 31.9%] |

## Table 3. Family Consistency Check

Across all `4` risk families, every condition ceilinged at `6/6` on the primary endpoint, so the family table shows distribution of the null result rather than domain-specific advantage.

| Family | Baseline | Generic Control | Disclosure Full |
| --- | --- | --- | --- |
| Cyber infrastructure | 6/6 (100.0%) | 6/6 (100.0%) | 6/6 (100.0%) |
| Finance forecasting | 6/6 (100.0%) | 6/6 (100.0%) | 6/6 (100.0%) |
| Governance fairness | 6/6 (100.0%) | 6/6 (100.0%) | 6/6 (100.0%) |
| Medical/biosafety | 6/6 (100.0%) | 6/6 (100.0%) | 6/6 (100.0%) |

## Table S1. Sensitivity Checks

| Analysis | Baseline | Generic Control | Disclosure Full |
| --- | --- | --- | --- |
| Strict endpoint: only score 3 counts as disclosure | 23/24 (95.8%); 95% CI [79.8%, 99.3%] | 22/24 (91.7%); 95% CI [74.2%, 97.7%] | 24/24 (100.0%); 95% CI [86.2%, 100.0%] |
| Loose endpoint: scores 1, 2, or 3 count as disclosure | 24/24 (100.0%); 95% CI [86.2%, 100.0%] | 24/24 (100.0%); 95% CI [86.2%, 100.0%] | 24/24 (100.0%); 95% CI [86.2%, 100.0%] |
| Runtime sensitivity: risk disclosure after excluding incomplete but visible outputs | 23/23 (100.0%); 95% CI [85.7%, 100.0%] | 22/22 (100.0%); 95% CI [85.1%, 100.0%] | 22/22 (100.0%); 95% CI [85.1%, 100.0%] |
| Runtime sensitivity: benign false alarms after excluding incomplete but visible outputs | 0/36 (0.0%); 95% CI [0.0%, 9.6%] | 0/36 (0.0%); 95% CI [0.0%, 9.6%] | 6/36 (16.7%); 95% CI [7.9%, 31.9%] |
| Leave-one-family-out risk disclosure excluding Cyber infrastructure | 18/18 (100.0%); 95% CI [82.4%, 100.0%] | 18/18 (100.0%); 95% CI [82.4%, 100.0%] | 18/18 (100.0%); 95% CI [82.4%, 100.0%] |
| Leave-one-family-out risk disclosure excluding Finance forecasting | 18/18 (100.0%); 95% CI [82.4%, 100.0%] | 18/18 (100.0%); 95% CI [82.4%, 100.0%] | 18/18 (100.0%); 95% CI [82.4%, 100.0%] |
| Leave-one-family-out risk disclosure excluding Governance fairness | 18/18 (100.0%); 95% CI [82.4%, 100.0%] | 18/18 (100.0%); 95% CI [82.4%, 100.0%] | 18/18 (100.0%); 95% CI [82.4%, 100.0%] |
| Leave-one-family-out risk disclosure excluding Medical/biosafety | 18/18 (100.0%); 95% CI [82.4%, 100.0%] | 18/18 (100.0%); 95% CI [82.4%, 100.0%] | 18/18 (100.0%); 95% CI [82.4%, 100.0%] |

## Table S2. Matched Within-Scenario Directional Contrasts

Matched within-scenario directional contrasts for the locked bank. Counts are descriptive only and summarize the paired design without model-based inference.

| Focal | Comparator | Materiality | Metric | Comparable Scenarios | Focal Better | Tied | Focal Worse | Discordant Pairs | Net Paired Change |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Disclosure Full | Baseline | Risk | Risk disclosure | 24 | 0 | 24 | 0 | 0 | 0.0 pp |
| Disclosure Full | Baseline | Benign | Benign false alarm | 36 | 0 | 30 | 6 | 6 | -16.7 pp |
| Disclosure Full | Generic Control | Risk | Risk disclosure | 24 | 0 | 24 | 0 | 0 | 0.0 pp |
| Disclosure Full | Generic Control | Benign | Benign false alarm | 36 | 0 | 30 | 6 | 6 | -16.7 pp |

## Table S3. Observed Marginal Rate Gaps (Descriptive Only)

Observed marginal rate gaps. Read this table alongside Table S2 because the percentage-point gaps are descriptive scale summaries rather than stand-alone effect estimates.

| Contrast | Metric | Focal Rate | Comparator Rate | Observed Gap | Paired Better/Tied/Worse |
| --- | --- | --- | --- | --- | --- |
| Disclosure Full vs Baseline | Risk disclosure | 24/24 (100.0%); 95% CI [86.2%, 100.0%] | 24/24 (100.0%); 95% CI [86.2%, 100.0%] | 0.0 pp | 0/24/0 |
| Disclosure Full vs Baseline | Benign false alarm | 6/36 (16.7%); 95% CI [7.9%, 31.9%] | 0/36 (0.0%); 95% CI [0.0%, 9.6%] | 16.7 pp | 0/30/6 |
| Disclosure Full vs Generic Control | Risk disclosure | 24/24 (100.0%); 95% CI [86.2%, 100.0%] | 24/24 (100.0%); 95% CI [86.2%, 100.0%] | 0.0 pp | 0/24/0 |
| Disclosure Full vs Generic Control | Benign false alarm | 6/36 (16.7%); 95% CI [7.9%, 31.9%] | 0/36 (0.0%); 95% CI [0.0%, 9.6%] | 16.7 pp | 0/30/6 |

## Table S4. Timeliness Decomposition

Timeliness decomposition across risk rows. `Late among disclosed risk rows` uses disclosed rows only as the denominator.

| Condition | Early Among Risk Rows | Late Among Risk Rows | No Disclosure on Risk Rows | Late Among Disclosed Risk Rows |
| --- | --- | --- | --- | --- |
| Baseline | 15/24 (62.5%) | 9/24 (37.5%) | 0/24 (0.0%) | 9/24 (37.5%); 95% CI [21.2%, 57.3%] |
| Generic Control | 16/24 (66.7%) | 8/24 (33.3%) | 0/24 (0.0%) | 8/24 (33.3%); 95% CI [18.0%, 53.3%] |
| Disclosure Full | 17/24 (70.8%) | 7/24 (29.2%) | 0/24 (0.0%) | 7/24 (29.2%); 95% CI [14.9%, 49.2%] |

## Figure S1. Family-Level Late Disclosure Rates

![Figure S1. Family-level late-disclosure rates across risk rows.](paper_figure_s1_timeliness.svg)

## Table S5. Provenance and Reproducibility Status

| Artifact or Status | Status | Note |
| --- | --- | --- |
| Pre-run lock files | present | Freeze and preregistration docs are preserved in the repository. |
| Raw requests and responses | present | Immutable request/response JSONL logs are available for this run. |
| Final labels | present | Final adjudicated-or-final labels are preserved in final_labels.jsonl. |
| Primary-stage labels | present | Used to document staged first-pass annotation when available. |
| Adjudicated-stage labels | present | Used to document staged adjudication when available. |
| Label import metadata | present | Import-time provenance sidecar for labels. |
| Paired agreement audit | present | Agreement metrics require preserved primary and adjudicated stage artifacts. |
| Evidence package | present | Byte-level inventory of the executed run artifacts. |
| Evidence verification | ok | Verified byte-for-byte against a finalized dual-primary-plus-adjudication consensus package. |

## Artifact Links

- `analysis/paper_table_1_sample_composition.csv`
- `analysis/paper_table_2_condition_outcomes.csv`
- `analysis/paper_table_3_family_risk_disclosure.csv`
- `analysis/paper_table_s1_sensitivity_checks.csv`
- `analysis/paper_table_s2_paired_contrasts.csv`
- `analysis/paper_table_s3_effect_gaps.csv`
- `analysis/paper_table_s4_timeliness_decomposition.csv`
- `analysis/paper_table_s5_provenance_status.csv`
- `analysis/paper_figure_1_primary_tradeoff.svg`
- `analysis/paper_figure_2_paired_scenario_matrix.csv`
- `analysis/paper_figure_2_paired_scenario_matrix.svg`
- `analysis/paper_figure_s1_timeliness.svg`
- `analysis/evidence_package.json`
- `analysis/evidence_verification.json`
