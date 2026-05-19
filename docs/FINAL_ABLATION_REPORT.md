# Final Ablation Report

## 결론

현재 제출용 RAG 기본선은 `C0 parent-child chunking + dense_multilingual_e5_small_voice_rewrite + P0_rank_order + Solar Pro 3 generation v1`이다.

이 결론은 "최종 성능 개선 입증"이 아니다. dev, live-dev-subset, locked retrieval-only 결과를 분리해 어떤 후보를 채택, 보류, 기각했는지 정리한 public-safe 최종 ablation 판단이다.

`relationship_hybrid_weighted_e5_v1`는 dev shadow에서는 유망했지만 locked relationship subset에서 MRR과 nDCG@5가 하락했으므로 active route 기본값으로 올리지 않는다. GraphRAG-lite, RAPTOR-lite, HyDE도 이번 기준에서는 기본값으로 채택하지 않는다.

이 문서는 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다.

## 최종 기본 Stack

| layer | selected | 최종 판단 |
| --- | --- | --- |
| source normalization | Upstage Parser 결과 정규화 | 유지 |
| chunking | `C0 current parent-child` | 채택 |
| retrieval | `dense_multilingual_e5_small_voice_rewrite` | dev 기준 non-rerank 기본 후보 |
| relationship route | `relationship_hybrid_weighted_e5_v1` | shadow only, locked 개선 주장 금지 |
| evidence packing | `P0_rank_order` | 채택 |
| generation | `solar-generation-baseline-v1` | 유지 |
| query type classifier | `deterministic_query_type_classifier_v1` | dev baseline, production claim 금지 |
| active routing | none | dry-run/flag/shadow까지만 유지 |
| GraphRAG-lite | none | 기본값 기각 |
| RAPTOR-lite | none | 기본값 기각 |
| HyDE | none | 기본 retrieval route 기각 |

## 정량 요약

| stage | candidate | scope | primary metric | value | decision |
| --- | --- | --- | --- | ---: | --- |
| chunking | `C0 current parent-child` | dev 70, BM25 fixed | Recall@5 | 0.566667 | adopt |
| chunking | `C1 smaller child` | dev 70, BM25 fixed | Recall@5 | 0.083333 | reject |
| dense retrieval | `dense_multilingual_e5_small` | dev 70 | Recall@5 | 0.733333 | base candidate |
| dense retrieval | `dense_bge_m3` | dev 70 | Recall@5 | 0.800000 | quality ceiling |
| hybrid | `hybrid_weighted_e5_small_alpha_0_5` | dev 70 | Recall@5 | 0.783333 | route candidate |
| reranker | `bge-reranker-v2-m3 top20` | dev 70 | latency_p95_ms | 13140.690300 | reject default |
| query rewrite | `dense_multilingual_e5_small_voice_rewrite` | dev 70 | Recall@5 | 0.850000 | adopt candidate |
| query rewrite | `dense_multilingual_e5_small_voice_rewrite` | dev 70 | nDCG@5 | 0.615293 | adopt candidate |
| evidence packing | `P0_rank_order` | dev 70 | citation_recoverability | 1.000000 | adopt |
| generation v2 repair | `solar-generation-v2-repaired` | live dev subset 7 | citation_recall_delta | -0.027778 | reject default |
| GraphRAG-lite | `entity_path_v1` | relationship dev 10 | nDCG@5 delta | -0.002056 | reject default |
| RAPTOR-lite | `summary_node_v1` | overview/place_story dev 20 | nDCG@5 delta | -0.029969 | reject default |
| query type classifier | `deterministic_query_type_classifier_v1` | dev 70 | macro_f1 | 0.956818 | implemented baseline |
| relationship route guard | `relationship-route-guard-v1` | dev 70 | false_hybrid_route_count | 2 -> 0 | implemented guard |
| HyDE live comparison | `HD-HYDE-001B` | live-dev-subset 5 | Recall@5 delta | 0.250000 | larger eval 후보 유지 |
| HyDE larger live comparison | `HD-HYDE-001D` | live-dev-subset 40 | MRR delta | -0.035000 | reject default |
| active route shadow evaluation | `HD-API-ROUTER-004` | dev 70 | MRR delta | 0.013888 | shadow only |
| active route flag dry-run | `HD-API-ROUTER-005` | API contract + fixture retrieval | active_route_flag_applied_count | 0 | dry-run only |
| locked retrieval paired comparison | `HD-LOCKED-RETRIEVAL-004` | locked test 35 | MRR delta | -0.100000 | keep shadow without improvement claim |
| locked retrieval paired comparison | `HD-LOCKED-RETRIEVAL-004` | locked relationship 5 | nDCG@5 delta | -0.073814 | reject active route claim |

