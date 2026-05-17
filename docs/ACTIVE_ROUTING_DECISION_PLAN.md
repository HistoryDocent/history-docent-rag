# Active Routing Decision Plan

## 결론

지금은 active routing을 바로 적용하지 않는다.

`HD-API-ROUTER-003`의 결론은 다음이다. 현재 증거로는 `relationship` query에 한해 `hybrid_weighted_e5_small_alpha_0_5`를 shadow route 후보로 올릴 수 있다. 그러나 `/api/v1/chat`의 실제 retrieval route를 바꾸기 전에는 shadow evaluation runner와 locked test 계획이 필요하다. `place_story_guarded_boost_v1`, HyDE, GraphRAG-lite, RAPTOR-lite는 active route 후보에서 제외한다.

이 문서는 public-safe 계획 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | 단일 기본 route는 유지하되 `relationship` hybrid route만 shadow 후보로 분리한다. |
| Retrieval | `relationship`에서는 hybrid weighted E5가 dev input 기준 우위지만, 전체 기본 route로 확장하면 latency와 top-rank trade-off가 있다. |
| Generation | route 변경은 Solar Pro 3 답변 품질 개선을 자동으로 의미하지 않는다. generation live 비교는 후순위다. |
| Evaluation | active 적용 전 shadow evaluation, no-answer guard, route-risk regression gate가 필요하다. |
| Data warehouse | route 판단 grain은 `run_id + query_id + predicted_query_type + baseline_route + candidate_route + decision_reason`으로 둔다. |
| Security | public artifact에는 aggregate metric, route label, decision tag만 남긴다. 원문 계열 필드는 금지한다. |
| Portfolio | “router를 켰다”보다 “active 적용 전 위험을 gate로 분리했다”가 더 강한 메시지다. |
| 외부 감사 | HyDE와 place_story boost를 기각한 뒤 route 후보를 하나로 줄인 판단은 과장 위험을 낮춘다. |

## 현재 근거

| 항목 | 값 | 판단 |
| --- | ---: | --- |
| classifier dev accuracy | 0.957143 | baseline 구현 완료, production claim 아님 |
| classifier macro_f1 | 0.956818 | dev-only |
| route_policy_accuracy | 0.971429 | guard 전 기준 |
| false_hybrid_route_count | 2 -> 0 | relationship guard 적용 시 dev-only 개선 |
| classifier_active_route_applied_count | 0 | API는 dry-run만 노출 |
| guarded_route_candidate guard_applied_count | 1 | API 관찰 field만 구현 |
| relationship baseline Recall@5 | 0.800000 | dense voice rewrite |
| relationship hybrid Recall@5 | 1.000000 | shadow route 후보 |
| relationship hybrid latency_p95_ms | 26.850500 | baseline 15.566600 대비 증가 |
| place_story locked selected_candidate_count | 0 | active 후보 제외 |
| HyDE larger MRR delta | -0.035000 | active 후보 제외 |
| HyDE larger nDCG@5 delta | -0.018384 | active 후보 제외 |

## Active Routing 범위

### 적용하지 않는 것

- `place_story_guarded_boost_v1` production route
- HyDE 기본 route
- GraphRAG-lite route
- RAPTOR-lite route
- reranker 기본 route
- Solar Pro 3 prompt policy 변경

### shadow 후보

| query_type | baseline_route | candidate_route | 상태 |
| --- | --- | --- | --- |
| `relationship` | `default_dense_voice_rewrite_v1` | `relationship_hybrid_weighted_e5_v1` | shadow evaluation 후보 |
| `no_answer` | `abstain_first_v1` | 없음 | hallucination guard 유지 |
| 나머지 answerable type | `default_dense_voice_rewrite_v1` | 없음 | baseline 유지 |

## 단계별 Gate

### Gate 0: 현재 상태 유지

목표는 active route 적용 없이 관찰 가능성을 유지하는 것이다.

통과 기준:

- `/api/v1/chat`에서 `classifier_router_dry_run.active_route_applied=false`
- `guarded_route_candidate` field 유지
- live Solar Pro 3 호출 0
- public leakage 0

### Gate 1: Shadow Evaluation Runner

목표는 같은 dev split에서 baseline route와 candidate route를 query 단위로 비교하는 것이다.

정량 metric:

| metric | 기준 |
| --- | --- |
| query_count | dev reviewed 70 |
| routed_candidate_query_count | `relationship` 예측/guard 통과 건수만 |
| false_hybrid_route_count | 0 |
| no_answer_candidate_route_count | 0 |
| overall MRR delta | -0.010000 이상 |
| overall nDCG@5 delta | -0.010000 이상 |
| relationship Recall@5 delta | 0 초과 |
| latency_p95_ms delta | 50ms 미만 또는 악화 사유 명시 |
| public_raw_text_leakage_count | 0 |

정성 tag:

