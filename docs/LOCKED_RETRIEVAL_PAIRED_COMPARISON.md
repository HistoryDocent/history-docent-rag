# Locked Retrieval Paired Comparison

## 결론

`HD-LOCKED-RETRIEVAL-004`는 locked retrieval paired comparison 실행 결과다.

locked test 35개에서 기본 후보와 relationship 전용 후보를 실행했다. 비교는 사전 승인된 `dense_multilingual_e5_small_voice_rewrite`와 `relationship_hybrid_weighted_e5_v1`만 사용했다.

이 문서는 public-safe 결과 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 핵심 수치

| metric | value |
| --- | ---: |
| locked_query_count | 35 |
| answerable_query_count | 30 |
| no_answer_query_count | 5 |
| paired_query_count | 5 |
| baseline_retrieval_run_count | 30 |
| candidate_retrieval_run_count | 5 |
| false_hybrid_route_count | 0 |
| no_answer_candidate_route_count | 0 |
| live_solar_call_count | 0 |
| primary_metric_delta | -0.100000 |
| primary_metric_ci_low | -0.300000 |
| primary_metric_ci_high | 0.000000 |
| latency_p95_ms_delta | 7.370080 |
| locked_decision | `keep_shadow_without_locked_improvement_claim` |

## 판단

- locked 결과는 tuning에 사용하지 않는다.
- `relationship` subset 5개에서만 paired delta와 bootstrap CI를 계산했다.
- Solar Pro 3 호출은 없다.
- generation 품질 개선 주장은 이 결과만으로 하지 않는다.
