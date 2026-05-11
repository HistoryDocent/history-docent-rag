# Chunking Ablation v2 Report

## 목적

BM25 retriever를 고정한 상태에서 parent-child chunking 단위가 retrieval metric에 미치는 영향을 비교한다.

이 리포트는 성능 개선 확정 결과가 아니다. Dense, Hybrid, Reranker 실험 전에 검색 단위를 먼저 검증하기 위한 dev-only ablation 기록이다.

v2에서는 기존 C0/C1/C2에 micro-parent merge, overlap 0/2, fixed-size block baseline을 추가했다.

locked test split은 사용하지 않는다. test split은 최종 확인 전까지 튜닝 의사결정에 사용하지 않는다.

full chunk text와 raw run result는 public repository에 저장하지 않는다. public report에는 alias와 집계 수치만 남긴다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `chunking-ablation-report/v2` |
| run_id | `chunking-ablation-C0-C1-C2-C3-C4-C5-C6-08efd77b` |
| generated_at_utc | `2026-05-11T11:06:16+00:00` |
| method | `bm25` |
| split | `dev` |
| top_k | 5 |
| dataset_query_count | 70 |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| normalized_blocks_path_alias | `<private artifact: normalized_blocks.json>` |
| baseline_chunks_path_alias | `<private artifact: parent_child_chunks.json>` |
| experiment_artifact_alias | `<private chunking ablation artifacts: chunking_ablation_v2>` |
| baseline_variant_id | `C0` |
| selected_variant_id | `C0` |
| selection_reason | `C1/C2/C3/C4/C5/C6가 selection gate와 개선 조건을 동시에 충족하지 못해 C0를 유지한다.` |

## 정량 리포트

| variant | label | boundary_policy | overlap_blocks | micro_merge | gate | parents | children | indexed_docs | child_p50 | child_p95 | max_chars | citation_recoverability | retrievable_coverage | duplicate_text_hash | replacement_char_rate | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_candidates | candidate_winner |
| --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| C0 | current parent-child | heading1_parent_child | 1 | no | PASS | 1882 | 3141 | 3141 | 717 | 931 | 1100 | 1.000000 | 1.000000 | 7 | 0.308819 | 0.400000 | 0.533333 | 0.566667 | 0.471389 | 0.344203 | 7.504000 | 10 | yes |
| C1 | smaller child | heading1_parent_child | 1 | no | PASS | 1882 | 4583 | 4583 | 522 | 703 | 800 | 1.000000 | 1.000000 | 7 | 0.277547 | 0.016667 | 0.083333 | 0.083333 | 0.044444 | 0.026033 | 10.086600 | 10 | no |
| C2 | larger child | heading1_parent_child | 1 | no | PASS | 1882 | 2620 | 2620 | 734 | 1141 | 1400 | 1.000000 | 1.000000 | 7 | 0.315267 | 0.383333 | 0.500000 | 0.533333 | 0.446389 | 0.272112 | 6.141000 | 10 | no |
| C3 | micro-parent merge | heading1_micro_merge | 1 | yes | PASS | 1626 | 2915 | 2915 | 738 | 939 | 1100 | 1.000000 | 1.000000 | 2 | 0.325901 | 0.400000 | 0.483333 | 0.533333 | 0.453333 | 0.330712 | 6.343100 | 10 | no |
| C4 | overlap 0 | heading1_parent_child | 0 | no | FAIL | 1882 | 2732 | 2732 | 694 | 977 | 1100 | 1.000000 | 1.000000 | 7 | 0.288799 | 0.300000 | 0.466667 | 0.483333 | 0.384722 | 0.241390 | 6.154800 | 10 | no |
| C5 | overlap 2 | heading1_parent_child | 2 | no | PASS | 1882 | 3591 | 3591 | 745 | 953 | 1100 | 1.000000 | 1.000000 | 7 | 0.340295 | 0.250000 | 0.500000 | 0.533333 | 0.368611 | 0.247787 | 8.998300 | 10 | no |
| C6 | fixed-size block baseline | fixed_size_block | 0 | no | FAIL | 286 | 2122 | 2122 | 778 | 959 | 1100 | 1.000000 | 1.000000 | 0 | 0.359095 | 0.216667 | 0.266667 | 0.316667 | 0.254167 | 0.145937 | 5.483900 | 10 | no |

## Query Type Breakdown

