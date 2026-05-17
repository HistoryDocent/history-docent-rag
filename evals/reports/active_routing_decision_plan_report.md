# Active Routing Decision Plan Report

## 목적

`HD-API-ROUTER-003`은 active routing을 바로 적용하는 작업이 아니다.

목적은 HyDE 확대 live 비교 이후 남은 route 후보를 정리하고, 실제 API route 변경 전에 필요한 shadow evaluation gate를 고정하는 것이다. 이 리포트는 public-safe 정량/정성 계획 검토이며 live Solar Pro 3 호출, CUDA 연산, locked test 실행을 포함하지 않는다.

raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `active-routing-decision-plan-report/v1` |
| work_id | `HD-API-ROUTER-003` |
| generated_from | public-safe aggregate reports |
| active_route_applied | false |
| live_solar_call_count | 0 |
| cuda_required | false |
| default_route | `default_dense_voice_rewrite_v1` |
| shadow_candidate_route | `relationship_hybrid_weighted_e5_v1` |
| excluded_routes | `place_story_guarded_boost_v1`, `hyde`, `graphrag_lite`, `raptor_lite` |

## 정량 리포트

### Existing Evidence Snapshot

| metric | value | 해석 |
| --- | ---: | --- |
| classifier_dev_accuracy | 0.957143 | dev-only baseline |
| classifier_macro_f1 | 0.956818 | dev-only baseline |
| route_policy_accuracy_before_guard | 0.971429 | guard 전 |
| false_hybrid_route_count_before_guard | 2 | route-risk 존재 |
| false_hybrid_route_count_after_guard | 0 | guard 후 dev-only 개선 |
| chat_classifier_active_route_applied_count | 0 | active 미적용 |
| chat_guarded_route_candidate_count | 6 | dry-run 관찰 field |
| chat_guard_applied_count | 1 | contract fixture 기준 |
| relationship_baseline_recall_at_5 | 0.800000 | dense voice rewrite |
| relationship_hybrid_recall_at_5 | 1.000000 | route 후보 |
| relationship_baseline_mrr | 0.750000 | dense voice rewrite |
| relationship_hybrid_mrr | 0.833333 | route 후보 |
| relationship_latency_p95_ms_delta | 11.283900 | hybrid latency 증가 |
| place_story_locked_selected_candidate_count | 0 | active 후보 제외 |
| hyde_larger_mrr_delta | -0.035000 | active 후보 제외 |
| hyde_larger_ndcg_at_5_delta | -0.018384 | active 후보 제외 |

### Gate Summary

| gate | status | 이유 |
| --- | --- | --- |
| active route immediate enable | reject | dev-only와 live-dev-subset 근거만 존재 |
| relationship shadow evaluation | approve_next | hybrid route 후보가 있으나 active 적용 전 paired shadow 필요 |
| place_story active route | reject | locked readiness에서 candidate 선택 0 |
| HyDE active route | reject | MRR/nDCG/latency 악화 |
| GraphRAG-lite active route | reject | relationship input-only에서 hybrid reference를 넘지 못함 |
| RAPTOR-lite active route | reject | overview/place_story input-only에서 baseline 개선 없음 |
| locked test execution | require_separate_approval | 계획과 stop condition 필요 |

## 정성 리포트

- `architecture`: route 후보를 늘리지 않고 `relationship` 하나만 shadow 대상으로 둔다.
- `retrieval`: hybrid weighted E5는 relationship에서 Recall@5와 MRR이 높지만 latency가 증가한다.
- `generation`: route 변경은 generation 품질 개선과 별개다. Solar Pro 3 live generation은 이번 gate 범위가 아니다.
- `evaluation`: active 적용 전 dev 70 shadow paired metric, no-answer guard, false hybrid route 0 조건이 필요하다.
- `security`: public artifact에는 route label과 aggregate metric만 남긴다.
- `portfolio`: 더 많은 기법을 켜는 것보다 route 적용 전 리스크를 gate로 고정한 점을 강조한다.
- `external_audit`: HyDE와 place_story boost를 기각했기 때문에 active route 후보가 과도하게 늘어나지 않았다.

## Public Output Gate

| metric | value |
| --- | ---: |
| source_report_count | 8 |
| planned_shadow_candidate_count | 1 |
| rejected_active_route_candidate_count | 4 |
| active_route_applied_count | 0 |
| live_solar_call_count_for_this_report | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 다음 Action

이 계획의 후속 작업인 `HD-API-ROUTER-004 active route shadow evaluation runner`는 완료됐다. 다음 실제 구현 후보는 `HD-API-ROUTER-005 API active route flag dry-run contract`다.

필수 acceptance:

- dev reviewed 70개 기준 baseline route와 candidate route를 같은 query set에서 비교한다.
- `relationship` guard 통과 건수만 candidate route로 집계한다.
- `no_answer_candidate_route_count=0`을 보장한다.
- overall MRR/nDCG@5 regression threshold를 둔다.
- public report에 raw query, raw answer, evidence text, prompt, chunk text, private path, secret을 기록하지 않는다.

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- shadow evaluation 전에는 active route 적용 근거가 부족하다.
- locked test 전에는 최종 성능 개선을 주장할 수 없다.
- relationship route가 retrieval에서 이겨도 generation answer quality가 자동으로 개선되지는 않는다.
