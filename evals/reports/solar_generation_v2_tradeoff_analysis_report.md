# Solar Pro 3 Generation v2 Trade-off Analysis Report

## 목적

Solar Pro 3 generation contract v2 live paired comparison 결과를 query 단위로 진단해 v2를 기본 contract로 채택할지 판단한다.

이 문서는 추가 Solar Pro 3 호출 결과가 아니다. 기존 live paired comparison의 private metric rows를 분석하며 raw query, raw answer, evidence text, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-generation-v2-tradeoff-analysis-report/v1` |
| analysis_id | `solar-generation-v2-tradeoff-q7-6c5420d9` |
| generated_at_utc | `2026-05-12T13:38:20+00:00` |
| source_result_rows | `<private solar_generation_contract_v2_live_comparison_results.jsonl>` |
| source_rows_fingerprint | `ca88c7c2d5e951a7` |

## 정량 리포트

| metric | value |
| --- | ---: |
| row_count | 7 |
| answerable_row_count | 6 |
| precision_gain_count | 3 |
| precision_regression_count | 2 |
| recall_regression_count | 2 |
| correctness_regression_count | 1 |
| unsupported_regression_count | 1 |
| citation_count_reduction_count | 6 |
| adoption_blocker_count | 1 |
| mean_citation_count_delta | -3.166667 |
| mean_latency_ms_delta | -2558.989700 |
| adoption_decision | `reject_default_contract` |

## Failure Surface Distribution

| failure_surface | count |
| --- | ---: |
| citation_selection | 2 |
| generation_contract_candidate | 1 |
| latency_cost | 1 |
| no_regression | 3 |

## Query Diagnostic Rows

| query_id | query_type | failure_surface | tags | blocker | Correct delta | precision delta | recall delta | unsupported delta | citation count delta | latency delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| q-dev-no-answer-001 | no_answer | no_regression | latency_improvement | false | 0 | 0.000000 | 0.000000 | 0 | 0 | -0.001400 |
| q-dev-overview-001 | overview | no_regression | precision_gain, citation_count_reduction, latency_improvement | false | 0 | 0.400000 | 0.000000 | 0 | -3 | -1343.588500 |
| q-dev-place-fact-001 | place_fact | no_regression | precision_gain, citation_count_reduction, latency_improvement | false | 0 | 0.800000 | 0.000000 | 0 | -4 | -11115.052900 |
| q-dev-place-story-001 | place_story | generation_contract_candidate | correctness_regression, unsupported_claim_regression, precision_regression, recall_regression, citation_count_reduction, evidence_over_pruning_risk, latency_regression | true | -1 | -0.200000 | -0.125000 | 1 | -4 | 865.560700 |
| q-dev-relationship-001 | relationship | citation_selection | recall_regression, citation_count_reduction, latency_improvement | false | 0 | 0.000000 | -0.166667 | 0 | -2 | -8627.965300 |
| q-dev-route-context-001 | route_context | latency_cost | precision_gain, citation_count_reduction, latency_regression | false | 0 | 0.400000 | 0.000000 | 0 | -3 | 2198.617900 |
| q-dev-voice-followup-001 | voice_followup | citation_selection | precision_regression, citation_count_reduction, latency_regression | false | 0 | -0.300000 | 0.000000 | 0 | -3 | 109.501600 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 7 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `decision`: v2는 현재 기본 generation contract로 채택하지 않는다.
- `primary_tradeoff`: selected evidence contract가 citation count를 줄여 precision은 올렸지만, 일부 query에서 근거 충족률과 unsupported claim이 악화됐다.
- `portfolio_message`: 기법을 적용한 뒤 무조건 채택하지 않고, paired metric으로 채택 보류 판단을 내린 점을 강조한다.
- `data_boundary`: 이 분석은 query-level metric과 tag만 public에 남기며 raw answer/evidence/chunk text는 포함하지 않는다.
- `next_experiment`: `place_story` retrieval hard-case와 v2 selected evidence prompt repair를 분리한다.

## 결론

v2는 citation 수를 줄여 precision을 올린 positive case가 있지만, answerable query 중 correctness와 unsupported claim regression이 발생했다. 따라서 현재 v2는 기본 generation contract로 채택하지 않는다.

다음 실험은 청킹 재실험이 아니라 `place_story` hard-case와 selected evidence prompt repair를 분리해서 진행한다.
