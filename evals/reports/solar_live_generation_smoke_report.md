# Solar Pro 3 Live Generation Smoke Report

## 목적

private retrieval 결과를 Solar Pro 3 structured output provider에 연결해 citation RAG answer contract와 generation eval harness가 실제 provider 호출을 견디는지 확인한다.

이 문서는 최종 답변 품질 개선 주장이 아니다. 작은 smoke subset이며, retrieval hit 여부와 답변 품질 판단은 추후 dev/test paired comparison에서 분리한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-live-generation-smoke-report/v1` |
| generation_eval_report_version | `generation-eval-report/v1` |
| answer_contract_version | `citation-rag-answer/v1` |
| eval_id | `generation-eval-q2-cc891f1e` |
| generated_at_utc | `2026-05-12T11:14:21+00:00` |
| dataset_fingerprint | `ba1a2fbeab90686c` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| retrieval_run_label | `dense_multilingual_e5_small_voice_rewrite` |
| packing_policy_id | `P0_rank_order` |
| provider_config_id | `solar-pro-3-2b17971612` |
| endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| model_id | `solar-pro3` |
| answerable_limit | 1 |
| no_answer_limit | 1 |

## 정량 리포트

| metric | value |
| --- | ---: |
| eval_count | 2 |
| answerable_count | 1 |
| no_answer_count | 1 |
| answered_count | 1 |
| abstained_count | 1 |
| Correct-with-Evidence | 1.000000 |
| citation_precision | 0.200000 |
| citation_recall | 0.500000 |
| place_relevance | 0.500000 |
| docent_usefulness | 0.500000 |
| spoken_answer_naturalness | 0.500000 |
| unsupported_claim_rate | 0.000000 |
| abstention_accuracy | 1.000000 |
| latency_p95_ms | 13524.912600 |
| solar_call_count | 1 |
| prompt_tokens | 2204 |
| completion_tokens | 272 |
| total_tokens | 2476 |
| estimated_cost | 0.000000 |
| missing_citation_count | 0 |
| unsupported_high_count | 0 |

## Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 1 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 0.046200 |
| place_fact | 1 | 1 | 1.000000 | 0.200000 | 0.500000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 13524.912600 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 2 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `harness_scope`: CitationRagAnswer를 query grain의 정량 metric으로 변환하는 평가 계층을 구현했다.
- `metric_boundary`: Correct-with-Evidence와 citation 지표는 answerable query만 품질 판단에 사용한다.
- `abstain_boundary`: no_answer query는 abstention_accuracy로 분리해 corpus 밖 질문 환각을 감시한다.
- `cost_boundary`: Solar Pro 3 호출 1회를 기록했다. estimated_cost는 provider 설정의 단가가 0이면 0으로 남을 수 있다.
- `public_policy`: public row와 report에는 원문 evidence, chunk text, raw answer text를 저장하지 않는다.
- `gate_status`: PASS

## 해석

이 smoke는 live provider 연결과 public-safe 평가 산출물 생성을 검증한다. 답변 원문과 evidence 원문은 report/result row에 저장하지 않는다.

다음 단계에서는 같은 generation eval harness로 chunking, retrieval, rerank, generation 조합을 고정된 dev/test set에서 비교한다.
