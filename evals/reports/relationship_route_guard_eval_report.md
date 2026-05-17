# Relationship Route Guard Eval Report

## 목적

`HD-CLASSIFIER-005`는 classifier가 `relationship`을 예측했을 때 hybrid route로 바로 보내기 전 보수적 guard가 false hybrid route를 줄이는지 검증한다.

이 문서는 classifier/router guard 평가다. active routing 적용, retrieval 성능 개선, locked test 개선, Solar Pro 3 답변 품질 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `relationship-route-guard-eval-report/v1` |
| run_id | `relationship-route-guard-q70-86617baa` |
| classifier_id | `deterministic_query_type_classifier_v1` |
| guard_policy_id | `relationship-route-guard-v1` |
| generated_at_utc | `2026-05-17T01:25:08+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| dataset_fingerprint | `224e3cad1c078eeb` |
| result_path | `<private artifact: relationship_route_guard_eval_rows.jsonl>` |
| solar_call_count | 0 |
| cuda_required | false |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 70 |
| baseline_correct_count | 67 |
| guarded_correct_count | 69 |
| baseline_accuracy | 0.957143 |
| guarded_accuracy | 0.985714 |
| accuracy_delta | 0.028571 |
| baseline_route_policy_correct_count | 68 |
| guarded_route_policy_correct_count | 70 |
| baseline_route_policy_accuracy | 0.971429 |
| guarded_route_policy_accuracy | 1.000000 |
| route_policy_accuracy_delta | 0.028571 |
| baseline_false_hybrid_route_count | 2 |
| guarded_false_hybrid_route_count | 0 |
| false_hybrid_route_delta | -2 |
| baseline_missed_hybrid_route_count | 0 |
| guarded_missed_hybrid_route_count | 0 |
| no_answer_route_regression_count | 0 |
| guard_applied_count | 2 |
| active_route_applied_count | 0 |

## Guard Tag Breakdown

| tag | count |
| --- | ---: |
| `not_relationship_prediction` | 58 |
| `allow_strong_relationship_intent` | 10 |
| `block_fact_reason_risk` | 1 |
| `block_overview_tie_risk` | 1 |
| `block_weak_relationship_intent` | 1 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 70 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `guard_scope`: `relationship` 예측에만 보수적 guard를 적용한다. 다른 query type은 변경하지 않는다.
- `guard_effect`: false hybrid route는 2건에서 0건으로 변했다.
- `regression_boundary`: missed hybrid, no-answer route regression, route policy accuracy regression을 gate로 본다.
- `api_boundary`: 이번 평가는 active route 적용이 아니다. API active_route_applied는 0이어야 한다.
- `security_boundary`: result row와 report에는 query id, label, route id, score, guard tag만 저장한다.
- `execution_boundary`: deterministic CPU 평가다. Solar Pro 3 호출과 CUDA 연산을 사용하지 않는다.
- `data_mart_grain`: fact_relationship_route_guard_eval grain은 run_id + query_id + guard_policy_id다.
- `gate_status`: PASS
- `external_audit`: guard가 false hybrid를 줄여도 production routing 완료로 표현하면 안 된다.

## 해석

relationship route guard는 active route 적용 전 안전장치다. 이번 결과가 좋아도 production routing 완료나 최종 성능 개선으로 표현하지 않는다.

다음 단계는 API dry-run field에 guarded route 후보를 노출하거나, 더 넓은 dev/test set에서 guard regression을 확인하는 것이다.