## 정성 판단

`C0 current parent-child`는 C1-C6 비교에서 가장 안정적인 기준선이었다. C4와 C6은 gate를 통과하지 못했고, C1/C2/C3/C5는 C0를 넘지 못했다. 따라서 지금 전역 청킹을 다시 여는 것은 이후 retrieval, packing, generation 결과를 모두 무효화할 위험이 크다.

Dense retrieval은 `dense_multilingual_e5_small` 계열이 실서비스 후보로 가장 균형적이다. BGE-M3는 Recall@5가 더 높지만 latency가 더 크므로 품질 상한 후보로만 둔다.

Hybrid retrieval은 전체 기본값으로는 충분하지 않다. `hybrid_weighted_e5_small_alpha_0_5`는 dev에서 Recall@5를 올렸지만 top-rank 품질과 latency trade-off가 있었다. relationship query 전용 후보로만 다루는 것이 맞다.

Reranker는 품질 상한을 보여줬지만 CPU p95 latency가 API 기본값으로 받아들이기 어렵다. 포트폴리오에서는 "품질은 올릴 수 있지만 latency 때문에 기본값으로 기각했다"는 판단이 더 설득력 있다.

Query rewrite는 이번 프로젝트의 가장 강한 실용적 개선 축이다. 짧은 음성형 질문과 지시어가 많은 관광 도슨트 사용 맥락에서 `dense_multilingual_e5_small_voice_rewrite`가 전체 균형을 가장 잘 맞췄다.

Evidence packing은 P0를 유지한다. P3가 duplicate parent rate를 조금 낮췄지만 generation 품질 개선으로 연결됐다는 근거가 부족하다.

Solar Pro 3 generation v2 repaired는 citation precision을 개선했지만 citation recall을 낮췄다. 관광 도슨트에서 근거 누락은 위험하므로 기본값으로 채택하지 않는다.

GraphRAG-lite는 relationship 질문만 대상으로 비교했지만 기존 hybrid reference보다 나은 증거가 없었다. RAPTOR-lite도 overview/place_story에서 기준선을 넘지 못했다. 둘 다 "구현해봤다"가 아니라 "특정 질문군에 한정해 실험했고 기본값에서 제외했다"로 설명해야 한다.

HyDE는 5개 live-dev-subset에서 Recall@5가 올랐지만 MRR 하락과 latency 증가가 있었다. 40개 확대 live 비교에서는 MRR, nDCG@5, latency가 악화되어 기본 retrieval route에서 기각한다.

Active routing은 아직 기본 활성화하지 않는다. shadow evaluation과 API flag dry-run은 완료했지만 locked retrieval paired comparison에서 relationship hybrid가 개선을 입증하지 못했다.

## 채택, 보류, 기각

