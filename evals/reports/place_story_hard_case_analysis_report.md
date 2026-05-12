# Place Story Hard-case Analysis Report

## 목적

`q-dev-place-story-001` 실패가 청킹 문제인지, retrieval/evidence packing 문제인지, generation contract 문제인지 분리한다.

이 문서는 추가 Solar Pro 3 호출 결과가 아니다. private retrieval dataset, private chunk artifact, 기존 generation comparison metric row를 사용하되 raw query, raw answer, evidence text, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `place-story-hard-case-analysis-report/v1` |
| analysis_id | `place-story-hard-case-q1-92de94e8` |
| generated_at_utc | `2026-05-12T13:59:32+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| generation_rows | `<private solar_generation_contract_v2_live_comparison_results.jsonl>` |
| source_fingerprint | `576c6f01c1ace5d7` |

## 정량 리포트

| metric | value |
| --- | ---: |
| analyzed_query_count | 1 |
| target_child_covered_count | 0 |
| target_parent_covered_count | 0 |
| target_doc_covered_count | 1 |
| generation_regression_count | 1 |
| retrieval_or_packing_miss_count | 0 |
| root_cause_decision | `target_grain_mismatch` |

## Root Cause Distribution

| root_cause_decision | count |
| --- | ---: |
| target_grain_mismatch | 1 |

## Query Diagnostic Rows

| query_id | query_type | method | candidates | packed | child | parent | doc | target retrieval rank | target pack rank | citation recoverability | order proxy | duplicate parent | duplicate doc | rewrite | generation regression | root cause | tags |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| q-dev-place-story-001 | place_story | dense_multilingual_e5_small_voice_rewrite | 5 | 5 | 0 | 0 | 1 | 5 | 5 | 1.000000 | 0.200000 | 0.000000 | 0.200000 | no | 1 | target_grain_mismatch | target_doc_in_pack, target_retrieval_rank_5, target_pack_rank_5, citation_recoverable, query_rewrite_not_changed, generation_correctness_regression, generation_unsupported_regression, v2_citation_count_reduction, v2_precision_regression, v2_recall_regression |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 1 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `root_cause`: doc-level target은 들어왔지만 child/parent target이 빠져 judgment grain 점검이 필요하다.
- `chunking_decision`: 청킹 전체 재실험보다 judgment target grain과 top-rank retrieval coverage를 먼저 점검한다.
- `generation_decision`: v2 generation regression은 확인됐지만 target child/parent가 pack에 없어 prompt repair만으로 해결된다고 단정할 수 없다.
- `data_boundary`: public report에는 metric, rank, boolean, tag만 남기며 raw query/answer/evidence/chunk text는 포함하지 않는다.
- `next_action`: judgment target grain과 parent-child chunk boundary를 점검한다.

## 결론

현재 증거만 보면 `place_story` 실패를 청킹 문제나 generation 문제 하나로 단정할 수 없다.

target doc은 pack에 들어왔지만 target child/parent는 빠졌고, target doc도 rank 5에 위치했다. 따라서 다음 작업은 전체 청킹 재실험이 아니라 judgment target grain, retrieval top-rank coverage, v2 selected evidence prompt를 순서대로 분리하는 것이다.
