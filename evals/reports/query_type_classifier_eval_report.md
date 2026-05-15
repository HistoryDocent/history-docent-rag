# Query Type Classifier Eval Report

## 목적

실제 API 입력에서 query type label이 직접 주어지지 않는다는 전제를 검증하기 위해 deterministic classifier baseline을 평가한다.

이 문서는 classifier contract와 라우팅 입력 품질 평가다. 검색 성능 개선, locked test 개선, Solar Pro 3 답변 품질 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `query-type-classifier-eval-report/v1` |
| run_id | `query-type-classifier-deterministic_query_type_classifier_v1-q70-973c17ea` |
| classifier_id | `deterministic_query_type_classifier_v1` |
| generated_at_utc | `2026-05-14T15:06:44+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| dataset_fingerprint | `224e3cad1c078eeb` |
| result_path | `<private artifact: query_type_classifier_eval_rows.jsonl>` |
| solar_call_count | 0 |
| cuda_required | false |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 70 |
| query_type_count | 7 |
| correct_count | 67 |
| accuracy | 0.957143 |
| macro_precision | 0.963203 |
| macro_recall | 0.957143 |
| macro_f1 | 0.956818 |
| route_policy_correct_count | 68 |
| route_policy_accuracy | 0.971429 |
| fallback_count | 0 |
| fallback_rate | 0.000000 |
| min_confidence | 0.560417 |
| average_confidence | 0.916869 |

## Query Type Breakdown

| query_type | support | predicted_count | true_positive_count | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `place_fact` | 10 | 8 | 8 | 1.000000 | 0.800000 | 0.888889 |
| `place_story` | 10 | 11 | 10 | 0.909091 | 1.000000 | 0.952381 |
| `relationship` | 10 | 12 | 10 | 0.833333 | 1.000000 | 0.909091 |
| `overview` | 10 | 9 | 9 | 1.000000 | 0.900000 | 0.947368 |
| `route_context` | 10 | 10 | 10 | 1.000000 | 1.000000 | 1.000000 |
| `voice_followup` | 10 | 10 | 10 | 1.000000 | 1.000000 | 1.000000 |
| `no_answer` | 10 | 10 | 10 | 1.000000 | 1.000000 | 1.000000 |

## Confusion Matrix

| expected_query_type | predicted_query_type | count |
| --- | --- | ---: |
| `place_fact` | `place_fact` | 8 |
| `place_fact` | `place_story` | 1 |
| `place_fact` | `relationship` | 1 |
| `place_story` | `place_story` | 10 |
| `relationship` | `relationship` | 10 |
| `overview` | `relationship` | 1 |
| `overview` | `overview` | 9 |
| `route_context` | `route_context` | 10 |
| `voice_followup` | `voice_followup` | 10 |
| `no_answer` | `no_answer` | 10 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 70 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `classifier_scope`: deterministic rules로 query type label을 추정하는 baseline contract 평가다.
- `router_impact`: exact label과 별도로 route policy accuracy를 기록해 default route 내부 오분류와 relationship/no_answer route 오분류를 분리했다.
- `security_boundary`: public row와 report에는 query id, query type label, metric만 저장한다.
- `execution_boundary`: 이번 classifier는 Solar Pro 3 호출과 CUDA 연산을 사용하지 않는다.
- `data_mart_grain`: fact_query_type_classification grain은 run_id + query_id + classifier_id다.
- `gate_status`: PASS
- `external_audit`: classifier는 구현됐지만 production routing 품질이나 locked 성능 개선 주장은 아니다.

## 해석

이 classifier는 Solar Pro 3나 CUDA를 사용하지 않는 deterministic baseline이다. 현재 router skeleton을 실제 API 입력과 연결하기 위한 최소 gate로만 해석한다.

후속 작업에서 오분류 query type이 retrieval 성능을 실제로 떨어뜨리는지 확인해야 한다. 특히 relationship/no_answer 오분류는 route policy 자체가 달라지므로 failure analysis 우선순위가 높다.
