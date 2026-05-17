# Place Story Targeted Chunk Audit

## 결론

`q-dev-place-story-001`는 전체 청킹 비교를 다시 열 근거가 아니다.

target child와 parent는 chunk artifact 안에 모두 존재하고, child-parent membership과 citation ref도 유지된다. 따라서 현재 실패는 chunk 생성 손실이 아니라 retrieval rank, target grain, generation input 품질 문제로 보는 것이 맞다.

이 문서는 public-safe targeted audit이다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| audit_case_count | 1 |
| target_child_exists_rate | 1.000000 |
| target_parent_exists_rate | 1.000000 |
| target_child_parent_membership_rate | 1.000000 |
| target_child_citation_ref_rate | 1.000000 |
| target_child_page_range_valid_rate | 1.000000 |
| target_child_quality_flag_count | 1 |
| target_parent_quality_flag_count | 1 |
| chunk_generation_loss_count | 0 |
| chunk_boundary_defect_count | 0 |
| parser_noise_observed_count | 1 |
| retrieved_target_child_count | 0 |
| retrieved_target_parent_count | 0 |
| retrieved_target_doc_count | 1 |
| reopen_global_chunking_count | 0 |
| open_targeted_chunk_repair_count | 0 |
| live_solar_call_count_for_this_report | 0 |
| cuda_required | false |
| recommended_decision | `do_not_reopen_global_chunking` |

## Audit Row

| query_id | child_target | parent_target | doc_target | child_exists | parent_exists | membership | citation_ref | page_valid | parser_noise | retrieved_child | retrieved_parent | retrieved_doc | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| `q-dev-place-story-001` | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 3 | true | false | false | true | `do_not_reopen_global_chunking` |

## 판단

전역 청킹 재실험은 열지 않는다.

근거:

| check | result |
| --- | --- |
| target_child_exists_rate | `1.000000` |
| target_parent_exists_rate | `1.000000` |
| target_child_parent_membership_rate | `1.000000` |
| target_child_citation_ref_rate | `1.000000` |
| retrieval coverage | target doc only |
| parser noise | observed, not chunk generation loss |

## 다음 작업

| priority | work_id | 작업 | 이유 |
| ---: | --- | --- | --- |
| 완료 | `HD-HYDE-001D` | HyDE larger dev live paired retrieval comparison | place_story Recall@5는 개선됐지만 전체 HyDE 기본 route는 기각했다. |
| 1 | `HD-API-ROUTER-003` | active routing 적용 판단 계획 | HyDE 대신 기존 classifier/router/guard 후보를 기준으로 판단한다. |
| 2 | `HD-API-ROUTER-003` | active routing 적용 판단 계획 | guarded route dry-run 이후에도 active 적용은 별도 gate가 필요하다. |

## Claim Boundary

허용 표현:

- `q-dev-place-story-001`의 target child/parent는 chunk artifact에 존재한다.
- 이 사례는 현재 증거상 전역 청킹 재실험 근거가 아니다.
- parser noise는 관찰됐지만 chunk boundary defect로 단정하지 않는다.

금지 표현:

- 청킹 문제가 해결됐다.
- retrieval 문제가 해결됐다.
- HyDE가 성능을 개선했다.
- locked test 개선을 입증했다.
