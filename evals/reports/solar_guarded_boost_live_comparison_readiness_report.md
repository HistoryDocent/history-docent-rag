# Solar Pro 3 Guarded Boost Live Comparison Readiness Report

## 목적

`parent_doc_context_boost_guarded` live paired comparison runner가 실제 Solar Pro 3 호출 전에 dry-run gate, call cap, public-safe gate를 강제하는지 검증한다.

이 문서는 readiness report다. Solar Pro 3 live 호출은 수행하지 않았고 raw query, raw evidence, prompt, answer text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-guarded-boost-live-comparison-readiness/v1` |
| readiness_id | `solar-guarded-boost-live-readiness-e6ec16f3` |
| generated_at_utc | `2026-05-14T10:55:32+00:00` |
| dry_run_report_version | `solar-guarded-boost-live-dry-run/v1` |
| dry_run_id | `solar-guarded-boost-dry-q10-bc3d9373` |
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

## Gate Summary

| metric | value |
| --- | ---: |
| execution_mode | `dry_run_only` |
| readiness_decision | `ready_for_live_execution_approval` |
| live_execution_requested | False |
| live_execution_confirmed | False |
| live_call_executed | False |
| approval_required_for_live | True |
| dry_run_gate_passed | True |
| call_cap_passed | True |
| public_safety_passed | True |
| expected_total_live_call_count | 11 |
| live_call_hard_cap | 20 |
| baseline_live_call_count | 10 |
| candidate_live_call_count | 1 |
| reused_candidate_count | 9 |
| changed_candidate_input_count | 1 |
| solar_call_count | 0 |

## Reuse Decision Distribution

| reuse_decision | count |
| --- | ---: |
| `candidate_live_call_required` | 1 |
| `reuse_baseline_result` | 9 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 1 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `execution_boundary`: HD-SOLAR-015는 readiness stage이며 Solar Pro 3 live 호출을 수행하지 않는다.
- `dry_run_gate`: live runner는 실행 전에 dry-run report를 재생성하고 dry-run gate를 통과해야 한다.
- `call_budget`: expected_total_live_call_count=11, hard_cap=20다.
- `reuse_policy`: guarded input fingerprint가 baseline과 동일한 query는 baseline 결과를 재사용한다.
- `data_mart_grain`: `fact_solar_guarded_boost_live_eval` grain은 run-query-strategy-answer_contract-router_policy다.
- `security_boundary`: public artifact에는 raw query, raw evidence, prompt, answer text, private path, secret을 기록하지 않는다.
- `next_action`: 별도 승인 후 HD-SOLAR-016에서 실제 Solar Pro 3 live paired comparison을 실행한다.

## 결론

readiness gate를 통과했다.

이 결과는 live 품질 개선 주장이 아니라, live 실행 전에 dry-run gate와 call budget을 코드로 강제했다는 검증이다.
