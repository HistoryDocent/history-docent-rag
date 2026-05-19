# Portfolio Result Summary

## 결론

이 프로젝트의 포트폴리오 메시지는 “최신 RAG 기법을 많이 붙였다”가 아니다.

핵심은 한국사 도서 parser 결과를 citation 가능한 RAG corpus로 정리하고, 청킹, retrieval, reranker, query rewrite, evidence packing, generation, GraphRAG-lite, RAPTOR-lite, query type router, API dry-run, route guard, guarded route API 관찰 필드, 실패 사례 10개, targeted chunk audit, HyDE readiness, HyDE live 비교, HyDE larger readiness, HyDE larger live 비교, active route shadow evaluation, active route flag dry-run contract, locked retrieval 검증 승인 계획, locked retrieval readiness, locked retrieval execution approval, locked retrieval paired comparison을 같은 평가 원칙으로 비교해 채택, 보류, 기각을 분리했다는 점이다.

이 문서는 public-safe 요약이다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 최종 현재 Stack

| layer | current choice | 판단 |
| --- | --- | --- |
| source | Upstage Parser 결과 정규화 | parser quality와 block schema gate 통과 |
| chunking | `C0 current parent-child` | C1-C6 비교 후 유지 |
| base retrieval | `dense_multilingual_e5_small_voice_rewrite` | dev 70 기준 non-rerank 기본 후보 |
| relationship route | `hybrid_weighted_e5_small_alpha_0_5` | relationship 전용 route 후보 |
| evidence packing | `P0_rank_order` | citation recoverability 1.000000 |
| generation | `solar-generation-baseline-v1` | repaired v2는 citation recall 하락으로 기본값 기각 |
| API | FastAPI `/api/v1/chat` contract + retrieval-backed smoke | live service 품질 주장이 아니라 contract 검증 |
| classifier/router | `deterministic_query_type_classifier_v1` + `query_type_router_v1` + API dry-run + relationship guard + guarded route candidate | classifier와 guard 판단은 응답에 노출하지만 production routing 주장은 아님 |
| active routing | 미적용 | API flag dry-run contract 완료, default enable 금지 |
| locked retrieval | 실행 완료 | relationship hybrid는 locked에서 개선 주장 보류 |

## 핵심 정량 결과