- `safe_route_candidate`
- `blocked_by_guard`
- `fallback_to_default`
- `no_answer_abstain`
- `latency_tradeoff`
- `metric_regression`

### Gate 2: Active Route Dry-run Contract

목표는 API contract에서 active route를 켰을 때의 response field와 rollback flag를 검증하는 것이다.

필수 조건:

- 기본값은 `ACTIVE_ROUTING_ENABLED=false`
- route별 feature flag 분리
- unknown query type은 default route fallback
- `no_answer`는 retrieval보다 abstention contract 우선
- response에는 active route label, fallback reason, guard reason만 노출
- raw query, evidence text, chunk text 미노출

### Gate 3: Locked Test 승인 계획

목표는 locked split을 쓰기 전에 실행 조건을 고정하는 것이다.

승인 전 금지:

- locked test 실행
- production 개선 claim
- active route default enable
- Solar Pro 3 live generation 재실행

## Data Mart 설계

`fact_active_routing_shadow_eval`의 grain은 `run_id + query_id + predicted_query_type + baseline_route + candidate_route + decision_reason`이다.

| field | 설명 |
| --- | --- |
| `run_id` | shadow eval 실행 id |
| `query_id` | public-safe query identifier |
| `gold_query_type` | reviewed label |
| `predicted_query_type` | classifier output label |
| `baseline_route` | 기존 route id |
| `candidate_route` | shadow route id |
| `guard_decision` | allow, block, fallback |
| `decision_reason` | sanitized reason tag |
| `metric_family` | retrieval, latency, safety |
| `metric_delta` | baseline 대비 aggregate delta |
| `claim_boundary` | dev-shadow-only, locked-only 등 |

금지 필드:

- raw query
- raw answer
- raw evidence
- prompt
- chunk text
- private file path
- secret

## 작업 명령 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| `HD-API-ROUTER-003` | `HD-HYDE-001D` | active routing 적용 여부 판단 계획 문서화 | 계획 문서, report, README/TODO/ledger 갱신, leakage scan 통과 | Low | 문서 변경 revert |
| `HD-API-ROUTER-004` | `HD-API-ROUTER-003` | active route shadow evaluation runner 구현 완료 | dev 70 route paired metrics, no-answer route 0, leakage 0 | Medium | runner/report revert |
| `HD-API-ROUTER-005` | `HD-API-ROUTER-004` | API active route flag dry-run contract 완료 | default disabled, fallback/guard field, contract test | Medium | feature flag와 response field revert |
| `HD-LOCKED-RETRIEVAL-001` | `HD-API-ROUTER-005` | locked retrieval 검증 승인 계획 완료 | locked split 사용 조건, stop condition, claim boundary | High | locked 실행 전 문서 revert |
| `HD-LOCKED-RETRIEVAL-002` | `HD-LOCKED-RETRIEVAL-001` | locked retrieval readiness dry-run runner 완료 | target resolvability, expected route/candidate count, locked metric execution 0 | High | runner/report revert |
| `HD-LOCKED-RETRIEVAL-003` | `HD-LOCKED-RETRIEVAL-002` | locked retrieval paired comparison 실행 여부 승인 | stop condition 재확인, 실행 승인서 | High | locked 실행 전 문서 revert |
| `HD-LOCKED-RETRIEVAL-004` | `HD-LOCKED-RETRIEVAL-003` | locked retrieval paired comparison runner 실행 | paired metric, bootstrap CI, public-safe summary | High | private result 폐기, public summary revert |

## Claim Boundary

허용 표현:

- active routing 적용 여부 판단 계획을 수립했다.
- 현재 active route는 적용하지 않는다.
- `relationship` hybrid route는 shadow evaluation 후보로 제한한다.
- active route shadow evaluation은 dev 70에서 실행했고, active route는 여전히 적용하지 않았다.
- `/api/v1/chat` active route flag dry-run contract를 추가했고, `active_route_applied_count=0`을 유지했다.
- locked retrieval 검증 승인 계획을 추가했고, locked test는 아직 실행하지 않았다.
- locked retrieval readiness를 추가했고, retrieval execution과 Solar Pro 3 호출은 0회로 유지했다.
- locked retrieval execution approval을 추가했고, bootstrap과 confidence interval 기준을 고정했다.
- HyDE와 place_story guarded boost는 active route 후보에서 제외했다.

금지 표현:

- active routing으로 성능이 개선됐다.
- router가 production에 적용됐다.
- active route flag를 기본 활성화했다.
- locked test에서 최종 개선을 입증했다.
- Solar Pro 3 답변 품질이 route 변경으로 개선됐다.
- GraphRAG, RAPTOR, HyDE가 최종 route로 채택됐다.

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- classifier와 guard는 dev-only 기준이다.
- relationship route는 retrieval metric 중심이며 generation 품질까지 검증하지 않았다.
- active 적용 시 latency와 운영 복잡도가 증가한다.
- locked test를 실행하기 전까지 최종 개선 claim은 금지해야 한다.
