# Solar Pro 3 Generation Baseline Report

## 목적

private dev stratified subset에서 Solar Pro 3 citation RAG generation baseline을 고정한다.

이 문서는 최종 품질 개선 주장이 아니다. prompt 개선, answer contract 개선, rerank/packing 변경의 비교 기준선을 만들기 위한 baseline이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-generation-baseline-report/v1` |
| generation_eval_report_version | `generation-eval-report/v1` |
| answer_contract_version | `citation-rag-answer/v1` |
| eval_id | `generation-eval-q7-11472c5e` |
| generated_at_utc | `2026-05-12T11:30:55+00:00` |
| dataset_fingerprint | `a08b0d906932c3f0` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| retrieval_run_label | `dense_multilingual_e5_small_voice_rewrite` |
| packing_policy_id | `P0_rank_order` |
| answer_policy_id | `solar-generation-baseline-v1` |
| provider_config_id | `solar-pro-3-2b17971612` |
| endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| model_id | `solar-pro3` |
| per_query_type | 1 |
| query_types | `place_fact, place_story, relationship, overview, route_context, voice_followup, no_answer` |

## 정량 리포트

| metric | value |
| --- | ---: |
| eval_count | 7 |
| answerable_count | 6 |
| no_answer_count | 1 |
| answered_count | 6 |
| abstained_count | 1 |
| Correct-with-Evidence | 1.000000 |
| citation_precision | 0.566667 |
| citation_recall | 0.509722 |
| place_relevance | 0.857143 |
| docent_usefulness | 1.000000 |
| spoken_answer_naturalness | 1.000000 |
| unsupported_claim_rate | 0.000000 |
| abstention_accuracy | 1.000000 |
| latency_p95_ms | 13144.776600 |
| solar_call_count | 6 |
| prompt_tokens | 13948 |
| completion_tokens | 1633 |
| total_tokens | 15581 |
| estimated_cost | 0.000000 |
| missing_citation_count | 0 |
| unsupported_high_count | 0 |

## Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 1 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 0.068200 |
| overview | 1 | 1 | 1.000000 | 0.600000 | 0.333333 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 4676.336600 |
| place_fact | 1 | 1 | 1.000000 | 0.200000 | 0.500000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 13144.776600 |
| place_story | 1 | 1 | 1.000000 | 0.200000 | 0.125000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2935.956800 |
| relationship | 1 | 1 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 3618.264500 |
| route_context | 1 | 1 | 1.000000 | 0.600000 | 0.500000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2942.061200 |
| voice_followup | 1 | 1 | 1.000000 | 0.800000 | 0.600000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 2441.724600 |

## Failure Analysis

| query_type | failure_tags |
| --- | --- |
| no_answer | `none` |
| overview | `low_citation_recall` |
| place_fact | `low_citation_precision, latency_slo_exceeded` |
| place_story | `low_citation_precision, low_citation_recall` |
| relationship | `none` |
| route_context | `none` |
| voice_followup | `none` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 7 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `harness_scope`: CitationRagAnswer를 query grain의 정량 metric으로 변환하는 평가 계층을 구현했다.
- `metric_boundary`: Correct-with-Evidence와 citation 지표는 answerable query만 품질 판단에 사용한다.
- `abstain_boundary`: no_answer query는 abstention_accuracy로 분리해 corpus 밖 질문 환각을 감시한다.
- `cost_boundary`: Solar Pro 3 호출 6회를 기록했다. estimated_cost는 provider 설정의 단가가 0이면 0으로 남을 수 있다.
- `public_policy`: public row와 report에는 원문 evidence, chunk text, raw answer text를 저장하지 않는다.
- `gate_status`: PASS

## 해석

이 baseline은 query type별 1건으로 live generation 경로와 실패 유형을 관찰하는 기준선이다.

다음 단계의 prompt 또는 answer contract 개선은 이 report와 같은 query set, 같은 retrieval label, 같은 packing policy에서 paired comparison으로만 주장한다.
