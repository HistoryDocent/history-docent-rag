# Evidence Packing Comparison Report

## 목적

검색된 evidence를 Solar Pro 3 generation 전에 어떤 순서와 범위로 묶을지 비교한다.

이 문서는 답변 생성 품질 주장이 아니다. LLM 호출 없이 retrieval 결과와 chunk metadata만 사용해 context budget, citation recoverability, target coverage, duplicate rate를 비교한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `evidence-packing-report/v1` |
| comparison_id | `evidence-packing-p5-q70-dcfa7f3c` |
| generated_at_utc | `2026-05-12T07:36:20+00:00` |
| baseline_policy_id | `P0_rank_order` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| retrieval_result_path | `<private artifact: retrieval_experiment_dense_multilingual_e5_small_voice_rewrite_results.jsonl>` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_fingerprint | `224e3cad1c078eeb` |
| retrieval_result_fingerprint | `4f53cda18c2baa0c` |
| corpus_fingerprint | `903f1dd854e2a4e0` |

## 정량 리포트

| policy_id | query_count | retrieve_query_count | abstain_query_count | packed_query_count | avg_packed_evidence_count | avg_unique_parent_count | avg_unique_doc_count | context_chars_p50 | context_chars_p95 | budget_violation | citation_recoverability | target_child_covered | target_parent_covered | target_doc_covered | duplicate_parent_rate | duplicate_doc_rate | order_relevance_proxy | abstain_with_evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P0_rank_order | 70 | 60 | 10 | 60 | 4.242857 | 3.614286 | 2.085714 | 3541 | 4154 | 0 | 1.000000 | 0.850000 | 0.866667 | 0.950000 | 0.127857 | 0.436429 | 0.898333 | 0 |
| P1_parent_expansion | 70 | 60 | 10 | 60 | 4.614286 | 2.742857 | 1.685714 | 3901 | 4105 | 0 | 1.000000 | 0.800000 | 0.816667 | 0.916667 | 0.352381 | 0.546191 | 0.886111 | 0 |
| P2_best_first_with_parent | 70 | 60 | 10 | 60 | 4.285714 | 2.571429 | 1.585714 | 3633 | 4089 | 0 | 1.000000 | 0.800000 | 0.800000 | 0.916667 | 0.342857 | 0.540000 | 0.886111 | 0 |
| P3_mmr_diversity | 70 | 60 | 10 | 60 | 4.242857 | 3.628571 | 2.085714 | 3541 | 4154 | 0 | 1.000000 | 0.850000 | 0.866667 | 0.950000 | 0.124286 | 0.436429 | 0.899167 | 0 |
| P4_voice_compact | 70 | 60 | 10 | 60 | 3.957143 | 3.471429 | 2.000000 | 3424 | 4154 | 0 | 1.000000 | 0.833333 | 0.850000 | 0.950000 | 0.097857 | 0.413810 | 0.898333 | 0 |

## Query Type Breakdown

