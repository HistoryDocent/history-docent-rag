# Place Story Target Grain Coverage Report

## 목적

`place_story` dev query 전체에서 child, parent, doc target grain별 retrieval/evidence coverage를 분리 진단한다.

이 문서는 청킹 재실험 결과가 아니며 Solar Pro 3 추가 호출도 아니다. private dev 평가셋과 private chunk artifact를 사용하지만 raw query, raw answer, evidence text, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `place-story-target-grain-coverage-report/v1` |
| analysis_id | `place-story-coverage-q10-966b2d5d` |
| generated_at_utc | `2026-05-12T14:23:43+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| retrieval_run_label | `dense_multilingual_e5_small_voice_rewrite` |
| packing_policy_id | `P0_rank_order` |
| source_fingerprint | `7a57129fef35181d` |

## 정량 리포트

| metric | value |
| --- | ---: |
| analyzed_query_count | 10 |
| target_child_covered_count | 6 |
| target_parent_covered_count | 6 |
| target_doc_covered_count | 9 |
| doc_only_covered_count | 3 |
| full_grain_miss_count | 1 |
| hard_case_count | 4 |
| target_child_recall_at_1 | 0.600000 |
| target_child_recall_at_3 | 0.600000 |
| target_child_recall_at_5 | 0.600000 |
| target_parent_recall_at_1 | 0.600000 |
| target_parent_recall_at_3 | 0.600000 |
| target_parent_recall_at_5 | 0.600000 |
| target_doc_recall_at_1 | 0.700000 |
| target_doc_recall_at_3 | 0.800000 |
| target_doc_recall_at_5 | 0.900000 |
| child_or_parent_recall_at_5 | 0.600000 |
| MRR | 0.770000 |
| nDCG@5 | 0.616818 |
| latency_p95_ms | 54.415800 |
| citation_recoverability_avg | 1.000000 |
| duplicate_parent_rate_avg | 0.140000 |
| evidence_order_relevance_proxy_avg | 0.770000 |
| recommended_decision | `repair_top_rank_retrieval_coverage` |

## Failure Tag Distribution

| failure_tag | count |
| --- | ---: |
| child_covered | 6 |
| doc_covered | 9 |
| evidence_rank_too_low | 1 |
| no_hard_case | 6 |
| parent_covered | 6 |
| retrieval_semantic_miss | 1 |
| target_too_narrow | 3 |

## Query Diagnostic Rows

| query_id | method | candidates | packed | latency_ms | child | parent | doc | child_rank | parent_rank | doc_rank | any_rank | RR | nDCG@5 | citation | order_proxy | duplicate_parent | hard_case | tags |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| q-dev-place-story-001 | dense_multilingual_e5_small_voice_rewrite | 5 | 5 | 54.415800 | 0 | 0 | 1 | NA | NA | 5 | 5 | 0.200000 | 0.131205 | 1.000000 | 0.200000 | 0.000000 | 1 | doc_covered, target_too_narrow, evidence_rank_too_low |
| q-dev-place-story-002 | dense_multilingual_e5_small_voice_rewrite | 5 | 5 | 14.483800 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.400000 | 0 | child_covered, parent_covered, doc_covered, no_hard_case |
| q-dev-place-story-003 | dense_multilingual_e5_small_voice_rewrite | 5 | 5 | 12.817300 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1.000000 | 0.553146 | 1.000000 | 1.000000 | 0.000000 | 0 | child_covered, parent_covered, doc_covered, no_hard_case |
| q-dev-place-story-004 | dense_multilingual_e5_small_voice_rewrite | 5 | 5 | 11.141400 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1.000000 | 0.868795 | 1.000000 | 1.000000 | 0.200000 | 0 | child_covered, parent_covered, doc_covered, no_hard_case |
| q-dev-place-story-005 | dense_multilingual_e5_small_voice_rewrite | 5 | 5 | 15.396300 | 0 | 0 | 1 | NA | NA | 2 | 2 | 0.500000 | 0.383566 | 1.000000 | 0.500000 | 0.000000 | 1 | doc_covered, target_too_narrow |
| q-dev-place-story-006 | dense_multilingual_e5_small_voice_rewrite | 5 | 5 | 14.673000 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.200000 | 0 | child_covered, parent_covered, doc_covered, no_hard_case |
| q-dev-place-story-007 | dense_multilingual_e5_small_voice_rewrite | 5 | 5 | 18.033800 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1.000000 | 0.722727 | 1.000000 | 1.000000 | 0.000000 | 0 | child_covered, parent_covered, doc_covered, no_hard_case |
| q-dev-place-story-008 | dense_multilingual_e5_small_voice_rewrite | 5 | 5 | 14.513900 | 0 | 0 | 0 | NA | NA | NA | NA | 0.000000 | 0.000000 | 1.000000 | 0.000000 | 0.400000 | 1 | retrieval_semantic_miss |
| q-dev-place-story-009 | dense_multilingual_e5_small_voice_rewrite | 5 | 5 | 10.133400 | 0 | 0 | 1 | NA | NA | 1 | 1 | 1.000000 | 0.639945 | 1.000000 | 1.000000 | 0.000000 | 1 | doc_covered, target_too_narrow |
| q-dev-place-story-010 | dense_multilingual_e5_small_voice_rewrite | 5 | 5 | 11.289000 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1.000000 | 0.868795 | 1.000000 | 1.000000 | 0.200000 | 0 | child_covered, parent_covered, doc_covered, no_hard_case |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 10 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `evaluation_scope`: `place_story` dev query만 대상으로 child, parent, doc target grain을 분리 측정했다.
- `chunking_decision`: 청킹 전체 재실험으로 바로 가지 않고, child/parent가 parent/doc 내부에 묻히는지 hard subset에서 확인한다.
- `retrieval_decision`: deterministic rewrite v2 또는 parent/doc context boost를 우선 비교한다.
- `generation_decision`: Solar Pro 3 v2 prompt repair는 retrieval 입력 품질 진단 뒤에 진행한다. 이번 실행의 live Solar call은 0이다.
- `data_mart_grain`: `fact_place_story_coverage`의 grain은 query-run-strategy이며, fact에는 metric과 id만 남긴다.
- `public_policy`: public report에는 query id, rank, boolean, metric, tag만 저장하고 raw query/evidence/chunk text는 저장하지 않는다.
- `next_action`: HD-PLACE-STORY-007에서 hard subset을 고정하고 top-rank coverage repair 후보를 비교한다.

## 결론

현재 우선순위는 청킹 재실험이 아니라 top-rank retrieval coverage repair다.

child/parent/doc grain별 coverage와 rank를 기준으로 hard subset을 고정한 뒤 deterministic rewrite 또는 parent/doc context boost를 비교한다.
