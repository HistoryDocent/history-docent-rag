# Portfolio Failure Analysis Report

## 목적

`HD-PORTFOLIO-002`는 제출용 포트폴리오에서 설명 가능한 실패 사례 10개를 public-safe aggregate로 정리한다.

이 리포트는 실패 분석과 다음 실험 설계 근거다. 청킹 개선, retrieval 개선, generation 개선, locked test 개선, production 성능 검증 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `portfolio-failure-analysis-report/v1` |
| run_id | `portfolio-failure-analysis-c10-688b2650` |
| work_id | `HD-PORTFOLIO-002` |
| generated_at_utc | `2026-05-17T03:54:07+00:00` |
| result_path | `<private artifact: portfolio_failure_analysis_rows.jsonl>` |
| live_solar_call_count_for_this_report | 0 |
| cuda_required | false |

## 정량 리포트

| metric | value |
| --- | ---: |
| case_count | 10 |
| unique_query_count | 10 |
| high_risk_count | 2 |
| medium_risk_count | 7 |
| low_risk_count | 1 |
| chunk_boundary_audit_candidate_count | 1 |
| query_type_misroute_count | 3 |
| retrieval_miss_count | 4 |
| generation_contract_gap_count | 1 |
| no_answer_risk_count | 1 |
| reopen_global_chunking_count | 0 |
| next_hyde_candidate_count | 6 |

## Category Breakdown

| primary_failure_category | count |
| --- | ---: |
| `retrieval_miss` | 4 |
| `query_type_misroute` | 3 |
| `chunk_boundary_risk` | 1 |
| `generation_contract_gap` | 1 |
| `no_answer_risk` | 1 |

## Stage Breakdown

| pipeline_stage | count |
| --- | ---: |
| `query_type_classifier` | 3 |
| `retrieval` | 3 |
| `chunking_retrieval_generation` | 1 |
| `generation` | 1 |
| `retrieval_generation_contract` | 1 |
| `retrieval_router` | 1 |

## Failure Cases

| case_id | query_id | query_type | split_scope | pipeline_stage | primary_failure_category | risk_level | claim_boundary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pf-failure-001` | `q-dev-place-fact-004` | `place_fact` | `dev-only` | `query_type_classifier` | `query_type_misroute` | `medium` | `dev-only` |
| `pf-failure-002` | `q-dev-overview-009` | `overview` | `dev-only` | `query_type_classifier` | `query_type_misroute` | `medium` | `dev-only` |
| `pf-failure-003` | `q-dev-place-fact-009` | `place_fact` | `dev-only` | `query_type_classifier` | `query_type_misroute` | `low` | `dev-only` |
| `pf-failure-004` | `q-dev-place-story-001` | `place_story` | `dev-only` | `chunking_retrieval_generation` | `chunk_boundary_risk` | `high` | `dev-only` |
| `pf-failure-005` | `q-dev-route-context-009` | `route_context` | `dev-only` | `retrieval` | `retrieval_miss` | `medium` | `dev-only` |
| `pf-failure-006` | `q-dev-place-story-008` | `place_story` | `dev-only` | `retrieval` | `retrieval_miss` | `medium` | `dev-only` |
| `pf-failure-007` | `q-dev-relationship-008` | `relationship` | `dev-only` | `retrieval_router` | `retrieval_miss` | `medium` | `dev-only` |
| `pf-failure-008` | `q-dev-overview-010` | `overview` | `dev-only` | `retrieval` | `retrieval_miss` | `medium` | `dev-input-only` |
| `pf-failure-009` | `q-dev-relationship-001` | `relationship` | `live-dev-subset` | `generation` | `generation_contract_gap` | `medium` | `live-dev-subset` |
| `pf-failure-010` | `q-dev-no-answer-001` | `no_answer` | `dev-only` | `retrieval_generation_contract` | `no_answer_risk` | `high` | `dev-only` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 10 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `analysis_scope`: 기존 public-safe report와 query id 단위 결과만 사용해 실패 원인을 분류했다.
- `chunking_decision`: 전역 청킹 재실험은 열지 않는다. chunk boundary 의심 1건은 targeted audit에서 전역 재청킹 근거가 아님을 확인했다.
- `retrieval_decision`: retrieval miss 4건은 HyDE 또는 route-specific retrieval 후보로 분리한다.
- `generation_decision`: generation contract gap은 Solar Pro 3 repaired v2 기본값 기각 근거로 유지한다.
- `no_answer_decision`: no-answer risk는 retriever 단독 문제가 아니라 answer abstain contract와 함께 검증한다.
- `security_boundary`: case row에는 query id, category, metric signal, next action만 남긴다.
- `execution_boundary`: 이번 리포트는 Solar Pro 3 호출과 CUDA 연산을 사용하지 않는다.
- `data_mart_grain`: fact_portfolio_failure_case grain은 run_id + case_id + query_id다.
- `gate_status`: PASS
- `external_audit`: 실패 분석은 개선 입증이 아니며 다음 실험의 범위를 줄이는 용도다.

## 해석

실패 사례는 전역 청킹 재설계보다 stage별 후속 실험으로 나누는 것이 맞다. 청킹은 C0를 유지하고, 특정 `place_story` grain miss는 targeted audit에서 전역 재청킹 근거가 아님을 확인했다. HyDE는 다음 실험 후보지만 아직 개선 주장이 아니다.
