# Locked Retrieval Paired Comparison Report

## 목적

`HD-LOCKED-RETRIEVAL-004`는 locked test split에서 사전 승인된 retrieval 후보 2개만 paired comparison으로 확인한다.

이 리포트는 retrieval-only 결과다. Solar Pro 3 답변 품질, production route enable, GraphRAG/RAPTOR/HyDE 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `locked-retrieval-paired-comparison/v1` |
| work_id | `HD-LOCKED-RETRIEVAL-004` |
| run_id | `locked-retrieval-paired-q35-bd83ba6a` |
| generated_at_utc | `2026-05-17T11:11:55+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_test.jsonl>` |
| chunks_path | `<private artifact: parent_child_chunks.json>` |
| result_path | `<private artifact: locked_retrieval_paired_comparison_fact_rows.jsonl>` |
| dataset_fingerprint | `79cad46a5c57afde` |
| router_policy_id | `query_type_router_v1` |
| baseline_route_policy_id | `default_dense_voice_rewrite_v1` |
| candidate_route_policy_id | `relationship_hybrid_weighted_e5_v1` |
| packing_policy_id | `P0_rank_order` |
| top_k | 5 |
| resolved_device | `cuda` |

## 정량 리포트

| metric | value |
| --- | ---: |
| locked_query_count | 35 |
| query_type_count | 7 |
| answerable_query_count | 30 |
| no_answer_query_count | 5 |
| baseline_retrieval_run_count | 30 |
| candidate_retrieval_run_count | 5 |
| paired_query_count | 5 |
| target_resolvability_fail_count | 0 |
| false_hybrid_route_count | 0 |
| no_answer_candidate_route_count | 0 |
| active_route_applied_count | 0 |
| live_solar_call_count | 0 |
| private_fact_row_count | 320 |
| bootstrap_iteration_count | 10000 |
| confidence_interval_percent | 95 |
| primary_metric | `mrr` |
| Recall@1 delta | -0.200000 |
| Recall@3 delta | 0.000000 |
| Recall@5 delta | 0.000000 |
| MRR delta | -0.100000 |
| nDCG@5 delta | -0.073814 |
| latency_p95_ms delta | 7.370080 |
| primary_metric_delta | -0.100000 |
| primary_metric_ci_low | -0.300000 |
| primary_metric_ci_high | 0.000000 |
| locked_decision | `keep_shadow_without_locked_improvement_claim` |

## Candidate Metrics

| candidate | scope | query_count | retrieve_query_count | retrieval_execution_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_with_candidate_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | answerable_all | 35 | 30 | 30 | 0.300000 | 0.466667 | 0.600000 | 0.403889 | 0.452389 | 11.956680 | 0 |
| candidate | relationship_only | 5 | 5 | 5 | 0.400000 | 0.600000 | 0.600000 | 0.500000 | 0.526186 | 19.071980 | 0 |

## Query Type Breakdown

| query_type | query_count | paired_query_count | baseline Recall@5 | candidate Recall@5 | Recall@5 delta | baseline MRR | candidate MRR | MRR delta | baseline nDCG@5 | candidate nDCG@5 | nDCG@5 delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `place_fact` | 5 | 0 | 1.000000 | 0.000000 | 0.000000 | 0.516667 | 0.000000 | 0.000000 | 0.638507 | 0.000000 | 0.000000 | 0.000000 |
| `place_story` | 5 | 0 | 0.800000 | 0.000000 | 0.000000 | 0.650000 | 0.000000 | 0.000000 | 0.686135 | 0.000000 | 0.000000 | 0.000000 |
| `relationship` | 5 | 5 | 0.600000 | 0.600000 | 0.000000 | 0.600000 | 0.500000 | -0.100000 | 0.600000 | 0.526186 | -0.073814 | 7.370080 |
| `overview` | 5 | 0 | 0.600000 | 0.000000 | 0.000000 | 0.190000 | 0.000000 | 0.000000 | 0.289692 | 0.000000 | 0.000000 | 0.000000 |
| `route_context` | 5 | 0 | 0.200000 | 0.000000 | 0.000000 | 0.200000 | 0.000000 | 0.000000 | 0.200000 | 0.000000 | 0.000000 | 0.000000 |
| `voice_followup` | 5 | 0 | 0.400000 | 0.000000 | 0.000000 | 0.266667 | 0.000000 | 0.000000 | 0.300000 | 0.000000 | 0.000000 | 0.000000 |
| `no_answer` | 5 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

## Bootstrap CI

| metric | observed_delta | ci_low | ci_high | iterations | decision_tag |
| --- | ---: | ---: | ---: | ---: | --- |
| `recall_at_1` | -0.200000 | -0.600000 | 0.000000 | 10000 | `ci_includes_zero` |
| `recall_at_3` | 0.000000 | 0.000000 | 0.000000 | 10000 | `ci_includes_zero` |
| `recall_at_5` | 0.000000 | 0.000000 | 0.000000 | 10000 | `ci_includes_zero` |
| `mrr` | -0.100000 | -0.300000 | 0.000000 | 10000 | `ci_includes_zero` |
| `ndcg_at_5` | -0.073814 | -0.221442 | 0.000000 | 10000 | `ci_includes_zero` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 15 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `architecture`: locked split에서 후보를 새로 늘리지 않고 승인된 두 후보만 실행했다.
- `retrieval`: baseline은 answerable 30개 dense voice rewrite, candidate는 relationship 5개 hybrid route로 제한했다.
- `evaluation`: primary_metric=mrr, bootstrap=10000, CI=95%로 계산했다.
- `safety`: false_hybrid_route_count=0, no_answer_candidate_route_count=0.
- `decision`: locked_decision=keep_shadow_without_locked_improvement_claim.
- `claim_boundary`: retrieval-only locked 결과이며 generation 또는 production 개선 주장이 아니다.
- `external_audit`: locked 결과를 보고 후보, threshold, chunking, prompt를 수정하지 않았다.

## Claim Boundary

허용 표현:

- locked retrieval paired comparison을 실행했다.
- relationship subset에서 baseline과 후보의 paired delta와 bootstrap CI를 계산했다.
- no-answer query는 candidate route에서 차단됐다.

금지 표현:

- production routing을 활성화했다.
- Solar Pro 3 답변 품질이 개선됐다.
- GraphRAG, RAPTOR, HyDE가 locked에서 개선됐다.
- locked 결과를 보고 threshold, chunking, prompt를 수정했다.

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- paired relationship query가 5개라 CI 폭 해석이 제한적이다.
- retrieval metric이 generation 품질 개선을 자동으로 의미하지 않는다.
- active route default enable은 별도 gate가 필요하다.
