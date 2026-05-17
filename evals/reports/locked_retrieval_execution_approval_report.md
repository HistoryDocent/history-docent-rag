# Locked Retrieval Execution Approval Report

## 목적

`HD-LOCKED-RETRIEVAL-003`은 locked retrieval paired comparison을 실행하기 전 승인 조건을 고정한다.

이 리포트는 성능 개선 주장이 아니다. 검색, 임베딩, metric 계산, Solar Pro 3 호출을 실행하지 않는다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `locked-retrieval-execution-approval-report/v1` |
| work_id | `HD-LOCKED-RETRIEVAL-003` |
| source_doc | `docs/LOCKED_RETRIEVAL_EXECUTION_APPROVAL.md` |
| depends_on | `HD-LOCKED-RETRIEVAL-002` |
| readiness_status | `PASS` |
| approval_decision | `ready_for_user_execution_approval` |
| locked_execution_approved | false |
| cuda_required_for_future_run | true |

## 정량 리포트

| metric | value |
| --- | ---: |
| planned_locked_query_count | 35 |
| planned_query_type_count | 7 |
| planned_candidate_count | 2 |
| rejected_candidate_count | 4 |
| planned_generation_candidate_count | 0 |
| planned_solar_call_count | 0 |
| planned_bootstrap_iteration_count | 10000 |
| confidence_interval_percent | 95 |
| retrieval_execution_count | 0 |
| locked_metric_result_count | 0 |
| target_resolvability_fail_count | 0 |
| no_answer_candidate_route_count | 0 |
| false_hybrid_route_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Candidate Boundary

| candidate_id | status | scope | reason |
| --- | --- | --- | --- |
| `dense_multilingual_e5_small_voice_rewrite` | baseline_allowed | answerable all | 현재 non-rerank 기본 후보 |
| `relationship_hybrid_weighted_e5_v1` | candidate_allowed | relationship only | relationship shadow 후보 |
| `hyde_larger_live_candidate` | rejected | not allowed | dev 40에서 MRR, nDCG, latency 악화 |
| `graphrag_lite_entity_path_v1` | rejected | not allowed | relationship input-only 개선 없음 |
| `raptor_lite_summary_node_v1` | rejected | not allowed | overview/place_story input-only 개선 없음 |
| `place_story_guarded_boost_v1` | rejected | not allowed | locked readiness에서 candidate 선택 0건 |

## Metric Approval Matrix

| metric_group | required_before_execution | decision |
| --- | --- | --- |
| paired comparison | same locked query set | approved_for_future_run |
| bootstrap | 10000 iterations | approved_for_future_run |
| confidence interval | 95 percent | approved_for_future_run |
| no-answer safety | candidate route count 0 | required_stop_condition |
| route safety | false hybrid route count 0 | required_stop_condition |
| latency | p50, p95, delta | required_tradeoff_report |
| public safety | leakage counts 0 | required_stop_condition |

## Data Mart Boundary

| table | grain |
| --- | --- |
| `fact_locked_retrieval_eval` | `run_id + query_id + candidate_id + metric_name` |
| `dim_locked_eval_run` | `run_id` |
| `dim_retrieval_candidate` | `candidate_id` |
| `dim_query_type` | `query_type` |
| `fact_locked_public_summary` | `run_id + candidate_id + query_type + metric_name` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 6 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `evaluation_scope`: 이번 단계는 실행 승인 계획이며 locked metric 계산은 하지 않는다.
- `candidate_scope`: 실행 후보는 baseline 1개와 relationship-only candidate 1개로 제한한다.
- `split_boundary`: locked 결과로 chunking, prompt, query rewrite, threshold를 수정하지 않는다.
- `cuda_boundary`: future run은 CUDA 사용 가능 시 CUDA로 실행하고 device 정보를 run dimension에 남긴다.
- `generation_boundary`: Solar Pro 3 generation 비교는 이번 gate에 포함하지 않는다.
- `security_boundary`: public artifact는 aggregate metric과 decision tag만 허용한다.
- `data_mart_boundary`: private fact grain과 public summary grain을 분리한다.
- `external_audit`: readiness 통과 후에도 실행 승인서를 따로 둔 판단은 test split 오염 방지에 타당하다.
- `gate_status`: PASS

## 다음 작업

다음 작업은 `HD-LOCKED-RETRIEVAL-004 locked retrieval paired comparison runner 실행`이다.

단, 실제 실행은 별도 사용자 승인 후에만 진행한다.
