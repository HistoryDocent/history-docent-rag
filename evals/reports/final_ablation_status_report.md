# Final Ablation Status Report

## 결론

현재 RAG 기본선은 `C0 parent-child chunking + dense_multilingual_e5_small_voice_rewrite + P0_rank_order + Solar Pro 3 generation v1`로 둔다.

GraphRAG-lite는 relationship 기본값으로 채택하지 않는다. 청킹 비교도 지금 다시 열지 않는다. 다음 우선순위는 query type별 router decision report다.

이 문서는 최종 성능 개선 주장이 아니다. public-safe 실험 상태 요약이며 locked test 전까지 모든 수치는 dev-only 또는 live-dev-subset으로 제한한다.

Public artifact에는 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `final-ablation-status-report/v1` |
| source_report_count | 8 |
| decision_row_count | 18 |
| adopted_default_count | 4 |
| rejected_default_count | 9 |
| route_or_router_candidate_count | 3 |
| quality_ceiling_candidate_count | 2 |
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
| GraphRAG-lite | none | rejected as default |

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

## Qualitative Assessment

- `chunking`: C0-C6 비교가 이미 완료됐다. C0 외 후보는 metric 또는 gate 조건을 통과하지 못했다.
- `retrieval`: non-rerank 기본 후보는 E5-small voice rewrite가 가장 설득력 있다.
- `relationship`: relationship query에서는 hybrid weighted E5 후보가 강하므로 query-type router 후보로 남긴다.
- `reranker`: 품질 상한은 높지만 CPU latency가 커서 기본값으로 부적합하다.
- `packing`: P0와 P3는 거의 동률이나 P3 개선폭이 작아 기본값을 바꾸지 않는다.
- `generation`: repaired v2는 citation precision과 latency를 개선했지만 citation recall을 떨어뜨려 기본값으로 채택하지 않는다.
- `GraphRAG-lite`: relationship input-only에서 기존 hybrid reference를 넘지 못했다.
- `portfolio`: 기법 추가보다 실험으로 선택과 기각을 설명하는 편이 더 강하다.

## Claim Boundary

| claim | allowed? | 조건 |
| --- | --- | --- |
| dev retrieval 후보가 BM25보다 좋았다 | yes | dev-only로 표현 |
| locked test에서 성능 개선 확정 | no | locked test 미실행 |
| GraphRAG가 relationship에서 더 좋다 | no | input-only 결과 개선 없음 |
| Solar Pro 3 v2 repaired가 기본값이다 | no | citation recall 하락 |
| 청킹은 C0로 고정한다 | yes | 현재 실험 흐름 기준 |
| production 성능 검증 완료 | no | 배포/운영 검증 없음 |

## Next Gate

다음 gate는 `HD-ROUTER-001 query-type router decision report`다.

이유:

- 전체 기본 retrieval 후보와 query type별 강한 후보가 다르다.
- relationship은 hybrid weighted 후보가 강하고, place_story는 guarded boost 후보가 존재한다.
- GraphRAG-lite는 reject됐기 때문에 relationship 개선은 GraphRAG가 아니라 router 판단으로 다뤄야 한다.
- RAPTOR-lite와 HyDE는 router baseline을 정리한 뒤 비교해야 변수 통제가 된다.

## External Audit

확인된 주요 문제는 없다.

남은 리스크:

- 대부분 dev split 또는 live-dev-subset 결과다.
- locked test는 아직 최종 성능 주장에 쓰지 않았다.
- Solar Pro 3 live 결과는 호출 수가 제한되어 통계적으로 강한 결론이 아니다.
- query-type router를 정리하지 않으면 포트폴리오에서 “최종 RAG 선택” 설명이 흔들릴 수 있다.
