# HyDE Subset Readiness

## 결론

`HD-HYDE-001A`는 live HyDE 비교 전 readiness gate다.

청킹 비교는 다시 열지 않는다. HyDE는 retrieval miss와 no-answer risk를 분리해 검증하는 비용성 실험 후보로만 둔다.

이 문서는 public-safe readiness 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| query_count | 5 |
| query_type_count | 4 |
| answerable_query_count | 4 |
| no_answer_query_count | 1 |
| hyde_candidate_query_count | 4 |
| no_answer_guard_query_count | 1 |
| baseline_retrieval_run_count | 5 |
| hyde_retrieval_run_count | 4 |
| expected_hyde_generation_live_call_count | 4 |
| live_call_hard_cap | 10 |
| hard_cap_exceeded | false |
| solar_call_count | 0 |
| cuda_required | false |
| readiness_decision | `ready_for_hyde_live_approval` |

## Query Plan

| query_id | query_type | baseline | hyde_candidate | live_call | no_answer_guard | readiness_status |
| --- | --- | --- | --- | ---: | --- | --- |
| `q-dev-place-story-001` | `place_story` | `dense_multilingual_e5_small_voice_rewrite_reference` | `solar_pro3_hyde_v1` | 1 | false | `ready_for_live_approval` |
| `q-dev-place-story-008` | `place_story` | `dense_multilingual_e5_small_voice_rewrite_reference` | `solar_pro3_hyde_v1` | 1 | false | `ready_for_live_approval` |
| `q-dev-relationship-008` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5_reference` | `solar_pro3_hyde_v1` | 1 | false | `ready_for_live_approval` |
| `q-dev-overview-010` | `overview` | `dense_multilingual_e5_small_voice_rewrite_reference` | `solar_pro3_hyde_v1` | 1 | false | `ready_for_live_approval` |
| `q-dev-no-answer-001` | `no_answer` | `abstain_first_v1` | `blocked_for_no_answer_guard` | 0 | true | `blocked_by_no_answer_guard` |

## 실행 경계

| boundary | value |
| --- | --- |
| live execution | disabled |
| model | `solar-pro3` |
| prompt policy | `solar-pro3-hyde-query-expansion-v1` |
| final citation | source child chunk only |
| no-answer policy | HyDE generation blocked |
| claim boundary | dev-readiness-only |

## 다음 작업

| priority | work_id | 작업 | 승인 필요 |
| ---: | --- | --- | --- |
| 완료 | `HD-HYDE-001B` | Solar Pro 3 HyDE live paired retrieval comparison | 완료 |
| 완료 | `HD-HYDE-001C` | HyDE larger dev subset readiness | 완료 |
| 완료 | `HD-HYDE-001D` | HyDE larger dev live paired retrieval comparison | 완료 |
| 1 | `HD-API-ROUTER-003` | active routing 적용 판단 계획 | 예 |
| 2 | `HD-API-ROUTER-003` | active routing 적용 판단 계획 | 예 |

## Claim Boundary

허용 표현:

- HyDE live 비교 전 subset, call budget, no-answer guard를 고정했다.
- readiness 단계에서 Solar Pro 3 live 호출은 0회다.
- 후속 live 비교는 별도 문서에서 실행했고, readiness 문서 자체는 성능 개선 증거가 아니다.

금지 표현:

- HyDE로 retrieval 성능이 개선됐다.
- no-answer hallucination 문제가 해결됐다.
- locked test 개선을 입증했다.
- production routing을 검증했다.
