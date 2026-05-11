# Retrieval Harness Report

## 목적

BM25, Dense, Hybrid retrieval을 같은 평가셋과 같은 metric으로 비교한다.

이 문서는 성능 개선 주장이 아니다. method별 기준선과 delta를 기록하고, locked test와 generation 평가 전까지는 개선 표현을 사용하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-experiment-report/v1` |
| comparison_id | `retrieval-harness-bm25-dense-dense_bge_m3-dense_multilingual_e5_small-dense_paraphrase_multilingual_minilm-q70-469d6028` |
| generated_at_utc | `2026-05-11T12:08:22+00:00` |
| baseline_method | `bm25` |
| methods | `bm25, dense, dense_bge_m3, dense_multilingual_e5_small, dense_paraphrase_multilingual_minilm` |
| top_k | 5 |
| dataset_fingerprint | `224e3cad1c078eeb` |
| corpus_fingerprint | `e23457a7ad59042f` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| result_paths | `<private artifact: retrieval_experiment_bm25_results.jsonl>, <private artifact: retrieval_experiment_dense_results.jsonl>, <private artifact: retrieval_experiment_dense_bge_m3_results.jsonl>, <private artifact: retrieval_experiment_dense_multilingual_e5_small_results.jsonl>, <private artifact: retrieval_experiment_dense_paraphrase_multilingual_minilm_results.jsonl>` |

## Method Config

| run_label | method | config |
| --- | --- | --- |
| bm25 | bm25 | `method=bm25, query_rewrite=False, reranking=False, tokenizer=regex-ko-en-num/v1, top_k=5` |
| dense | dense | `embedding_dim=128, encoder_backend=sklearn_tfidf_svd, encoder_id=sklearn-tfidf-svd-v1, include_doc_title=True, max_features=50000, method=dense, n_components=128, ngram_range=1-2, normalize_embeddings=True, query_rewrite=False, random_state=42, reranking=False, top_k=5` |
| dense_bge_m3 | dense | `batch_size=16, device=cpu, document_prefix_enabled=False, embedding_dim=1024, encoder_backend=sentence_transformers, encoder_id=bge-m3, include_doc_title=True, method=dense, model_name=BAAI/bge-m3, normalize_embeddings=True, query_prefix_enabled=False, query_rewrite=False, reranking=False, top_k=5` |
| dense_multilingual_e5_small | dense | `batch_size=16, device=cpu, document_prefix_enabled=True, embedding_dim=384, encoder_backend=sentence_transformers, encoder_id=multilingual-e5-small, include_doc_title=True, method=dense, model_name=intfloat/multilingual-e5-small, normalize_embeddings=True, query_prefix_enabled=True, query_rewrite=False, reranking=False, top_k=5` |
| dense_paraphrase_multilingual_minilm | dense | `batch_size=16, device=cpu, document_prefix_enabled=False, embedding_dim=384, encoder_backend=sentence_transformers, encoder_id=paraphrase-multilingual-minilm-l12-v2, include_doc_title=True, method=dense, model_name=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, normalize_embeddings=True, query_prefix_enabled=False, query_rewrite=False, reranking=False, top_k=5` |

## 정량 리포트

| run_label | method | query_count | retrieve_query_count | abstain_query_count | result_count | missing_result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p50_ms | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | 70 | 60 | 10 | 70 | 0 | 0.400000 | 0.533333 | 0.566667 | 0.471389 | 0.344203 | 4.751500 | 6.323600 | 10 |
| dense | dense | 70 | 60 | 10 | 70 | 0 | 0.200000 | 0.316667 | 0.350000 | 0.261111 | 0.220955 | 14.207900 | 18.228000 | 10 |
| dense_bge_m3 | dense | 70 | 60 | 10 | 70 | 0 | 0.566667 | 0.733333 | 0.800000 | 0.658611 | 0.567476 | 48.589900 | 57.088400 | 10 |
| dense_multilingual_e5_small | dense | 70 | 60 | 10 | 70 | 0 | 0.633333 | 0.716667 | 0.733333 | 0.675556 | 0.533797 | 14.070600 | 15.717100 | 10 |
| dense_paraphrase_multilingual_minilm | dense | 70 | 60 | 10 | 70 | 0 | 0.050000 | 0.066667 | 0.100000 | 0.065000 | 0.039444 | 13.686100 | 15.559500 | 10 |

## Query Type Breakdown

| run_label | method | query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 6.161100 | 10 |
| bm25 | bm25 | overview | 10 | 0.500000 | 0.500000 | 0.600000 | 0.525000 | 0.357596 | 6.323600 | 0 |
| bm25 | bm25 | place_fact | 10 | 0.400000 | 0.700000 | 0.700000 | 0.533333 | 0.426514 | 6.596900 | 0 |
| bm25 | bm25 | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.424299 | 5.902600 | 0 |
| bm25 | bm25 | relationship | 10 | 0.400000 | 0.700000 | 0.800000 | 0.570000 | 0.434678 | 6.030800 | 0 |
| bm25 | bm25 | route_context | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.383448 | 6.794100 | 0 |
| bm25 | bm25 | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 4.751500 | 0 |
| dense | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 26.266200 | 10 |
| dense | dense | overview | 10 | 0.200000 | 0.500000 | 0.500000 | 0.333333 | 0.285759 | 20.178200 | 0 |
| dense | dense | place_fact | 10 | 0.300000 | 0.500000 | 0.500000 | 0.383333 | 0.351563 | 19.359000 | 0 |
| dense | dense | place_story | 10 | 0.300000 | 0.400000 | 0.400000 | 0.350000 | 0.267139 | 16.508900 | 0 |
| dense | dense | relationship | 10 | 0.100000 | 0.200000 | 0.400000 | 0.200000 | 0.176226 | 15.171800 | 0 |
| dense | dense | route_context | 10 | 0.300000 | 0.300000 | 0.300000 | 0.300000 | 0.245044 | 14.409300 | 0 |
| dense | dense | voice_followup | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 16.005300 | 0 |
| dense_bge_m3 | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 48.589900 | 10 |
| dense_bge_m3 | dense | overview | 10 | 0.400000 | 0.800000 | 0.900000 | 0.603333 | 0.493230 | 52.383200 | 0 |
| dense_bge_m3 | dense | place_fact | 10 | 0.800000 | 0.900000 | 0.900000 | 0.850000 | 0.810108 | 72.256600 | 0 |
| dense_bge_m3 | dense | place_story | 10 | 0.600000 | 0.700000 | 0.700000 | 0.650000 | 0.551555 | 52.082900 | 0 |
| dense_bge_m3 | dense | relationship | 10 | 0.600000 | 0.900000 | 1.000000 | 0.758333 | 0.679525 | 55.853300 | 0 |
| dense_bge_m3 | dense | route_context | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.600109 | 57.917300 | 0 |
| dense_bge_m3 | dense | voice_followup | 10 | 0.300000 | 0.300000 | 0.500000 | 0.340000 | 0.270327 | 45.246800 | 0 |
| dense_multilingual_e5_small | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 15.103700 | 10 |
| dense_multilingual_e5_small | dense | overview | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.610343 | 14.619100 | 0 |
| dense_multilingual_e5_small | dense | place_fact | 10 | 0.800000 | 1.000000 | 1.000000 | 0.900000 | 0.783397 | 16.061300 | 0 |
| dense_multilingual_e5_small | dense | place_story | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.438900 | 15.525700 | 0 |
| dense_multilingual_e5_small | dense | relationship | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.652090 | 17.228800 | 0 |
| dense_multilingual_e5_small | dense | route_context | 10 | 0.700000 | 0.800000 | 0.900000 | 0.753333 | 0.533275 | 15.717100 | 0 |
| dense_multilingual_e5_small | dense | voice_followup | 10 | 0.300000 | 0.300000 | 0.300000 | 0.300000 | 0.184779 | 14.911700 | 0 |
| dense_paraphrase_multilingual_minilm | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 14.474900 | 10 |
| dense_paraphrase_multilingual_minilm | dense | overview | 10 | 0.100000 | 0.100000 | 0.200000 | 0.120000 | 0.079469 | 14.761200 | 0 |
| dense_paraphrase_multilingual_minilm | dense | place_fact | 10 | 0.100000 | 0.100000 | 0.100000 | 0.100000 | 0.039038 | 15.605700 | 0 |
| dense_paraphrase_multilingual_minilm | dense | place_story | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 15.536800 | 0 |
| dense_paraphrase_multilingual_minilm | dense | relationship | 10 | 0.100000 | 0.100000 | 0.200000 | 0.120000 | 0.079469 | 15.465100 | 0 |
| dense_paraphrase_multilingual_minilm | dense | route_context | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 15.621800 | 0 |
| dense_paraphrase_multilingual_minilm | dense | voice_followup | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 14.210700 | 0 |

## Baseline Delta

| baseline_run_label | baseline_method | compared_run_label | compared_method | Recall@1 delta | Recall@3 delta | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | bm25 | bm25 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| bm25 | bm25 | dense | dense | -0.200000 | -0.216666 | -0.216667 | -0.210278 | -0.123248 | 11.904400 |
| bm25 | bm25 | dense_bge_m3 | dense | 0.166667 | 0.200000 | 0.233333 | 0.187222 | 0.223273 | 50.764800 |
| bm25 | bm25 | dense_multilingual_e5_small | dense | 0.233333 | 0.183334 | 0.166666 | 0.204167 | 0.189594 | 9.393500 |
| bm25 | bm25 | dense_paraphrase_multilingual_minilm | dense | -0.350000 | -0.466666 | -0.466667 | -0.406389 | -0.304759 | 9.235900 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 1750 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `harness_scope`: 공통 schema로 평가한 method는 bm25, dense, dense_bge_m3, dense_multilingual_e5_small, dense_paraphrase_multilingual_minilm다.
- `dense_encoder_boundary`: Dense neural encoder는 bge-m3, multilingual-e5-small, paraphrase-multilingual-minilm-l12-v2다. sentence-transformers backend로 실행했고, embedding vector/cache는 private artifact로만 저장한다.
- `baseline_reproduction`: bm25: Recall@5=0.566667, MRR=0.471389, nDCG@5=0.344203.
- `comparison_status`: 현재 delta는 dev 기준 비교 결과다. 성능 개선 주장이 아니라 비교 형식과 후보 성능 기록이다.
- `public_policy`: public result와 report에는 rank, id, score, metric만 저장하고 검색 본문은 저장하지 않는다.
- `next_step`: Neural dense 후보 중 BM25보다 Recall@5 또는 MRR이 높은 모델을 Hybrid/Reranker 비교에 투입하고, latency/cost trade-off를 별도로 기록한다.
- `delta_row_count`: 5개 method delta row를 생성했다.

## 해석

현재 harness는 선택한 retrieval method를 공통 실험 형식으로 평가했다.

후속 method를 추가할 때는 dataset, corpus, metric, output gate를 바꾸지 않고 `method` 실행기만 추가한다. 개선 주장은 paired comparison과 bootstrap confidence interval을 붙인 뒤에만 가능하다.
