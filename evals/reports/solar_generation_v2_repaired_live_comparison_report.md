# Solar Pro 3 Generation v2 Repaired Live Comparison Report

## 목적

Solar Pro 3 실제 호출로 v1 baseline과 repaired v2 routed policy를 같은 query set, 같은 retrieval label, 같은 evidence packing policy에서 paired comparison으로 비교한다.

이 문서는 private dev subset 기반 실험 결과다. 최종 성능 개선 주장이 아니라 repaired v2를 기본값으로 채택할 수 있는지 판단하기 위한 근거다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-generation-v2-repaired-live-comparison-report/v1` |
| comparison_id | `solar-generation-contract-v2-q7-cb079823` |
| generated_at_utc | `2026-05-14T13:00:53+00:00` |
| dataset_fingerprint | `a08b0d906932c3f0` |
| readiness_id | `solar-generation-v2-repaired-dry-run-q7-51a6d716` |
| repair_id | `solar_generation_v2_repaired_prompt_policy_v1` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| retrieval_run_label | `dense_multilingual_e5_small_voice_rewrite` |
| packing_policy_id | `P0_rank_order` |
| baseline_answer_policy_id | `solar-generation-baseline-v1` |
| repaired_answer_policy_id | `solar-generation-v2-repaired` |
| repaired_prompt_policy_id | `v2_repair_coverage_floor` |
| baseline_provider_config_id | `solar-pro-3-204eb9617a` |
| repaired_provider_config_id | `solar-pro-3-6d01735b90` |
| baseline_model_id | `solar-pro3` |
| repaired_model_id | `solar-pro3` |
| baseline_endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| repaired_endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| per_query_type | 1 |
| query_types | `place_fact, place_story, relationship, overview, route_context, voice_followup, no_answer` |

## 정량 리포트

| metric | v1 baseline | repaired v2 routed | delta |
| --- | ---: | ---: | ---: |
| eval_count | 7 | 7 | 0 |
| Correct-with-Evidence | 1.000000 | 1.000000 | 0.000000 |
| citation_precision | 0.566667 | 0.783333 | 0.216666 |
| citation_recall | 0.509722 | 0.481944 | -0.027778 |
| place_relevance | 0.857143 | 0.857143 | 0.000000 |
| docent_usefulness | 1.000000 | 1.000000 | 0.000000 |
| spoken_answer_naturalness | 1.000000 | 1.000000 | 0.000000 |
| unsupported_claim_rate | 0.000000 | 0.000000 | 0.000000 |
| abstention_accuracy | 1.000000 | 1.000000 | 0.000000 |
| latency_p95_ms | 12026.922400 | 3675.885500 | -8351.036900 |
| solar_call_count | 6 | 5 | -1 |
| prompt_tokens | 13948 | 13277 | -671 |
| completion_tokens | 1689 | 1406 | -283 |
| total_tokens | 15637 | 14683 | -954 |
| estimated_cost | 0.000000 | 0.000000 | 0.000000 |
| missing_citation_count | 0 | 0 | 0 |
| unsupported_high_count | 0 | 0 | 0 |

## Live Call Summary

| metric | value |
| --- | ---: |
| route_count | 7 |
| repaired_candidate_route_count | 5 |
| v1_fallback_route_count | 1 |
| no_answer_route_count | 1 |
| baseline_live_call_count | 6 |
| repaired_candidate_live_call_count | 5 |
| no_answer_live_call_count | 0 |
| expected_total_live_call_count | 11 |
| actual_total_solar_call_count | 11 |
| live_call_hard_cap | 20 |
| hard_cap_exceeded | False |
| adoption_decision | `reject_repaired_v2_default` |

## Route Decision Distribution

| route_decision | count |
| --- | ---: |
| `abstain_no_live_call` | 1 |
| `use_repaired_v2_candidate` | 5 |
| `use_v1_fallback` | 1 |

## Route Rows

| query_id | query_type | route_decision | baseline_call | repaired_call | fallback_reused | expected_calls | actual_baseline_calls | actual_repaired_calls |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q-dev-place-fact-001 | place_fact | `use_repaired_v2_candidate` | True | True | False | 2 | 1 | 1 |
| q-dev-place-story-001 | place_story | `use_v1_fallback` | True | False | True | 1 | 1 | 0 |
| q-dev-relationship-001 | relationship | `use_repaired_v2_candidate` | True | True | False | 2 | 1 | 1 |
| q-dev-overview-001 | overview | `use_repaired_v2_candidate` | True | True | False | 2 | 1 | 1 |
| q-dev-route-context-001 | route_context | `use_repaired_v2_candidate` | True | True | False | 2 | 1 | 1 |
| q-dev-voice-followup-001 | voice_followup | `use_repaired_v2_candidate` | True | True | False | 2 | 1 | 1 |
| q-dev-no-answer-001 | no_answer | `abstain_no_live_call` | False | False | False | 0 | 0 | 0 |

## Baseline Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 1 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 0.048700 |
| overview | 1 | 1 | 1.000000 | 0.600000 | 0.333333 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 4770.714800 |
| place_fact | 1 | 1 | 1.000000 | 0.200000 | 0.500000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 12026.922400 |
| place_story | 1 | 1 | 1.000000 | 0.200000 | 0.125000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2260.664100 |
| relationship | 1 | 1 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 5142.628200 |
| route_context | 1 | 1 | 1.000000 | 0.600000 | 0.500000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2964.319000 |
| voice_followup | 1 | 1 | 1.000000 | 0.800000 | 0.600000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2569.096200 |

## Repaired Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 1 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 0.046400 |
| overview | 1 | 1 | 1.000000 | 1.000000 | 0.333333 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 3041.329200 |
| place_fact | 1 | 1 | 1.000000 | 1.000000 | 0.500000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2867.705000 |
| place_story | 1 | 1 | 1.000000 | 0.200000 | 0.125000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2260.664100 |
| relationship | 1 | 1 | 1.000000 | 1.000000 | 0.833333 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 3234.660100 |
| route_context | 1 | 1 | 1.000000 | 1.000000 | 0.500000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 3675.885500 |
| voice_followup | 1 | 1 | 1.000000 | 0.500000 | 0.600000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2751.587100 |

## Paired Delta

| query_id | query_type | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim delta | citation_count delta | latency_ms delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q-dev-no-answer-001 | no_answer | 0 | 0.000000 | 0.000000 | 0 | 0 | -0.002300 |
| q-dev-overview-001 | overview | 0 | 0.400000 | 0.000000 | 0 | -3 | -1729.385600 |
| q-dev-place-fact-001 | place_fact | 0 | 0.800000 | 0.000000 | 0 | -4 | -9159.217400 |
| q-dev-place-story-001 | place_story | 0 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| q-dev-relationship-001 | relationship | 0 | 0.000000 | -0.166667 | 0 | -3 | -1907.968100 |
| q-dev-route-context-001 | route_context | 0 | 0.400000 | 0.000000 | 0 | -3 | 711.566500 |
| q-dev-voice-followup-001 | voice_followup | 0 | -0.300000 | 0.000000 | 0 | -3 | 182.490900 |

## Query Type Delta

| query_type | eval_count | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim_rate delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 1 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | -0.002300 |
| overview | 1 | 0.000000 | 0.400000 | 0.000000 | 0.000000 | -1729.385600 |
| place_fact | 1 | 0.000000 | 0.800000 | 0.000000 | 0.000000 | -9159.217400 |
| place_story | 1 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| relationship | 1 | 0.000000 | 0.000000 | -0.166667 | 0.000000 | -1907.968100 |
| route_context | 1 | 0.000000 | 0.400000 | 0.000000 | 0.000000 | 711.566500 |
| voice_followup | 1 | 0.000000 | -0.300000 | 0.000000 | 0.000000 | 182.490900 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 7 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: v1 baseline과 repaired v2 routed policy를 같은 query set, retrieval label, packing policy에서 비교했다.
- `provider_boundary`: 이번 runner는 Solar Pro 3 live API를 호출했다. no_answer query는 provider를 호출하지 않았다.
- `fallback_boundary`: place_story는 repaired v2 후보에서 제외하고 v1 fallback answer를 재사용했다.
- `metric_grain`: `fact_solar_generation_v2_repaired_live_eval`의 grain은 repair_id-query_id-route_decision-answer_policy_id-metric_family다.
- `call_budget`: actual_total_solar_call_count=11, hard_cap=20로 제한했다.
- `adoption_boundary`: adoption_decision=reject_repaired_v2_default. dev subset 결과라 production 채택 주장이 아니다.
- `public_policy`: public report와 result row에는 raw query, raw answer, evidence text, chunk text, private path, secret을 저장하지 않는다.
- `external_audit`: route/fallback/call budget과 품질 metric을 분리해 비용 통제와 claim boundary를 유지했다.
- `gate_status`: PASS

## 해석

repaired v2 routed policy는 `place_story`를 v1 fallback으로 처리하고, `no_answer`는 provider 호출 없이 abstain한다.

이 결과는 private dev subset의 live paired comparison이다. 포트폴리오에는 채택/기각 판단 과정으로만 쓰고, 최종 개선 주장은 locked test와 confidence interval을 붙인 뒤에만 사용한다.
