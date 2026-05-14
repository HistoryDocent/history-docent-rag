# Solar Pro 3 Guarded Boost Hard-case Validation Report

## 목적

HD-SOLAR-016 live paired comparison 이후 `parent_doc_context_boost_guarded`의 route decision을 추가 dev hard-case bucket으로 검증한다.

이 문서는 Solar Pro 3 추가 호출 결과가 아니다. 기존 public-safe live metric row와 현재 input-only route decision을 결합해 검증하며 raw query, raw answer, raw evidence, prompt, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-guarded-boost-hard-case-validation/v1` |
| validation_id | `solar-guarded-boost-hard-case-q10-cc46719b` |
| generated_at_utc | `2026-05-14T11:43:17+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| live_paired_rows_path | `<private public-safe live paired metric rows>` |
| baseline_strategy_id | `baseline_dense_e5_voice_rewrite` |
| candidate_strategy_id | `parent_doc_context_boost` |
| guarded_strategy_id | `parent_doc_context_boost_guarded` |
| router_policy_id | `place_story_guarded_boost_v1` |
| answer_policy_id | `solar-guarded-boost-live-v1` |
| top_k | 5 |
| candidate_k | 20 |
| max_context_chars | 11000 |
| resolved_device | `cuda` |

## 정량 리포트

| metric | value |
| --- | ---: |
| expected_query_count | 10 |
| query_count | 10 |
| bucket_coverage_count | 10 |
| hard_case_bucket_count | 6 |
| selected_candidate_count | 1 |
| guardrail_block_count | 9 |
| manual_review_count | 2 |
| doc_guardrail_count | 1 |
| precision_guardrail_count | 2 |
| no_candidate_gain_control_count | 3 |
| candidate_live_call_required_count | 1 |
| live_reference_row_count | 10 |
| route_decision_mismatch_count | 0 |
| selected_candidate_safety_passed | True |
| manual_review_block_passed | True |
| doc_guardrail_block_passed | True |
| citation_recoverability_min | 1.000000 |
| solar_call_count | 0 |
| validation_decision | `keep_guarded_router_for_next_runner` |

## Hard-case Bucket Distribution

| bucket | count |
| --- | ---: |
| `candidate_direct_gain` | 1 |
| `correctness_guardrail` | 1 |
| `doc_guardrail` | 1 |
| `manual_review_required` | 2 |
| `no_candidate_gain_control` | 3 |
| `precision_guardrail` | 2 |

## Bucket Summary

| bucket | query_count | selected_candidate | blocked | candidate_live_call | route_mismatch | live_correct_min | live_precision_min | live_recall_avg | unsupported_max | order_delta_min | citation_recoverability_min |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `candidate_direct_gain` | 1 | 1 | 0 | 1 | 0 | 0 | 0.000000 | 0.285715 | 0 | 0.000000 | 1.000000 |
| `correctness_guardrail` | 1 | 0 | 1 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | -0.200000 | 1.000000 |
| `doc_guardrail` | 1 | 0 | 1 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0.000000 | 1.000000 |
| `manual_review_required` | 2 | 0 | 2 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | -0.666667 | 1.000000 |
| `no_candidate_gain_control` | 3 | 0 | 3 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0.000000 | 1.000000 |
| `precision_guardrail` | 2 | 0 | 2 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0.000000 | 1.000000 |

## Query-level Sanitized Validation

| query_id | bucket | decision | selected | blocked | reuse | input_correct_delta | input_precision_delta | input_recall_delta | order_delta | live_correct_delta | live_precision_delta | live_recall_delta | unsupported_delta | tags |
| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `q-dev-place-story-001` | `correctness_guardrail` | `use_baseline_correctness_guardrail` | `baseline_dense_e5_voice_rewrite` | True | `reuse_baseline_result` | -1 | -0.200000 | -0.125000 | -0.200000 | 0 | 0.000000 | 0.000000 | 0 | `blocked_correctness_risk` |
| `q-dev-place-story-002` | `candidate_direct_gain` | `use_candidate_direct_gain` | `parent_doc_context_boost_guarded` | False | `candidate_live_call_required` | 0 | 0.000000 | 0.285715 | 0.000000 | 0 | 0.000000 | 0.285715 | 0 | `safe_direct_gain`, `candidate_live_reference_available`, `live_citation_recall_gain` |
| `q-dev-place-story-003` | `no_candidate_gain_control` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | True | `reuse_baseline_result` | 0 | 0.200000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0.000000 | 0 | `control_no_gain` |
| `q-dev-place-story-004` | `precision_guardrail` | `use_baseline_precision_guardrail` | `baseline_dense_e5_voice_rewrite` | True | `reuse_baseline_result` | 0 | -0.200000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0.000000 | 0 | `blocked_precision_or_order_risk` |
| `q-dev-place-story-005` | `precision_guardrail` | `use_baseline_precision_guardrail` | `baseline_dense_e5_voice_rewrite` | True | `reuse_baseline_result` | 0 | 0.100000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0.000000 | 0 | `blocked_precision_or_order_risk` |
| `q-dev-place-story-006` | `no_candidate_gain_control` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | True | `reuse_baseline_result` | 0 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0.000000 | 0 | `control_no_gain` |
| `q-dev-place-story-007` | `no_candidate_gain_control` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | True | `reuse_baseline_result` | 0 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0.000000 | 0 | `control_no_gain` |
| `q-dev-place-story-008` | `doc_guardrail` | `use_baseline_doc_guardrail` | `baseline_dense_e5_voice_rewrite` | True | `reuse_baseline_result` | 0 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0.000000 | 0 | `blocked_doc_loss` |
| `q-dev-place-story-009` | `manual_review_required` | `manual_review_required` | `baseline_dense_e5_voice_rewrite` | True | `reuse_baseline_result` | 0 | 0.000000 | 0.400000 | -0.666667 | 0 | 0.000000 | 0.000000 | 0 | `manual_review_kept_blocked` |
| `q-dev-place-story-010` | `manual_review_required` | `manual_review_required` | `baseline_dense_e5_voice_rewrite` | True | `reuse_baseline_result` | 0 | -0.200000 | 0.285715 | -0.666667 | 0 | 0.000000 | 0.000000 | 0 | `manual_review_kept_blocked` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 17 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `scope`: HD-SOLAR-016 live paired metric rows와 현재 input-only route decision을 결합해 `place_story` dev hard-case를 검증했다.
- `llm_call_boundary`: 이번 runner는 Solar Pro 3를 호출하지 않는다. solar_call_count는 0이다.
- `metric_grain`: `validation_id + query_id + hard_case_bucket + strategy_id + router_policy_id + answer_policy_id` grain으로 기록한다.
- `bucket_policy`: route decision을 candidate/direct, correctness/doc/precision guardrail, manual review, no-gain control bucket으로 분리했다.
- `qualitative_tags`: blocked_correctness_risk=1, blocked_doc_loss=1, blocked_precision_or_order_risk=2, candidate_live_reference_available=1, control_no_gain=3, live_citation_recall_gain=1, manual_review_kept_blocked=2, safe_direct_gain=1
- `claim_boundary`: 이 결과는 dev hard-case route safety 검증이며 final benchmark 또는 production 채택 주장이 아니다.
- `public_policy`: public report와 result row에는 raw query, raw answer, evidence text, prompt, chunk text, private path, secret을 저장하지 않는다.
- `gate_status`: PASS

## 결론

`guarded_boost` hard-case validation gate를 통과했다. 다음 단계는 router threshold를 바꾸지 않고 후속 검증 계획으로 이동하는 것이다.
