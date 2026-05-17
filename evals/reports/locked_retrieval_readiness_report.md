# Locked Retrieval Readiness Report

## 목적

`HD-LOCKED-RETRIEVAL-002`는 locked retrieval paired comparison을 실행하기 전 data, route, candidate, device, public output 조건을 검증한다.

이 리포트는 성능 개선 주장이 아니다. 검색, 임베딩, metric 계산, Solar Pro 3 호출을 실행하지 않는다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `locked-retrieval-readiness-report/v1` |
| readiness_id | `locked-readiness-q35-5406e4c1` |
| work_id | `HD-LOCKED-RETRIEVAL-002` |
| generated_at_utc | `2026-05-17T09:49:05+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_test.jsonl>` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| result_path | `<private artifact: locked_retrieval_readiness_rows.jsonl>` |
| source_fingerprint | `82c0b74d353f358c` |
| readiness_status | `PASS` |

## 정량 리포트

| metric | value |
| --- | ---: |
| planned_locked_query_count | 35 |
| locked_query_count | 35 |
| planned_query_type_count | 7 |
| query_type_count | 7 |
| expected_query_count_per_type | 5 |
| answerable_query_count | 30 |
| no_answer_query_count | 5 |
| allowed_candidate_count | 2 |
| rejected_candidate_count | 4 |
| planned_retrieval_candidate_count | 2 |
| planned_generation_candidate_count | 0 |
| target_resolvability_fail_count | 0 |
| missing_child_target_count | 0 |
| missing_parent_target_count | 0 |
| missing_doc_target_count | 0 |
| no_answer_candidate_route_count | 0 |
| candidate_scope_violation_count | 0 |
| locked_test_execution_count | 0 |
| locked_metric_result_count | 0 |
| retrieval_execution_count | 0 |
| solar_call_count | 0 |
| cuda_required_for_future_run | true |
| resolved_device | `cuda` |
| readiness_decision | `ready_for_locked_retrieval_approval` |

## Query Type Route Plan

| query_type | locked_query_count | expected_candidate_count | route_policy_id | no_answer_guard | scope_violation |
| --- | ---: | ---: | --- | --- | ---: |
| place_fact | 5 | 1 | default_dense_voice_rewrite_v1 | false | 0 |
| place_story | 5 | 1 | default_dense_voice_rewrite_v1 | false | 0 |
| relationship | 5 | 2 | relationship_shadow_comparison_v1 | false | 0 |
| overview | 5 | 1 | default_dense_voice_rewrite_v1 | false | 0 |
| route_context | 5 | 1 | default_dense_voice_rewrite_v1 | false | 0 |
| voice_followup | 5 | 1 | default_dense_voice_rewrite_v1 | false | 0 |
| no_answer | 5 | 0 | no_answer_abstain_guard_v1 | true | 0 |

## Candidate Boundary

| candidate_id | status | route_policy_id | scope | planned_query_count | retrieval_execution_count | locked_metric_result_count |
| --- | --- | --- | --- | ---: | ---: | ---: |
| dense_multilingual_e5_small_voice_rewrite | baseline_allowed | default_dense_voice_rewrite_v1 | answerable_all | 30 | 0 | 0 |
| relationship_hybrid_weighted_e5_v1 | candidate_allowed_for_relationship_only | relationship_shadow_comparison_v1 | relationship_only | 5 | 0 | 0 |
| hyde_larger_live_candidate | rejected_for_locked_readiness | not_allowed | not_allowed | 0 | 0 | 0 |
| graphrag_lite_entity_path_v1 | rejected_for_locked_readiness | not_allowed | not_allowed | 0 | 0 | 0 |
| raptor_lite_summary_node_v1 | rejected_for_locked_readiness | not_allowed | not_allowed | 0 | 0 | 0 |
| place_story_guarded_boost_v1 | rejected_for_locked_readiness | not_allowed | not_allowed | 0 | 0 | 0 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 14 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
readiness_failures=[]
```

## 정성 리포트

- `scope`: locked split을 실행하지 않고 실행 전 조건만 검증했다.
- `candidate_scope`: 허용 후보는 기본 dense voice rewrite와 relationship hybrid 2개뿐이다.
- `no_answer_boundary`: no_answer query는 retrieval candidate route로 보내지 않는다.
- `device_boundary`: future run은 CUDA 사용 가능 시 CUDA를 쓰며 현재 resolved_device는 cuda다.
- `metric_boundary`: readiness 단계의 locked metric result와 retrieval execution은 0이다.
- `generation_boundary`: 이번 gate는 retrieval readiness이며 Solar Pro 3 호출은 없다.
- `data_mart_grain`: `fact_locked_retrieval_eval` grain은 run_id + query_id + candidate_id + metric_name이다.
- `security_boundary`: public artifact에는 query type, candidate id, count, decision만 남긴다.
- `external_audit`: locked test 실행 전에 후보와 stop condition을 고정한 판단은 타당하다.
- `gate_status`: PASS

## 해석

readiness gate는 통과했다. `HD-LOCKED-RETRIEVAL-003` 실행 승인 조건도 문서화했다. 다음 단계는 별도 승인 후 locked retrieval paired comparison runner를 실행하는 것이다.
