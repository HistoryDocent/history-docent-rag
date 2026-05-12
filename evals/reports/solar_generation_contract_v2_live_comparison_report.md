# Solar Pro 3 Generation Contract v2 Live Comparison Report

## 목적

Solar Pro 3 실제 호출로 `CitationRagDraft` v1과 `CitationRagDraftV2` selected evidence contract를 같은 query set, 같은 retrieval label, 같은 evidence packing policy에서 paired comparison으로 비교한다.

이 문서는 private dev subset 기반의 실험 결과다. 최종 성능 개선 주장이 아니라 generation contract v2 채택 여부를 판단하기 위한 근거다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-generation-contract-v2-live-comparison-report/v1` |
| comparison_id | `solar-generation-contract-v2-q7-dedd6bf6` |
| generated_at_utc | `2026-05-12T13:24:02+00:00` |
| dataset_fingerprint | `a08b0d906932c3f0` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| retrieval_run_label | `dense_multilingual_e5_small_voice_rewrite` |
| packing_policy_id | `P0_rank_order` |
| baseline_answer_policy_id | `solar-generation-baseline-v1` |
| candidate_answer_policy_id | `solar-generation-contract-v2` |
| baseline_provider_config_id | `solar-pro-3-2b17971612` |
| candidate_provider_config_id | `solar-pro-3-8d22036345` |
| baseline_model_id | `solar-pro3` |
| candidate_model_id | `solar-pro3` |
| baseline_endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| candidate_endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| per_query_type | 1 |
| query_types | `place_fact, place_story, relationship, overview, route_context, voice_followup, no_answer` |

## 정량 리포트

| metric | v1 baseline | v2 candidate | delta |
| --- | ---: | ---: | ---: |
| eval_count | 7 | 7 | 0 |
| Correct-with-Evidence | 1.000000 | 0.833333 | -0.166667 |
| citation_precision | 0.566667 | 0.750000 | 0.183333 |
| citation_recall | 0.509722 | 0.461111 | -0.048611 |
| place_relevance | 0.857143 | 0.857143 | 0.000000 |
| docent_usefulness | 1.000000 | 0.857143 | -0.142857 |
| spoken_answer_naturalness | 1.000000 | 1.000000 | 0.000000 |
| unsupported_claim_rate | 0.000000 | 0.142857 | 0.142857 |
| abstention_accuracy | 1.000000 | 1.000000 | 0.000000 |
| latency_p95_ms | 13743.580900 | 4372.871200 | -9370.709700 |
| solar_call_count | 6 | 6 | 0 |
| prompt_tokens | 13948 | 15196 | 1248 |
| completion_tokens | 1546 | 1815 | 269 |
| total_tokens | 15494 | 17011 | 1517 |
| estimated_cost | 0.000000 | 0.000000 | 0.000000 |
| missing_citation_count | 0 | 0 | 0 |
| unsupported_high_count | 0 | 0 | 0 |

## Baseline Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 1 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 0.048900 |
| overview | 1 | 1 | 1.000000 | 0.600000 | 0.333333 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 5337.116300 |
| place_fact | 1 | 1 | 1.000000 | 0.200000 | 0.500000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 13743.580900 |
| place_story | 1 | 1 | 1.000000 | 0.200000 | 0.125000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2176.167800 |
| relationship | 1 | 1 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 11397.932100 |
| route_context | 1 | 1 | 1.000000 | 0.600000 | 0.500000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2174.253300 |
| voice_followup | 1 | 1 | 1.000000 | 0.800000 | 0.600000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 3033.280000 |

## Candidate Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 1 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 0.047500 |
| overview | 1 | 1 | 1.000000 | 1.000000 | 0.333333 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 3993.527800 |
| place_fact | 1 | 1 | 1.000000 | 1.000000 | 0.500000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2628.528000 |
| place_story | 1 | 1 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 1.000000 | 3041.728500 |
| relationship | 1 | 1 | 1.000000 | 1.000000 | 0.833333 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2769.966800 |
| route_context | 1 | 1 | 1.000000 | 1.000000 | 0.500000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 4372.871200 |
| voice_followup | 1 | 1 | 1.000000 | 0.500000 | 0.600000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 3142.781600 |

## Paired Delta

| query_id | query_type | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim delta | citation_count delta | latency_ms delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q-dev-no-answer-001 | no_answer | 0 | 0.000000 | 0.000000 | 0 | 0 | -0.001400 |
| q-dev-overview-001 | overview | 0 | 0.400000 | 0.000000 | 0 | -3 | -1343.588500 |
| q-dev-place-fact-001 | place_fact | 0 | 0.800000 | 0.000000 | 0 | -4 | -11115.052900 |
| q-dev-place-story-001 | place_story | -1 | -0.200000 | -0.125000 | 1 | -4 | 865.560700 |
| q-dev-relationship-001 | relationship | 0 | 0.000000 | -0.166667 | 0 | -2 | -8627.965300 |
| q-dev-route-context-001 | route_context | 0 | 0.400000 | 0.000000 | 0 | -3 | 2198.617900 |
| q-dev-voice-followup-001 | voice_followup | 0 | -0.300000 | 0.000000 | 0 | -3 | 109.501600 |

## Query Type Delta

| query_type | eval_count | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim_rate delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 1 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | -0.001400 |
| overview | 1 | 0.000000 | 0.400000 | 0.000000 | 0.000000 | -1343.588500 |
| place_fact | 1 | 0.000000 | 0.800000 | 0.000000 | 0.000000 | -11115.052900 |
| place_story | 1 | -1.000000 | -0.200000 | -0.125000 | 1.000000 | 865.560700 |
| relationship | 1 | 0.000000 | 0.000000 | -0.166667 | 0.000000 | -8627.965300 |
| route_context | 1 | 0.000000 | 0.400000 | 0.000000 | 0.000000 | 2198.617900 |
| voice_followup | 1 | 0.000000 | -0.300000 | 0.000000 | 0.000000 | 109.501600 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 7 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: v1/v2 generation contract만 다르게 두고 query set, retrieval label, packing policy를 고정했다.
- `provider_boundary`: 이번 runner는 Solar Pro 3 live API를 호출한다. no_answer query는 abstain contract로 처리해 provider를 호출하지 않는다.
- `metric_grain`: query 단위 paired delta와 query_type delta를 분리해 기록한다.
- `citation_policy`: v1은 packed evidence 전체를 citation으로 붙이고, v2는 selected evidence rank만 citation으로 붙인다.
- `latency_cost_boundary`: candidate latency_p95 delta는 -9370.709700ms다. token/cost 변화는 정량 표에서 별도로 판단한다.
- `place_story_boundary`: `place_story`는 retrieval hard-case 영향을 받기 쉬워 generation contract 개선 판단에서 별도 모니터링한다.
- `claim_boundary`: 현재 결과는 private dev subset의 live paired comparison이며 final production 성능 개선 주장이 아니다.
- `public_policy`: public report와 result row에는 raw query, raw answer, evidence text, chunk text, private path, secret을 저장하지 않는다.
- `gate_status`: PASS

## 해석

v2는 Solar Pro 3가 선택한 evidence rank만 citation으로 붙이는 계약이다. 따라서 citation precision, citation count, latency/token 변화를 함께 본다.

이번 실험은 locked test가 아니라 private dev subset에서 실행했다. 포트폴리오에는 "채택 후보 검증"으로만 쓰고, 최종 개선 주장은 이후 locked test와 bootstrap confidence interval을 붙인 뒤에만 사용한다.
