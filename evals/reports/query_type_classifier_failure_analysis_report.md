# Query Type Classifier Failure Analysis Report

## 목적

`HD-ROUTER-003` classifier baseline에서 남은 오분류가 router policy를 실제로 바꾸는지 분리해서 기록한다.

이 문서는 failure analysis와 route impact 점검이다. classifier 개선, retrieval 성능 개선, locked test 개선, Solar Pro 3 답변 품질 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `query-type-classifier-failure-analysis-report/v1` |
| run_id | `query-type-classifier-failure-q70-f3-d5947030` |
| classifier_id | `deterministic_query_type_classifier_v1` |
| generated_at_utc | `2026-05-15T13:51:26+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| dataset_fingerprint | `224e3cad1c078eeb` |
| result_path | `<private artifact: query_type_classifier_failure_analysis_rows.jsonl>` |
| solar_call_count | 0 |
| cuda_required | false |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 70 |
| failure_count | 3 |
| failure_rate | 0.042857 |
| route_risk_failure_count | 2 |
| route_risk_failure_rate | 0.028571 |
| default_route_internal_failure_count | 1 |
| false_hybrid_route_count | 2 |
| missed_hybrid_route_count | 0 |
| false_abstain_count | 0 |
| missed_abstain_count | 0 |
| no_answer_failure_count | 0 |
| fallback_failure_count | 0 |
| high_confidence_failure_count | 0 |
| min_failure_confidence | 0.633333 |
| average_failure_confidence | 0.756250 |

## Failure Rows

| query_id | expected_query_type | predicted_query_type | route_policy_changed | confidence | score_margin | impact_level | failure_tags |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `q-dev-place-fact-004` | `place_fact` | `relationship` | true | 0.843750 | 1.450000 | `medium` | `route_policy_changed, false_hybrid_route, relationship_over_trigger` |
| `q-dev-place-fact-009` | `place_fact` | `place_story` | false | 0.791667 | 1.200000 | `low` | `default_route_internal, default_intent_boundary` |
| `q-dev-overview-009` | `overview` | `relationship` | true | 0.633333 | 0.000000 | `medium` | `route_policy_changed, false_hybrid_route, relationship_over_trigger` |

## Failure Tag Breakdown

| tag | count |
| --- | ---: |
| `false_hybrid_route` | 2 |
| `relationship_over_trigger` | 2 |
| `route_policy_changed` | 2 |
| `default_intent_boundary` | 1 |
| `default_route_internal` | 1 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 3 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `analysis_scope`: classifier를 재학습하거나 규칙 수정하지 않고 남은 오분류의 route impact만 분석했다.
- `route_impact`: 2건은 route policy가 바뀌는 오분류다. 1건은 default route 내부 오분류다.
- `highest_risk`: no_answer 관련 오분류는 없었다. 현재 위험은 default query가 relationship hybrid route로 잘못 이동하는 false hybrid route다.
- `recommended_guard`: relationship route는 active 적용 전에 score margin, 명시적 관계 표현, 다중 장소 신호를 함께 요구하는 보수적 guard가 필요하다.
- `api_rollout`: 다음 API 작업은 active routing이 아니라 classifier/router dry-run field 노출로 제한한다.
- `security_boundary`: failure row와 report에는 query id, label, route id, score, tag만 저장한다.
- `execution_boundary`: 이번 분석은 Solar Pro 3 호출과 CUDA 연산을 사용하지 않는다.
- `data_mart_grain`: fact_query_type_classifier_failure grain은 run_id + failure_id + query_id다.
- `gate_status`: PASS
- `external_audit`: classifier baseline은 통과했지만 route-risk failure가 남아 있어 production routing 완성으로 표현하면 안 된다.

## 해석

오분류는 exact label 관점과 route policy 관점이 다르다. 같은 default route 안에서 label만 틀린 경우는 retrieval 후보가 바뀌지 않지만, default query가 relationship route로 잘못 이동하면 hybrid route가 실행될 수 있다.

따라서 다음 API 연결은 active route 변경이 아니라 dry-run field로 먼저 넣는 것이 맞다. 실제 route 적용은 route-risk failure를 줄이는 보수적 guard를 추가한 뒤 별도 gate로 판단한다.
