# HyDE Live Paired Retrieval Comparison

## 결론

`HD-HYDE-001B`는 Solar Pro 3 HyDE live paired retrieval comparison이다.

이 문서는 HyDE 성능 개선 확정 주장이 아니다. dev subset 5개에서 baseline route와 HyDE query expansion 후보를 같은 target judgment로 비교한 결과다.

raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| query_count | 5 |
| answerable_query_count | 4 |
| no_answer_query_count | 1 |
| baseline_retrieval_run_count | 5 |
| hyde_retrieval_run_count | 4 |
| hyde_generation_request_count | 4 |
| no_answer_guard_query_count | 1 |
| solar_api_call_count | 4 |
| live_call_hard_cap | 10 |
| Recall@5 delta | 0.250000 |
| MRR delta | -0.062500 |
| nDCG@5 delta | 0.015402 |
| latency_p95_ms delta | 1499.894500 |
| adoption_decision | `keep_hyde_candidate_for_larger_eval` |

## Candidate Summary

| candidate | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.250000 | 0.250000 | 0.250000 | 0.250000 | 0.250000 | 297.450600 |
| HyDE | 0.000000 | 0.250000 | 0.500000 | 0.187500 | 0.265402 | 1797.345100 |

## Query Pair Rows

| query_id | query_type | baseline_rank | hyde_rank | baseline@5 | hyde@5 | no_answer_guard | hyde_call |
| --- | --- | ---: | ---: | --- | --- | --- | ---: |
| `q-dev-place-story-001` | `place_story` | 0 | 0 | false | false | false | 1 |
| `q-dev-place-story-008` | `place_story` | 0 | 0 | false | false | false | 1 |
| `q-dev-relationship-008` | `relationship` | 1 | 4 | true | true | false | 1 |
| `q-dev-overview-010` | `overview` | 0 | 2 | false | true | false | 1 |
| `q-dev-no-answer-001` | `no_answer` | 0 | 0 | false | false | true | 0 |

## 실행 경계

| boundary | value |
| --- | --- |
| readiness_id | `hyde-subset-readiness-q5-c4-b74ec047069e` |
| model | `solar-pro3` |
| prompt_policy | `solar-pro3-hyde-query-expansion-v1` |
| provider | `solar_pro_3` |
| resolved_device | `cuda` |
| final citation | source child chunk only |
| no-answer policy | HyDE generation blocked |
| claim boundary | live-dev-subset |

## Claim Boundary

| claim | allowed |
| --- | --- |
| HyDE live paired retrieval comparison을 dev subset 5개에서 실행했다 | yes |
| no-answer query는 HyDE generation과 retrieval에서 차단했다 | yes |
| Solar Pro 3 HyDE generation request는 4회다 | yes |
| HyDE로 최종 retrieval 성능이 개선됐다 | no |
| no-answer hallucination 문제가 해결됐다 | no |
| locked test 개선을 입증했다 | no |
| production routing을 검증했다 | no |
