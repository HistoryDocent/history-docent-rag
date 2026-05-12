# Solar Pro 3 Generation Contract v2 Comparison Report

## 목적

`CitationRagDraft` v1과 `CitationRagDraftV2` selected evidence contract를 같은 query set, 같은 retrieval label, 같은 evidence packing policy에서 비교한다.

이 문서는 fake provider 기반 contract 비교다. live Solar Pro 3 호출 결과가 아니며, 최종 성능 개선 주장이 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-generation-contract-v2-comparison-report/v1` |
| comparison_id | `solar-generation-contract-v2-q7-84bbc1a5` |
| generated_at_utc | `2026-05-12T12:55:41+00:00` |
| dataset_fingerprint | `a506c91b33189c1c` |
| retrieval_run_label | `dense_multilingual_e5_small_voice_rewrite` |
| packing_policy_id | `P0_rank_order` |
| baseline_answer_policy_id | `solar-generation-baseline-v1` |
| candidate_answer_policy_id | `solar-generation-contract-v2` |
| baseline_provider_config_id | `fake-solar-generation-v1` |
| candidate_provider_config_id | `fake-solar-generation-v2` |
| live_solar_call_count | 0 |

## 정량 리포트

| metric | v1 baseline | v2 candidate | delta |
| --- | ---: | ---: | ---: |
| eval_count | 7 | 7 | 0 |
| Correct-with-Evidence | 1.000000 | 1.000000 | 0.000000 |
| citation_precision | 0.333333 | 1.000000 | 0.666667 |
| citation_recall | 1.000000 | 1.000000 | 0.000000 |
| unsupported_claim_rate | 0.000000 | 0.000000 | 0.000000 |
| abstention_accuracy | 1.000000 | 1.000000 | 0.000000 |
| latency_p95_ms | 0.000000 | 0.000000 | 0.000000 |
| solar_call_count | 0 | 0 | 0 |

## Paired Delta

| query_id | query_type | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim delta | citation_count delta | latency_ms delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q-fake-no_answer-001 | no_answer | 0 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| q-fake-overview-001 | overview | 0 | 0.666667 | 0.000000 | 0 | -2 | 0.000000 |
| q-fake-place_fact-001 | place_fact | 0 | 0.666667 | 0.000000 | 0 | -2 | 0.000000 |
| q-fake-place_story-001 | place_story | 0 | 0.666667 | 0.000000 | 0 | -2 | 0.000000 |
| q-fake-relationship-001 | relationship | 0 | 0.666667 | 0.000000 | 0 | -2 | 0.000000 |
| q-fake-route_context-001 | route_context | 0 | 0.666667 | 0.000000 | 0 | -2 | 0.000000 |
| q-fake-voice_followup-001 | voice_followup | 0 | 0.666667 | 0.000000 | 0 | -2 | 0.000000 |

## Query Type Delta

| query_type | eval_count | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim_rate delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 1 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| overview | 1 | 0.000000 | 0.666667 | 0.000000 | 0.000000 | 0.000000 |
| place_fact | 1 | 0.000000 | 0.666667 | 0.000000 | 0.000000 | 0.000000 |
| place_story | 1 | 0.000000 | 0.666667 | 0.000000 | 0.000000 | 0.000000 |
| relationship | 1 | 0.000000 | 0.666667 | 0.000000 | 0.000000 | 0.000000 |
| route_context | 1 | 0.000000 | 0.666667 | 0.000000 | 0.000000 | 0.000000 |
| voice_followup | 1 | 0.000000 | 0.666667 | 0.000000 | 0.000000 | 0.000000 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 7 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: v1/v2 answer policy만 다르게 두고 query set, retrieval label, packing policy를 고정했다.
- `provider_boundary`: 이번 runner는 fake provider 기반 contract gate다. Solar Pro 3 live API를 호출하지 않았다.
- `metric_grain`: query 단위 paired delta와 query_type delta를 분리해 기록한다.
- `citation_policy`: v1은 packed evidence 전체를 citation으로 붙이고, v2는 selected evidence rank만 citation으로 붙인다.
- `place_story_boundary`: `place_story`는 fake contract run에는 포함하지만 live 개선 판단에서는 retrieval hard-case monitor로 분리한다.
- `claim_boundary`: 현재 결과는 성능 개선 주장이 아니라 live paired comparison 전의 runner 검증이다.
- `public_policy`: public report와 result row에는 raw query, raw answer, evidence text, chunk text를 저장하지 않는다.
- `gate_status`: PASS

## 해석

이번 결과는 selected evidence contract가 citation 수와 precision metric에 어떤 영향을 주는지 확인하는 fake provider gate다.

다음 단계에서만 같은 7개 query set, 같은 retrieval label, 같은 packing policy로 live Solar Pro 3 paired comparison을 실행한다.
