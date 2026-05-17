# Portfolio Result Summary Report

## 목적

README와 포트폴리오 문구에 사용할 RAG 실험 결과를 public-safe 형태로 압축한다.

이 문서는 성능 개선 주장이 아니다. dev-only, dev-input-only, live-dev-subset, locked-readiness-only 결과를 구분해 제출용 메시지의 claim boundary를 고정한다.

raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `portfolio-result-summary-report/v1` |
| work_id | `HD-PORTFOLIO-001` |
| source_decision_ledger | `docs/RAG_DECISION_LEDGER.md` |
| source_final_ablation_report | `evals/reports/final_ablation_status_report.md` |
| solar_call_count | 0 |
| cuda_required | false |

## 정량 리포트

| metric | value |
| --- | ---: |
| summarized_stage_count | 24 |
| adopted_or_implemented_count | 12 |
| rejected_default_count | 7 |
| held_candidate_count | 3 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| live_solar_call_count_for_this_report | 0 |

## Result Snapshot

| stage | candidate | scope | key_metric | value | portfolio_status |
| --- | --- | --- | --- | ---: | --- |
| chunking | `C0 current parent-child` | dev 70 | Recall@5 | 0.566667 | adopted |
| dense retrieval | `dense_multilingual_e5_small` | dev 70 | Recall@5 | 0.733333 | base candidate |
| dense retrieval | `dense_bge_m3` | dev 70 | Recall@5 | 0.800000 | held quality ceiling |
| hybrid | `hybrid_weighted_e5_small_alpha_0_5` | dev 70 | Recall@5 | 0.783333 | route candidate |
| reranker | `bge-reranker-v2-m3 top20` | dev 70 | latency_p95_ms | 13140.690300 | reject default |
| query rewrite | `dense_multilingual_e5_small_voice_rewrite` | dev 70 | Recall@5 | 0.850000 | adopted candidate |
| evidence packing | `P0_rank_order` | dev 70 | citation_recoverability | 1.000000 | adopted |
| generation v2 repair | `solar-generation-v2-repaired` | live dev subset 7 | citation_recall_delta | -0.027778 | reject default |
| place_story router | `place_story_guarded_boost_v1` | locked readiness 5 | selected_candidate_count | 0 | reject production route |
| GraphRAG-lite | `entity_path_v1` | relationship dev 10 | nDCG@5 delta | -0.002056 | reject default |
| GraphRAG-lite | `community_hint_v1` | relationship dev 10 | nDCG@5 delta | -0.030337 | reject default |
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
| HyDE live comparison | `HD-HYDE-001B` | live-dev-subset 5 | Recall@5 delta | 0.250000 | held for larger eval |
| HyDE larger readiness | `HD-HYDE-001C` | dev-readiness-only 40 | expected_hyde_generation_live_call_count | 30 | ready for larger live approval |
| HyDE larger live comparison | `HD-HYDE-001D` | live-dev-subset 40 | MRR delta | -0.035000 | reject default |

## 정성 리포트

- `portfolio_scope`: README 첫 화면에서 현재 stack, 실험 결과, 채택/기각 이유, claim boundary를 먼저 보이게 한다.
- `decision_quality`: 좋은 수치만 선택하지 않고 latency, citation recall, nDCG 하락, locked readiness, HyDE MRR 하락을 기준으로 기각하거나 보류한 과정을 강조한다.
- `retrieval_message`: BM25에서 neural dense, hybrid, reranker, query rewrite로 확장했지만 최종 기본 후보는 균형이 가장 좋은 dense voice rewrite로 둔다.
- `advanced_rag_message`: GraphRAG-lite와 RAPTOR-lite는 특정 query type에 한정해 비교했고 개선이 없어 기본값에서 제외했다.
- `router_message`: query type classifier baseline, router skeleton, API dry-run, relationship guard, guarded route candidate는 구현됐지만 production routing과 locked 성능 개선은 아직 없다.
- `security_boundary`: public README와 docs에는 저작권 원문, private eval payload, secret을 넣지 않는다.
- `claim_boundary`: production 성능, locked 개선, 통계적 유의성 표현은 금지한다.
- `external_audit`: 실패 원인표와 targeted audit으로 청킹 재실험 범위를 닫았고 HyDE larger live 비교도 완료했다. Recall@5만 보고 채택하지 않고 MRR, nDCG@5, latency 악화를 기준으로 기본 route를 기각한 판단이 타당하다.

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 24 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 채택 판단

`HD-PORTFOLIO-001`은 문서 gate로 통과한다.

README 첫 화면에는 다음이 보여야 한다.

- 프로젝트 목적
- 현재 RAG stack
- 핵심 실험 결과 표
- 채택/보류/기각 판단
- public 데이터 정책
- claim boundary

## 금지 문구

- production 성능 검증 완료
- locked test 개선 입증
- GraphRAG로 성능 개선
- RAPTOR로 성능 개선
- 음성 관광 앱 완성
- Solar Pro 3 품질 최종 개선
- 원본 도서 데이터 공개
