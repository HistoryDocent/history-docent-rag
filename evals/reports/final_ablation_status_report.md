# Final Ablation Status Report

## 결론

현재 RAG 기본선은 `C0 parent-child chunking + dense_multilingual_e5_small_voice_rewrite + P0_rank_order + Solar Pro 3 generation v1`로 둔다.

GraphRAG-lite와 RAPTOR-lite는 기본값으로 채택하지 않는다. 청킹 비교도 지금 다시 열지 않는다. query type classifier baseline, failure analysis, `/chat` classifier/router dry-run 연결, relationship route guard 평가, guarded route 후보 API dry-run 노출, 포트폴리오 실패 분석 10개 정리, `place_story` targeted chunk audit, HyDE subset readiness, HyDE live paired retrieval comparison, HyDE larger dev subset readiness는 통과했다.

이 문서는 최종 성능 개선 주장이 아니다. public-safe 실험 상태 요약이며 locked test 전까지 모든 수치는 dev-only 또는 live-dev-subset으로 제한한다.

Public artifact에는 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `final-ablation-status-report/v1` |
| source_report_count | 18 |
| decision_row_count | 29 |
| adopted_default_count | 4 |
| rejected_default_count | 11 |
| route_or_router_candidate_count | 6 |
| quality_ceiling_candidate_count | 2 |
| held_larger_eval_candidate_count | 1 |
| raw_text_public_count | 0 |
| private_path_public_count | 0 |
| secret_like_public_count | 0 |

## Current Default Stack

| layer | selected | status |
| --- | --- | --- |
| chunking | `C0 current parent-child` | adopted |
| retrieval | `dense_multilingual_e5_small_voice_rewrite` | adopted as dev retrieval candidate |
| relationship route option | `hybrid_weighted_e5_small_alpha_0_5` | route candidate, not global default |
| reranker | none | rejected as default due latency |
| evidence packing | `P0_rank_order` | adopted |
| generation | `solar-generation-baseline-v1` | maintained |
| query type classifier | `deterministic_query_type_classifier_v1` | implemented baseline, not production claim |
| classifier/router API | `chat-classifier-router-dry-run-v1` | dry-run only, active route unchanged |
| relationship route guard | `relationship-route-guard-v1` | implemented guard, active route unchanged |
| guarded route API field | `guarded_route_candidate` | dry-run only, active route unchanged |
| GraphRAG-lite | none | rejected as default |
| RAPTOR-lite | none | rejected as default |

## Quantitative Snapshot