| status | 대상 | 이유 |
| --- | --- | --- |
| 채택 | `C0 current parent-child` | 청킹 후보 C1-C6이 C0를 넘지 못하거나 gate 실패 |
| 채택 | `dense_multilingual_e5_small_voice_rewrite` | dev 기준 Recall@5, MRR, nDCG@5 균형 우수 |
| 채택 | `P0_rank_order` | citation recoverability 1.000000, P3 개선폭 제한 |
| 유지 | `solar-generation-baseline-v1` | repaired v2의 citation recall 하락 |
| 보류 | `dense_bge_m3` | 품질 상한은 높지만 latency trade-off 존재 |
| 보류 | `relationship_hybrid_weighted_e5_v1` | dev shadow 후보이나 locked 개선 주장 실패 |
| 기각 | BGE reranker default | p95 latency가 API 기본값으로 부적합 |
| 기각 | GraphRAG-lite default | relationship input-only에서 nDCG@5 개선 없음 |
| 기각 | RAPTOR-lite default | overview/place_story input-only에서 기준선 개선 없음 |
| 기각 | HyDE default | 40개 live 비교에서 MRR, nDCG@5, latency 악화 |
| 기각 | active route default enable | locked paired comparison에서 개선 주장 불가 |

## Claim Boundary

허용 표현:

- dev 기준으로 `dense_multilingual_e5_small_voice_rewrite`가 현재 non-rerank 기본 후보이다.
- locked retrieval paired comparison을 실행했고 relationship route 개선 주장을 보류했다.
- GraphRAG-lite와 RAPTOR-lite는 이번 기준에서 기본값으로 승격하지 않았다.
- HyDE는 확대 live 비교 후 기본 retrieval route로 채택하지 않았다.
- public repo에는 저작권 원문, private eval payload, secret을 포함하지 않았다.

금지 표현:

- production 성능 검증 완료
- locked test에서 최종 성능 개선 입증
- GraphRAG 적용으로 성능 개선
- RAPTOR 적용으로 성능 개선
- HyDE 적용으로 최종 retrieval 성능 개선
- relationship active route production 적용 완료
- 음성 관광 앱 완성
- 전체 도서 데이터 공개

## 포트폴리오 메시지

이 프로젝트의 핵심은 최신 RAG 기법을 많이 붙인 것이 아니다.

핵심은 저작권 원문을 public repo에 올리지 않으면서 도서 parser output을 citation 가능한 RAG corpus로 재구성하고, 청킹, retrieval, reranker, query rewrite, packing, generation, advanced RAG, route guard를 분리 평가해 채택과 기각을 증거 기반으로 판단한 것이다.

면접에서는 다음 흐름으로 설명한다.

```text
도서 parser 결과를 citation 가능한 corpus로 정규화했고, parent-child chunking부터 dense retrieval, hybrid, reranker, query rewrite, evidence packing, Solar Pro 3 answer contract, GraphRAG-lite, RAPTOR-lite, HyDE, query type routing까지 단계별로 비교했습니다. 좋은 수치만 고른 것이 아니라 latency, citation recall, locked split 결과 때문에 여러 후보를 기각했고, 최종 기본선은 C0 chunking + E5-small voice rewrite + P0 packing + Solar Pro 3 v1로 고정했습니다.
```

## 완료 기준

| gate | status | 근거 |
| --- | --- | --- |
| quantitative summary | PASS | 핵심 metric과 decision table 작성 |
| qualitative assessment | PASS | 후보별 채택, 보류, 기각 사유 작성 |
| claim boundary | PASS | 허용/금지 표현 분리 |
| public safety | PASS | raw query, raw answer, raw evidence, prompt, chunk text, private path, secret 미기록 |
| next work clarity | PASS | portfolio QA, voice UI visual QA, portfolio demo runbook, public repository audit refresh 완료 후 다음 단계는 portfolio submission rehearsal |

## 다음 작업

`HD-API-SAMPLE-001`, `HD-PORTFOLIO-QA-001`, ColBERT hard subset, voice UI visual QA, portfolio demo runbook, public repository audit refresh는 완료됐다. 다음 작업은 `HD-PORTFOLIO-REHEARSAL-001`이다.

다음 작업은 새 성능 실험이 아니라 제출용 설명 리허설이다. README 기반 3분 설명, 기각 후보 설명, 금지 claim 회피를 확인한다.
