# Place Story Guarded Boost Comparison Report

## 목적

`parent_doc_context_boost`를 전체 적용하지 않고 guardrail/router로 제한했을 때 input-only 품질이 어떻게 변하는지 비교한다.

이 문서는 Solar Pro 3 live generation 결과가 아니다. raw query, raw evidence, prompt, answer text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `place-story-guarded-boost-comparison/v1` |
| comparison_id | `place-story-guarded-boost-q10-e4f01657` |
| generated_at_utc | `2026-05-14T10:31:35+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| baseline_strategy_id | `baseline_dense_e5_voice_rewrite` |
| candidate_strategy_id | `parent_doc_context_boost` |
| router_policy_id | `place_story_guarded_boost_v1` |
| top_k | 5 |
| candidate_k | 20 |
| max_context_chars | 11000 |
| resolved_device | `cuda` |
| selected_strategy_id | `parent_doc_context_boost_guarded` |
| selection_decision | `promote_guarded_to_live_plan_review` |

## Strategy Summary

| strategy_id | eval_count | selected_candidate | blocked | context_build | direct_ready | Correct-with-Evidence | citation_precision | citation_recall | doc_coverage | evidence_order | duplicate_parent | avg_evidence | latency_p95_ms | solar_calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline_dense_e5_voice_rewrite` | 10 | 0 | 0 | 1.000000 | 0.600000 | 0.900000 | 0.580000 | 0.481309 | 0.900000 | 0.770000 | 0.140000 | 5.000000 | 10.053800 | 0 |
| `parent_doc_context_boost_always` | 10 | 10 | 0 | 1.000000 | 0.700000 | 0.800000 | 0.550000 | 0.565953 | 0.800000 | 0.616667 | 0.145000 | 4.900000 | 7.865900 | 0 |
| `parent_doc_context_boost_guarded` | 10 | 1 | 9 | 1.000000 | 0.600000 | 0.900000 | 0.580000 | 0.509881 | 0.900000 | 0.770000 | 0.140000 | 5.000000 | 10.053800 | 0 |

## Baseline Delta

| compared_strategy_id | direct_ready delta | Correct delta | precision delta | recall delta | doc delta | evidence_order delta | duplicate_parent delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline_dense_e5_voice_rewrite` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| `parent_doc_context_boost_always` | 0.100000 | -0.100000 | -0.030000 | 0.084644 | -0.100000 | -0.153333 | 0.005000 | -2.187900 |
| `parent_doc_context_boost_guarded` | 0.000000 | 0.000000 | 0.000000 | 0.028572 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

## Route Decision Distribution

| route_decision | count |
| --- | ---: |
| `manual_review_required` | 2 |
| `use_baseline_correctness_guardrail` | 1 |
| `use_baseline_doc_guardrail` | 1 |
| `use_baseline_no_candidate_gain` | 3 |
| `use_baseline_precision_guardrail` | 2 |
| `use_candidate_direct_gain` | 1 |

## Query-level Sanitized Routes

| query_id | decision | selected | blocked | direct_delta | correct_delta | precision_delta | recall_delta | order_delta | reason_tags |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `q-dev-place-story-001` | `use_baseline_correctness_guardrail` | `baseline_dense_e5_voice_rewrite` | True | 0 | -1 | -0.200000 | -0.125000 | -0.200000 | `candidate_direct_missing`, `doc_coverage_loss`, `correctness_regression`, `precision_regression_without_recall_gain`, `low_evidence_order` |
| `q-dev-place-story-002` | `use_candidate_direct_gain` | `parent_doc_context_boost_guarded` | False | 0 | 0 | 0.000000 | 0.285715 | 0.000000 | `candidate_passed_guardrail` |
| `q-dev-place-story-003` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | True | 0 | 0 | 0.200000 | 0.000000 | 0.000000 | `no_candidate_gain` |
| `q-dev-place-story-004` | `use_baseline_precision_guardrail` | `baseline_dense_e5_voice_rewrite` | True | 0 | 0 | -0.200000 | 0.000000 | 0.000000 | `no_candidate_gain`, `precision_regression_without_recall_gain` |
| `q-dev-place-story-005` | `use_baseline_precision_guardrail` | `baseline_dense_e5_voice_rewrite` | True | 0 | 0 | 0.100000 | 0.000000 | 0.000000 | `candidate_direct_missing`, `duplicate_parent_over_limit` |
| `q-dev-place-story-006` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | True | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | `no_candidate_gain` |
| `q-dev-place-story-007` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | True | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | `no_candidate_gain` |
| `q-dev-place-story-008` | `use_baseline_doc_guardrail` | `baseline_dense_e5_voice_rewrite` | True | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | `candidate_direct_missing`, `doc_coverage_loss`, `low_evidence_order` |
| `q-dev-place-story-009` | `manual_review_required` | `baseline_dense_e5_voice_rewrite` | True | 1 | 0 | 0.000000 | 0.400000 | -0.666667 | `low_evidence_order`, `evidence_order_drop`, `direct_ready_gain`, `citation_recall_gain` |
| `q-dev-place-story-010` | `manual_review_required` | `baseline_dense_e5_voice_rewrite` | True | 0 | 0 | -0.200000 | 0.285715 | -0.666667 | `low_evidence_order`, `evidence_order_drop`, `citation_recall_gain` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 16 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: baseline, always_boost, guarded_boost를 같은 place_story dev query set에서 비교했다.
- `guardrail_boundary`: guarded_boost는 candidate가 hard block 조건을 통과할 때만 candidate evidence를 사용한다.
- `llm_call_boundary`: Solar Pro 3 호출 없이 input-only citation assembly만 평가했다.
- `data_mart_grain`: `fact_place_story_guarded_boost`의 grain은 query-router_policy-candidate_strategy다.
- `security_boundary`: public artifact에는 raw query, raw evidence, prompt, answer text를 기록하지 않는다.
- `next_action`: Solar Pro 3 live paired comparison 계획을 작성하되 실행 전 별도 승인을 받는다.

## 결론

`guarded_boost`는 input-only gate에서 baseline 안전성을 유지하며 candidate 이득을 일부 보존했다.