| variant | query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_candidates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C0 | place_fact | 10 | 0.400000 | 0.700000 | 0.700000 | 0.533333 | 0.426514 | 91.863200 | 0 |
| C0 | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.424299 | 6.048300 | 0 |
| C0 | relationship | 10 | 0.400000 | 0.700000 | 0.800000 | 0.570000 | 0.434678 | 6.661800 | 0 |
| C0 | overview | 10 | 0.500000 | 0.500000 | 0.600000 | 0.525000 | 0.357596 | 6.832400 | 0 |
| C0 | route_context | 10 | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.383448 | 7.524200 | 0 |
| C0 | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 5.063300 | 0 |
| C0 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 8.043500 | 10 |
| C1 | place_fact | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.024630 | 9.819300 | 0 |
| C1 | place_story | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 10.754300 | 0 |
| C1 | relationship | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 9.905800 | 0 |
| C1 | overview | 10 | 0.000000 | 0.200000 | 0.200000 | 0.083333 | 0.053072 | 13.446900 | 0 |
| C1 | route_context | 10 | 0.100000 | 0.200000 | 0.200000 | 0.133333 | 0.078493 | 10.086600 | 0 |
| C1 | voice_followup | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 7.312600 | 0 |
| C1 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 8.828000 | 10 |
| C2 | place_fact | 10 | 0.400000 | 0.600000 | 0.700000 | 0.508333 | 0.330669 | 6.526000 | 0 |
| C2 | place_story | 10 | 0.400000 | 0.600000 | 0.600000 | 0.500000 | 0.320531 | 6.141000 | 0 |
| C2 | relationship | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.332894 | 6.074500 | 0 |
| C2 | overview | 10 | 0.400000 | 0.500000 | 0.600000 | 0.470000 | 0.276417 | 6.487700 | 0 |
| C2 | route_context | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.310847 | 6.293300 | 0 |
| C2 | voice_followup | 10 | 0.100000 | 0.100000 | 0.100000 | 0.100000 | 0.061315 | 4.338800 | 0 |
| C2 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 6.000000 | 10 |
| C3 | place_fact | 10 | 0.400000 | 0.500000 | 0.500000 | 0.450000 | 0.353083 | 12.710200 | 0 |
| C3 | place_story | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.424299 | 6.343100 | 0 |
| C3 | relationship | 10 | 0.500000 | 0.600000 | 0.800000 | 0.595000 | 0.442172 | 6.034600 | 0 |
| C3 | overview | 10 | 0.500000 | 0.500000 | 0.600000 | 0.525000 | 0.357596 | 6.377000 | 0 |
| C3 | route_context | 10 | 0.500000 | 0.600000 | 0.600000 | 0.550000 | 0.368435 | 6.468100 | 0 |
| C3 | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 4.244800 | 0 |
| C3 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 5.165400 | 10 |
| C4 | place_fact | 10 | 0.400000 | 0.700000 | 0.700000 | 0.533333 | 0.340066 | 6.405400 | 0 |
| C4 | place_story | 10 | 0.300000 | 0.500000 | 0.500000 | 0.400000 | 0.288504 | 9.743600 | 0 |
| C4 | relationship | 10 | 0.400000 | 0.600000 | 0.700000 | 0.525000 | 0.302779 | 6.263400 | 0 |
| C4 | overview | 10 | 0.400000 | 0.500000 | 0.500000 | 0.450000 | 0.261315 | 6.154800 | 0 |
| C4 | route_context | 10 | 0.300000 | 0.400000 | 0.400000 | 0.350000 | 0.216991 | 5.941900 | 0 |
| C4 | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 4.076700 | 0 |
| C4 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 4.609300 | 10 |
| C5 | place_fact | 10 | 0.300000 | 0.700000 | 0.700000 | 0.483333 | 0.347045 | 7.326900 | 0 |
| C5 | place_story | 10 | 0.400000 | 0.600000 | 0.600000 | 0.466667 | 0.330657 | 8.604600 | 0 |
| C5 | relationship | 10 | 0.300000 | 0.500000 | 0.600000 | 0.420000 | 0.275326 | 7.234200 | 0 |
| C5 | overview | 10 | 0.200000 | 0.600000 | 0.600000 | 0.366667 | 0.234740 | 8.422100 | 0 |
| C5 | route_context | 10 | 0.300000 | 0.500000 | 0.600000 | 0.425000 | 0.260268 | 8.312700 | 0 |
| C5 | voice_followup | 10 | 0.000000 | 0.100000 | 0.100000 | 0.050000 | 0.038685 | 10.523100 | 0 |
| C5 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 8.186200 | 10 |
| C6 | place_fact | 10 | 0.300000 | 0.400000 | 0.400000 | 0.350000 | 0.218486 | 5.483900 | 0 |
| C6 | place_story | 10 | 0.300000 | 0.400000 | 0.500000 | 0.375000 | 0.190603 | 5.451700 | 0 |
| C6 | relationship | 10 | 0.300000 | 0.300000 | 0.400000 | 0.325000 | 0.198845 | 6.260700 | 0 |
| C6 | overview | 10 | 0.100000 | 0.100000 | 0.100000 | 0.100000 | 0.046928 | 5.042500 | 0 |
| C6 | route_context | 10 | 0.300000 | 0.400000 | 0.400000 | 0.350000 | 0.200547 | 6.749600 | 0 |
| C6 | voice_followup | 10 | 0.000000 | 0.000000 | 0.100000 | 0.025000 | 0.020211 | 4.051200 | 0 |
| C6 | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 4.067600 | 10 |

## Chunking Gate Result

| variant | gate_status | gate_failures |
| --- | --- | --- |
| C0 | PASS | `[]` |
| C1 | PASS | `[]` |
| C2 | PASS | `[]` |
| C3 | PASS | `[]` |
| C4 | FAIL | `['short_standalone_child']` |
| C5 | PASS | `[]` |
| C6 | FAIL | `['short_standalone_child']` |

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
- `selection_reason`: C1/C2/C3/C4/C5/C6가 selection gate와 개선 조건을 동시에 충족하지 못해 C0를 유지한다.
- `next_step`: 선택 후보를 고정한 뒤 Dense/Hybrid retrieval을 같은 dev/test contract에서 비교한다.
- `portfolio_boundary`: 이번 단계는 청킹 단위 선택 근거다. locked test와 generation 평가 전에는 성능 개선을 확정 주장하지 않는다.

## 해석

이번 실험은 BM25와 dev split만 사용한다.

variant 간 child_id가 달라지므로 gold child target을 baseline source block target으로 변환해 평가했다. child target은 baseline gold child의 source_block_ids 전체를 포함한 새 chunk만 relevant hit로 계산한다.

`selected_variant_id`는 다음 단계 후보일 뿐 최종 성능 개선 주장이 아니다. locked test와 generation 평가 전에는 포트폴리오에서 개선 확정 표현을 사용하지 않는다.