| stage | candidate | key metric | value | decision |
| --- | --- | --- | ---: | --- |
| chunking | `C0 current parent-child` | Recall@5 | 0.566667 | adopt |
| embedding | `dense_multilingual_e5_small` | Recall@5 | 0.733333 | base candidate |
| embedding | `dense_bge_m3` | Recall@5 | 0.800000 | quality ceiling |
| hybrid | `hybrid_weighted_e5_small_alpha_0_5` | Recall@5 | 0.783333 | route candidate |
| reranker | `dense_multilingual_e5_small_rerank_bge_m3_top20` | latency_p95_ms | 13140.690300 | reject default |
| query_rewrite | `dense_multilingual_e5_small_voice_rewrite` | Recall@5 | 0.850000 | adopt candidate |
| query_rewrite | `dense_multilingual_e5_small_voice_rewrite` | nDCG@5 | 0.615293 | adopt candidate |
| evidence_packing | `P0_rank_order` | citation_recoverability | 1.000000 | adopt |
| generation | `solar-generation-v2-repaired` | citation_recall_delta | -0.027778 | reject default |
| place_story_router | `parent_doc_context_boost_guarded` | citation_recall_delta | 0.028571 | keep router candidate |
| graphrag_lite | `graphrag_lite_entity_path_v1` | nDCG@5 delta | -0.002056 | reject default |
| graphrag_lite | `graphrag_lite_community_hint_v1` | nDCG@5 delta | -0.030337 | reject default |
| raptor_lite | `raptor_lite_parent_summary_v1` | nDCG@5 delta | -0.074957 | reject default |
| raptor_lite | `raptor_lite_summary_node_v1` | nDCG@5 delta | -0.029969 | reject default |
| query_type_classifier | `deterministic_query_type_classifier_v1` | macro_f1 | 0.956818 | implemented baseline |
| query_type_classifier_failure | `deterministic_query_type_classifier_v1` | route_risk_failure_count | 2 | dry-run before active route |
| chat_classifier_router_dry_run | `chat-classifier-router-dry-run-v1` | classifier_active_route_applied_count | 0 | implemented dry-run |
| relationship_route_guard | `relationship-route-guard-v1` | false_hybrid_route_count | 2 -> 0 | implemented guard |
| chat_guarded_route_dry_run | `guarded_route_candidate` | guard_applied_count | 1 | implemented dry-run |
| portfolio_failure_analysis | `HD-PORTFOLIO-002` | case_count | 10 | implemented |
| place_story_targeted_chunk_audit | `HD-CHUNK-AUDIT-001` | chunk_boundary_defect_count | 0 | do_not_reopen_global_chunking |
| hyde_subset_readiness | `HD-HYDE-001A` | expected_hyde_generation_live_call_count | 4 | ready_for_hyde_live_approval |
| hyde_live_paired_retrieval | `HD-HYDE-001B` | Recall@5 delta | 0.250000 | keep candidate for larger eval |
| hyde_larger_dev_readiness | `HD-HYDE-001C` | expected_hyde_generation_live_call_count | 30 | ready_for_hyde_larger_live_approval |

## Qualitative Assessment

- `chunking`: C0-C6 비교가 이미 완료됐다. C0 외 후보는 metric 또는 gate 조건을 통과하지 못했다.
- `retrieval`: non-rerank 기본 후보는 E5-small voice rewrite가 가장 설득력 있다.
- `relationship`: relationship query에서는 hybrid weighted E5 후보가 강하므로 query-type router 후보로 남긴다.
- `reranker`: 품질 상한은 높지만 CPU latency가 커서 기본값으로 부적합하다.
- `packing`: P0와 P3는 거의 동률이나 P3 개선폭이 작아 기본값을 바꾸지 않는다.
- `generation`: repaired v2는 citation precision과 latency를 개선했지만 citation recall을 떨어뜨려 기본값으로 채택하지 않는다.
- `GraphRAG-lite`: relationship input-only에서 기존 hybrid reference를 넘지 못했다.
- `RAPTOR-lite`: overview/place_story input-only에서 기존 dense voice rewrite reference를 넘지 못했다.
- `classifier`: deterministic baseline은 dev 70개에서 gate를 통과했지만 production routing 검증은 아니다.
- `classifier_failure`: no-answer 오분류는 없지만 false hybrid route 2건이 남아 active route 적용 전 guard가 필요하다.
- `api_dry_run`: `/api/v1/chat`은 classifier/router 판단을 응답에 노출하지만 retrieval route 선택에는 적용하지 않는다.
- `relationship_guard`: dev 70 기준 false hybrid route를 줄였지만 active routing 적용은 아니다.
- `guarded_route_api`: guard 결과는 `/api/v1/chat`의 `guarded_route_candidate`로 관찰 가능하지만 active route에는 적용하지 않는다.
- `portfolio`: 기법 추가보다 실험으로 선택과 기각, 실패 원인 10개를 설명하는 편이 더 강하다.
- `targeted_chunk_audit`: `place_story` 1건에서 target child/parent chunk 존재와 citation provenance를 확인했고 전역 재청킹은 열지 않는다.
- `hyde_readiness`: subset, call budget, no-answer guard를 고정했고 live call은 readiness 단계에서 실행하지 않았다.
- `hyde_live`: live-dev-subset 5개에서 Recall@5 delta는 0.250000이지만 MRR delta는 -0.062500이고 p95 latency가 증가했다. HyDE는 larger eval 후보이지 기본값이 아니다.
- `hyde_larger_readiness`: dev 40개로 확대할 범위와 예상 Solar Pro 3 호출 30회를 고정했고 no-answer 10개는 차단했다.

