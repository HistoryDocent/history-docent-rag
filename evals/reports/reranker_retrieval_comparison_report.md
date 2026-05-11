# Retrieval Harness Report

## 목적

BM25, Dense, Hybrid retrieval을 같은 평가셋과 같은 metric으로 비교한다.

이 문서는 성능 개선 주장이 아니다. method별 기준선과 delta를 기록하고, locked test와 generation 평가 전까지는 개선 표현을 사용하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-experiment-report/v1` |
| comparison_id | `retrieval-harness-bm25-dense_multilingual_e5_small-hybrid_weighted_e5_small_alpha_0_5-dense_multilingual_e5_small_rerank_bge_m3_top20-q70-bb71a06c` |
| generated_at_utc | `2026-05-11T14:26:53+00:00` |
| baseline_method | `bm25` |
| method_count | 4 |
| top_k | 5 |
| dataset_fingerprint | `224e3cad1c078eeb` |
| corpus_fingerprint | `e23457a7ad59042f` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| result_artifact_count | 4 |

## Result Artifacts

| run_label | result_path |
| --- | --- |
| bm25 | `<private artifact: retrieval_experiment_bm25_results.jsonl>` |
| dense_multilingual_e5_small | `<private artifact: retrieval_experiment_dense_multilingual_e5_small_results.jsonl>` |
| hybrid_weighted_e5_small_alpha_0_5 | `<private artifact: retrieval_experiment_hybrid_weighted_e5_small_alpha_0_5_results.jsonl>` |
| dense_multilingual_e5_small_rerank_bge_m3_top20 | `<private artifact: retrieval_experiment_dense_multilingual_e5_small_rerank_bge_m3_top20_results.jsonl>` |

## Method Config

| run_label | method | config |
| --- | --- | --- |
| bm25 | bm25 | `method=bm25, top_k=5, reranking=False` |
| dense_multilingual_e5_small | dense | `method=dense, top_k=5, encoder_id=multilingual-e5-small, encoder_backend=sentence_transformers, model_name=intfloat/multilingual-e5-small, reranking=False` |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | `method=hybrid_weighted, top_k=5, dense_encoder_id=multilingual-e5-small, dense_encoder_backend=sentence_transformers, dense_model_name=intfloat/multilingual-e5-small, dense_weight_alpha=0.5, fusion=minmax_weighted_sum, reranking=False` |
| dense_multilingual_e5_small_rerank_bge_m3_top20 | dense | `method=dense, top_k=5, encoder_id=multilingual-e5-small, encoder_backend=sentence_transformers, model_name=intfloat/multilingual-e5-small, retrieval_candidate_k=20, reranking=True, base_run_label=dense_multilingual_e5_small, reranker_id=bge-reranker-v2-m3, reranker_backend=sentence_transformers_cross_encoder, reranker_model_name=BAAI/bge-reranker-v2-m3` |

## 정량 리포트

| run_label | method | query_count | retrieve_query_count | abstain_query_count | result_count | missing_result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p50_ms | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | 70 | 60 | 10 | 70 | 0 | 0.400000 | 0.533333 | 0.566667 | 0.471389 | 0.344203 | 6.312200 | 7.983400 | 10 |
| dense_multilingual_e5_small | dense | 70 | 60 | 10 | 70 | 0 | 0.633333 | 0.716667 | 0.733333 | 0.675556 | 0.533797 | 14.958000 | 17.921900 | 10 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | 70 | 60 | 10 | 70 | 0 | 0.566667 | 0.733333 | 0.783333 | 0.655278 | 0.509310 | 24.112200 | 30.737600 | 10 |
| dense_multilingual_e5_small_rerank_bge_m3_top20 | dense | 70 | 60 | 10 | 70 | 0 | 0.716667 | 0.816667 | 0.833333 | 0.761667 | 0.635787 | 10125.663400 | 13140.690300 | 10 |

## Query Type Breakdown

| run_label | method | query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 7.836500 | 10 |
| bm25 | bm25 | overview | 10 | 0.500000 | 0.500000 | 0.600000 | 0.525000 | 0.357596 | 8.157000 | 0 |
| bm25 | bm25 | place_fact | 10 | 0.400000 | 0.700000 | 0.700000 | 0.533333 | 0.426514 | 7.605800 | 0 |
| bm25 | bm25 | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.424299 | 7.596100 | 0 |
| bm25 | bm25 | relationship | 10 | 0.400000 | 0.700000 | 0.800000 | 0.570000 | 0.434678 | 7.813900 | 0 |
| bm25 | bm25 | route_context | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.383448 | 8.489200 | 0 |
| bm25 | bm25 | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 5.366200 | 0 |
| dense_multilingual_e5_small | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 16.132600 | 10 |
| dense_multilingual_e5_small | dense | overview | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.610343 | 18.121100 | 0 |
| dense_multilingual_e5_small | dense | place_fact | 10 | 0.800000 | 1.000000 | 1.000000 | 0.900000 | 0.783397 | 17.963700 | 0 |
| dense_multilingual_e5_small | dense | place_story | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.438900 | 18.214700 | 0 |
| dense_multilingual_e5_small | dense | relationship | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.652090 | 17.581600 | 0 |
| dense_multilingual_e5_small | dense | route_context | 10 | 0.700000 | 0.800000 | 0.900000 | 0.753333 | 0.533275 | 16.476700 | 0 |
| dense_multilingual_e5_small | dense | voice_followup | 10 | 0.300000 | 0.300000 | 0.300000 | 0.300000 | 0.184779 | 15.863300 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 24.868600 | 10 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | overview | 10 | 0.700000 | 0.700000 | 0.900000 | 0.745000 | 0.524598 | 32.248100 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | place_fact | 10 | 0.800000 | 0.900000 | 1.000000 | 0.870000 | 0.700028 | 30.300800 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.406144 | 26.361900 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | relationship | 10 | 0.700000 | 1.000000 | 1.000000 | 0.833333 | 0.709355 | 27.982600 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | route_context | 10 | 0.600000 | 0.800000 | 0.800000 | 0.700000 | 0.551700 | 31.774900 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | voice_followup | 10 | 0.100000 | 0.400000 | 0.400000 | 0.233333 | 0.164033 | 35.404500 | 0 |
| dense_multilingual_e5_small_rerank_bge_m3_top20 | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 13626.863900 | 10 |
| dense_multilingual_e5_small_rerank_bge_m3_top20 | dense | overview | 10 | 0.800000 | 1.000000 | 1.000000 | 0.883333 | 0.678187 | 10639.979500 | 0 |
| dense_multilingual_e5_small_rerank_bge_m3_top20 | dense | place_fact | 10 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.896099 | 11369.000600 | 0 |
| dense_multilingual_e5_small_rerank_bge_m3_top20 | dense | place_story | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.617320 | 10820.995600 | 0 |
| dense_multilingual_e5_small_rerank_bge_m3_top20 | dense | relationship | 10 | 0.800000 | 0.900000 | 0.900000 | 0.833333 | 0.687433 | 10989.726100 | 0 |
| dense_multilingual_e5_small_rerank_bge_m3_top20 | dense | route_context | 10 | 0.600000 | 0.800000 | 0.900000 | 0.703333 | 0.627443 | 13514.306600 | 0 |
| dense_multilingual_e5_small_rerank_bge_m3_top20 | dense | voice_followup | 10 | 0.400000 | 0.400000 | 0.400000 | 0.400000 | 0.308243 | 11302.415000 | 0 |

## Baseline Delta

| baseline_run_label | baseline_method | compared_run_label | compared_method | Recall@1 delta | Recall@3 delta | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | bm25 | bm25 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| bm25 | bm25 | dense_multilingual_e5_small | dense | 0.233333 | 0.183334 | 0.166666 | 0.204167 | 0.189594 | 9.938500 |
| bm25 | bm25 | hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | 0.166667 | 0.200000 | 0.216666 | 0.183889 | 0.165107 | 22.754200 |
| bm25 | bm25 | dense_multilingual_e5_small_rerank_bge_m3_top20 | dense | 0.316667 | 0.283334 | 0.266666 | 0.290278 | 0.291584 | 13132.706900 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 1400 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `harness_scope`: 공통 schema로 평가한 method는 bm25, dense_multilingual_e5_small, hybrid_weighted_e5_small_alpha_0_5, dense_multilingual_e5_small_rerank_bge_m3_top20다.
- `dense_encoder_boundary`: Dense neural encoder는 multilingual-e5-small다. sentence-transformers backend로 실행했고, embedding vector/cache는 private artifact로만 저장한다.
- `reranker_boundary`: Reranker 최고 후보는 dense_multilingual_e5_small_rerank_bge_m3_top20: Recall@5=0.833333, MRR=0.761667, nDCG@5=0.635787, latency_p95_ms=13140.690300. CPU latency가 커서 실서비스 기본 후보로 바로 채택하지 않는다.
- `baseline_reproduction`: bm25: Recall@5=0.566667, MRR=0.471389, nDCG@5=0.344203.
- `comparison_status`: 현재 delta는 dev 기준 비교 결과다. 성능 개선 주장이 아니라 비교 형식과 후보 성능 기록이다.
- `public_policy`: public result와 report에는 rank, id, score, metric만 저장하고 검색 본문은 저장하지 않는다.
- `next_step`: Reranker 최고 top-rank 후보는 `dense_multilingual_e5_small_rerank_bge_m3_top20`다. Dense/Hybrid 원본과 latency trade-off를 비교한 뒤 locked test와 generation 평가 전까지 최종 개선 주장은 보류한다.
- `delta_row_count`: 4개 method delta row를 생성했다.

## 해석

현재 harness는 선택한 retrieval method를 공통 실험 형식으로 평가했다.

후속 method를 추가할 때는 dataset, corpus, metric, output gate를 바꾸지 않고 `method` 실행기만 추가한다. 개선 주장은 paired comparison과 bootstrap confidence interval을 붙인 뒤에만 가능하다.