| stage | candidate | scope | key metric | value | decision |
| --- | --- | --- | --- | ---: | --- |
| chunking | `C0 current parent-child` | dev 70, BM25 fixed | Recall@5 | 0.566667 | adopt |
| dense retrieval | `dense_multilingual_e5_small` | dev 70 | Recall@5 | 0.733333 | base candidate |
| dense retrieval | `dense_bge_m3` | dev 70 | Recall@5 | 0.800000 | quality ceiling, latency trade-off |
| hybrid | `hybrid_weighted_e5_small_alpha_0_5` | dev 70 | Recall@5 | 0.783333 | route candidate, not global default |
| reranker | `bge-reranker-v2-m3 top20` | dev 70 | latency_p95_ms | 13140.690300 | reject default |
| query rewrite | `dense_multilingual_e5_small_voice_rewrite` | dev 70 | Recall@5 | 0.850000 | adopt retrieval candidate |
| query rewrite | `dense_multilingual_e5_small_voice_rewrite` | dev 70 | nDCG@5 | 0.615293 | adopt retrieval candidate |
| evidence packing | `P0_rank_order` | dev 70 | citation_recoverability | 1.000000 | adopt |
| generation v2 repair | `solar-generation-v2-repaired` | live dev subset 7 | citation_recall_delta | -0.027778 | reject default |
| place_story route | `place_story_guarded_boost_v1` | locked readiness 5 | selected_candidate_count | 0 | reject production route |
| GraphRAG-lite | `entity_path_v1` | relationship dev 10 | nDCG@5 delta | -0.002056 | reject default |
| RAPTOR-lite | `summary_node_v1` | overview/place_story dev 20 | nDCG@5 delta | -0.029969 | reject default |
| router skeleton | `query_type_router_v1` | contract-only | route_policy_count | 3 | implemented |
| query type classifier | `deterministic_query_type_classifier_v1` | dev 70 | macro_f1 | 0.956818 | implemented baseline |
| classifier failure analysis | `deterministic_query_type_classifier_v1` | dev 70 | route_risk_failure_count | 2 | dry-run before active route |
| classifier/router dry-run | `chat-classifier-router-dry-run-v1` | API contract + fixture retrieval | active_route_applied_count | 0 | implemented dry-run |
| relationship route guard | `relationship-route-guard-v1` | dev 70 | false_hybrid_route_count | 2 -> 0 | implemented guard |
| guarded route dry-run | `guarded_route_candidate` | API contract + fixture retrieval | guard_applied_count | 1 | implemented dry-run |
| portfolio failure analysis | `HD-PORTFOLIO-002` | public-safe summary | case_count | 10 | implemented |
| targeted chunk audit | `HD-CHUNK-AUDIT-001` | dev-only single case | chunk_boundary_defect_count | 0 | do not reopen global chunking |
| HyDE readiness | `HD-HYDE-001A` | dev-readiness-only | expected_hyde_generation_live_call_count | 4 | ready for live approval |
| HyDE live comparison | `HD-HYDE-001B` | live-dev-subset 5 | Recall@5 delta | 0.250000 | larger eval 후보 유지 |
| HyDE larger readiness | `HD-HYDE-001C` | dev-readiness-only 40 | expected_hyde_generation_live_call_count | 30 | ready for larger live approval |
| HyDE larger live comparison | `HD-HYDE-001D` | live-dev-subset 40 | MRR delta | -0.035000 | reject default |
| active routing decision | `HD-API-ROUTER-003` | plan-only | active_route_applied_count | 0 | shadow eval completed |
| active route shadow evaluation | `HD-API-ROUTER-004` | dev 70 | MRR delta | 0.013888 | ready for API flag dry-run |
| active route flag dry-run | `HD-API-ROUTER-005` | API contract + fixture retrieval | active_route_flag_applied_count | 0 | implemented dry-run |
| locked retrieval validation plan | `HD-LOCKED-RETRIEVAL-001` | plan-only | locked_test_execution_count | 0 | ready for readiness dry-run |
| locked retrieval readiness | `HD-LOCKED-RETRIEVAL-002` | readiness-only | target_resolvability_fail_count | 0 | ready for execution approval |
| locked retrieval execution approval | `HD-LOCKED-RETRIEVAL-003` | approval-only | planned_bootstrap_iteration_count | 10000 | ready for user approval |
| locked retrieval paired comparison | `HD-LOCKED-RETRIEVAL-004` | locked test 35 | MRR delta | -0.100000 | keep shadow without improvement claim |

## 채택, 보류, 기각

