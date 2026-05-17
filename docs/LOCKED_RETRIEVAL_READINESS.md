# Locked Retrieval Readiness

## 결론

`HD-LOCKED-RETRIEVAL-002`는 locked retrieval 실행 전 readiness gate다.

이번 단계에서는 검색, 임베딩, metric 계산, Solar Pro 3 호출을 실행하지 않는다. locked test는 최종 확인용이므로 실행 전 target resolvability, route 후보 수, no-answer guard, CUDA device, public-safe output만 검증한다.

이 문서는 public-safe readiness 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| planned_locked_query_count | 35 |
| locked_query_count | 35 |
| planned_query_type_count | 7 |
| query_type_count | 7 |
| expected_query_count_per_type | 5 |
| answerable_query_count | 30 |
| no_answer_query_count | 5 |
| allowed_candidate_count | 2 |
| rejected_candidate_count | 4 |
| target_resolvability_fail_count | 0 |
| no_answer_candidate_route_count | 0 |
| locked_metric_result_count | 0 |
| retrieval_execution_count | 0 |
| solar_call_count | 0 |
| cuda_required_for_future_run | true |
| resolved_device | `cuda` |
| readiness_decision | `ready_for_locked_retrieval_approval` |

## Query Type Route Plan

| query_type | locked_query_count | expected_candidate_count | route_policy_id | no_answer_guard |
| --- | ---: | ---: | --- | --- |
| place_fact | 5 | 1 | default_dense_voice_rewrite_v1 | false |
| place_story | 5 | 1 | default_dense_voice_rewrite_v1 | false |
| relationship | 5 | 2 | relationship_shadow_comparison_v1 | false |
| overview | 5 | 1 | default_dense_voice_rewrite_v1 | false |
| route_context | 5 | 1 | default_dense_voice_rewrite_v1 | false |
| voice_followup | 5 | 1 | default_dense_voice_rewrite_v1 | false |
| no_answer | 5 | 0 | no_answer_abstain_guard_v1 | true |

## Candidate Boundary

| candidate_id | status | scope | planned_query_count | execution_count |
| --- | --- | --- | ---: | ---: |
| dense_multilingual_e5_small_voice_rewrite | baseline_allowed | answerable_all | 30 | 0 |
| relationship_hybrid_weighted_e5_v1 | candidate_allowed_for_relationship_only | relationship_only | 5 | 0 |
| hyde_larger_live_candidate | rejected_for_locked_readiness | not_allowed | 0 | 0 |
| graphrag_lite_entity_path_v1 | rejected_for_locked_readiness | not_allowed | 0 | 0 |
| raptor_lite_summary_node_v1 | rejected_for_locked_readiness | not_allowed | 0 | 0 |
| place_story_guarded_boost_v1 | rejected_for_locked_readiness | not_allowed | 0 | 0 |

## 실행 경계

| boundary | value |
| --- | --- |
| locked retrieval execution | disabled |
| locked metric execution | disabled |
| Solar Pro 3 call | disabled |
| generation candidate | none |
| final citation source | source child chunk only in future run |
| no-answer policy | abstain guard, candidate route 0 |
| data mart grain for future run | `run_id + query_id + candidate_id + metric_name` |

## 다음 작업

| priority | work_id | 작업 | 승인 필요 |
| ---: | --- | --- | --- |
| 1 | `HD-LOCKED-RETRIEVAL-004` | locked retrieval paired comparison runner 실행 | 예 |
| 2 | `HD-COLBERT-001` | late interaction hard subset 검토 | 예 |

## Claim Boundary

| claim | allowed |
| --- | --- |
| locked retrieval 실행 전 준비 gate를 통과했다 | yes |
| readiness 단계에서 retrieval execution은 0회다 | yes |
| readiness 단계에서 Solar Pro 3 호출은 0회다 | yes |
| no-answer query는 candidate route로 보내지 않는다 | yes |
| locked test에서 retrieval 성능 개선을 입증했다 | no |
| active route가 기본 활성화됐다 | no |
| production 성능 검증이 끝났다 | no |