## Claim Boundary

| claim | allowed? | 조건 |
| --- | --- | --- |
| dev retrieval 후보가 BM25보다 좋았다 | yes | dev-only로 표현 |
| locked test에서 성능 개선 확정 | no | locked test 미실행 |
| GraphRAG가 relationship에서 더 좋다 | no | input-only 결과 개선 없음 |
| RAPTOR가 overview/place_story에서 더 좋다 | no | input-only 결과 개선 없음 |
| Solar Pro 3 v2 repaired가 기본값이다 | no | citation recall 하락 |
| 청킹은 C0로 고정한다 | yes | 현재 실험 흐름 기준 |
| query type classifier baseline이 dev gate를 통과했다 | yes | dev-only로 표현 |
| `/chat` classifier/router dry-run이 연결됐다 | yes | active route 미적용으로 표현 |
| relationship route guard가 false hybrid를 줄였다 | yes | dev-only, active route 미적용으로 표현 |
| `/chat` guarded route candidate가 노출됐다 | yes | dry-run only, active route 미적용으로 표현 |
| query type classifier production 검증 완료 | no | 실제 API 로그와 locked route impact 미검증 |
| HyDE live-dev-subset에서 Recall@5 delta가 양수였다 | yes | 5개 subset, Solar Pro 3 호출 4회, MRR/latency trade-off 동시 표기 |
| HyDE larger dev live 비교 전 범위와 call budget을 고정했다 | yes | readiness-only, Solar Pro 3 호출 0회 |
| HyDE가 최종 retrieval 성능을 개선했다 | no | larger dev/locked test 미검증 |
| production 성능 검증 완료 | no | 배포/운영 검증 없음 |

## Next Gate

다음 gate는 `HD-HYDE-001D HyDE larger dev live paired retrieval comparison`이다.

이유:

- classifier exact accuracy, failure analysis, API dry-run 연결, relationship guard, guarded route dry-run 노출, 포트폴리오 실패 분석 10개는 통과했지만 active routing은 아직 이르다.
- route-risk 오분류 2건은 guard 평가에서 0건으로 줄었지만 dev-only 결과다.
- guarded route 후보도 API dry-run에 노출했으므로 active route 적용 전 관찰 경로는 확보됐다.
- 전체 기본 retrieval 후보와 query type별 강한 후보가 다르다.
- relationship은 hybrid weighted 후보가 강하고, place_story는 guarded boost 후보가 존재한다.
- GraphRAG-lite는 reject됐기 때문에 relationship 개선은 GraphRAG가 아니라 router 판단으로 다뤄야 한다.
- RAPTOR-lite도 reject됐기 때문에 overview/place_story 개선은 classifier와 generation prompt 경계에서 다시 봐야 한다.
- HyDE larger readiness에서 예상 Solar Pro 3 호출 30회와 no-answer guard 10건은 고정됐지만 live 실행은 별도 승인이 필요하다.
- targeted chunk audit은 `place_story` 1건에서 전역 재청킹 근거가 없음을 확인했다.

## External Audit

확인된 주요 문제는 없다.

남은 리스크:

- 대부분 dev split 또는 live-dev-subset 결과다.
- locked test는 아직 최종 성능 주장에 쓰지 않았다.
- Solar Pro 3 live 결과는 호출 수가 제한되어 통계적으로 강한 결론이 아니다.
- HyDE는 larger readiness까지 통과했지만 40개 live 비교와 locked test 전까지 최종 개선으로 주장하면 안 된다.
- classifier/router와 guard는 구현됐고 API에서 관찰 가능하지만 active route 적용은 아직 금지해야 한다.
