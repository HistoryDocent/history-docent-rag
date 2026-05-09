# BM25 Baseline Report

## 목적

BM25 lexical retrieval을 seed 평가셋에서 측정한다.

이 문서는 성능 개선 주장이 아니다. Dense, Hybrid, query rewrite 비교를 위한 기준선 기록이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `bm25-baseline-report/v1` |
| run_id | `bm25-baseline-q14-d3141-892bc202` |
| generated_at_utc | `2026-05-09T17:21:24+00:00` |
| method | `bm25` |
| top_k | 5 |
| indexed_document_count | 3141 |
| dataset_query_count | 14 |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_path | `evals/datasets/retrieval_eval_seed.jsonl` |
| result_path | `evals/results/bm25_baseline_results.jsonl` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 14 |
| retrieve_query_count | 12 |
| abstain_query_count | 2 |
| result_count | 14 |
| missing_result_count | 0 |
| Recall@1 | 0.083333 |
| Recall@3 | 0.250000 |
| Recall@5 | 0.250000 |
| MRR | 0.152778 |
| nDCG@5 | 0.120124 |
| latency_p50_ms | 6.284100 |
| latency_p95_ms | 7.368800 |
| abstain_with_candidate_count | 2 |

## Query Type Breakdown

| query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | abstain_with_candidate_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 7.055400 | 2 |
| overview | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 8.384900 | 0 |
| place_fact | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 7.039000 | 0 |
| place_story | 2 | 0.500000 | 0.500000 | 0.500000 | 0.500000 | 0.382680 | 7.368800 | 0 |
| relationship | 2 | 0.000000 | 0.500000 | 0.500000 | 0.250000 | 0.220746 | 6.284100 | 0 |
| route_context | 2 | 0.000000 | 0.500000 | 0.500000 | 0.166666 | 0.117319 | 7.253200 | 0 |
| voice_followup | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 4.114100 | 0 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 70 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `baseline_scope`: BM25 lexical baseline만 측정했다. query rewrite, dense retrieval, hybrid retrieval은 제외했다.
- `overall_retrieval`: Recall@5=0.250000, MRR=0.152778, nDCG@5=0.120124.
- `weakest_query_type`: overview: Recall@5=0.000000, MRR=0.000000.
- `abstention_scope`: no_answer는 retrieval recall 대상이 아니라 후보 반환 여부를 보는 abstention risk로 분리한다.
- `voice_followup_risk`: voice_followup: Recall@5=0.000000, MRR=0.000000. lexical query만 사용했다.
- `no_answer_risk`: no_answer 후보 반환 수=2. BM25는 검색기이므로 corpus 밖 질문을 독립적으로 거절하지 못한다.
- `next_step`: Dense retrieval과 Hybrid retrieval을 같은 seed 평가셋에서 비교하고, query rewrite는 별도 ablation으로 검증한다.

## 해석

BM25는 query rewrite, place expansion, dense retrieval, reranking을 적용하지 않은 lexical baseline이다.

`voice_followup`, 영어 query, route형 질문은 이후 query rewrite와 hybrid retrieval의 개선 여지가 큰 영역으로 본다.

`no_answer` 질문에서 후보를 반환하는 것은 BM25의 한계로 기록한다. 최종 RAG에서는 no-answer detector와 answer contract에서 다시 통제해야 한다.
