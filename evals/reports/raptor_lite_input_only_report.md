# RAPTOR-lite Input-only Report

## 결론

RAPTOR-lite 후보는 dev input-only 기준에서 기본 RAG pipeline으로 승격하지 않는다.

이 결과는 parent/doc summary-like group을 이용해 source child chunk 후보를 재정렬한 검색 입력 비교다. Solar Pro 3 호출, 답변 생성 품질, production 성능 개선 주장이 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `raptor-lite-input-only-report/v1` |
| run_id | `raptor-lite-input-only-q20-24a726ed` |
| generated_at_utc | `2026-05-14T14:19:01+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path_alias | `<private artifact: parent_child_chunks.json>` |
| baseline_rows_path_alias | `<private artifact: retrieval_experiment_dense_multilingual_e5_small_voice_rewrite_results.jsonl>` |
| result_rows_path_alias | `<private artifact: raptor_lite_input_only_rows.jsonl>` |
| target_query_types | `overview, place_story` |
| query_type_counts | `overview=10, place_story=10` |
| decision | `reject_raptor_lite_default` |
| best_strategy_id | `dense_multilingual_e5_small_voice_rewrite_reference` |

## 정량 리포트

| strategy_id | role | query_scope | query_count | result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | citation_recoverability | summary_group_pool_count |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `dense_multilingual_e5_small_voice_rewrite_reference` | baseline | combined | 20 | 20 | 0.650000 | 0.700000 | 0.700000 | 0.675000 | 0.524622 | 15.564100 | 1.000000 | 0 |
| `dense_multilingual_e5_small_voice_rewrite_reference` | baseline | overview | 10 | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.610343 | 16.004600 | 1.000000 | 0 |
| `dense_multilingual_e5_small_voice_rewrite_reference` | baseline | place_story | 10 | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.438900 | 15.156600 | 1.000000 | 0 |
| `raptor_lite_parent_summary_v1` | candidate | combined | 20 | 20 | 0.650000 | 0.700000 | 0.700000 | 0.675000 | 0.449665 | 29.923700 | 1.000000 | 160 |
| `raptor_lite_parent_summary_v1` | candidate | overview | 10 | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.472934 | 30.018000 | 1.000000 | 160 |
| `raptor_lite_parent_summary_v1` | candidate | place_story | 10 | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.426397 | 28.022500 | 1.000000 | 160 |
| `raptor_lite_summary_node_v1` | candidate | combined | 20 | 20 | 0.650000 | 0.700000 | 0.700000 | 0.675000 | 0.494653 | 122.111000 | 1.000000 | 160 |
| `raptor_lite_summary_node_v1` | candidate | overview | 10 | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.571987 | 122.111000 | 1.000000 | 160 |
| `raptor_lite_summary_node_v1` | candidate | place_story | 10 | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.417320 | 136.229000 | 1.000000 | 160 |

## Baseline Delta

| strategy_id | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: |
| `raptor_lite_parent_summary_v1` | 0.000000 | 0.000000 | -0.074957 | 14.359600 |
| `raptor_lite_summary_node_v1` | 0.000000 | 0.000000 | -0.029969 | 106.546900 |

## Gate

| metric | value |
| --- | ---: |
| target_dev_query_count | 20 |
| expected_target_dev_query_count | 20 |
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
| result_row_count | 70 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `scope`: overview/place_story dev 20개에 한정한 input-only retrieval 후보 비교다.
- `baseline`: dense_multilingual_e5_small_voice_rewrite_reference 기준 Recall@5=0.700000, MRR=0.675000, nDCG@5=0.524622이다.
- `candidate_result`: 최고 candidate는 raptor_lite_summary_node_v1이며 Recall@5 delta=0.000000, MRR delta=0.000000, nDCG@5 delta=-0.029969이다.
- `raptor_boundary`: 이번 구현은 LLM 요약 생성이 아니라 parent/doc group의 summary-like token signal만 사용하는 RAPTOR-lite다.
- `citation_boundary`: summary-like group은 citation이 아니며 최종 후보는 source child chunk id로만 남겼다.
- `llm_boundary`: Solar Pro 3 호출은 0이다. 생성 품질 평가는 수행하지 않았다.
- `data_boundary`: public rows는 query id, candidate id, rank, metric, sanitized failure tag만 포함한다.
- `decision_boundary`: dev input-only 결과이므로 locked test 또는 production 개선으로 표현하지 않는다.
- `external_audit`: RAPTOR-lite가 유효하려면 overview/place_story에서 top-rank 품질 또는 recall이 기준선보다 올라야 한다.
- `gate_status`: PASS
