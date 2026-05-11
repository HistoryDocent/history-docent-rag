# Retrieval Overlap Analysis Report

## 목적

BM25와 Dense D0가 서로 보완되는지 확인한다.

이 문서는 Hybrid 성능 개선 주장이 아니다. 실제 Hybrid RRF/Weighted 실험 전에 oracle union 상한과 query type별 보완 가능성을 검증하는 중간 리포트다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-overlap-analysis/v1` |
| analysis_id | `retrieval-overlap-q70-9b827f0e` |
| generated_at_utc | `2026-05-11T09:20:33+00:00` |
| methods | `bm25, dense` |
| top_k | 5 |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| result_paths | `<private artifact: retrieval_experiment_bm25_results.jsonl>, <private artifact: retrieval_experiment_dense_results.jsonl>` |
| hybrid_decision | `proceed_to_hybrid_rrf` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 70 |
| retrieve_query_count | 60 |
| abstain_query_count | 10 |
| bm25_only_hit_count | 15 |
| dense_only_hit_count | 2 |
| both_hit_count | 19 |
| both_fail_count | 24 |
| oracle_union_hit_count | 36 |
| bm25_recall_at_5 | 0.566667 |
| dense_recall_at_5 | 0.350000 |
| oracle_union_recall_at_5 | 0.600000 |
| oracle_union_delta_vs_bm25 | 0.033333 |
| dense_only_share | 0.033333 |
| bm25_abstain_with_candidate_count | 10 |
| dense_abstain_with_candidate_count | 10 |

## Query Type Breakdown

| query_type | query_count | retrieve_query_count | abstain_query_count | bm25_only_hit_count | dense_only_hit_count | both_hit_count | both_fail_count | oracle_union_hit_count | bm25_recall_at_5 | dense_recall_at_5 | oracle_union_recall_at_5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 10 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 |
| overview | 10 | 10 | 0 | 2 | 1 | 4 | 3 | 7 | 0.600000 | 0.500000 | 0.700000 |
| place_fact | 10 | 10 | 0 | 3 | 1 | 4 | 2 | 8 | 0.700000 | 0.500000 | 0.800000 |
| place_story | 10 | 10 | 0 | 2 | 0 | 4 | 4 | 6 | 0.600000 | 0.400000 | 0.600000 |
| relationship | 10 | 10 | 0 | 4 | 0 | 4 | 2 | 8 | 0.800000 | 0.400000 | 0.800000 |
| route_context | 10 | 10 | 0 | 3 | 0 | 3 | 4 | 6 | 0.600000 | 0.300000 | 0.600000 |
| voice_followup | 10 | 10 | 0 | 1 | 0 | 0 | 9 | 1 | 0.100000 | 0.000000 | 0.100000 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 70 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `analysis_scope`: private dev split의 BM25와 Dense D0 top-k 후보 ID만 비교했다.
- `oracle_union_boundary`: oracle union은 두 method 중 하나라도 정답을 포함했는지 보는 상한이며 실제 retriever가 아니다.
- `dense_boundary`: Dense D0는 sklearn-tfidf-svd-v1이며 BGE-M3 또는 multilingual-E5 같은 neural embedding 결과가 아니다.
- `hybrid_decision`: Dense D0가 BM25 실패 query 일부를 보완했다. Hybrid RRF/Weighted 실험을 진행할 근거는 있으나 개선 주장은 아직 불가하다.
- `no_answer_policy`: no-answer query candidate count는 BM25 10, Dense 10로 기록했다.
- `public_policy`: public report에는 query text, chunk text, raw result body를 저장하지 않는다.

## 해석

oracle union은 실제 Hybrid 결과가 아니라 BM25와 Dense D0가 동시에 제공할 수 있는 검색 상한이다.

Hybrid 구현 여부는 이 리포트의 보완성 수치로 판단하되, 최종 성능 개선 주장은 별도 Hybrid 실행 결과와 locked test 확인 전까지 금지한다.