| status | 대상 | 이유 |
| --- | --- | --- |
| 채택 | `C0 current parent-child` | 청킹 후보 C1-C6이 C0를 넘지 못하거나 gate 실패 |
| 채택 | `dense_multilingual_e5_small_voice_rewrite` | Recall@5, MRR, nDCG@5 균형이 가장 좋음 |
| 채택 | `P0_rank_order` | P3 개선폭이 작고 generation 품질 개선으로 연결되지 않음 |
| 구현 | `query_type_router_v1` skeleton | relationship/no_answer/default route branch를 contract로 고정 |
| 구현 | `deterministic_query_type_classifier_v1` | dev 70에서 macro F1과 route policy accuracy gate 통과 |
| 구현 | `relationship-route-guard-v1` | false hybrid route를 줄였지만 active route 적용은 보류 |
| 구현 | `guarded_route_candidate` | guard 결과를 API 응답에서 관찰하되 active route에는 적용하지 않음 |
| 구현 | `PORTFOLIO_FAILURE_ANALYSIS` | 실패 10건을 public-safe category로 분류하고 전역 청킹 재실험 보류 판단 |
| 구현 | `HD-CHUNK-AUDIT-001` | `place_story` 1건에서 target child/parent chunk 존재를 확인하고 전역 재청킹을 열지 않음 |
| 구현 | `HD-HYDE-001A` | HyDE live 비교 전 subset, call budget, no-answer guard를 고정 |
| 구현 | `HD-HYDE-001C` | dev 40개 확대 live 비교 전 query type 범위, call budget, no-answer guard를 고정 |
| 구현 | `HD-API-ROUTER-003` | active routing을 바로 적용하지 않고 relationship route만 shadow 후보로 고정 |
| 구현 | `HD-API-ROUTER-004` | relationship route shadow 평가를 통과했지만 active route default enable은 보류 |
| 구현 | `HD-API-ROUTER-005` | `active_route_mode=shadow`를 추가했지만 actual retrieval route 적용은 0건으로 유지 |
| 구현 | `HD-LOCKED-RETRIEVAL-001` | locked test를 실행하지 않고 승인 조건, 후보, stop condition, data mart grain을 먼저 고정 |
| 구현 | `HD-LOCKED-RETRIEVAL-002` | locked test metric 실행 없이 target resolvability, route/candidate count, CUDA device를 확인 |
| 구현 | `HD-LOCKED-RETRIEVAL-003` | bootstrap 10000회, 95% CI, stop condition, data mart grain을 실행 전 고정 |
| 구현 | `HD-LOCKED-RETRIEVAL-004` | locked 35개에서 relationship hybrid가 MRR/nDCG 개선을 입증하지 못해 active route 개선 주장을 보류 |
| 보류 | `HD-HYDE-001B` | live-dev-subset에서 Recall@5는 올랐지만 MRR 하락과 latency 증가가 있어 larger eval 후보로만 유지 |
| 기각 | `HD-HYDE-001D` | 40개 확대 live 비교에서 Recall@5는 소폭 상승했지만 MRR, nDCG@5, latency가 악화되어 기본 route로 채택하지 않음 |
| 보류 | BGE-M3 dense | Recall@5는 높지만 latency가 커서 기본값 부적합 |
| 보류 | BGE reranker | 품질 상한은 높지만 CPU p95 latency가 API 기본값으로 부적합 |
| 기각 | GraphRAG-lite relationship 기본값 | hybrid reference 대비 nDCG@5 개선 없음 |
| 기각 | RAPTOR-lite overview/place_story 기본값 | baseline 대비 Recall/MRR 개선 없음, nDCG@5 하락 |
| 기각 | Solar Pro 3 repaired v2 기본값 | citation precision은 올랐지만 citation recall 하락 |
| 기각 | place_story guarded boost production route | locked readiness에서 candidate 선택 0건 |

## 면접에서 말할 핵심 문장

```text
도서 parser output을 citation 가능한 RAG corpus로 재구성하고, BM25부터 neural dense, hybrid, reranker, query rewrite, evidence packing, generation contract, GraphRAG-lite, RAPTOR-lite, query type classifier/router, API dry-run, route guard, guarded route API 관찰 필드, 실패 사례 10개, targeted chunk audit, HyDE readiness와 HyDE live 비교, active route shadow evaluation, active route flag dry-run contract, locked retrieval 검증 승인 계획, readiness, execution approval, paired comparison까지 단계별로 검증했습니다. 작은 subset의 좋은 수치를 바로 채택하지 않고, HyDE를 40개 dev live 비교로 확장한 뒤 MRR과 nDCG 하락 때문에 기본 route에서 기각했고, relationship route도 locked 35개에서 MRR delta=-0.100000으로 개선 주장을 보류한 과정을 포트폴리오 핵심으로 정리했습니다.
```

## Claim Boundary

허용 표현:

