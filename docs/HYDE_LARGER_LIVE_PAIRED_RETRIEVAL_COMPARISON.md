# HyDE Larger Live Paired Retrieval Comparison

## 결론

`HD-HYDE-001D`는 Solar Pro 3 HyDE larger dev live paired retrieval comparison이다.

이 문서는 최종 성능 개선 주장이 아니다. `HD-HYDE-001C`에서 고정한 dev 40개 query로 baseline route와 HyDE query expansion 후보를 같은 target judgment로 비교한 결과다.

raw query, raw answer, raw evidence, raw HyDE text, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| query_count | 40 |
| answerable_query_count | 30 |
| no_answer_query_count | 10 |
| baseline_retrieval_run_count | 40 |
| hyde_retrieval_run_count | 30 |
| hyde_generation_request_count | 30 |
| no_answer_guard_query_count | 10 |
| solar_api_call_count | 30 |
| live_call_hard_cap | 40 |
| Recall@5 delta | 0.033333 |
| MRR delta | -0.035000 |
| nDCG@5 delta | -0.018384 |
| latency_p95_ms delta | 1855.705900 |
| adoption_decision | `reject_hyde_for_now` |

## Candidate Summary

| candidate | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.666667 | 0.800000 | 0.800000 | 0.727778 | 0.746426 | 23.188300 |
| HyDE | 0.600000 | 0.766667 | 0.833333 | 0.692778 | 0.728042 | 1878.894200 |

## Query Type Delta

| query_type | query_count | baseline Recall@5 | HyDE Recall@5 | Recall@5 delta | baseline MRR | HyDE MRR | MRR delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `no_answer` | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| `overview` | 10 | 0.800000 | 0.900000 | 0.100000 | 0.750000 | 0.703333 | -0.046667 |
| `place_story` | 10 | 0.600000 | 0.800000 | 0.200000 | 0.600000 | 0.725000 | 0.125000 |
| `relationship` | 10 | 1.000000 | 0.800000 | -0.200000 | 0.833333 | 0.650000 | -0.183333 |

## Query Pair Rows

| query_id | query_type | baseline_rank | hyde_rank | baseline@5 | hyde@5 | no_answer_guard | hyde_call |
| --- | --- | ---: | ---: | --- | --- | --- | ---: |
| `q-dev-no-answer-001` | `no_answer` | 0 | 0 | false | false | true | 0 |
| `q-dev-no-answer-002` | `no_answer` | 0 | 0 | false | false | true | 0 |
| `q-dev-no-answer-003` | `no_answer` | 0 | 0 | false | false | true | 0 |
| `q-dev-no-answer-004` | `no_answer` | 0 | 0 | false | false | true | 0 |
| `q-dev-no-answer-005` | `no_answer` | 0 | 0 | false | false | true | 0 |
| `q-dev-no-answer-006` | `no_answer` | 0 | 0 | false | false | true | 0 |
| `q-dev-no-answer-007` | `no_answer` | 0 | 0 | false | false | true | 0 |
| `q-dev-no-answer-008` | `no_answer` | 0 | 0 | false | false | true | 0 |
| `q-dev-no-answer-009` | `no_answer` | 0 | 0 | false | false | true | 0 |
| `q-dev-no-answer-010` | `no_answer` | 0 | 0 | false | false | true | 0 |
| `q-dev-overview-001` | `overview` | 1 | 1 | true | true | false | 1 |
| `q-dev-overview-002` | `overview` | 1 | 1 | true | true | false | 1 |
| `q-dev-overview-003` | `overview` | 1 | 3 | true | true | false | 1 |
| `q-dev-overview-004` | `overview` | 1 | 1 | true | true | false | 1 |
| `q-dev-overview-005` | `overview` | 0 | 0 | false | false | false | 1 |
| `q-dev-overview-006` | `overview` | 1 | 1 | true | true | false | 1 |
| `q-dev-overview-007` | `overview` | 1 | 2 | true | true | false | 1 |
| `q-dev-overview-008` | `overview` | 2 | 5 | true | true | false | 1 |
| `q-dev-overview-009` | `overview` | 1 | 1 | true | true | false | 1 |
| `q-dev-overview-010` | `overview` | 0 | 1 | false | true | false | 1 |
| `q-dev-place-story-001` | `place_story` | 0 | 0 | false | false | false | 1 |
| `q-dev-place-story-002` | `place_story` | 1 | 1 | true | true | false | 1 |
| `q-dev-place-story-003` | `place_story` | 1 | 1 | true | true | false | 1 |
| `q-dev-place-story-004` | `place_story` | 1 | 1 | true | true | false | 1 |
| `q-dev-place-story-005` | `place_story` | 0 | 4 | false | true | false | 1 |
| `q-dev-place-story-006` | `place_story` | 1 | 1 | true | true | false | 1 |
| `q-dev-place-story-007` | `place_story` | 1 | 1 | true | true | false | 1 |
| `q-dev-place-story-008` | `place_story` | 0 | 0 | false | false | false | 1 |
| `q-dev-place-story-009` | `place_story` | 0 | 1 | false | true | false | 1 |
| `q-dev-place-story-010` | `place_story` | 1 | 1 | true | true | false | 1 |
| `q-dev-relationship-001` | `relationship` | 3 | 2 | true | true | false | 1 |
| `q-dev-relationship-002` | `relationship` | 1 | 1 | true | true | false | 1 |
| `q-dev-relationship-003` | `relationship` | 1 | 1 | true | true | false | 1 |
| `q-dev-relationship-004` | `relationship` | 2 | 2 | true | true | false | 1 |
| `q-dev-relationship-005` | `relationship` | 1 | 2 | true | true | false | 1 |
| `q-dev-relationship-006` | `relationship` | 1 | 1 | true | true | false | 1 |
| `q-dev-relationship-007` | `relationship` | 1 | 1 | true | true | false | 1 |
| `q-dev-relationship-008` | `relationship` | 1 | 0 | true | false | false | 1 |
| `q-dev-relationship-009` | `relationship` | 2 | 0 | true | false | false | 1 |
| `q-dev-relationship-010` | `relationship` | 1 | 1 | true | true | false | 1 |

## 실행 경계

| boundary | value |
| --- | --- |
| readiness_id | `hyde-larger-dev-readiness-q40-c30-d01462ab869e` |
| model | `solar-pro3` |
| prompt_policy | `solar-pro3-hyde-query-expansion-v1` |
| provider | `solar_pro_3` |
| endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| resolved_device | `cuda` |
| chunking baseline | `C0 parent-child` |
| final citation | source child chunk only |
| no-answer policy | HyDE generation blocked |
| claim boundary | larger-live-dev-only |

## Claim Boundary

| claim | allowed |
| --- | --- |
| HyDE larger live paired retrieval comparison을 dev 40개에서 실행했다 | yes |
| no-answer query 10개는 HyDE generation과 retrieval에서 차단했다 | yes |
| Solar Pro 3 HyDE generation request 수를 기록했다 | yes |
| HyDE를 production 기본 retrieval route로 채택했다 | no |
| locked test 개선을 입증했다 | no |
| no-answer hallucination 문제가 해결됐다 | no |
