# Retrieval Harness Report

## 목적

BM25, Dense, Hybrid retrieval을 같은 평가셋과 같은 metric으로 비교한다.

이 문서는 성능 개선 주장이 아니다. method별 기준선과 delta를 기록하고, locked test와 generation 평가 전까지는 개선 표현을 사용하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-experiment-report/v1` |
| comparison_id | `retrieval-harness-bm25-dense_multilingual_e5_small-dense_bge_m3-hybrid_rrf_e5_small-hybrid_weighted_e5_small_alpha_0_3-hybrid_weighted_e5_small_alpha_0_5-hybrid_rrf_bge_m3-hybrid_weighted_bge_m3_alpha_0_3-q70-e8987763` |
| generated_at_utc | `2026-05-11T13:04:04+00:00` |
| baseline_method | `bm25` |
| methods | `bm25, dense_multilingual_e5_small, dense_bge_m3, hybrid_rrf_e5_small, hybrid_weighted_e5_small_alpha_0_3, hybrid_weighted_e5_small_alpha_0_5, hybrid_rrf_bge_m3, hybrid_weighted_bge_m3_alpha_0_3` |
| top_k | 5 |
| dataset_fingerprint | `224e3cad1c078eeb` |
| corpus_fingerprint | `e23457a7ad59042f` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| result_artifact_count | 8 |

## Result Artifacts

| run_label | result_path |
| --- | --- |
| bm25 | `<private artifact: retrieval_experiment_bm25_results.jsonl>` |
| dense_multilingual_e5_small | `<private artifact: retrieval_experiment_dense_multilingual_e5_small_results.jsonl>` |
| dense_bge_m3 | `<private artifact: retrieval_experiment_dense_bge_m3_results.jsonl>` |
| hybrid_rrf_e5_small | `<private artifact: retrieval_experiment_hybrid_rrf_e5_small_results.jsonl>` |
| hybrid_weighted_e5_small_alpha_0_3 | `<private artifact: retrieval_experiment_hybrid_weighted_e5_small_alpha_0_3_results.jsonl>` |
| hybrid_weighted_e5_small_alpha_0_5 | `<private artifact: retrieval_experiment_hybrid_weighted_e5_small_alpha_0_5_results.jsonl>` |
| hybrid_rrf_bge_m3 | `<private artifact: retrieval_experiment_hybrid_rrf_bge_m3_results.jsonl>` |
| hybrid_weighted_bge_m3_alpha_0_3 | `<private artifact: retrieval_experiment_hybrid_weighted_bge_m3_alpha_0_3_results.jsonl>` |

## Method Config

| run_label | method | config |
| --- | --- | --- |
| bm25 | bm25 | `method=bm25, query_rewrite=False, reranking=False, tokenizer=regex-ko-en-num/v1, top_k=5` |
| dense_multilingual_e5_small | dense | `batch_size=16, device=cpu, document_prefix_enabled=True, embedding_dim=384, encoder_backend=sentence_transformers, encoder_id=multilingual-e5-small, include_doc_title=True, method=dense, model_name=intfloat/multilingual-e5-small, normalize_embeddings=True, query_prefix_enabled=True, query_rewrite=False, reranking=False, top_k=5` |
| dense_bge_m3 | dense | `batch_size=16, device=cpu, document_prefix_enabled=False, embedding_dim=1024, encoder_backend=sentence_transformers, encoder_id=bge-m3, include_doc_title=True, method=dense, model_name=BAAI/bge-m3, normalize_embeddings=True, query_prefix_enabled=False, query_rewrite=False, reranking=False, top_k=5` |
| hybrid_rrf_e5_small | hybrid_rrf | `candidate_k=50, dense_embedding_dim=384, dense_encoder_backend=sentence_transformers, dense_encoder_id=multilingual-e5-small, dense_model_name=intfloat/multilingual-e5-small, fusion=reciprocal_rank_fusion, method=hybrid_rrf, query_rewrite=False, reranking=False, rrf_k=60, top_k=5` |
| hybrid_weighted_e5_small_alpha_0_3 | hybrid_weighted | `candidate_k=50, dense_embedding_dim=384, dense_encoder_backend=sentence_transformers, dense_encoder_id=multilingual-e5-small, dense_model_name=intfloat/multilingual-e5-small, dense_weight_alpha=0.3, fusion=minmax_weighted_sum, method=hybrid_weighted, query_rewrite=False, reranking=False, score_normalization=per-method-minmax, top_k=5` |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | `candidate_k=50, dense_embedding_dim=384, dense_encoder_backend=sentence_transformers, dense_encoder_id=multilingual-e5-small, dense_model_name=intfloat/multilingual-e5-small, dense_weight_alpha=0.5, fusion=minmax_weighted_sum, method=hybrid_weighted, query_rewrite=False, reranking=False, score_normalization=per-method-minmax, top_k=5` |
| hybrid_rrf_bge_m3 | hybrid_rrf | `candidate_k=50, dense_embedding_dim=1024, dense_encoder_backend=sentence_transformers, dense_encoder_id=bge-m3, dense_model_name=BAAI/bge-m3, fusion=reciprocal_rank_fusion, method=hybrid_rrf, query_rewrite=False, reranking=False, rrf_k=60, top_k=5` |
| hybrid_weighted_bge_m3_alpha_0_3 | hybrid_weighted | `candidate_k=50, dense_embedding_dim=1024, dense_encoder_backend=sentence_transformers, dense_encoder_id=bge-m3, dense_model_name=BAAI/bge-m3, dense_weight_alpha=0.3, fusion=minmax_weighted_sum, method=hybrid_weighted, query_rewrite=False, reranking=False, score_normalization=per-method-minmax, top_k=5` |

## 정량 리포트

| run_label | method | query_count | retrieve_query_count | abstain_query_count | result_count | missing_result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p50_ms | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | 70 | 60 | 10 | 70 | 0 | 0.400000 | 0.533333 | 0.566667 | 0.471389 | 0.344203 | 5.004100 | 6.769400 | 10 |
| dense_multilingual_e5_small | dense | 70 | 60 | 10 | 70 | 0 | 0.633333 | 0.716667 | 0.733333 | 0.675556 | 0.533797 | 14.228500 | 16.606300 | 10 |
| dense_bge_m3 | dense | 70 | 60 | 10 | 70 | 0 | 0.566667 | 0.733333 | 0.800000 | 0.658611 | 0.567476 | 54.375200 | 61.248100 | 10 |
| hybrid_rrf_e5_small | hybrid_rrf | 70 | 60 | 10 | 70 | 0 | 0.583333 | 0.683333 | 0.700000 | 0.629167 | 0.475437 | 22.938700 | 29.268200 | 10 |
| hybrid_weighted_e5_small_alpha_0_3 | hybrid_weighted | 70 | 60 | 10 | 70 | 0 | 0.450000 | 0.616667 | 0.666667 | 0.538611 | 0.414977 | 24.318800 | 28.607700 | 10 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | 70 | 60 | 10 | 70 | 0 | 0.566667 | 0.733333 | 0.783333 | 0.655278 | 0.509310 | 23.049000 | 27.547000 | 10 |
| hybrid_rrf_bge_m3 | hybrid_rrf | 70 | 60 | 10 | 70 | 0 | 0.533333 | 0.700000 | 0.733333 | 0.613889 | 0.462699 | 62.322700 | 72.581100 | 10 |
| hybrid_weighted_bge_m3_alpha_0_3 | hybrid_weighted | 70 | 60 | 10 | 70 | 0 | 0.466667 | 0.616667 | 0.666667 | 0.545833 | 0.415055 | 63.084800 | 74.303700 | 10 |

## Query Type Breakdown

| run_label | method | query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 5.849900 | 10 |
| bm25 | bm25 | overview | 10 | 0.500000 | 0.500000 | 0.600000 | 0.525000 | 0.357596 | 6.733800 | 0 |
| bm25 | bm25 | place_fact | 10 | 0.400000 | 0.700000 | 0.700000 | 0.533333 | 0.426514 | 7.343600 | 0 |
| bm25 | bm25 | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.424299 | 6.174100 | 0 |
| bm25 | bm25 | relationship | 10 | 0.400000 | 0.700000 | 0.800000 | 0.570000 | 0.434678 | 6.376900 | 0 |
| bm25 | bm25 | route_context | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.383448 | 7.093900 | 0 |
| bm25 | bm25 | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 4.554800 | 0 |
| dense_multilingual_e5_small | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 15.765800 | 10 |
| dense_multilingual_e5_small | dense | overview | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.610343 | 16.286600 | 0 |
| dense_multilingual_e5_small | dense | place_fact | 10 | 0.800000 | 1.000000 | 1.000000 | 0.900000 | 0.783397 | 16.606300 | 0 |
| dense_multilingual_e5_small | dense | place_story | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.438900 | 16.401400 | 0 |
| dense_multilingual_e5_small | dense | relationship | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.652090 | 16.928600 | 0 |
| dense_multilingual_e5_small | dense | route_context | 10 | 0.700000 | 0.800000 | 0.900000 | 0.753333 | 0.533275 | 17.329000 | 0 |
| dense_multilingual_e5_small | dense | voice_followup | 10 | 0.300000 | 0.300000 | 0.300000 | 0.300000 | 0.184779 | 15.964700 | 0 |
| dense_bge_m3 | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 55.393300 | 10 |
| dense_bge_m3 | dense | overview | 10 | 0.400000 | 0.800000 | 0.900000 | 0.603333 | 0.493230 | 67.265200 | 0 |
| dense_bge_m3 | dense | place_fact | 10 | 0.800000 | 0.900000 | 0.900000 | 0.850000 | 0.810108 | 65.957700 | 0 |
| dense_bge_m3 | dense | place_story | 10 | 0.600000 | 0.700000 | 0.700000 | 0.650000 | 0.551555 | 60.847800 | 0 |
| dense_bge_m3 | dense | relationship | 10 | 0.600000 | 0.900000 | 1.000000 | 0.758333 | 0.679525 | 78.048800 | 0 |
| dense_bge_m3 | dense | route_context | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.600109 | 60.446600 | 0 |
| dense_bge_m3 | dense | voice_followup | 10 | 0.300000 | 0.300000 | 0.500000 | 0.340000 | 0.270327 | 56.573400 | 0 |
| hybrid_rrf_e5_small | hybrid_rrf | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 24.920300 | 10 |
| hybrid_rrf_e5_small | hybrid_rrf | overview | 10 | 0.600000 | 0.700000 | 0.800000 | 0.675000 | 0.488142 | 29.404900 | 0 |
| hybrid_rrf_e5_small | hybrid_rrf | place_fact | 10 | 0.800000 | 0.800000 | 0.800000 | 0.800000 | 0.612536 | 27.786400 | 0 |
| hybrid_rrf_e5_small | hybrid_rrf | place_story | 10 | 0.600000 | 0.700000 | 0.700000 | 0.633333 | 0.454122 | 26.092500 | 0 |
| hybrid_rrf_e5_small | hybrid_rrf | relationship | 10 | 0.700000 | 1.000000 | 1.000000 | 0.816667 | 0.671669 | 32.092900 | 0 |
| hybrid_rrf_e5_small | hybrid_rrf | route_context | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.473403 | 30.640300 | 0 |
| hybrid_rrf_e5_small | hybrid_rrf | voice_followup | 10 | 0.200000 | 0.300000 | 0.300000 | 0.250000 | 0.152752 | 24.613200 | 0 |
| hybrid_weighted_e5_small_alpha_0_3 | hybrid_weighted | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 23.805600 | 10 |
| hybrid_weighted_e5_small_alpha_0_3 | hybrid_weighted | overview | 10 | 0.600000 | 0.700000 | 0.700000 | 0.650000 | 0.451018 | 28.037500 | 0 |
| hybrid_weighted_e5_small_alpha_0_3 | hybrid_weighted | place_fact | 10 | 0.600000 | 0.700000 | 0.800000 | 0.675000 | 0.523649 | 28.607700 | 0 |
| hybrid_weighted_e5_small_alpha_0_3 | hybrid_weighted | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.406144 | 30.687200 | 0 |
| hybrid_weighted_e5_small_alpha_0_3 | hybrid_weighted | relationship | 10 | 0.400000 | 0.900000 | 1.000000 | 0.653333 | 0.553863 | 28.471100 | 0 |
| hybrid_weighted_e5_small_alpha_0_3 | hybrid_weighted | route_context | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.474885 | 29.422400 | 0 |
| hybrid_weighted_e5_small_alpha_0_3 | hybrid_weighted | voice_followup | 10 | 0.000000 | 0.200000 | 0.300000 | 0.103333 | 0.080303 | 22.818100 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 23.239100 | 10 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | overview | 10 | 0.700000 | 0.700000 | 0.900000 | 0.745000 | 0.524598 | 26.288400 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | place_fact | 10 | 0.800000 | 0.900000 | 1.000000 | 0.870000 | 0.700028 | 29.493100 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.406144 | 28.017200 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | relationship | 10 | 0.700000 | 1.000000 | 1.000000 | 0.833333 | 0.709355 | 26.850500 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | route_context | 10 | 0.600000 | 0.800000 | 0.800000 | 0.700000 | 0.551700 | 29.145000 | 0 |
| hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | voice_followup | 10 | 0.100000 | 0.400000 | 0.400000 | 0.233333 | 0.164033 | 23.229300 | 0 |
| hybrid_rrf_bge_m3 | hybrid_rrf | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 60.002300 | 10 |
| hybrid_rrf_bge_m3 | hybrid_rrf | overview | 10 | 0.500000 | 0.700000 | 0.800000 | 0.608333 | 0.432380 | 70.536800 | 0 |
| hybrid_rrf_bge_m3 | hybrid_rrf | place_fact | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.582969 | 70.601100 | 0 |
| hybrid_rrf_bge_m3 | hybrid_rrf | place_story | 10 | 0.500000 | 0.800000 | 0.800000 | 0.633333 | 0.491758 | 68.826200 | 0 |
| hybrid_rrf_bge_m3 | hybrid_rrf | relationship | 10 | 0.700000 | 1.000000 | 1.000000 | 0.833333 | 0.638882 | 70.469800 | 0 |
| hybrid_rrf_bge_m3 | hybrid_rrf | route_context | 10 | 0.600000 | 0.600000 | 0.700000 | 0.625000 | 0.487535 | 75.546300 | 0 |
| hybrid_rrf_bge_m3 | hybrid_rrf | voice_followup | 10 | 0.200000 | 0.300000 | 0.300000 | 0.233333 | 0.142667 | 73.542300 | 0 |
| hybrid_weighted_bge_m3_alpha_0_3 | hybrid_weighted | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 83.754500 | 10 |
| hybrid_weighted_bge_m3_alpha_0_3 | hybrid_weighted | overview | 10 | 0.600000 | 0.600000 | 0.700000 | 0.625000 | 0.441144 | 67.699700 | 0 |
| hybrid_weighted_bge_m3_alpha_0_3 | hybrid_weighted | place_fact | 10 | 0.600000 | 0.700000 | 0.800000 | 0.658333 | 0.531415 | 68.813700 | 0 |
| hybrid_weighted_bge_m3_alpha_0_3 | hybrid_weighted | place_story | 10 | 0.500000 | 0.700000 | 0.700000 | 0.583333 | 0.460266 | 71.406600 | 0 |
| hybrid_weighted_bge_m3_alpha_0_3 | hybrid_weighted | relationship | 10 | 0.500000 | 0.900000 | 0.900000 | 0.700000 | 0.526339 | 76.106400 | 0 |
| hybrid_weighted_bge_m3_alpha_0_3 | hybrid_weighted | route_context | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.448809 | 74.864200 | 0 |
| hybrid_weighted_bge_m3_alpha_0_3 | hybrid_weighted | voice_followup | 10 | 0.000000 | 0.200000 | 0.300000 | 0.108333 | 0.082360 | 59.864800 | 0 |

## Baseline Delta

| baseline_run_label | baseline_method | compared_run_label | compared_method | Recall@1 delta | Recall@3 delta | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | bm25 | bm25 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| bm25 | bm25 | dense_multilingual_e5_small | dense | 0.233333 | 0.183334 | 0.166666 | 0.204167 | 0.189594 | 9.836900 |
| bm25 | bm25 | dense_bge_m3 | dense | 0.166667 | 0.200000 | 0.233333 | 0.187222 | 0.223273 | 54.478700 |
| bm25 | bm25 | hybrid_rrf_e5_small | hybrid_rrf | 0.183333 | 0.150000 | 0.133333 | 0.157778 | 0.131234 | 22.498800 |
| bm25 | bm25 | hybrid_weighted_e5_small_alpha_0_3 | hybrid_weighted | 0.050000 | 0.083334 | 0.100000 | 0.067222 | 0.070774 | 21.838300 |
| bm25 | bm25 | hybrid_weighted_e5_small_alpha_0_5 | hybrid_weighted | 0.166667 | 0.200000 | 0.216666 | 0.183889 | 0.165107 | 20.777600 |
| bm25 | bm25 | hybrid_rrf_bge_m3 | hybrid_rrf | 0.133333 | 0.166667 | 0.166666 | 0.142500 | 0.118496 | 65.811700 |
| bm25 | bm25 | hybrid_weighted_bge_m3_alpha_0_3 | hybrid_weighted | 0.066667 | 0.083334 | 0.100000 | 0.074444 | 0.070852 | 67.534300 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 2800 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `harness_scope`: 공통 schema로 평가한 method는 bm25, dense_multilingual_e5_small, dense_bge_m3, hybrid_rrf_e5_small, hybrid_weighted_e5_small_alpha_0_3, hybrid_weighted_e5_small_alpha_0_5, hybrid_rrf_bge_m3, hybrid_weighted_bge_m3_alpha_0_3다.
- `dense_encoder_boundary`: Dense neural encoder는 bge-m3, multilingual-e5-small다. sentence-transformers backend로 실행했고, embedding vector/cache는 private artifact로만 저장한다.
- `baseline_reproduction`: bm25: Recall@5=0.566667, MRR=0.471389, nDCG@5=0.344203.
- `comparison_status`: 현재 delta는 dev 기준 비교 결과다. 성능 개선 주장이 아니라 비교 형식과 후보 성능 기록이다.
- `public_policy`: public result와 report에는 rank, id, score, metric만 저장하고 검색 본문은 저장하지 않는다.
- `next_step`: Neural dense Hybrid 최고 Recall@5 후보는 `hybrid_weighted_e5_small_alpha_0_5`다. Dense 단독 후보와 top-rank, latency trade-off를 비교한 뒤 상위 2개 method에만 reranker comparison을 적용한다.
- `delta_row_count`: 8개 method delta row를 생성했다.

## 해석

현재 harness는 선택한 retrieval method를 공통 실험 형식으로 평가했다.

후속 method를 추가할 때는 dataset, corpus, metric, output gate를 바꾸지 않고 `method` 실행기만 추가한다. 개선 주장은 paired comparison과 bootstrap confidence interval을 붙인 뒤에만 가능하다.
