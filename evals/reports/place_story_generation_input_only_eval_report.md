# Place Story Generation Input-only Eval Report

## 목적

`parent_doc_context_boost` 적용 후 Solar Pro 3를 호출하기 전에 generation 입력 evidence의 citation 품질과 prompt 입력 안정성을 비교한다.

이 문서는 live LLM 답변 품질 결과가 아니다. dummy draft와 citation assembler를 사용해 evidence 입력만 평가하며 Solar Pro 3 호출 수는 0이어야 한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `place-story-generation-input-only-eval-report/v1` |
| comparison_id | `place-story-input-only-s2-q10-bfa5d39f` |
| generated_at_utc | `2026-05-12T16:20:31+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| top_k | 5 |
| candidate_k | 20 |
| max_context_chars | 11000 |
| resolved_device | `cuda` |
| selected_strategy_id | `parent_doc_context_boost` |
| decision | keep_as_tradeoff_candidate |

## Strategy Summary

| strategy_id | eval_count | context_build | direct_ready | Correct-with-Evidence | citation_precision | citation_recall | citation_recoverability | evidence_order | avg_evidence | avg_context_chars | context_chars_p95 | truncated | input_latency_p95_ms | solar_calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_dense_e5_voice_rewrite | 10 | 1.000000 | 0.600000 | 0.900000 | 0.580000 | 0.481309 | 1.000000 | 0.770000 | 5.000000 | 4317.000000 | 4724.000000 | 0 | 11.764400 | 0 |
| parent_doc_context_boost | 10 | 1.000000 | 0.700000 | 0.800000 | 0.550000 | 0.565953 | 1.000000 | 0.616667 | 4.900000 | 4309.600000 | 4704.000000 | 0 | 8.362300 | 0 |

## Baseline Delta

| compared_strategy_id | context_build delta | direct_ready delta | Correct delta | precision delta | recall delta | evidence_order delta | avg_evidence delta | avg_context_chars delta | truncated delta | missing_citation delta | input_latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_dense_e5_voice_rewrite | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| parent_doc_context_boost | 0.000000 | 0.100000 | -0.100000 | -0.030000 | 0.084644 | -0.153333 | -0.100000 | -7.400000 | 0 | 0 | -3.402100 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 4 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: baseline과 parent/doc context boost의 generation 입력 evidence만 비교했다.
- `llm_call_boundary`: Solar Pro 3 live 호출은 수행하지 않았고 solar_call_count는 0이어야 한다.
- `metric_boundary`: Correct-with-Evidence는 dummy draft에 붙은 citation이 target refs를 덮는지 보는 input-only proxy다.
- `security_boundary`: raw query, raw evidence, prompt, answer text는 public report/result에 기록하지 않는다.
- `data_mart_grain`: `fact_place_story_generation_input_only`의 grain은 strategy-query이며 공개 row는 aggregate/delta만 남긴다.
- `next_action`: candidate를 trade-off 후보로 유지하고 query별 입력 regression을 점검한다.

## 결론

`parent_doc_context_boost`는 입력 일부를 개선하지만 trade-off가 남아 있다.

Solar Pro 3 live 호출 전 query별 regression 확인이 필요하다.
