# Portfolio Result Summary

## 결론

이 프로젝트의 포트폴리오 메시지는 “최신 RAG 기법을 많이 붙였다”가 아니다.

핵심은 한국사 도서 parser 결과를 citation 가능한 RAG corpus로 정리하고, 청킹, retrieval, reranker, query rewrite, evidence packing, generation, GraphRAG-lite, RAPTOR-lite, query type router, API dry-run, route guard, guarded route API 관찰 필드, 실패 사례 10개, targeted chunk audit, HyDE readiness와 HyDE live 비교를 같은 평가 원칙으로 비교해 채택, 보류, 기각을 분리했다는 점이다.

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
| 보류 | `HD-HYDE-001B` | live-dev-subset에서 Recall@5는 올랐지만 MRR 하락과 latency 증가가 있어 larger eval 후보로만 유지 |
| 보류 | BGE-M3 dense | Recall@5는 높지만 latency가 커서 기본값 부적합 |
| 보류 | BGE reranker | 품질 상한은 높지만 CPU p95 latency가 API 기본값으로 부적합 |
| 기각 | GraphRAG-lite relationship 기본값 | hybrid reference 대비 nDCG@5 개선 없음 |
| 기각 | RAPTOR-lite overview/place_story 기본값 | baseline 대비 Recall/MRR 개선 없음, nDCG@5 하락 |
| 기각 | Solar Pro 3 repaired v2 기본값 | citation precision은 올랐지만 citation recall 하락 |
| 기각 | place_story guarded boost production route | locked readiness에서 candidate 선택 0건 |

## 면접에서 말할 핵심 문장

```text
도서 parser output을 citation 가능한 RAG corpus로 재구성하고, BM25부터 neural dense, hybrid, reranker, query rewrite, evidence packing, generation contract, GraphRAG-lite, RAPTOR-lite, query type classifier/router, API dry-run, route guard, guarded route API 관찰 필드, 실패 사례 10개, targeted chunk audit, HyDE readiness와 HyDE live 비교까지 단계별로 검증했습니다. 좋은 수치만 채택하지 않고 latency, citation recall, nDCG 하락, locked readiness와 실패 원인 분류 때문에 후보를 기각하거나 보류한 과정을 포트폴리오 핵심으로 정리했습니다.
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
- 전체 도서 데이터 공개

## 다음 작업

| priority | work_id | 이유 |
| ---: | --- | --- |
| 1 | `HD-HYDE-001C` | HyDE larger dev subset readiness |
| 2 | `HD-API-ROUTER-003` | active routing 적용 여부 판단 계획 |

## 외부 감사 결론

현재 포트폴리오 메시지는 타당하다.

다만 “성능 개선”보다 “평가 기반 의사결정”을 강조해야 한다. HyDE도 live-dev-subset 후보 유지이지 최종 채택이 아니므로, 최종 제출 문구에서는 claim boundary를 같이 써야 한다.
