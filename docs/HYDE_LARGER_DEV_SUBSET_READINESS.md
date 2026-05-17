# HyDE Larger Dev Subset Readiness

## 결론

`HD-HYDE-001C`는 HyDE larger dev subset live 비교 전 readiness gate다.

청킹 비교는 다시 열지 않는다. 이번 단계는 dev 70 중 HyDE 후보성이 있는 query type만 확대하고 Solar Pro 3 호출 예산과 no-answer guard를 고정한다.

이 문서는 public-safe readiness 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| query_count | 40 |
| target_query_type_count | 4 |
| expected_query_count_per_type | 10 |
| answerable_query_count | 30 |
| no_answer_query_count | 10 |
| hyde_candidate_query_count | 30 |
| no_answer_guard_query_count | 10 |
| expected_hyde_generation_live_call_count | 30 |
| live_call_hard_cap | 40 |
| hard_cap_exceeded | false |
| solar_call_count | 0 |
| cuda_required | false |
| readiness_decision | `ready_for_hyde_larger_live_approval` |

## Query Type Plan

| query_type | query_count | answerable | no_answer | expected_live_call | no_answer_guard | baseline | hyde_candidate |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `overview` | 10 | 10 | 0 | 10 | 0 | `dense_multilingual_e5_small_voice_rewrite_reference` | `solar_pro3_hyde_v1` |
| `place_story` | 10 | 10 | 0 | 10 | 0 | `dense_multilingual_e5_small_voice_rewrite_reference` | `solar_pro3_hyde_v1` |
| `relationship` | 10 | 10 | 0 | 10 | 0 | `hybrid_weighted_e5_small_alpha_0_5_reference` | `solar_pro3_hyde_v1` |
| `no_answer` | 10 | 0 | 10 | 0 | 10 | `abstain_first_v1` | `blocked_for_no_answer_guard` |

## 실행 경계

| boundary | value |
| --- | --- |
| live execution | disabled |
| model | `solar-pro3` |
| prompt policy | `solar-pro3-hyde-query-expansion-v1` |
| selection strategy | `hyde_larger_dev_subset_v1_q10_per_type` |
| resolved_device | `cuda` |
| final citation | source child chunk only |
| no-answer policy | HyDE generation blocked |
| claim boundary | larger-dev-readiness-only |

## 다음 작업

| priority | work_id | 작업 | 승인 필요 |
| ---: | --- | --- | --- |
| 완료 | `HD-HYDE-001D` | HyDE larger dev live paired retrieval comparison | 완료 |
| 1 | `HD-API-ROUTER-003` | active routing 적용 판단 계획 | 예 |

## Claim Boundary

| claim | allowed |
| --- | --- |
| HyDE larger live 비교 전 query type 범위와 call budget을 고정했다 | yes |
| readiness 단계에서 Solar Pro 3 live 호출은 0회다 | yes |
| no-answer query 10개는 HyDE generation 후보에서 차단했다 | yes |
| HyDE로 최종 retrieval 성능이 개선됐다 | no |
| no-answer hallucination 문제가 해결됐다 | no |
| locked test 개선을 입증했다 | no |
| production routing을 검증했다 | no |
