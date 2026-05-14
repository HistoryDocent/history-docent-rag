# Solar Pro 3 Generation v2 Repaired Dry-run Readiness Report

## 목적

HD-SOLAR-026에서 repaired v2 prompt policy를 Solar Pro 3 live paired comparison에 넣기 전에 route, fallback, 예상 live call budget, public-safe gate를 검증한다.

이 리포트는 dry-run readiness 결과다. Solar Pro 3 live 호출은 수행하지 않았고 raw query, raw evidence, raw prompt, raw answer, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-generation-v2-repaired-dry-run-readiness-report/v1` |
| readiness_id | `solar-generation-v2-repaired-dry-run-q7-51a6d716` |
| generated_at_utc | `2026-05-14T12:45:07+00:00` |
| source_plan | `docs/SOLAR_GENERATION_V2_PROMPT_REPAIR_PLAN.md` |
| validation_id | `solar-generation-v2-prompt-policy-validator-q7-8e96e7b2` |
| repair_id | `solar_generation_v2_repaired_prompt_policy_v1` |
| model_id | `solar-pro3` |
| provider_config_id_alias | `<solar-pro3-repaired-v2-live-config>` |
| endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| answer_contract_version | `citation-rag-answer/v2` |
| baseline_answer_policy_id | `solar-generation-v1-baseline` |
| repaired_answer_policy_id | `solar-generation-v2-repaired` |
| system_prompt_version | `solar-pro3-citation-rag-draft-v2-repaired` |
| resolved_device | `cuda` |

## 정량 리포트

| metric | value |
| --- | ---: |
| expected_query_count | 7 |
| query_count | 7 |
| query_type_count | 7 |
| validation_pass_count | 6 |
| validation_fallback_required_count | 1 |
| validation_fail_count | 0 |
| repaired_candidate_route_count | 5 |
| v1_fallback_route_count | 1 |
| blocked_route_count | 0 |
| baseline_live_call_count | 6 |
| repaired_candidate_live_call_count | 5 |
| no_answer_live_call_count | 0 |
| expected_total_live_call_count | 11 |
| live_call_hard_cap | 20 |
| live_execution_requested | False |
| live_execution_confirmed | False |
| hard_cap_exceeded | False |
| solar_call_count | 0 |
| readiness_decision | `ready_for_repaired_v2_live_approval` |

## Route Decision Distribution

| route_decision | count |
| --- | ---: |
| `abstain_no_live_call` | 1 |
| `use_repaired_v2_candidate` | 5 |
| `use_v1_fallback` | 1 |

## Reuse Decision Distribution

| reuse_decision | count |
| --- | ---: |
| `baseline_and_repaired_live_call_required` | 5 |
| `baseline_only_v1_fallback` | 1 |
| `no_live_call_required` | 1 |

## Query Type Breakdown

| query_type | rows | route_decision | expected_live_call_count |
| --- | ---: | --- | ---: |
| no_answer | 1 | `abstain_no_live_call` | 0 |
| overview | 1 | `use_repaired_v2_candidate` | 2 |
| place_fact | 1 | `use_repaired_v2_candidate` | 2 |
| place_story | 1 | `use_v1_fallback` | 1 |
| relationship | 1 | `use_repaired_v2_candidate` | 2 |
| route_context | 1 | `use_repaired_v2_candidate` | 2 |
| voice_followup | 1 | `use_repaired_v2_candidate` | 2 |

## Query-level Sanitized Readiness

| query_id | query_type | prompt_policy_id | validation | route | reuse | baseline_call | repaired_call | expected_calls | selected | min_required | tags |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `q-dev-place-fact-001` | place_fact | `v2_repair_risk_aware_selection` | `pass` | `use_repaired_v2_candidate` | `baseline_and_repaired_live_call_required` | True | True | 2 | 1 | 1 | policy_pass |
| `q-dev-place-story-001` | place_story | `v2_repair_query_type_router` | `fallback_required` | `use_v1_fallback` | `baseline_only_v1_fallback` | True | False | 1 | 2 | 2 | v1_fallback_required, monitor_only_query_type |
| `q-dev-relationship-001` | relationship | `v2_repair_coverage_floor` | `pass` | `use_repaired_v2_candidate` | `baseline_and_repaired_live_call_required` | True | True | 2 | 2 | 2 | policy_pass |
| `q-dev-overview-001` | overview | `v2_repair_coverage_floor` | `pass` | `use_repaired_v2_candidate` | `baseline_and_repaired_live_call_required` | True | True | 2 | 2 | 2 | policy_pass |
| `q-dev-route-context-001` | route_context | `v2_repair_risk_aware_selection` | `pass` | `use_repaired_v2_candidate` | `baseline_and_repaired_live_call_required` | True | True | 2 | 1 | 1 | policy_pass |
| `q-dev-voice-followup-001` | voice_followup | `v2_repair_coverage_floor` | `pass` | `use_repaired_v2_candidate` | `baseline_and_repaired_live_call_required` | True | True | 2 | 2 | 2 | policy_pass |
| `q-dev-no-answer-001` | no_answer | `v2_repair_risk_aware_selection` | `pass` | `abstain_no_live_call` | `no_live_call_required` | False | False | 0 | 0 | 0 | no_answer_abstain_path |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 8 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: 기존 7개 query type dev subset 구조에서 repaired v2 route와 call budget만 검증했다.
- `llm_call_boundary`: readiness dry-run 단계라 Solar Pro 3 live 호출은 수행하지 않았고 solar_call_count는 0이다.
- `fallback_policy`: place_story는 repaired v2 성공률 계산에서 분리하고 v1 fallback route로 둔다.
- `no_answer_policy`: no_answer는 abstain path를 유지하며 live call을 요구하지 않는다.
- `call_budget`: expected_total_live_call_count=11, hard_cap=20로 제한한다.
- `data_mart_grain`: `fact_solar_generation_v2_repaired_readiness`의 grain은 repair_id-query_id-query_type-prompt_policy_id-route_decision이다.
- `security_boundary`: public artifact에는 raw query, raw evidence, raw prompt, raw answer, chunk text, private path, secret을 기록하지 않는다.
- `external_audit`: route, call budget, public-safe gate가 분리되어 있어 live 품질 개선 주장으로 과장되지 않는다.
- `next_action`: 별도 승인 후 repaired v2 Solar Pro 3 live paired comparison 실행 여부를 결정한다.

## 결론

readiness gate를 통과했다.

이 결과는 live 품질 개선 주장이 아니라, repaired v2 live paired comparison 실행 전 route, fallback, call budget, public-safe boundary가 계획 범위 안에 있다는 검증이다.