| policy_id | query_type | query_count | target_child_covered | target_parent_covered | target_doc_covered | context_chars_p95 | duplicate_parent_rate | order_relevance_proxy |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P0_rank_order | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0.000000 |
| P0_rank_order | overview | 10 | 0.800000 | 0.900000 | 0.900000 | 4151 | 0.205000 | 0.900000 |
| P0_rank_order | place_fact | 10 | 1.000000 | 1.000000 | 1.000000 | 4056 | 0.120000 | 1.000000 |
| P0_rank_order | place_story | 10 | 0.600000 | 0.600000 | 0.900000 | 4196 | 0.140000 | 0.770000 |
| P0_rank_order | relationship | 10 | 0.800000 | 0.800000 | 0.900000 | 3941 | 0.140000 | 0.820000 |
| P0_rank_order | route_context | 10 | 0.900000 | 0.900000 | 1.000000 | 4121 | 0.080000 | 1.000000 |
| P0_rank_order | voice_followup | 10 | 1.000000 | 1.000000 | 1.000000 | 3942 | 0.210000 | 0.900000 |
| P1_parent_expansion | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0.000000 |
| P1_parent_expansion | overview | 10 | 0.800000 | 0.800000 | 0.900000 | 4089 | 0.446667 | 0.900000 |
| P1_parent_expansion | place_fact | 10 | 1.000000 | 1.000000 | 1.000000 | 4083 | 0.386667 | 1.000000 |
| P1_parent_expansion | place_story | 10 | 0.600000 | 0.600000 | 0.800000 | 4109 | 0.410000 | 0.733333 |
| P1_parent_expansion | relationship | 10 | 0.800000 | 0.800000 | 0.800000 | 4088 | 0.400000 | 0.800000 |
| P1_parent_expansion | route_context | 10 | 0.700000 | 0.700000 | 1.000000 | 4183 | 0.386667 | 1.000000 |
| P1_parent_expansion | voice_followup | 10 | 0.900000 | 1.000000 | 1.000000 | 4105 | 0.436667 | 0.883333 |
| P2_best_first_with_parent | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0.000000 |
| P2_best_first_with_parent | overview | 10 | 0.800000 | 0.800000 | 0.900000 | 4089 | 0.420000 | 0.900000 |
| P2_best_first_with_parent | place_fact | 10 | 1.000000 | 1.000000 | 1.000000 | 4016 | 0.400000 | 1.000000 |
| P2_best_first_with_parent | place_story | 10 | 0.600000 | 0.600000 | 0.800000 | 4109 | 0.360000 | 0.733333 |
| P2_best_first_with_parent | relationship | 10 | 0.800000 | 0.800000 | 0.800000 | 3983 | 0.400000 | 0.800000 |
| P2_best_first_with_parent | route_context | 10 | 0.700000 | 0.700000 | 1.000000 | 4158 | 0.400000 | 1.000000 |
| P2_best_first_with_parent | voice_followup | 10 | 0.900000 | 0.900000 | 1.000000 | 4099 | 0.420000 | 0.883333 |
| P3_mmr_diversity | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0.000000 |
| P3_mmr_diversity | overview | 10 | 0.800000 | 0.900000 | 0.900000 | 4151 | 0.205000 | 0.900000 |
| P3_mmr_diversity | place_fact | 10 | 1.000000 | 1.000000 | 1.000000 | 4056 | 0.120000 | 1.000000 |
| P3_mmr_diversity | place_story | 10 | 0.600000 | 0.600000 | 0.900000 | 4196 | 0.140000 | 0.775000 |
| P3_mmr_diversity | relationship | 10 | 0.800000 | 0.800000 | 0.900000 | 3941 | 0.140000 | 0.820000 |
| P3_mmr_diversity | route_context | 10 | 0.900000 | 0.900000 | 1.000000 | 4121 | 0.080000 | 1.000000 |
| P3_mmr_diversity | voice_followup | 10 | 1.000000 | 1.000000 | 1.000000 | 3942 | 0.185000 | 0.900000 |
| P4_voice_compact | no_answer | 10 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0.000000 |
| P4_voice_compact | overview | 10 | 0.800000 | 0.900000 | 0.900000 | 4151 | 0.205000 | 0.900000 |
| P4_voice_compact | place_fact | 10 | 1.000000 | 1.000000 | 1.000000 | 4056 | 0.120000 | 1.000000 |
| P4_voice_compact | place_story | 10 | 0.600000 | 0.600000 | 0.900000 | 4196 | 0.140000 | 0.770000 |
| P4_voice_compact | relationship | 10 | 0.800000 | 0.800000 | 0.900000 | 3941 | 0.140000 | 0.820000 |
| P4_voice_compact | route_context | 10 | 0.900000 | 0.900000 | 1.000000 | 4121 | 0.080000 | 1.000000 |
| P4_voice_compact | voice_followup | 10 | 0.900000 | 0.900000 | 1.000000 | 2537 | 0.000000 | 0.900000 |

## Baseline Delta

| baseline_policy_id | compared_policy_id | target_child_delta | target_parent_delta | target_doc_delta | citation_recoverability_delta | duplicate_parent_delta | order_relevance_delta | context_chars_p95_delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P0_rank_order | P0_rank_order | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 |
| P0_rank_order | P1_parent_expansion | -0.050000 | -0.050000 | -0.033333 | 0.000000 | 0.224524 | -0.012222 | -49 |
| P0_rank_order | P2_best_first_with_parent | -0.050000 | -0.066667 | -0.033333 | 0.000000 | 0.215000 | -0.012222 | -65 |
| P0_rank_order | P3_mmr_diversity | 0.000000 | 0.000000 | 0.000000 | 0.000000 | -0.003571 | 0.000834 | 0 |
| P0_rank_order | P4_voice_compact | -0.016667 | -0.016667 | 0.000000 | 0.000000 | -0.030000 | 0.000000 | 0 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 1544 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `comparison_scope`: 검색 결과를 새로 만들지 않고 고정된 retrieval result 위에서 evidence packing만 비교했다.
- `default_policy_candidate`: `P0_rank_order`를 v1 기본값으로 유지한다. `P3_mmr_diversity`의 개선은 동률에 가까워 generation 전 기본 교체 근거가 부족하다.
- `coverage_candidate`: `P3_mmr_diversity`가 coverage 관점의 최고 후보이나 `P0_rank_order` 대비 차이가 generation 품질로 이어지는지는 아직 미검증이다.
- `diversity_candidate`: `P4_voice_compact`가 duplicate parent 억제 수치는 가장 낮지만 target coverage 손실이 있으면 기본 정책으로 채택하지 않는다.
- `citation_boundary`: 모든 evidence는 child chunk와 source block id 기준으로만 pack하며 요약 node를 citation으로 쓰지 않는다.
- `no_answer_policy`: abstain query에는 evidence를 pack하지 않아 generation 단계의 corpus 밖 질문 환각 위험을 낮춘다.
- `claim_boundary`: 이 결과는 generation 품질 개선 주장이 아니다. LLM 답변 평가는 다음 단계에서 분리한다.

## 해석

현재 결과는 dev retrieval 결과 위에서 evidence 구성 정책만 비교한 것이다.

다음 단계에서는 선택된 packing 후보를 citation RAG answer contract와 generation evaluation harness에 연결한다. `Correct-with-Evidence`, `citation_precision`, `unsupported_claim_rate`는 Solar Pro 3 generation 단계에서 별도로 측정한다.