- dev 기준으로 `dense_multilingual_e5_small_voice_rewrite`가 현재 non-rerank 기본 후보다.
- relationship query에서는 hybrid weighted E5 route 후보가 있다.
- GraphRAG-lite는 이번 relationship input-only 비교에서 기본값으로 승격하지 않았다.
- RAPTOR-lite는 이번 overview/place_story input-only 비교에서 기본값으로 승격하지 않았다.
- public repo에는 저작권 원문과 private eval payload를 포함하지 않았다.
- API는 contract와 retrieval-backed smoke까지 검증했다.
- query type classifier baseline은 dev 기준 macro F1 0.956818을 기록했다.
- classifier failure analysis에서 no-answer 오분류는 0건이지만 false hybrid route 2건이 남았다.
- `/chat` classifier/router dry-run은 연결됐지만 active route 적용은 0건이다.
- relationship route guard는 dev 기준 false hybrid route를 2건에서 0건으로 줄였지만 active route에는 적용하지 않았다.
- `/chat` guarded route candidate는 연결됐지만 active route 적용은 0건이다.
- 실패 사례 10개를 public-safe 방식으로 분류했다.
- `place_story` 1건 targeted audit에서 target child/parent chunk 존재를 확인했고, 현재 증거로는 전체 청킹 재실험을 열지 않는 것이 적절하다.
- HyDE live 비교 전 subset, call budget, no-answer guard를 고정했고 readiness 단계에서 Solar Pro 3 호출은 0회다.
- HyDE live-dev-subset 5개에서 Solar Pro 3 호출 4회로 paired retrieval 비교를 실행했고, Recall@5 delta는 0.250000이다.
- HyDE live 비교에서 no-answer 1개는 generation과 retrieval을 모두 차단했다.
- HyDE larger dev readiness에서 40개 query와 예상 Solar Pro 3 호출 30회를 고정했고, no-answer 10개는 차단했다.
- HyDE larger live 비교에서 Solar Pro 3 호출 30회로 paired retrieval 비교를 실행했고, Recall@5 delta는 0.033333이지만 MRR delta는 -0.035000, nDCG@5 delta는 -0.018384라 기본 route로 채택하지 않았다.
- active route shadow evaluation에서 dev 70개 paired 비교를 실행했고, false_hybrid_route_count=0, no_answer_candidate_route_count=0, MRR delta=0.013888, relationship Recall@5 delta=0.200000을 기록했다.
- `/chat` active route flag dry-run contract에서 `active_route_mode=shadow`를 검증했고, active_route_flag_applied_count=0과 default_enabled=0을 유지했다.
- locked retrieval 검증 승인 계획에서 planned_locked_query_count=35, locked_test_execution_count=0, solar_call_count=0으로 실행 전 조건을 고정했다.
- locked retrieval readiness에서 target_resolvability_fail_count=0, no_answer_candidate_route_count=0, retrieval_execution_count=0, solar_call_count=0을 확인했다.
- locked retrieval execution approval에서 planned_bootstrap_iteration_count=10000, confidence_interval_percent=95, locked_metric_result_count=0을 고정했다.
- locked retrieval paired comparison에서 relationship subset 5개 기준 MRR delta=-0.100000, nDCG@5 delta=-0.073814, 95% CI=[-0.300000, 0.000000]을 기록해 active route 개선 주장을 보류했다.

금지 표현:

- production 성능 검증 완료
- locked test에서 최종 성능 개선 입증
- GraphRAG 적용으로 성능 개선
- RAPTOR 적용으로 성능 개선
- 음성 관광 앱 완성
- Solar Pro 3 generation 품질 최종 개선
- HyDE 최종 retrieval 성능 개선
- HyDE production route 채택
- query type classifier production 검증 완료
- relationship active route production 적용 완료
- active route flag 기본 활성화 완료
- 전체 도서 데이터 공개

## 다음 작업

| priority | work_id | 이유 |
| ---: | --- | --- |
| 1 | `HD-PORTFOLIO-REHEARSAL-001` | 제출 전 3분 설명, 기각 후보 설명, 금지 claim 회피 리허설 |

## 외부 감사 결론

현재 포트폴리오 메시지는 타당하다.

다만 “성능 개선”보다 “평가 기반 의사결정”을 강조해야 한다. HyDE도 40개 확대 live 비교에서 기본값으로 기각했고 active routing도 shadow 평가 후 바로 켜지 않았으며 locked retrieval paired comparison에서도 relationship hybrid 개선 주장을 보류했다. 최종 제출 문구에서는 좋은 수치보다 채택하지 않은 이유를 같이 써야 한다. `HD-PORTFOLIO-DEMO-001`과 `HD-SUBMISSION-REFRESH-001`은 완료됐으므로 다음 단계는 portfolio submission rehearsal이다.
