# Place Story Full Dev Generation Input Impact Report

## 목적

`parent_doc_context_boost`가 full `place_story` dev query에서 generation 입력 품질을 실제로 개선하는지 검증한다.

이 문서는 청킹 재실험 결과가 아니며 Solar Pro 3 live 호출 결과도 아니다. 같은 private dev split, 같은 parent-child chunk corpus, 같은 `P0_rank_order` evidence packing을 유지한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `place-story-full-dev-generation-input-impact-report/v1` |
| comparison_id | `place-story-full-dev-input-s2-q10-60c40e9e` |
| generated_at_utc | `2026-05-12T15:18:29+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| place_catalog_path | `data_samples/place_catalog_seed.json` |
| top_k | 5 |
| candidate_k | 20 |
| resolved_device | `cuda` |
| selected_strategy_id | `parent_doc_context_boost` |
| selection_decision | `promote_to_generation_input_eval` |
| selection_reason | full dev에서 직접 근거 coverage가 개선되고 direct evidence regression이 없어 generation 입력 평가 후보로 승격한다. |

## Strategy Summary

| strategy_id | query_count | child@1 | child@3 | child@5 | parent@1 | parent@3 | parent@5 | doc@5 | child_or_parent@5 | input_ready | doc_only | full_miss | hard_case | MRR | nDCG@5 | latency_p95_ms | citation | evidence_order | duplicate_parent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_dense_e5_voice_rewrite | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.900000 | 0.600000 | 0.600000 | 3 | 1 | 4 | 0.770000 | 0.616818 | 10.233600 | 1.000000 | 0.770000 | 0.140000 |
| parent_doc_context_boost | 10 | 0.500000 | 0.700000 | 0.700000 | 0.500000 | 0.700000 | 0.700000 | 0.800000 | 0.700000 | 0.700000 | 1 | 2 | 3 | 0.616667 | 0.544546 | 8.235900 | 1.000000 | 0.616667 | 0.145000 |

## Baseline Delta

| compared_strategy_id | child_or_parent@5 delta | input_ready delta | child@5 delta | parent@5 delta | doc@5 delta | doc_only delta | full_miss delta | hard_case delta | MRR delta | nDCG@5 delta | latency_p95_ms delta | evidence_order delta | direct improve | direct regress |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_dense_e5_voice_rewrite | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 |
| parent_doc_context_boost | 0.100000 | 0.100000 | 0.100000 | 0.100000 | -0.100000 | -2 | 1 | -1 | -0.153333 | -0.072272 | -1.997700 | -0.153333 | 1 | 0 |

## Failure Tag Distribution

| strategy_id | failure_tag | count |
| --- | --- | ---: |
| baseline_dense_e5_voice_rewrite | child_covered | 6 |
| baseline_dense_e5_voice_rewrite | doc_covered | 9 |
| baseline_dense_e5_voice_rewrite | evidence_rank_too_low | 1 |
| baseline_dense_e5_voice_rewrite | no_hard_case | 6 |
| baseline_dense_e5_voice_rewrite | parent_covered | 6 |
| baseline_dense_e5_voice_rewrite | retrieval_semantic_miss | 1 |
| baseline_dense_e5_voice_rewrite | target_too_narrow | 3 |
| parent_doc_context_boost | child_covered | 7 |
| parent_doc_context_boost | doc_covered | 8 |
| parent_doc_context_boost | no_hard_case | 7 |
| parent_doc_context_boost | parent_covered | 7 |
| parent_doc_context_boost | retrieval_semantic_miss | 2 |
| parent_doc_context_boost | target_too_narrow | 1 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 4 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: baseline과 parent/doc context boost를 full place_story dev query에서 비교했다.
- `generation_input_boundary`: generation_input_ready는 child 또는 parent 직접 근거가 있고 citation recoverability가 1.0인 query 비율이다.
- `chunking_decision`: 이번 결과는 청킹 재실험이 아니다. chunk corpus와 evidence packing 정책을 고정했다.
- `selection_boundary`: 선택 판단은 private dev 기준이다. locked test와 Solar Pro 3 generation 평가 전 최종 개선 주장으로 쓰지 않는다.
- `security_boundary`: public report/result에는 raw query, raw evidence, chunk text, private path, secret을 기록하지 않는다.
- `data_mart_grain`: `fact_place_story_generation_input_impact`의 grain은 strategy-query이며, 공개 산출물에는 strategy aggregate와 paired delta만 남긴다.
- `next_action`: 같은 query set에서 Solar Pro 3 호출 전 generation input-only 평가를 먼저 수행한다.

## 결론

`parent_doc_context_boost`는 full place_story dev에서 generation 입력 품질 후보로 승격할 수 있다.

다만 이 결과는 private dev input-only 기준이며 Solar Pro 3 live generation 개선 주장이 아니다.
