# Retrieval Harness Report

## 목적

BM25, Dense, Hybrid retrieval을 같은 평가셋과 같은 metric으로 비교하기 위한 공통 evaluation harness를 검증한다.

이 문서는 성능 개선 주장이 아니다. 현재는 BM25 baseline을 새 harness에서 재현해 이후 Dense/Hybrid 비교의 실험대를 고정한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-experiment-report/v1` |
| comparison_id | `retrieval-harness-bm25-q14-894ab98f` |
| generated_at_utc | `2026-05-10T03:08:42+00:00` |
| baseline_method | `bm25` |
| methods | `bm25` |
| top_k | 5 |
| dataset_fingerprint | `0ce1a719712c2b9f` |
| corpus_fingerprint | `e23457a7ad59042f` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_path | `evals/datasets/retrieval_eval_seed.jsonl` |
| result_paths | `evals/results/retrieval_experiment_bm25_results.jsonl` |

## 정량 리포트

| method | query_count | retrieve_query_count | abstain_query_count | result_count | missing_result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p50_ms | latency_p95_ms | abstain_with_candidate_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | 14 | 12 | 2 | 14 | 0 | 0.083333 | 0.250000 | 0.250000 | 0.152778 | 0.120124 | 5.075500 | 6.171700 | 2 |

## Query Type Breakdown

| method | query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | no_answer | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 5.075500 | 2 |
| bm25 | overview | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 6.592400 | 0 |
| bm25 | place_fact | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 5.733100 | 0 |
| bm25 | place_story | 2 | 0.500000 | 0.500000 | 0.500000 | 0.500000 | 0.382680 | 5.924100 | 0 |
| bm25 | relationship | 2 | 0.000000 | 0.500000 | 0.500000 | 0.250000 | 0.220746 | 5.274900 | 0 |
| bm25 | route_context | 2 | 0.000000 | 0.500000 | 0.500000 | 0.166666 | 0.117319 | 6.098400 | 0 |
| bm25 | voice_followup | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 3.341200 | 0 |

## Baseline Delta

| baseline_method | compared_method | Recall@1 delta | Recall@3 delta | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | bm25 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 70 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `harness_scope`: 공통 schema로 평가한 method는 bm25다. Dense/Hybrid 구현은 아직 포함하지 않았다.
- `baseline_reproduction`: bm25: Recall@5=0.250000, MRR=0.152778, nDCG@5=0.120124.
- `comparison_status`: 현재 delta는 harness 검증용이다. 성능 개선 주장이 아니라 비교 형식 고정이다.
- `public_policy`: public result와 report에는 rank, id, score, metric만 저장하고 검색 본문은 저장하지 않는다.
- `next_step`: Dense retriever와 Hybrid retriever를 같은 report에 추가한 뒤 query type별 delta를 비교한다.
- `delta_row_count`: 1개 method delta row를 생성했다.

## 해석

현재 harness는 BM25 baseline을 공통 실험 형식으로 재현했다.

Dense/Hybrid를 추가할 때는 dataset, metric, output gate를 바꾸지 않고 `method` 실행기만 추가한다. 개선 주장은 paired comparison과 bootstrap confidence interval을 붙인 뒤에만 가능하다.
