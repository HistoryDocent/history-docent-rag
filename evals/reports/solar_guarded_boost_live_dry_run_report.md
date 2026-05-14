# Solar Pro 3 Guarded Boost Live Dry-run Report

## 목적

`parent_doc_context_boost_guarded`를 Solar Pro 3 live paired comparison에 넣기 전에 input fingerprint, reuse 대상, 예상 live call 수, public-safe gate를 검증한다.

이 문서는 dry-run 결과다. Solar Pro 3 live 호출은 수행하지 않았고 raw query, raw evidence, prompt, answer text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-guarded-boost-live-dry-run/v1` |
| dry_run_id | `solar-guarded-boost-dry-q10-bc3d9373` |
| generated_at_utc | `2026-05-14T10:47:02+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| baseline_strategy_id | `baseline_dense_e5_voice_rewrite` |
| candidate_strategy_id | `parent_doc_context_boost` |
| guarded_strategy_id | `parent_doc_context_boost_guarded` |
| router_policy_id | `place_story_guarded_boost_v1` |
| answer_contract_version | `citation-rag-answer/v1` |
| answer_policy_id | `solar-guarded-boost-live-v1` |
| provider_config_id_alias | `<solar-pro3-v1-live-config>` |
| endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| model_id | `solar-pro3` |
| top_k | 5 |
| candidate_k | 20 |
| max_context_chars | 11000 |
| resolved_device | `cuda` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 10 |
| baseline_live_call_count | 10 |
| candidate_live_call_count | 1 |
| expected_total_live_call_count | 11 |
| live_call_hard_cap | 20 |
| reused_candidate_count | 9 |
| changed_candidate_input_count | 1 |
| selected_candidate_count | 1 |
| guardrail_block_count | 9 |
| solar_call_count | 0 |
| hard_cap_exceeded | False |

## Reuse Decision Distribution

| reuse_decision | count |
| --- | ---: |
| `candidate_live_call_required` | 1 |
| `reuse_baseline_result` | 9 |

## Query-level Sanitized Dry-run

| query_id | decision | selected_strategy | reuse_decision | fingerprint_equal | baseline_call | candidate_call | baseline_chars | guarded_chars | baseline_evidence | guarded_evidence |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `q-dev-place-story-001` | `use_baseline_correctness_guardrail` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 4695 | 4695 | 5 | 5 |
| `q-dev-place-story-002` | `use_candidate_direct_gain` | `parent_doc_context_boost_guarded` | `candidate_live_call_required` | False | True | True | 4125 | 4561 | 5 | 5 |
| `q-dev-place-story-003` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 3997 | 3997 | 5 | 5 |
| `q-dev-place-story-004` | `use_baseline_precision_guardrail` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 3686 | 3686 | 5 | 5 |
| `q-dev-place-story-005` | `use_baseline_precision_guardrail` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 4721 | 4721 | 5 | 5 |
| `q-dev-place-story-006` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 4313 | 4313 | 5 | 5 |
| `q-dev-place-story-007` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 4732 | 4732 | 5 | 5 |
| `q-dev-place-story-008` | `use_baseline_doc_guardrail` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 3922 | 3922 | 5 | 5 |
| `q-dev-place-story-009` | `manual_review_required` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 4725 | 4725 | 5 | 5 |
| `q-dev-place-story-010` | `manual_review_required` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 4334 | 4334 | 5 | 5 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 11 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: private place_story dev query에서 baseline과 guarded retrieval input을 비교했다.
- `llm_call_boundary`: dry-run 단계라 Solar Pro 3 live 호출은 수행하지 않았고 solar_call_count는 0이다.
- `reuse_policy`: baseline과 guarded input fingerprint가 동일한 query는 live 실행 시 baseline generation 결과를 재사용한다.
- `call_budget`: expected_total_live_call_count=11, hard_cap=20로 제한한다.
- `data_mart_grain`: `fact_solar_guarded_boost_live_eval`의 grain은 run-query-strategy-answer_contract-router_policy다.
- `security_boundary`: public artifact에는 raw query, raw evidence, prompt, answer text, private path, secret을 기록하지 않는다.
- `next_action`: 별도 승인 후 Solar Pro 3 guarded boost live paired comparison runner를 구현하거나 실행한다.

## 결론

dry-run gate를 통과했다.

이 결과는 live 품질 개선 주장이 아니라, live paired comparison 실행 전 input reuse와 call budget이 계획 범위 안에 있다는 검증이다.
