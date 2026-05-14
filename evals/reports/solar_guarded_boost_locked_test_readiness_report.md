# Solar Pro 3 Guarded Boost Locked Test Readiness Report

## 목적

`place_story_guarded_boost_v1`을 locked test live paired comparison에 넣기 전에 split, route decision, expected live call budget, target resolvability, public-safe gate를 검증한다.

이 문서는 readiness dry-run 결과다. Solar Pro 3 live 호출은 수행하지 않았고 raw query, raw evidence, prompt, answer text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-guarded-boost-locked-test-readiness/v1` |
| readiness_id | `solar-guarded-boost-locked-ready-q5-1a304b6c` |
| generated_at_utc | `2026-05-14T12:06:28+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_test.jsonl>` |
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
| expected_query_count | 5 |
| locked_place_story_query_count | 5 |
| route_decision_computed_count | 5 |
| selected_candidate_count | 0 |
| guardrail_block_count | 5 |
| manual_review_count | 0 |
| baseline_live_call_count | 5 |
| candidate_live_call_count | 0 |
| expected_total_live_call_count | 5 |
| live_call_hard_cap | 20 |
| reused_candidate_count | 5 |
| changed_candidate_input_count | 0 |
| citation_recoverability_min | 1.000000 |
| target_resolvability_fail_count | 0 |
| missing_child_target_count | 0 |
| missing_parent_target_count | 0 |
| missing_doc_target_count | 0 |
| solar_call_count | 0 |
| live_execution_requested | False |
| live_execution_confirmed | False |
| hard_cap_exceeded | False |
| readiness_decision | `ready_without_candidate_live_call` |

## Route Decision Distribution

| route_decision | count |
| --- | ---: |
| `use_baseline_no_candidate_gain` | 4 |
| `use_baseline_precision_guardrail` | 1 |

## Reuse Decision Distribution

| reuse_decision | count |
| --- | ---: |
| `reuse_baseline_result` | 5 |

## Query-level Sanitized Readiness

| query_id | decision | selected_strategy | reuse_decision | fingerprint_equal | baseline_call | candidate_call | baseline_chars | guarded_chars | baseline_evidence | guarded_evidence |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `q-test-place_story-001` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 3765 | 3765 | 4 | 4 |
| `q-test-place_story-002` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 4253 | 4253 | 5 | 5 |
| `q-test-place_story-003` | `use_baseline_precision_guardrail` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 4179 | 4179 | 5 | 5 |
| `q-test-place_story-004` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 4200 | 4200 | 5 | 5 |
| `q-test-place_story-005` | `use_baseline_no_candidate_gain` | `baseline_dense_e5_voice_rewrite` | `reuse_baseline_result` | True | True | False | 4708 | 4708 | 5 | 5 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 6 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: private locked place_story test subset에서 baseline과 guarded retrieval input을 비교했다.
- `llm_call_boundary`: readiness dry-run 단계라 Solar Pro 3 live 호출은 수행하지 않았고 solar_call_count는 0이다.
- `test_split_boundary`: locked test는 live 품질 평가가 아니라 route와 call budget readiness 확인에만 사용했다.
- `call_budget`: expected_total_live_call_count=5, hard_cap=20로 제한한다.
- `data_mart_grain`: `fact_guarded_boost_locked_readiness`의 grain은 run_id-query_id-router_policy_id-execution_mode다.
- `security_boundary`: public artifact에는 raw query, raw evidence, prompt, answer text, private path, secret을 기록하지 않는다.
- `next_action`: candidate live call 대상이 없어 live paired comparison을 보류하고 dev router를 재검토한다.

## 결론

readiness gate는 통과했지만 candidate live call 대상이 없다.

이 경우 locked live paired comparison은 보류하고 router 적용 폭을 재검토한다.

## HD-SOLAR-023 후속 판단

[Solar Pro 3 Guarded Boost Locked Readiness Next Gate Decision](../../docs/SOLAR_GUARDED_BOOST_LOCKED_READINESS_NEXT_GATE_DECISION.md)에 후속 판단을 고정했다.

결정:

- locked live paired comparison은 실행하지 않는다.
- locked test 결과를 기준으로 router threshold를 완화하지 않는다.
- `place_story_guarded_boost_v1`은 production 기본값으로 채택하지 않는다.
- 청킹 비교 재개 조건은 충족하지 않는다.
- 다음 작업은 Solar Pro 3 generation v2 prompt repair 계획 작성이다.
