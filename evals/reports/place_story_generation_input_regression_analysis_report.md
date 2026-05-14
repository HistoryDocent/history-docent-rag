# Place Story Generation Input Regression Analysis Report

## 목적

`parent_doc_context_boost`가 generation input-only 평가에서 만든 trade-off를 query 단위로 분해한다.

이 문서는 Solar Pro 3 live generation 결과가 아니다. raw query, raw evidence, prompt, answer text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `place-story-generation-input-regression-analysis/v1` |
| analysis_id | `place-story-input-regression-q10-ef62d524` |
| generated_at_utc | `2026-05-14T10:08:34+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| baseline_strategy_id | `baseline_dense_e5_voice_rewrite` |
| candidate_strategy_id | `parent_doc_context_boost` |
| top_k | 5 |
| candidate_k | 20 |
| max_context_chars | 11000 |
| resolved_device | `cuda` |

## 정량 요약

| metric | value |
| --- | ---: |
| query_count | 10 |
| direct_ready_gain_count | 1 |
| direct_ready_loss_count | 0 |
| correct_with_evidence_regression_count | 1 |
| citation_precision_regression_count | 3 |
| citation_recall_gain_count | 3 |
| evidence_order_regression_count | 3 |
| mixed_tradeoff_count | 1 |
| guardrail_required_count | 1 |
| input_latency_improved_count | 5 |
| solar_call_count | 0 |
| recommended_decision | `require_guardrail_before_live_generation` |

## Tag Distribution

| tag | count |
| --- | ---: |
| `citation_precision_regression` | 3 |
| `citation_recall_gain` | 3 |
| `citation_recall_regression` | 1 |
| `correctness_regression` | 1 |
| `direct_ready_gain` | 1 |
| `evidence_order_regression` | 3 |
| `guardrail_required` | 1 |
| `latency_improved` | 5 |
| `mixed_tradeoff` | 1 |
| `no_material_change` | 2 |

## Query-level Sanitized Rows

| query_id | direct_delta | correct_delta | precision_delta | recall_delta | evidence_order_delta | latency_delta_ms | tags | recommendation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `q-dev-place-story-001` | 0 | -1 | -0.200000 | -0.125000 | -0.200000 | -7.911200 | `citation_precision_regression`, `citation_recall_regression`, `correctness_regression`, `evidence_order_regression`, `latency_improved`, `guardrail_required` | `exclude_from_candidate_until_guardrail` |
| `q-dev-place-story-002` | 0 | 0 | 0.000000 | 0.285715 | 0.000000 | 0.747600 | `citation_recall_gain` | `monitor` |
| `q-dev-place-story-003` | 0 | 0 | 0.200000 | 0.000000 | 0.000000 | -0.800900 | `latency_improved` | `monitor` |
| `q-dev-place-story-004` | 0 | 0 | -0.200000 | 0.000000 | 0.000000 | 0.613400 | `citation_precision_regression` | `monitor` |
| `q-dev-place-story-005` | 0 | 0 | 0.100000 | 0.000000 | 0.000000 | -0.464300 | `latency_improved` | `monitor` |
| `q-dev-place-story-006` | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.018700 | `no_material_change` | `keep_baseline` |
| `q-dev-place-story-007` | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.193200 | `no_material_change` | `keep_baseline` |
| `q-dev-place-story-008` | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | -0.320700 | `latency_improved` | `monitor` |
| `q-dev-place-story-009` | 1 | 0 | 0.000000 | 0.400000 | -0.666667 | -1.382500 | `direct_ready_gain`, `citation_recall_gain`, `evidence_order_regression`, `latency_improved` | `candidate_router_positive` |
| `q-dev-place-story-010` | 0 | 0 | -0.200000 | 0.285715 | -0.666667 | 2.486600 | `citation_precision_regression`, `citation_recall_gain`, `evidence_order_regression`, `mixed_tradeoff` | `manual_review_before_live_call` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 11 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: 같은 place_story dev query set에서 baseline과 parent_doc_context_boost를 query grain으로 비교했다.
- `root_cause_boundary`: raw text를 보지 않는 공개 리포트이므로 root cause는 metric tag 수준의 원인 후보로만 기록한다.
- `decision_boundary`: candidate는 전체 기본값으로 승격하지 않고 hard-case router 또는 reranking guardrail 후보로 제한한다.
- `llm_call_boundary`: Solar Pro 3 호출 없이 input-only citation assembly만 평가했다.
- `data_mart_grain`: `fact_place_story_input_regression`의 grain은 query-pair이며 fact에는 metric delta와 tag만 둔다.
- `next_action`: candidate 적용 조건을 제한하는 reranking guardrail 또는 query router를 먼저 설계한다.

## 결론

`parent_doc_context_boost`는 일부 입력을 개선했지만 correctness regression이 있어 guardrail 없이 live generation에 투입하지 않는다.
