# Place Story Top-rank Coverage Repair Report

## 목적

`place_story` hard subset에서 top-rank retrieval coverage repair 후보를 비교한다.

이 문서는 청킹 재실험 결과가 아니며 Solar Pro 3 추가 호출도 아니다. 같은 private dev split, 같은 parent-child chunk corpus, 같은 `P0_rank_order` evidence packing을 유지한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `place-story-top-rank-coverage-repair-report/v1` |
| comparison_id | `place-story-top-rank-repair-s3-h4-2839e440` |
| generated_at_utc | `2026-05-12T14:45:19+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| place_catalog_path | `data_samples/place_catalog_seed.json` |
| top_k | 5 |
| candidate_k | 20 |
| hard_subset_query_count | 4 |
| hard_subset_query_ids | `q-dev-place-story-001`, `q-dev-place-story-005`, `q-dev-place-story-008`, `q-dev-place-story-009` |
| selected_strategy_id | `parent_doc_context_boost` |
| selection_decision | `adopt_candidate` |
| selection_reason | hard subset child_or_parent@5가 baseline보다 개선되어 후보 채택 대상이다. |

## Strategy Summary

| strategy_id | query_count | child@1 | child@3 | child@5 | parent@1 | parent@3 | parent@5 | doc@5 | child_or_parent@5 | doc_only | full_miss | hard_case | MRR | nDCG@5 | latency_p95_ms | citation | rewrite_changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_dense_e5_voice_rewrite | 4 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.750000 | 0.000000 | 3 | 1 | 4 | 0.425000 | 0.288679 | 16.814800 | 1.000000 | 0 |
| place_story_rewrite_v2 | 4 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.750000 | 0.000000 | 3 | 1 | 4 | 0.550000 | 0.202381 | 18.885900 | 1.000000 | 4 |
| parent_doc_context_boost | 4 | 0.000000 | 0.250000 | 0.250000 | 0.000000 | 0.250000 | 0.250000 | 0.500000 | 0.250000 | 1 | 2 | 3 | 0.208333 | 0.207605 | 15.864400 | 1.000000 | 0 |

## Baseline Delta

| compared_strategy_id | child_or_parent@5 delta | child@5 delta | parent@5 delta | doc@5 delta | doc_only delta | full_miss delta | hard_case delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_dense_e5_voice_rewrite | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 |
| place_story_rewrite_v2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0.125000 | -0.086298 | 2.071100 |
| parent_doc_context_boost | 0.250000 | 0.250000 | 0.250000 | -0.250000 | -2 | 1 | -1 | -0.216667 | -0.081074 | -0.950400 |

## Failure Tag Distribution

| strategy_id | failure_tag | count |
| --- | --- | ---: |
| baseline_dense_e5_voice_rewrite | doc_covered | 3 |
| baseline_dense_e5_voice_rewrite | evidence_rank_too_low | 1 |
| baseline_dense_e5_voice_rewrite | retrieval_semantic_miss | 1 |
| baseline_dense_e5_voice_rewrite | target_too_narrow | 3 |
| place_story_rewrite_v2 | doc_covered | 3 |
| place_story_rewrite_v2 | evidence_rank_too_low | 1 |
| place_story_rewrite_v2 | lexical_alias_miss | 4 |
| place_story_rewrite_v2 | retrieval_semantic_miss | 1 |
| place_story_rewrite_v2 | target_too_narrow | 3 |
| parent_doc_context_boost | child_covered | 1 |
| parent_doc_context_boost | doc_covered | 2 |
| parent_doc_context_boost | no_hard_case | 1 |
| parent_doc_context_boost | parent_covered | 1 |
| parent_doc_context_boost | retrieval_semantic_miss | 2 |
| parent_doc_context_boost | target_too_narrow | 1 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 3 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: baseline, place_story deterministic rewrite v2, parent/doc context boost를 hard subset에서 비교했다.
- `chunking_decision`: 이번 결과는 청킹 재실험이 아니다. chunk corpus와 evidence packing 정책을 고정해 retrieval repair 후보만 비교했다.
- `selection_boundary`: 선택 판단은 private dev hard subset 기준이다. locked test와 generation 평가 전에는 최종 개선 주장으로 쓰지 않는다.
- `security_boundary`: public report/result에는 raw query, raw evidence, chunk text, private path, secret을 기록하지 않는다.
- `data_mart_grain`: `fact_place_story_repair`의 grain은 strategy-query이며, 공개 산출물에는 strategy aggregate만 남긴다.
- `next_action`: 채택 후보를 full place_story/dev query와 generation eval 전 입력으로 재검증한다.

## 결론

`parent_doc_context_boost`가 hard subset에서 baseline보다 직접 근거 coverage를 개선했다.

다만 이 결과는 private dev hard subset 기준이며 locked test와 generation 평가 전 최종 개선 주장이 아니다.
