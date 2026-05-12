# Generation Evaluation Harness Report

## 목적

Citation RAG answer contract 결과를 Solar Pro 3 provider 연결 전에 평가 가능한 metric으로 고정한다.

이 문서는 답변 품질 개선 주장이 아니다. 현재 리포트는 harness smoke 결과이며, 실제 품질 주장은 private dev/test generation 실행과 paired comparison 이후에만 가능하다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `generation-eval-report/v1` |
| answer_contract_version | `citation-rag-answer/v1` |
| eval_id | `generation-eval-q2-dd33cce7` |
| generated_at_utc | `2026-05-12T08:34:26+00:00` |
| dataset_fingerprint | `fe5949712fdc1936` |

## 정량 리포트

| metric | value |
| --- | ---: |
| eval_count | 2 |
| answerable_count | 1 |
| no_answer_count | 1 |
| answered_count | 1 |
| abstained_count | 1 |
| Correct-with-Evidence | 1.000000 |
| citation_precision | 1.000000 |
| citation_recall | 1.000000 |
| place_relevance | 1.000000 |
| docent_usefulness | 1.000000 |
| spoken_answer_naturalness | 1.000000 |
| unsupported_claim_rate | 0.000000 |
| abstention_accuracy | 1.000000 |
| latency_p95_ms | 0.000000 |
| solar_call_count | 0 |
| estimated_cost | 0.000000 |
| missing_citation_count | 0 |
| unsupported_high_count | 0 |

## Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 1 | 0 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 0.000000 |
| place_story | 1 | 1 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 0.000000 |

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
- `cost_boundary`: 현재 smoke run은 Solar Pro 3를 호출하지 않아 solar_call_count와 estimated_cost가 0이다.
- `public_policy`: public row와 report에는 원문 evidence, chunk text, raw answer text를 저장하지 않는다.
- `gate_status`: PASS

## 해석

현재 단계는 generation 평가 harness 구현이다.

다음 단계에서 Solar Pro 3 provider를 연결하되, 이 metric과 public-safe output gate를 그대로 사용한다.
