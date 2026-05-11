# Retrieval Harness Report

## 목적

BM25, Dense, Hybrid retrieval을 같은 평가셋과 같은 metric으로 비교한다.

이 문서는 성능 개선 주장이 아니다. method별 기준선과 delta를 기록하고, locked test와 generation 평가 전까지는 개선 표현을 사용하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-experiment-report/v1` |
| comparison_id | `retrieval-harness-bm25-dense-q70-f215f2a0` |
| generated_at_utc | `2026-05-11T07:48:48+00:00` |
| baseline_method | `bm25` |
| methods | `bm25, dense` |
| top_k | 5 |
| dataset_fingerprint | `224e3cad1c078eeb` |
| corpus_fingerprint | `e23457a7ad59042f` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| result_paths | `<private artifact: retrieval_experiment_bm25_results.jsonl>, <private artifact: retrieval_experiment_dense_results.jsonl>` |

## Method Config

| method | config |
| --- | --- |
| bm25 | `method=bm25, query_rewrite=False, reranking=False, tokenizer=regex-ko-en-num/v1, top_k=5` |
| dense | `embedding_dim=128, encoder_id=sklearn-tfidf-svd-v1, include_doc_title=True, max_features=50000, method=dense, n_components=128, ngram_range=1-2, normalize_embeddings=True, query_rewrite=False, random_state=42, reranking=False, top_k=5` |

## 정량 리포트

| method | query_count | retrieve_query_count | abstain_query_count | result_count | missing_result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p50_ms | latency_p95_ms | abstain_with_candidate_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | 70 | 60 | 10 | 70 | 0 | 0.400000 | 0.533333 | 0.566667 | 0.471389 | 0.344203 | 3.971800 | 5.351400 | 10 |
| dense | 70 | 60 | 10 | 70 | 0 | 0.200000 | 0.316667 | 0.350000 | 0.261111 | 0.220955 | 15.462300 | 18.084200 | 10 |

## Query Type Breakdown

| method | query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 4.568900 | 10 |
| bm25 | overview | 10 | 0.500000 | 0.500000 | 0.600000 | 0.525000 | 0.357596 | 5.609400 | 0 |
| bm25 | place_fact | 10 | 0.400000 | 0.700000 | 0.700000 | 0.533333 | 0.426514 | 6.386100 | 0 |
| bm25 | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.424299 | 4.912500 | 0 |
| bm25 | relationship | 10 | 0.400000 | 0.700000 | 0.800000 | 0.570000 | 0.434678 | 5.551800 | 0 |
| bm25 | route_context | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.383448 | 5.351400 | 0 |
| bm25 | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 3.336000 | 0 |
| dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 16.263800 | 10 |
| dense | overview | 10 | 0.200000 | 0.500000 | 0.500000 | 0.333333 | 0.285759 | 18.084200 | 0 |
| dense | place_fact | 10 | 0.300000 | 0.500000 | 0.500000 | 0.383333 | 0.351563 | 17.164100 | 0 |
| dense | place_story | 10 | 0.300000 | 0.400000 | 0.400000 | 0.350000 | 0.267139 | 16.485700 | 0 |
| dense | relationship | 10 | 0.100000 | 0.200000 | 0.400000 | 0.200000 | 0.176226 | 16.425300 | 0 |
| dense | route_context | 10 | 0.300000 | 0.300000 | 0.300000 | 0.300000 | 0.245044 | 21.978000 | 0 |
| dense | voice_followup | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 15.865700 | 0 |

## Baseline Delta

| baseline_method | compared_method | Recall@1 delta | Recall@3 delta | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| bm25 | dense | -0.200000 | -0.216666 | -0.216667 | -0.210278 | -0.123248 | 12.732800 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 700 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `harness_scope`: 공통 schema로 평가한 method는 bm25, dense다.
- `dense_encoder_boundary`: Dense v1 encoder는 sklearn-tfidf-svd-v1다. 이 결과는 neural embedding 모델인 BGE-M3 또는 multilingual-E5 결과가 아니다.
- `baseline_reproduction`: bm25: Recall@5=0.566667, MRR=0.471389, nDCG@5=0.344203.
- `comparison_status`: 현재 delta는 dev 기준 비교 결과다. 성능 개선 주장이 아니라 비교 형식과 후보 성능 기록이다.
- `public_policy`: public result와 report에는 rank, id, score, metric만 저장하고 검색 본문은 저장하지 않는다.
- `next_step`: Dense baseline 결과를 기준으로 Hybrid RRF/Weighted retrieval을 같은 report에 추가한다.
- `delta_row_count`: 2개 method delta row를 생성했다.

## 해석

현재 harness는 선택한 retrieval method를 공통 실험 형식으로 평가했다.

후속 method를 추가할 때는 dataset, corpus, metric, output gate를 바꾸지 않고 `method` 실행기만 추가한다. 개선 주장은 paired comparison과 bootstrap confidence interval을 붙인 뒤에만 가능하다.
