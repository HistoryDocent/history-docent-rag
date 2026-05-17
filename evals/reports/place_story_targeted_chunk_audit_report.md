# Place Story Targeted Chunk Audit Report

## 목적

`HD-CHUNK-AUDIT-001`은 `q-dev-place-story-001`의 child/parent grain 손실이 청킹 생성 문제인지 확인한다.

이 리포트는 청킹 개선, retrieval 개선, generation 개선, locked test 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `place-story-targeted-chunk-audit-report/v1` |
| audit_id | `place-story-targeted-chunk-audit-1a430af1d1ecb13d` |
| work_id | `HD-CHUNK-AUDIT-001` |
| generated_at_utc | `2026-05-17T03:54:08+00:00` |
| query_id | `q-dev-place-story-001` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private artifact: parent_child_chunks.json>` |
| hard_case_rows | `<private artifact: place_story_hard_case_analysis_rows.jsonl>` |
| result_path | `<private artifact: place_story_targeted_chunk_audit_rows.jsonl>` |
| source_fingerprint | `f5df96ea6701c558` |

## 정량 리포트

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

## Audit Detail

| query_id | query_type | target_child_count | target_parent_count | target_doc_count | child_exists | parent_exists | membership | citation_ref | page_valid | child_quality_flags | parent_quality_flags | child_len_min | child_len_max | parent_child_count_min | parent_child_count_max | retrieved_child | retrieved_parent | retrieved_doc | min_retrieval_rank | min_pack_rank | hard_case_root_cause | audit_decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: | ---: | --- | --- |
| `q-dev-place-story-001` | `place_story` | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 3 | 1 | 1 | 295 | 837 | 1 | 4 | false | false | true | 5 | 5 | `target_grain_mismatch` | `do_not_reopen_global_chunking` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 1 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `analysis_scope`: 단일 place_story failure case에서 target child/parent chunk 존재와 provenance만 점검했다.
- `chunking_decision`: 전역 청킹 재실험은 열지 않는다.
- `targeted_repair_decision`: target child와 parent가 모두 존재하므로 targeted chunk repair도 현재는 열지 않는다.
- `retrieval_decision`: target doc만 retrieval/pack에 들어왔으므로 다음 변수는 retrieval top-rank coverage다.
- `parser_noise_boundary`: parser noise flag 1건은 관찰됐지만 boundary defect로 단정하지 않는다.
- `security_boundary`: 공개 row에는 id, count, boolean, rank, decision만 남긴다.
- `execution_boundary`: 이번 audit은 Solar Pro 3 호출과 CUDA 연산을 사용하지 않는다.
- `data_mart_grain`: fact_place_story_targeted_chunk_audit grain은 audit_id + query_id다.
- `gate_status`: PASS
- `external_audit`: 청킹 문제로 단정하지 않고 retrieval/HyDE 실험으로 넘긴 판단은 타당하다.

## 해석

target chunk와 parent는 존재하고 citation provenance도 복구된다. 따라서 이 사례는 전역 청킹 재실험이 아니라 retrieval top-rank coverage와 HyDE 후보 실험으로 넘기는 것이 맞다.
