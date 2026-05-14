# GraphRAG-lite Relationship 실험 계획

## 결론

청킹 비교 테스트는 지금 재개하지 않는다.

다음 실험은 `relationship` 질문 전용 GraphRAG-lite input-only 비교다. 목적은 장소, 인물, 사건, 제도 관계를 찾는 검색 후보가 기존 hybrid/dense reference보다 좋아지는지 확인하는 것이다.

이 문서는 실행 계획이다. GraphRAG-lite 성능 개선, production 채택, GraphRAG 우위 주장이 아니다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | GraphRAG-lite는 기본 pipeline이 아니라 `relationship` 전용 실험군으로 둔다. |
| Retrieval | 기존 relationship reference가 이미 강하므로 Recall@5만 보지 말고 MRR, nDCG@5, citation recoverability를 함께 본다. |
| Generation | graph summary는 답변 citation이 될 수 없다. 최종 citation은 원문 child chunk 기준만 허용한다. |
| Evaluation | 첫 단계는 Solar Pro 3 호출 없는 input-only 비교다. |
| Data warehouse | fact grain은 `plan_id + strategy_id + query_type + metric_family`로 고정한다. |
| Security | raw query, raw evidence, raw answer, chunk text, private path, secret은 public artifact에 기록하지 않는다. |
| Portfolio | GraphRAG를 무조건 적용한 것이 아니라 relationship 실패 유형에 한정해 검증했다는 메시지가 더 강하다. |
| 외부 감사 | 청킹 재실험보다 관계 검색 가설을 분리하는 편이 변수 통제에 맞다. |

## 실험 가설

`relationship` 질문은 단일 장소 설명보다 장소-인물-사건-제도 관계를 함께 찾는 문제가 많다. GraphRAG-lite가 의미 있으려면 그래프 노드나 요약 자체가 아니라, 관련 source child chunk 후보를 더 정확히 끌어올려야 한다.

## 비교 전략

| strategy_id | role | 설명 | citation 정책 |
| --- | --- | --- | --- |
| `hybrid_weighted_e5_small_alpha_0_5_reference` | baseline | 기존 relationship 상위 reference | source child chunk만 허용 |
| `graphrag_lite_entity_path_v1` | candidate | entity mention과 relation hint로 후보 child를 확장 | source child chunk만 허용 |
| `graphrag_lite_community_hint_v1` | candidate | community hint를 retrieval 보조 feature로 사용 | source child chunk만 허용 |

## 정량 Gate

| gate | 기준 |
| --- | --- |
| query type | `relationship` only |
| dev query count | 10 |
| test query count | 5, 후속 locked gate 전까지 미사용 |
| Solar Pro 3 call | 0 |
| raw public text | 0 |
| private path leakage | 0 |
| citation recoverability | 0.990000 이상 |
| Recall@5 delta | +0.030000 이상이면 후보 |
| MRR delta | +0.030000 이상이면 후보 |
| nDCG@5 delta | +0.030000 이상이면 후보 |
| latency p95 | 2500ms 이하를 1차 목표로 기록 |

## 정성 Gate

| 항목 | 기준 |
| --- | --- |
| relationship fidelity | 관계를 만들지 않고 source chunk에서 복구 가능한 후보만 올린다. |
| entity canonicalization | 동일 인물/장소 표기 흔들림을 별도 error tag로 기록한다. |
| graph contamination | graph/community summary를 citation으로 쓰지 않는다. |
| regression boundary | 기존 hybrid/dense reference보다 나빠진 query를 failure tag로 분리한다. |
| claim boundary | dev input-only 결과를 최종 성능 개선으로 표현하지 않는다. |

## Data Mart 설계

`fact_graphrag_lite_relationship_eval`의 grain은 `plan_id + strategy_id + query_id + query_type + metric_family`다.

| field | 설명 |
| --- | --- |
| `plan_id` | GraphRAG-lite relationship 실험 계획 id |
| `strategy_id` | baseline 또는 candidate strategy |
| `query_id` | private eval query id, public report에는 id만 허용 |
| `query_type` | 항상 `relationship` |
| `metric_family` | retrieval, citation, latency, safety, graph_quality |
| `metric_value` | public-safe numeric metric |
| `failure_tag` | sanitized failure tag |
| `claim_boundary` | plan-only, dev-only, locked-only |

free-text query, raw answer, raw evidence, raw prompt, chunk text는 fact에 저장하지 않는다.

## 작업 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-ADV-RAG-001 | HD-SOLAR-027 | GraphRAG-lite relationship 실험 계획과 runner skeleton | 계획 문서, plan report, unit test, Solar call 0, public leakage 0 | Medium | 신규 문서/runner/test revert |
| HD-ADV-RAG-002 | HD-ADV-RAG-001 + 별도 승인 | relationship dev input-only 비교 실행 | Recall@1/3/5, MRR, nDCG@5, latency p95, citation recoverability, 정성 리포트 | High | candidate 미채택, report revert |
| HD-ADV-RAG-003 | HD-ADV-RAG-002 | GraphRAG-lite next gate 판단 | 채택/보류 판단 문서, locked test 오염 방지 | Medium | 판단 문서 revert |

## 다음 승인 후보

다음 작업은 HD-ADV-RAG-002다. 승인 전에는 실제 graph index build와 input-only 비교를 실행하지 않는다.
