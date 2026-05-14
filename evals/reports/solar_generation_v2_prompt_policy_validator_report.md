# Solar Pro 3 Generation v2 Prompt Policy Validator Report

## 목적

HD-SOLAR-025에서 repaired v2 prompt policy가 Solar Pro 3 live 호출 전에 selected evidence floor, risk aware selection, query type fallback 규칙을 만족하는지 검증한다.

이 리포트는 fake provider/validator 결과다. Solar Pro 3 호출, live generation 재평가, 청킹 비교 테스트는 수행하지 않았다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-generation-v2-prompt-policy-validator-report/v1` |
| validation_id | `solar-generation-v2-prompt-policy-validator-q7-8e96e7b2` |
| generated_at_utc | `2026-05-14T12:36:14+00:00` |
| source_plan | `docs/SOLAR_GENERATION_V2_PROMPT_REPAIR_PLAN.md` |
| validator_stage | `fake_provider_validator` |

## 정량 리포트

| metric | value |
| --- | ---: |
| row_count | 7 |
| query_type_policy_count | 7 |
| prompt_policy_count | 3 |
| pass_count | 6 |
| fallback_required_count | 1 |
| fail_count | 0 |
| invalid_rank_count | 0 |
| evidence_floor_violation_count | 0 |
| coverage_intent_violation_count | 0 |
| unsupported_risk_violation_count | 0 |
| no_answer_abstain_pass_count | 1 |
| live_solar_call_count | 0 |
| readiness_decision | `ready_for_repaired_prompt_dry_run` |

## Prompt Policy Distribution

| prompt_policy_id | count |
| --- | ---: |
| v2_repair_coverage_floor | 3 |
| v2_repair_query_type_router | 1 |
| v2_repair_risk_aware_selection | 3 |

## Query Type Breakdown

| query_type | rows | pass | fallback_required | fail | min_required_evidence |
| --- | ---: | ---: | ---: | ---: | ---: |
| no_answer | 1 | 1 | 0 | 0 | 0 |
| overview | 1 | 1 | 0 | 0 | 2 |
| place_fact | 1 | 1 | 0 | 0 | 1 |
| place_story | 1 | 0 | 1 | 0 | 2 |
| relationship | 1 | 1 | 0 | 0 | 2 |
| route_context | 1 | 1 | 0 | 0 | 1 |
| voice_followup | 1 | 1 | 0 | 0 | 2 |

## Validation Rows

| query_id | query_type | prompt_policy_id | status | selected | min_required | available | invalid_rank | tags |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| q-validator-place_fact-001 | place_fact | v2_repair_risk_aware_selection | pass | 1 | 1 | 3 | 0 | policy_pass |
| q-validator-place_story-001 | place_story | v2_repair_query_type_router | fallback_required | 2 | 2 | 3 | 0 | v1_fallback_required, monitor_only_query_type |
| q-validator-relationship-001 | relationship | v2_repair_coverage_floor | pass | 2 | 2 | 3 | 0 | policy_pass |
| q-validator-overview-001 | overview | v2_repair_coverage_floor | pass | 2 | 2 | 3 | 0 | policy_pass |
| q-validator-route_context-001 | route_context | v2_repair_risk_aware_selection | pass | 1 | 1 | 3 | 0 | policy_pass |
| q-validator-voice_followup-001 | voice_followup | v2_repair_coverage_floor | pass | 2 | 2 | 3 | 0 | policy_pass |
| q-validator-no_answer-001 | no_answer | v2_repair_risk_aware_selection | pass | 0 | 0 | 0 | 0 | no_answer_abstain_path |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 7 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `validator_scope`: selected evidence rank, query type별 evidence floor, fallback rule만 검증했다.
- `provider_boundary`: fake provider draft만 사용했고 Solar Pro 3 live API는 호출하지 않았다.
- `chunking_boundary`: target resolvability와 citation recoverability가 정상이라 청킹 비교를 재개하지 않는다.
- `data_grain`: fact grain은 repair_id-query_type-prompt_policy_id-eval_stage-metric_family다.
- `security_boundary`: public report에는 raw prompt, raw answer, raw evidence, query text, private path, secret을 저장하지 않는다.
- `next_action`: HD-SOLAR-026 repaired v2 dry-run/readiness runner를 구현한다.
- `gate_status`: PASS

## 결론

청킹 비교 테스트는 계속 보류한다.

repaired v2 prompt policy는 fake provider/validator 단계에서 fail 없이 통과했으며, `place_story`는 v1 fallback이 필요한 monitor case로 분리됐다. 다음 단계는 Solar Pro 3 live 호출 없이 repaired v2 dry-run/readiness runner를 구현하는 것이다.
