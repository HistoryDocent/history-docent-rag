# Solar Pro 3 Guarded Boost Live Comparison Report

## 목적

`parent_doc_context_boost_guarded`가 실제 Solar Pro 3 답변 품질에서도 baseline 대비 도움이 되는지 `place_story` dev 10개에서 paired comparison으로 검증한다.

이 문서는 private dev subset 기반의 실험 결과다. 최종 성능 개선 주장이 아니라 guarded boost 채택 여부를 판단하기 위한 근거다. raw query, raw answer, raw evidence, prompt, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-guarded-boost-live-comparison-report/v1` |
| comparison_id | `solar-guarded-boost-live-q10-a93675ab` |
| generated_at_utc | `2026-05-14T11:13:15+00:00` |
| dataset_fingerprint | `fade128ced35d07d` |
| dry_run_id | `solar-guarded-boost-dry-q10-bc3d9373` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| baseline_strategy_id | `baseline_dense_e5_voice_rewrite` |
| candidate_strategy_id | `parent_doc_context_boost` |
| guarded_strategy_id | `parent_doc_context_boost_guarded` |
| router_policy_id | `place_story_guarded_boost_v1` |
| answer_contract_version | `citation-rag-answer/v1` |
| answer_policy_id | `solar-guarded-boost-live-v1` |
| provider_config_id | `solar-pro-3-2b17971612` |
| endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| model_id | `solar-pro3` |
| top_k | 5 |
| candidate_k | 20 |
| max_context_chars | 11000 |

## Live Call Summary

| metric | value |
| --- | ---: |
| query_count | 10 |
| baseline_live_call_count | 10 |
| candidate_live_call_count | 1 |
| reused_candidate_count | 9 |
| changed_candidate_input_count | 1 |
| expected_total_live_call_count | 11 |
| actual_solar_call_count | 11 |
| live_call_hard_cap | 20 |
| baseline_prompt_tokens | 23706 |
| baseline_completion_tokens | 2997 |
| baseline_total_tokens | 26703 |
| candidate_prompt_tokens | 2574 |
| candidate_completion_tokens | 460 |
| candidate_total_tokens | 3034 |
| total_prompt_tokens | 26280 |
| total_completion_tokens | 3457 |
| total_tokens | 29737 |
| estimated_cost | 0.000000 |

## 정량 리포트

| metric | baseline | guarded candidate | delta |
| --- | ---: | ---: | ---: |
| eval_count | 10 | 10 | 0 |
| Correct-with-Evidence | 0.900000 | 0.900000 | 0.000000 |
| citation_precision | 0.580000 | 0.580000 | 0.000000 |
| citation_recall | 0.481309 | 0.509881 | 0.028572 |
| place_relevance | 1.000000 | 1.000000 | 0.000000 |
| docent_usefulness | 0.800000 | 0.800000 | 0.000000 |
| spoken_answer_naturalness | 0.900000 | 0.900000 | 0.000000 |
| unsupported_claim_rate | 0.100000 | 0.100000 | 0.000000 |
| abstention_accuracy | 1.000000 | 1.000000 | 0.000000 |
| latency_p95_ms | 5066.690100 | 5455.679600 | 388.989500 |
| solar_call_count | 10 | 1 | -9 |
| estimated_cost | 0.000000 | 0.000000 | 0.000000 |
| missing_citation_count | 0 | 0 | 0 |
| unsupported_high_count | 0 | 0 | 0 |

## Baseline Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| place_story | 10 | 10 | 0.900000 | 0.580000 | 0.481309 | 1.000000 | 0.800000 | 0.900000 | 0.100000 | 1.000000 | 5066.690100 |

## Candidate Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| place_story | 10 | 10 | 0.900000 | 0.580000 | 0.509881 | 1.000000 | 0.800000 | 0.900000 | 0.100000 | 1.000000 | 5455.679600 |

## Paired Delta

| query_id | query_type | route_decision | reuse_decision | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim delta | citation_count delta | latency_ms delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q-dev-place-story-001 | place_story | use_baseline_correctness_guardrail | reuse_baseline_result | 0 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| q-dev-place-story-002 | place_story | use_candidate_direct_gain | candidate_live_call_required | 0 | 0.000000 | 0.285715 | 0 | 0 | 2074.931200 |
| q-dev-place-story-003 | place_story | use_baseline_no_candidate_gain | reuse_baseline_result | 0 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| q-dev-place-story-004 | place_story | use_baseline_precision_guardrail | reuse_baseline_result | 0 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| q-dev-place-story-005 | place_story | use_baseline_precision_guardrail | reuse_baseline_result | 0 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| q-dev-place-story-006 | place_story | use_baseline_no_candidate_gain | reuse_baseline_result | 0 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| q-dev-place-story-007 | place_story | use_baseline_no_candidate_gain | reuse_baseline_result | 0 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| q-dev-place-story-008 | place_story | use_baseline_doc_guardrail | reuse_baseline_result | 0 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| q-dev-place-story-009 | place_story | manual_review_required | reuse_baseline_result | 0 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| q-dev-place-story-010 | place_story | manual_review_required | reuse_baseline_result | 0 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |

## Query Type Delta

| query_type | eval_count | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim_rate delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| place_story | 10 | 0.000000 | 0.000000 | 0.028571 | 0.000000 | 2074.931200 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 10 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: `place_story` dev 10개에서 baseline retrieval과 guarded boost retrieval만 다르게 둔 live paired comparison이다.
- `provider_boundary`: Solar Pro 3 live API를 호출했다. 동일 input fingerprint candidate는 baseline generation 결과를 재사용했다.
- `metric_grain`: query 단위 paired delta와 query_type delta를 분리해 기록한다.
- `reuse_policy`: candidate 9건은 baseline 결과를 재사용했고, 1건만 추가 호출했다.
- `qualitative_tags`: citation_recall_gain=1, citation_precision_regression=0, unsupported_regression=0, no_material_change=9
- `adoption_decision`: promote_guarded_candidate_for_next_gate
- `claim_boundary`: 현재 결과는 private dev 10건의 live comparison이며 최종 성능 개선 주장이 아니다.
- `public_policy`: public report와 result row에는 raw query, raw answer, evidence text, chunk text, private path, secret을 저장하지 않는다.
- `gate_status`: PASS

## 채택 판단

`promote_guarded_candidate_for_next_gate`

## 해석

이번 실험은 locked test가 아니라 private dev `place_story` 10건에서 실행했다. candidate 채택은 Correct-with-Evidence, citation precision, citation recall, unsupported claim, latency/cost를 함께 보고 판단한다.
