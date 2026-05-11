# Chunking Ablation Report

## 목적

BM25 retriever를 고정한 상태에서 parent-child chunking 단위가 retrieval metric에 미치는 영향을 비교한다.

이 리포트는 성능 개선 확정 결과가 아니다. Dense, Hybrid, Reranker 실험 전에 검색 단위를 먼저 검증하기 위한 dev-only ablation 기록이다.

locked test split은 사용하지 않는다. test split은 최종 확인 전까지 튜닝 의사결정에 사용하지 않는다.

full chunk text와 raw run result는 public repository에 저장하지 않는다. public report에는 alias와 집계 수치만 남긴다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `chunking-ablation-report/v1` |
| run_id | `chunking-ablation-C0-C1-C2-3309f7b3` |
| generated_at_utc | `2026-05-11T07:20:08+00:00` |
| method | `bm25` |
| split | `dev` |
| top_k | 5 |
| dataset_query_count | 70 |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| normalized_blocks_path_alias | `<private artifact: normalized_blocks.json>` |
| baseline_chunks_path_alias | `<private artifact: parent_child_chunks.json>` |
| experiment_artifact_alias | `<private chunking ablation artifacts: chunking_ablation>` |
| baseline_variant_id | `C0` |
| selected_variant_id | `C0` |
| selection_reason | `C1/C2가 selection gate와 개선 조건을 동시에 충족하지 못해 C0를 유지한다.` |

## 정량 리포트

| variant | label | gate | parents | children | indexed_docs | child_p50 | child_p95 | max_chars | citation_recoverability | retrievable_coverage | duplicate_text_hash | replacement_char_rate | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_candidates | candidate_winner |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| C0 | current parent-child | PASS | 1882 | 3141 | 3141 | 717 | 931 | 1100 | 1.000000 | 1.000000 | 7 | 0.308819 | 0.400000 | 0.533333 | 0.566667 | 0.471389 | 0.344203 | 6.416900 | 10 | yes |
| C1 | smaller child | PASS | 1882 | 4583 | 4583 | 522 | 703 | 800 | 1.000000 | 1.000000 | 7 | 0.277547 | 0.016667 | 0.083333 | 0.083333 | 0.044444 | 0.026033 | 10.345600 | 10 | no |
| C2 | larger child | PASS | 1882 | 2620 | 2620 | 734 | 1141 | 1400 | 1.000000 | 1.000000 | 7 | 0.315267 | 0.383333 | 0.500000 | 0.533333 | 0.446389 | 0.272112 | 4.586700 | 10 | no |

## Query Type Breakdown

| variant | query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_candidates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C0 | place_fact | 10 | 0.400000 | 0.700000 | 0.700000 | 0.533333 | 0.426514 | 12.014600 | 0 |
| C0 | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.424299 | 5.938200 | 0 |
| C0 | relationship | 10 | 0.400000 | 0.700000 | 0.800000 | 0.570000 | 0.434678 | 75.050400 | 0 |
| C0 | overview | 10 | 0.500000 | 0.500000 | 0.600000 | 0.525000 | 0.357596 | 6.183000 | 0 |
| C0 | route_context | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.383448 | 6.416900 | 0 |
| C0 | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 3.600600 | 0 |
| C0 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 5.421700 | 10 |
| C1 | place_fact | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.024630 | 8.962400 | 0 |
| C1 | place_story | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 9.574700 | 0 |
| C1 | relationship | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 12.167400 | 0 |
| C1 | overview | 10 | 0.000000 | 0.200000 | 0.200000 | 0.083333 | 0.053072 | 10.787300 | 0 |
| C1 | route_context | 10 | 0.100000 | 0.200000 | 0.200000 | 0.133333 | 0.078493 | 11.871800 | 0 |
| C1 | voice_followup | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 6.165900 | 0 |
| C1 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 7.814000 | 10 |
| C2 | place_fact | 10 | 0.400000 | 0.600000 | 0.700000 | 0.508333 | 0.330669 | 5.371800 | 0 |
| C2 | place_story | 10 | 0.400000 | 0.600000 | 0.600000 | 0.500000 | 0.320531 | 4.032600 | 0 |
| C2 | relationship | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.332894 | 4.586700 | 0 |
| C2 | overview | 10 | 0.400000 | 0.500000 | 0.600000 | 0.470000 | 0.276417 | 4.642700 | 0 |
| C2 | route_context | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.310847 | 4.632600 | 0 |
| C2 | voice_followup | 10 | 0.100000 | 0.100000 | 0.100000 | 0.100000 | 0.061315 | 2.810600 | 0 |
| C2 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 3.738300 | 10 |

## Chunking Gate Result

| variant | gate_status | gate_failures |
| --- | --- | --- |
| C0 | PASS | `[]` |
| C1 | PASS | `[]` |
| C2 | PASS | `[]` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `experiment_scope`: BM25 retriever와 private dev split만 사용했다. locked test split은 사용하지 않았다.
- `target_alignment`: child target은 baseline gold child의 source_block_ids 전체를 포함해야 relevant hit로 계산했다. parent/doc target은 stable identifier로만 계산했다.
- `baseline_metric`: C0 Recall@5=0.566667, MRR=0.471389, nDCG@5=0.344203.
- `selected_metric`: C0 Recall@5=0.566667, MRR=0.471389, nDCG@5=0.344203.
- `selection_reason`: C1/C2가 selection gate와 개선 조건을 동시에 충족하지 못해 C0를 유지한다.
- `next_step`: 선택 후보를 고정한 뒤 Dense/Hybrid retrieval을 같은 dev/test contract에서 비교한다.
- `portfolio_boundary`: 이번 단계는 청킹 단위 선택 근거다. locked test와 generation 평가 전에는 성능 개선을 확정 주장하지 않는다.

## 해석

이번 실험은 BM25와 dev split만 사용한다.

variant 간 child_id가 달라지므로 gold child target을 baseline source block target으로 변환해 평가했다. child target은 baseline gold child의 source_block_ids 전체를 포함한 새 chunk만 relevant hit로 계산한다.

`selected_variant_id`는 다음 단계 후보일 뿐 최종 성능 개선 주장이 아니다. locked test와 generation 평가 전에는 포트폴리오에서 개선 확정 표현을 사용하지 않는다.
