# Retrieval Harness Report

## 목적

BM25, Dense, Hybrid retrieval을 같은 평가셋과 같은 metric으로 비교한다.

이 문서는 성능 개선 주장이 아니다. method별 기준선과 delta를 기록하고, locked test와 generation 평가 전까지는 개선 표현을 사용하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-experiment-report/v1` |
| comparison_id | `retrieval-harness-bm25-dense-hybrid_rrf-hybrid_weighted_alpha_0_3-hybrid_weighted_alpha_0_5-hybrid_weighted_alpha_0_7-q70-c9a613c4` |
| generated_at_utc | `2026-05-11T09:54:40+00:00` |
| baseline_method | `bm25` |
| methods | `bm25, dense, hybrid_rrf, hybrid_weighted_alpha_0_3, hybrid_weighted_alpha_0_5, hybrid_weighted_alpha_0_7` |
| top_k | 5 |
| dataset_fingerprint | `224e3cad1c078eeb` |
| corpus_fingerprint | `e23457a7ad59042f` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| result_paths | `<private artifact: retrieval_experiment_bm25_results.jsonl>, <private artifact: retrieval_experiment_dense_results.jsonl>, <private artifact: retrieval_experiment_hybrid_rrf_results.jsonl>, <private artifact: retrieval_experiment_hybrid_weighted_alpha_0_3_results.jsonl>, <private artifact: retrieval_experiment_hybrid_weighted_alpha_0_5_results.jsonl>, <private artifact: retrieval_experiment_hybrid_weighted_alpha_0_7_results.jsonl>` |

## Method Config

| run_label | method | config |
| --- | --- | --- |
| bm25 | bm25 | `method=bm25, query_rewrite=False, reranking=False, tokenizer=regex-ko-en-num/v1, top_k=5` |
| dense | dense | `embedding_dim=128, encoder_id=sklearn-tfidf-svd-v1, include_doc_title=True, max_features=50000, method=dense, n_components=128, ngram_range=1-2, normalize_embeddings=True, query_rewrite=False, random_state=42, reranking=False, top_k=5` |
| hybrid_rrf | hybrid_rrf | `candidate_k=50, dense_embedding_dim=128, dense_encoder_id=sklearn-tfidf-svd-v1, fusion=reciprocal_rank_fusion, method=hybrid_rrf, query_rewrite=False, reranking=False, rrf_k=60, top_k=5` |
| hybrid_weighted_alpha_0_3 | hybrid_weighted | `candidate_k=50, dense_embedding_dim=128, dense_encoder_id=sklearn-tfidf-svd-v1, dense_weight_alpha=0.3, fusion=minmax_weighted_sum, method=hybrid_weighted, query_rewrite=False, reranking=False, score_normalization=per-method-minmax, top_k=5` |
| hybrid_weighted_alpha_0_5 | hybrid_weighted | `candidate_k=50, dense_embedding_dim=128, dense_encoder_id=sklearn-tfidf-svd-v1, dense_weight_alpha=0.5, fusion=minmax_weighted_sum, method=hybrid_weighted, query_rewrite=False, reranking=False, score_normalization=per-method-minmax, top_k=5` |
| hybrid_weighted_alpha_0_7 | hybrid_weighted | `candidate_k=50, dense_embedding_dim=128, dense_encoder_id=sklearn-tfidf-svd-v1, dense_weight_alpha=0.7, fusion=minmax_weighted_sum, method=hybrid_weighted, query_rewrite=False, reranking=False, score_normalization=per-method-minmax, top_k=5` |

## 정량 리포트

| run_label | method | query_count | retrieve_query_count | abstain_query_count | result_count | missing_result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p50_ms | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | 70 | 60 | 10 | 70 | 0 | 0.400000 | 0.533333 | 0.566667 | 0.471389 | 0.344203 | 4.377400 | 5.697700 | 10 |
| dense | dense | 70 | 60 | 10 | 70 | 0 | 0.200000 | 0.316667 | 0.350000 | 0.261111 | 0.220955 | 14.571700 | 19.703900 | 10 |
| hybrid_rrf | hybrid_rrf | 70 | 60 | 10 | 70 | 0 | 0.266667 | 0.433333 | 0.516667 | 0.359722 | 0.282463 | 20.708600 | 22.643800 | 10 |
| hybrid_weighted_alpha_0_3 | hybrid_weighted | 70 | 60 | 10 | 70 | 0 | 0.416667 | 0.533333 | 0.566667 | 0.479722 | 0.347259 | 20.874200 | 23.038700 | 10 |
| hybrid_weighted_alpha_0_5 | hybrid_weighted | 70 | 60 | 10 | 70 | 0 | 0.350000 | 0.500000 | 0.533333 | 0.427778 | 0.323149 | 21.042600 | 25.907100 | 10 |
| hybrid_weighted_alpha_0_7 | hybrid_weighted | 70 | 60 | 10 | 70 | 0 | 0.300000 | 0.383333 | 0.450000 | 0.354722 | 0.285376 | 20.635400 | 22.609100 | 10 |

## Query Type Breakdown

| run_label | method | query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 4.898500 | 10 |
| bm25 | bm25 | overview | 10 | 0.500000 | 0.500000 | 0.600000 | 0.525000 | 0.357596 | 5.487700 | 0 |
| bm25 | bm25 | place_fact | 10 | 0.400000 | 0.700000 | 0.700000 | 0.533333 | 0.426514 | 6.292000 | 0 |
| bm25 | bm25 | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.424299 | 5.627500 | 0 |
| bm25 | bm25 | relationship | 10 | 0.400000 | 0.700000 | 0.800000 | 0.570000 | 0.434678 | 5.048200 | 0 |
| bm25 | bm25 | route_context | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.383448 | 5.890100 | 0 |
| bm25 | bm25 | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 3.843100 | 0 |
| dense | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 26.888200 | 10 |
| dense | dense | overview | 10 | 0.200000 | 0.500000 | 0.500000 | 0.333333 | 0.285759 | 19.432300 | 0 |
| dense | dense | place_fact | 10 | 0.300000 | 0.500000 | 0.500000 | 0.383333 | 0.351563 | 14.674800 | 0 |
| dense | dense | place_story | 10 | 0.300000 | 0.400000 | 0.400000 | 0.350000 | 0.267139 | 16.603100 | 0 |
| dense | dense | relationship | 10 | 0.100000 | 0.200000 | 0.400000 | 0.200000 | 0.176226 | 24.079700 | 0 |
| dense | dense | route_context | 10 | 0.300000 | 0.300000 | 0.300000 | 0.300000 | 0.245044 | 15.268000 | 0 |
| dense | dense | voice_followup | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 19.703900 | 0 |
| hybrid_rrf | hybrid_rrf | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 21.069500 | 10 |
| hybrid_rrf | hybrid_rrf | overview | 10 | 0.400000 | 0.600000 | 0.600000 | 0.466667 | 0.335093 | 22.643800 | 0 |
| hybrid_rrf | hybrid_rrf | place_fact | 10 | 0.400000 | 0.400000 | 0.600000 | 0.450000 | 0.390096 | 22.501200 | 0 |
| hybrid_rrf | hybrid_rrf | place_story | 10 | 0.300000 | 0.600000 | 0.700000 | 0.475000 | 0.361467 | 21.545000 | 0 |
| hybrid_rrf | hybrid_rrf | relationship | 10 | 0.200000 | 0.600000 | 0.800000 | 0.416667 | 0.333965 | 21.769000 | 0 |
| hybrid_rrf | hybrid_rrf | route_context | 10 | 0.300000 | 0.300000 | 0.300000 | 0.300000 | 0.235474 | 22.917000 | 0 |
| hybrid_rrf | hybrid_rrf | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 31.540800 | 0 |
| hybrid_weighted_alpha_0_3 | hybrid_weighted | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 21.834900 | 10 |
| hybrid_weighted_alpha_0_3 | hybrid_weighted | overview | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.385966 | 22.185200 | 0 |
| hybrid_weighted_alpha_0_3 | hybrid_weighted | place_fact | 10 | 0.400000 | 0.600000 | 0.600000 | 0.500000 | 0.401166 | 31.827000 | 0 |
| hybrid_weighted_alpha_0_3 | hybrid_weighted | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.426355 | 22.500800 | 0 |
| hybrid_weighted_alpha_0_3 | hybrid_weighted | relationship | 10 | 0.500000 | 0.700000 | 0.900000 | 0.628333 | 0.455125 | 24.501400 | 0 |
| hybrid_weighted_alpha_0_3 | hybrid_weighted | route_context | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.376255 | 23.038700 | 0 |
| hybrid_weighted_alpha_0_3 | hybrid_weighted | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 20.860300 | 0 |
| hybrid_weighted_alpha_0_5 | hybrid_weighted | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 21.008000 | 10 |
| hybrid_weighted_alpha_0_5 | hybrid_weighted | overview | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.368646 | 25.907100 | 0 |
| hybrid_weighted_alpha_0_5 | hybrid_weighted | place_fact | 10 | 0.400000 | 0.500000 | 0.600000 | 0.475000 | 0.437858 | 30.940600 | 0 |
| hybrid_weighted_alpha_0_5 | hybrid_weighted | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.420211 | 25.180400 | 0 |
| hybrid_weighted_alpha_0_5 | hybrid_weighted | relationship | 10 | 0.400000 | 0.700000 | 0.700000 | 0.533333 | 0.366442 | 30.910200 | 0 |
| hybrid_weighted_alpha_0_5 | hybrid_weighted | route_context | 10 | 0.300000 | 0.500000 | 0.600000 | 0.408333 | 0.307049 | 23.321300 | 0 |
| hybrid_weighted_alpha_0_5 | hybrid_weighted | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 22.957400 | 0 |
| hybrid_weighted_alpha_0_7 | hybrid_weighted | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 21.638400 | 10 |
| hybrid_weighted_alpha_0_7 | hybrid_weighted | overview | 10 | 0.300000 | 0.400000 | 0.500000 | 0.375000 | 0.316509 | 26.216900 | 0 |
| hybrid_weighted_alpha_0_7 | hybrid_weighted | place_fact | 10 | 0.500000 | 0.500000 | 0.600000 | 0.525000 | 0.460487 | 25.431200 | 0 |
| hybrid_weighted_alpha_0_7 | hybrid_weighted | place_story | 10 | 0.400000 | 0.600000 | 0.600000 | 0.500000 | 0.359772 | 22.609100 | 0 |
| hybrid_weighted_alpha_0_7 | hybrid_weighted | relationship | 10 | 0.300000 | 0.500000 | 0.600000 | 0.403333 | 0.304035 | 25.561300 | 0 |
| hybrid_weighted_alpha_0_7 | hybrid_weighted | route_context | 10 | 0.300000 | 0.300000 | 0.300000 | 0.300000 | 0.245044 | 22.471300 | 0 |
| hybrid_weighted_alpha_0_7 | hybrid_weighted | voice_followup | 10 | 0.000000 | 0.000000 | 0.100000 | 0.025000 | 0.026407 | 20.606400 | 0 |

## Baseline Delta

| baseline_run_label | baseline_method | compared_run_label | compared_method | Recall@1 delta | Recall@3 delta | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | bm25 | bm25 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| bm25 | bm25 | dense | dense | -0.200000 | -0.216666 | -0.216667 | -0.210278 | -0.123248 | 14.006200 |
| bm25 | bm25 | hybrid_rrf | hybrid_rrf | -0.133333 | -0.100000 | -0.050000 | -0.111667 | -0.061740 | 16.946100 |
| bm25 | bm25 | hybrid_weighted_alpha_0_3 | hybrid_weighted | 0.016667 | 0.000000 | 0.000000 | 0.008333 | 0.003056 | 17.341000 |
| bm25 | bm25 | hybrid_weighted_alpha_0_5 | hybrid_weighted | -0.050000 | -0.033333 | -0.033334 | -0.043611 | -0.021054 | 20.209400 |
| bm25 | bm25 | hybrid_weighted_alpha_0_7 | hybrid_weighted | -0.100000 | -0.150000 | -0.116667 | -0.116667 | -0.058827 | 16.911400 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 2100 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `harness_scope`: 공통 schema로 평가한 method는 bm25, dense, hybrid_rrf, hybrid_weighted_alpha_0_3, hybrid_weighted_alpha_0_5, hybrid_weighted_alpha_0_7다.
- `dense_encoder_boundary`: Dense v1 encoder는 sklearn-tfidf-svd-v1다. 이 결과는 neural embedding 모델인 BGE-M3 또는 multilingual-E5 결과가 아니다.
- `baseline_reproduction`: bm25: Recall@5=0.566667, MRR=0.471389, nDCG@5=0.344203.
- `comparison_status`: 현재 delta는 dev 기준 비교 결과다. 성능 개선 주장이 아니라 비교 형식과 후보 성능 기록이다.
- `public_policy`: public result와 report에는 rank, id, score, metric만 저장하고 검색 본문은 저장하지 않는다.
- `next_step`: 현재 Hybrid 후보는 선택 gate를 통과하지 못했다. BM25를 유지하고 neural embedding 또는 shared dense index 최적화 후 재실험한다.
- `delta_row_count`: 6개 method delta row를 생성했다.

## 해석

현재 harness는 선택한 retrieval method를 공통 실험 형식으로 평가했다.

후속 method를 추가할 때는 dataset, corpus, metric, output gate를 바꾸지 않고 `method` 실행기만 추가한다. 개선 주장은 paired comparison과 bootstrap confidence interval을 붙인 뒤에만 가능하다.
