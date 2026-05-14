# GraphRAG-lite Relationship Input-only Report

## 결론

GraphRAG-lite relationship 후보는 dev input-only 기준에서 기본 RAG pipeline으로 승격하지 않는다.

이 결과는 source child chunk 후보를 재정렬한 검색 입력 비교다. Solar Pro 3 호출, 답변 생성 품질, production 성능 개선 주장이 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `graphrag-lite-relationship-input-only-report/v1` |
| run_id | `graphrag-lite-relationship-input-only-q10-5683abe5` |
| generated_at_utc | `2026-05-14T13:26:46+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path_alias | `<private artifact: parent_child_chunks.json>` |
| baseline_rows_path_alias | `<private artifact: retrieval_experiment_hybrid_weighted_e5_small_alpha_0_5_results.jsonl>` |
| result_rows_path_alias | `<private artifact: graphrag_lite_relationship_input_only_rows.jsonl>` |
| decision | `reject_graphrag_lite_default` |
| best_strategy_id | `hybrid_weighted_e5_small_alpha_0_5_reference` |

## 정량 리포트

| strategy_id | role | query_count | result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | citation_recoverability | graph_candidate_pool_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `hybrid_weighted_e5_small_alpha_0_5_reference` | baseline | 10 | 10 | 0.700000 | 1.000000 | 1.000000 | 0.833333 | 0.709355 | 18.375100 | 1.000000 | 0 |
| `graphrag_lite_entity_path_v1` | candidate | 10 | 10 | 0.700000 | 1.000000 | 1.000000 | 0.833333 | 0.707299 | 27.580100 | 1.000000 | 122 |
| `graphrag_lite_community_hint_v1` | candidate | 10 | 10 | 0.700000 | 1.000000 | 1.000000 | 0.833333 | 0.679018 | 27.511100 | 1.000000 | 122 |

## Baseline Delta

| strategy_id | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: |
| `graphrag_lite_entity_path_v1` | 0.000000 | 0.000000 | -0.002056 | 9.205000 |
| `graphrag_lite_community_hint_v1` | 0.000000 | 0.000000 | -0.030337 | 9.136000 |

## Gate

| metric | value |
| --- | ---: |
| relationship_dev_query_count | 10 |
| expected_relationship_dev_query_count | 10 |
| strategy_count | 3 |
| baseline_count | 1 |
| candidate_count | 2 |
| promoted_candidate_count | 0 |
| solar_call_count | 0 |
| min_citation_recoverability | 1.000000 |
| target_recall_at_5_delta | 0.030000 |
| target_mrr_delta | 0.030000 |
| target_ndcg_at_5_delta | 0.030000 |
| max_latency_p95_ms | 2500.000000 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 34 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `scope`: relationship dev 10개에 한정한 input-only retrieval 후보 비교다.
- `baseline`: hybrid_weighted_e5_small_alpha_0_5_reference 기준 Recall@5=1.000000, MRR=0.833333, nDCG@5=0.709355이다.
- `candidate_result`: 최고 candidate는 graphrag_lite_entity_path_v1이며 Recall@5 delta=0.000000, MRR delta=0.000000, nDCG@5 delta=-0.002056이다.
- `citation_boundary`: Graph/community hint는 citation이 아니며 최종 후보는 source child chunk id로만 남겼다.
- `llm_boundary`: Solar Pro 3 호출은 0이다. 생성 품질 평가는 수행하지 않았다.
- `data_boundary`: public rows는 query id, candidate id, rank, metric, sanitized failure tag만 포함한다.
- `decision_boundary`: dev input-only 결과이므로 locked test 또는 production 개선으로 표현하지 않는다.
- `external_audit`: baseline Recall@5가 이미 높은 경우 GraphRAG-lite는 recall 개선보다 top-rank 품질과 관계형 실패 복구 여부로만 제한적으로 판단해야 한다.
- `gate_status`: PASS
