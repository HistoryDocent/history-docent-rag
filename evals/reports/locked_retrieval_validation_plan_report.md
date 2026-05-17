# Locked Retrieval Validation Plan Report

## 목적

`HD-LOCKED-RETRIEVAL-001`은 locked retrieval test를 실행하기 전 승인 조건을 고정한다.

이 리포트는 성능 개선 주장이 아니다. CUDA 연산, locked retrieval 실행, Solar Pro 3 호출을 포함하지 않는다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `locked-retrieval-validation-plan-report/v1` |
| work_id | `HD-LOCKED-RETRIEVAL-001` |
| source_plan | `docs/LOCKED_RETRIEVAL_VALIDATION_PLAN.md` |
| depends_on | `HD-API-ROUTER-005` |
| cuda_required_for_future_run | true |
| locked_test_execution_count | 0 |
| solar_call_count | 0 |

## 정량 리포트

| metric | value |
| --- | ---: |
| planned_locked_query_count | 35 |
| planned_query_type_count | 7 |
| planned_retrieval_candidate_count | 2 |
| rejected_candidate_count | 4 |
| planned_generation_candidate_count | 0 |
| locked_test_execution_count | 0 |
| locked_metric_result_count | 0 |
| solar_call_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Candidate Boundary

| candidate_id | status | reason |
| --- | --- | --- |
| `dense_multilingual_e5_small_voice_rewrite` | baseline_allowed | 현재 기본 retrieval 후보 |
| `relationship_hybrid_weighted_e5_v1` | candidate_allowed_for_relationship_only | active route shadow와 API flag dry-run 이후 relationship 전용 후보 |
| `hyde_larger_live_candidate` | rejected_for_locked_plan | dev 40에서 MRR/nDCG/latency 악화 |
| `graphrag_lite_entity_path_v1` | rejected_for_locked_plan | dev input-only 개선 없음 |
| `raptor_lite_summary_node_v1` | rejected_for_locked_plan | dev input-only 개선 없음 |
| `place_story_guarded_boost_v1` | rejected_for_locked_plan | locked readiness에서 candidate 선택 0 |

## 정성 리포트

- `evaluation_scope`: locked split은 최종 확인용이므로 이번 단계에서는 실행하지 않는다.
- `candidate_scope`: locked에서 비교할 후보는 기본 E5 voice rewrite와 relationship hybrid route로 제한한다.
- `split_boundary`: locked 결과를 보고 threshold, prompt, chunking, query rewrite rule을 수정하지 않는다.
- `generation_boundary`: 이번 gate는 retrieval 검증 계획이며 Solar Pro 3 generation live 비교를 포함하지 않는다.
- `security_boundary`: public report에는 aggregate count, candidate id, decision tag만 남긴다.
- `data_mart_boundary`: 실제 실행 시 grain은 `run_id + query_id + candidate_id + metric_name`이고 public summary는 aggregate만 허용한다.
- `external_audit`: locked test 실행 전 조건을 고정한 것은 타당하다. 실행 결과를 튜닝에 사용하면 split contamination이므로 별도 금지 문구가 필요하다.
- `gate_status`: PASS

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 6 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 다음 작업

다음 작업인 `HD-LOCKED-RETRIEVAL-002 locked retrieval readiness dry-run runner`는 완료됐다.

결과는 `docs/LOCKED_RETRIEVAL_READINESS.md`와 `evals/reports/locked_retrieval_readiness_report.md`에 기록한다. 실제 locked retrieval metric 계산이 아니라 다음 항목만 확인했다.

- locked query target resolvability
- expected route/candidate count
- no-answer route guard
- CUDA device availability
- public-safe output gate
- locked metric execution 0

다음 gate는 `HD-LOCKED-RETRIEVAL-003 locked retrieval paired comparison 실행 여부 승인`이다.
