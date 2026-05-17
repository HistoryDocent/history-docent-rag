# ColBERT-style Late Interaction Hard Subset Report

## 결론

`HD-COLBERT-001C` 실행 결과의 결정은 `reject_default_keep_as_experiment_result`이다.

이 결과는 dev hard subset 검색 비교이며 locked test, Solar Pro 3, production route 결과가 아니다.
public report에는 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다.

## 정량 결과

| metric | value |
| --- | ---: |
| selected_query_count | 21 |
| query_type_count | 3 |
| place_story_query_count | 4 |
| relationship_query_count | 10 |
| route_context_query_count | 7 |
| target_resolvability_fail_count | 0 |
| candidate_run_count | 2 |
| locked_test_execution_count | 0 |
| solar_call_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Run Metrics

| run_label | Recall@5 | MRR | nDCG@5 | latency_p95_ms | cuda_memory_peak_mb |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline_dense_e5_voice_rewrite | 0.809524 | 0.715873 | 0.567386 | 15.483000 | 0.000000 |
| colbert_style_late_interaction_top20_cuda | 0.761905 | 0.678571 | 0.506797 | 117.263100 | 937.871582 |
| colbert_style_late_interaction_top50_cuda | 0.809524 | 0.738095 | 0.545716 | 164.956000 | 936.381836 |

## Baseline Delta

| run_label | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: |
| baseline_dense_e5_voice_rewrite | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| colbert_style_late_interaction_top20_cuda | -0.047619 | -0.037302 | -0.060589 | 101.780100 |
| colbert_style_late_interaction_top50_cuda | 0.000000 | 0.022222 | -0.021670 | 149.473000 |

## Query Type Breakdown

| run_label | query_type | query_count | Recall@5 | MRR | nDCG@5 | latency_p95_ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| baseline_dense_e5_voice_rewrite | place_story | 4 | 0.750000 | 0.750000 | 0.632680 | 23.818600 |
| baseline_dense_e5_voice_rewrite | relationship | 10 | 0.800000 | 0.750000 | 0.652090 | 15.483000 |
| baseline_dense_e5_voice_rewrite | route_context | 7 | 0.857143 | 0.647619 | 0.409068 | 15.080200 |
| colbert_style_late_interaction_top20_cuda | place_story | 4 | 0.750000 | 0.750000 | 0.500000 | 159.190300 |
| colbert_style_late_interaction_top20_cuda | relationship | 10 | 0.900000 | 0.725000 | 0.600026 | 67.590500 |
| colbert_style_late_interaction_top20_cuda | route_context | 7 | 0.571429 | 0.571429 | 0.377497 | 63.119100 |
| colbert_style_late_interaction_top50_cuda | place_story | 4 | 0.750000 | 0.750000 | 0.500000 | 204.111100 |
| colbert_style_late_interaction_top50_cuda | relationship | 10 | 1.000000 | 0.900000 | 0.702329 | 113.506300 |
| colbert_style_late_interaction_top50_cuda | route_context | 7 | 0.571429 | 0.500000 | 0.348107 | 154.415800 |

## 정성 결과

| gate | status | 판단 |
| --- | --- | --- |
| CUDA | PASS | CUDA 사용 가능 환경에서 late interaction 후보를 실행했다. |
| scope | PASS | dev hard subset만 사용했고 locked split은 사용하지 않았다. |
| Solar | PASS | Solar Pro 3 호출은 0회다. |
| privacy | PASS | public artifact에는 raw payload를 기록하지 않는다. |
| claim | PASS | 개선 주장은 금지하고 dev-only 비교 결과로만 둔다. |

## Data Mart Grain

`fact_colbert_late_interaction_hard_subset`의 grain은 `work_id + run_label + query_type + metric_name + claim_boundary`다.

금지 필드:

- raw query
- raw answer
- raw evidence
- prompt
- chunk text
- private file path
- secret

## Claim Boundary

허용:

- ColBERT-style late interaction을 dev hard subset에서 비교했다.
- CUDA 사용 시 latency와 memory peak를 함께 기록했다.
- locked test와 Solar Pro 3 호출 없이 retrieval-only 실험을 수행했다.

금지:

- ColBERT로 production 성능 개선
- locked test에서 ColBERT 개선 입증
- ColBERT를 기본 route로 채택
- Solar Pro 3 기반 ColBERT 개선
