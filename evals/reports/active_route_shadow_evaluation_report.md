# Active Route Shadow Evaluation Report

## 목적

`HD-API-ROUTER-004`는 active routing을 켜기 전 shadow route가 기존 baseline보다 안전한지 paired 방식으로 검토한다.

이 리포트는 dev-shadow-only 평가다. production routing, locked test 개선, Solar Pro 3 답변 품질 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `active-route-shadow-evaluation-report/v1` |
| work_id | `HD-API-ROUTER-004` |
| run_id | `active-route-shadow-eval-q70-80d5ef11` |
| generated_at_utc | `2026-05-17T08:24:27+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private artifact: parent_child_chunks.json>` |
| result_path | `<private artifact: active_route_shadow_evaluation_rows.jsonl>` |
| dataset_fingerprint | `224e3cad1c078eeb` |
| classifier_id | `deterministic_query_type_classifier_v1` |
| router_policy_id | `query_type_router_v1` |
| guard_policy_id | `relationship-route-guard-v1` |
| baseline_route_policy_id | `default_dense_voice_rewrite_v1` |
| shadow_candidate_route_policy_id | `relationship_hybrid_weighted_e5_v1` |
| packing_policy_id | `P0_rank_order` |
| top_k | 5 |
| resolved_device | `cuda` |
| live_solar_call_count | 0 |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 70 |
| answerable_query_count | 60 |
| no_answer_query_count | 10 |
| baseline_retrieval_run_count | 60 |
| shadow_retrieval_run_count | 60 |
| routed_candidate_query_count | 10 |
| guard_applied_count | 2 |
| blocked_by_guard_count | 2 |
| fallback_default_count | 48 |
| false_hybrid_route_count | 0 |
| missed_hybrid_route_count | 0 |
| no_answer_candidate_route_count | 0 |
| active_route_applied_count | 0 |
| Recall@1 delta | 0.000000 |
| Recall@3 delta | 0.033333 |
| Recall@5 delta | 0.033333 |
| MRR delta | 0.013888 |
| nDCG@5 delta | 0.009544 |
| latency_p95_ms delta | 5.035485 |
| relationship Recall@5 delta | 0.200000 |
| relationship MRR delta | 0.083333 |
| shadow_decision | `ready_for_active_route_dry_run_contract` |

## Candidate Metrics

| candidate | query_count | retrieve_query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_with_candidate_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 70 | 60 | 0.700000 | 0.800000 | 0.850000 | 0.758056 | 0.615293 | 8.811445 | 0 |
| shadow | 70 | 60 | 0.700000 | 0.833333 | 0.883333 | 0.771944 | 0.624837 | 13.846930 | 0 |

## Query Type Delta

| query_type | query_count | baseline Recall@5 | shadow Recall@5 | Recall@5 delta | baseline MRR | shadow MRR | MRR delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `no_answer` | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| `overview` | 10 | 0.800000 | 0.800000 | 0.000000 | 0.750000 | 0.750000 | 0.000000 |
| `place_fact` | 10 | 1.000000 | 1.000000 | 0.000000 | 0.900000 | 0.900000 | 0.000000 |
| `place_story` | 10 | 0.600000 | 0.600000 | 0.000000 | 0.600000 | 0.600000 | 0.000000 |
| `relationship` | 10 | 0.800000 | 1.000000 | 0.200000 | 0.750000 | 0.833333 | 0.083333 |
| `route_context` | 10 | 0.900000 | 0.900000 | 0.000000 | 0.753333 | 0.753333 | 0.000000 |
| `voice_followup` | 10 | 1.000000 | 1.000000 | 0.000000 | 0.795000 | 0.795000 | 0.000000 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 80 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `architecture`: active route를 바로 켜지 않고 relationship route만 shadow 후보로 비교했다.
- `retrieval`: baseline은 dense voice rewrite, shadow는 guard를 통과한 relationship에만 hybrid route를 적용한다.
- `safety`: false_hybrid_route_count=0, no_answer_candidate_route_count=0로 기록했다.
- `evaluation`: dev reviewed split 기준 paired metric이며 locked test 또는 production 개선 주장이 아니다.
- `decision`: shadow_decision=ready_for_active_route_dry_run_contract.
- `public_policy`: public report에는 query id, route label, aggregate metric만 남기고 원문 계열 필드는 금지한다.

## Claim Boundary

허용 표현:

- dev shadow evaluation을 실행했다.
- active route는 아직 적용하지 않았다.
- `relationship` hybrid route의 active 적용 여부를 paired metric으로 검토했다.
- no-answer query는 candidate route에서 차단했다.

금지 표현:

- active routing으로 production 성능이 개선됐다.
- locked test에서 개선을 입증했다.
- Solar Pro 3 답변 품질이 개선됐다.
- HyDE, GraphRAG, RAPTOR가 active route로 채택됐다.

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- 이 평가는 dev-shadow-only다.
- generation 품질을 직접 평가하지 않았다.
- active route default enable은 아직 금지해야 한다.
