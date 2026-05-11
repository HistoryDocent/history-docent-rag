# Retrieval Harness Report

## 목적

BM25, Dense, Hybrid, Query Rewrite retrieval을 같은 평가셋과 같은 metric으로 비교한다.

이 문서는 성능 개선 주장이 아니다. method별 기준선과 delta를 기록하고, locked test와 generation 평가 전까지는 개선 표현을 사용하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-experiment-report/v1` |
| comparison_id | `retrieval-harness-bm25-dense_multilingual_e5_small-dense_multilingual_e5_small_place_rewrite-dense_multilingual_e5_small_voice_rewrite-q70-6d6d2957` |
| generated_at_utc | `2026-05-11T15:43:53+00:00` |
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
| dense_multilingual_e5_small_place_rewrite | `<private artifact: retrieval_experiment_dense_multilingual_e5_small_place_rewrite_results.jsonl>` |
| dense_multilingual_e5_small_voice_rewrite | `<private artifact: retrieval_experiment_dense_multilingual_e5_small_voice_rewrite_results.jsonl>` |

## Method Config

| run_label | method | config |
| --- | --- | --- |
| bm25 | bm25 | `method=bm25, top_k=5, query_rewrite=False, reranking=False` |
| dense_multilingual_e5_small | dense | `method=dense, top_k=5, encoder_id=multilingual-e5-small, encoder_backend=sentence_transformers, model_name=intfloat/multilingual-e5-small, query_rewrite=False, reranking=False` |
| dense_multilingual_e5_small_place_rewrite | dense | `method=dense, top_k=5, encoder_id=multilingual-e5-small, encoder_backend=sentence_transformers, model_name=intfloat/multilingual-e5-small, query_rewrite=True, query_rewrite_strategy=place-aware-deterministic-v1, query_rewrite_target_types=place_fact,place_story,route_context,voice_followup, query_rewrite_changed_count=40, query_rewrite_invalid_json_count=0, query_rewrite_invalid_json_rate=0.0, query_rewrite_no_answer_guard_count=10, query_rewrite_latency_p95_ms=0.0779, query_rewrite_solar_call_count=0, reranking=False` |
| dense_multilingual_e5_small_voice_rewrite | dense | `method=dense, top_k=5, encoder_id=multilingual-e5-small, encoder_backend=sentence_transformers, model_name=intfloat/multilingual-e5-small, query_rewrite=True, query_rewrite_strategy=voice-followup-deterministic-v1, query_rewrite_target_types=voice_followup, query_rewrite_changed_count=10, query_rewrite_invalid_json_count=0, query_rewrite_invalid_json_rate=0.0, query_rewrite_no_answer_guard_count=10, query_rewrite_latency_p95_ms=0.0999, query_rewrite_solar_call_count=0, reranking=False` |

## 정량 리포트

| run_label | method | query_count | retrieve_query_count | abstain_query_count | result_count | missing_result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p50_ms | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | 70 | 60 | 10 | 70 | 0 | 0.400000 | 0.533333 | 0.566667 | 0.471389 | 0.344203 | 4.920500 | 6.361000 | 10 |
| dense_multilingual_e5_small | dense | 70 | 60 | 10 | 70 | 0 | 0.633333 | 0.716667 | 0.733333 | 0.675556 | 0.533797 | 13.451400 | 15.638500 | 10 |
| dense_multilingual_e5_small_place_rewrite | dense | 70 | 60 | 10 | 70 | 0 | 0.633333 | 0.766667 | 0.833333 | 0.709444 | 0.583976 | 15.874200 | 21.273600 | 10 |
| dense_multilingual_e5_small_voice_rewrite | dense | 70 | 60 | 10 | 70 | 0 | 0.700000 | 0.800000 | 0.850000 | 0.758056 | 0.615293 | 14.485000 | 19.560200 | 10 |

## Query Type Breakdown

| run_label | method | query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 5.201800 | 10 |
| bm25 | bm25 | overview | 10 | 0.500000 | 0.500000 | 0.600000 | 0.525000 | 0.357596 | 6.361000 | 0 |
| bm25 | bm25 | place_fact | 10 | 0.400000 | 0.700000 | 0.700000 | 0.533333 | 0.426514 | 7.443500 | 0 |
| bm25 | bm25 | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.424299 | 5.869600 | 0 |
| bm25 | bm25 | relationship | 10 | 0.400000 | 0.700000 | 0.800000 | 0.570000 | 0.434678 | 5.507100 | 0 |
| bm25 | bm25 | route_context | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.383448 | 6.490700 | 0 |
| bm25 | bm25 | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 4.850000 | 0 |
| dense_multilingual_e5_small | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 14.004100 | 10 |
| dense_multilingual_e5_small | dense | overview | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.610343 | 15.498300 | 0 |
| dense_multilingual_e5_small | dense | place_fact | 10 | 0.800000 | 1.000000 | 1.000000 | 0.900000 | 0.783397 | 14.784200 | 0 |
| dense_multilingual_e5_small | dense | place_story | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.438900 | 15.537600 | 0 |
| dense_multilingual_e5_small | dense | relationship | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.652090 | 15.706900 | 0 |
| dense_multilingual_e5_small | dense | route_context | 10 | 0.700000 | 0.800000 | 0.900000 | 0.753333 | 0.533275 | 16.543700 | 0 |
| dense_multilingual_e5_small | dense | voice_followup | 10 | 0.300000 | 0.300000 | 0.300000 | 0.300000 | 0.184779 | 15.187400 | 0 |
| dense_multilingual_e5_small_place_rewrite | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 15.219000 | 10 |
| dense_multilingual_e5_small_place_rewrite | dense | overview | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.610343 | 15.484200 | 0 |
| dense_multilingual_e5_small_place_rewrite | dense | place_fact | 10 | 0.600000 | 0.800000 | 0.900000 | 0.703333 | 0.654528 | 20.620500 | 0 |
| dense_multilingual_e5_small_place_rewrite | dense | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.406144 | 32.128000 | 0 |
| dense_multilingual_e5_small_place_rewrite | dense | relationship | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.652090 | 20.697600 | 0 |
| dense_multilingual_e5_small_place_rewrite | dense | route_context | 10 | 0.600000 | 0.800000 | 0.900000 | 0.708333 | 0.506997 | 21.179500 | 0 |
| dense_multilingual_e5_small_place_rewrite | dense | voice_followup | 10 | 0.700000 | 0.800000 | 1.000000 | 0.795000 | 0.673753 | 19.582000 | 0 |
| dense_multilingual_e5_small_voice_rewrite | dense | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 15.591100 | 10 |
| dense_multilingual_e5_small_voice_rewrite | dense | overview | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.610343 | 16.004600 | 0 |
| dense_multilingual_e5_small_voice_rewrite | dense | place_fact | 10 | 0.800000 | 1.000000 | 1.000000 | 0.900000 | 0.783397 | 15.779200 | 0 |
| dense_multilingual_e5_small_voice_rewrite | dense | place_story | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.438900 | 15.156600 | 0 |
| dense_multilingual_e5_small_voice_rewrite | dense | relationship | 10 | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.652090 | 15.566600 | 0 |
| dense_multilingual_e5_small_voice_rewrite | dense | route_context | 10 | 0.700000 | 0.800000 | 0.900000 | 0.753333 | 0.533275 | 15.828100 | 0 |
| dense_multilingual_e5_small_voice_rewrite | dense | voice_followup | 10 | 0.700000 | 0.800000 | 1.000000 | 0.795000 | 0.673753 | 20.991400 | 0 |

## Baseline Delta

| baseline_run_label | baseline_method | compared_run_label | compared_method | Recall@1 delta | Recall@3 delta | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | bm25 | bm25 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| bm25 | bm25 | dense_multilingual_e5_small | dense | 0.233333 | 0.183334 | 0.166666 | 0.204167 | 0.189594 | 9.277500 |
| bm25 | bm25 | dense_multilingual_e5_small_place_rewrite | dense | 0.233333 | 0.233334 | 0.266666 | 0.238055 | 0.239773 | 14.912600 |
| bm25 | bm25 | dense_multilingual_e5_small_voice_rewrite | dense | 0.300000 | 0.266667 | 0.283333 | 0.286667 | 0.271090 | 13.199200 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 1400 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `harness_scope`: 공통 schema로 평가한 method는 bm25, dense_multilingual_e5_small, dense_multilingual_e5_small_place_rewrite, dense_multilingual_e5_small_voice_rewrite다.
- `dense_encoder_boundary`: Dense neural encoder는 multilingual-e5-small다. sentence-transformers backend로 실행했고, embedding vector/cache는 private artifact로만 저장한다.
- `query_rewrite_boundary`: Query rewrite 최고 후보는 dense_multilingual_e5_small_voice_rewrite: Recall@5=0.850000, MRR=0.758056, nDCG@5=0.615293, changed_count=10, invalid_json_count=0. Solar Pro 3 호출 없이 deterministic place/context expansion만 사용했다.
- `reranker_boundary`: Reranker는 아직 실행하지 않았다.
- `baseline_reproduction`: bm25: Recall@5=0.566667, MRR=0.471389, nDCG@5=0.344203.
- `comparison_status`: 현재 delta는 dev 기준 비교 결과다. 성능 개선 주장이 아니라 비교 형식과 후보 성능 기록이다.
- `public_policy`: public result와 report에는 rank, id, score, metric만 저장하고 검색 본문은 저장하지 않는다.
- `next_step`: Query rewrite 후보 `dense_multilingual_e5_small_voice_rewrite`를 Dense 기본 후보와 비교했다. 다음 판단은 evidence packing과 generation eval에서 citation 품질까지 확인한 뒤 한다.
- `delta_row_count`: 4개 method delta row를 생성했다.

## 해석

현재 harness는 선택한 retrieval method를 공통 실험 형식으로 평가했다.

후속 method를 추가할 때는 dataset, corpus, metric, output gate를 바꾸지 않고 `method` 실행기만 추가한다. 개선 주장은 paired comparison과 bootstrap confidence interval을 붙인 뒤에만 가능하다.
