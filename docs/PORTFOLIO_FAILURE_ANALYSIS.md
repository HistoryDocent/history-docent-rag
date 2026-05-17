# Portfolio Failure Analysis

## 결론

전체 청킹 비교 테스트를 다시 열지 않는다.

현재 10개 실패 사례 중 전역 청킹 재설계가 필요한 증거는 없다. `chunk_boundary_risk` 1건은 `HD-CHUNK-AUDIT-001`로 별도 확인했고, target child/parent chunk가 존재해 전역 재청킹 근거가 아니었다. HyDE 비용성 실험은 5개 live-dev-subset에서 후보성을 확인했지만, larger eval 전 최종 개선으로 주장하지 않는다.

이 문서는 public-safe failure analysis다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| case_count | 10 |
| unique_query_count | 10 |
| high_risk_count | 2 |
| medium_risk_count | 7 |
| low_risk_count | 1 |
| chunk_boundary_audit_candidate_count | 1 |
| query_type_misroute_count | 3 |
| retrieval_miss_count | 4 |
| generation_contract_gap_count | 1 |
| no_answer_risk_count | 1 |
| reopen_global_chunking_count | 0 |
| next_hyde_candidate_count | 6 |
| live_solar_call_count_for_this_report | 0 |
| cuda_required | false |

## Category Breakdown

| primary_failure_category | count |
| --- | ---: |
| `retrieval_miss` | 4 |
| `query_type_misroute` | 3 |
| `chunk_boundary_risk` | 1 |
| `generation_contract_gap` | 1 |
| `no_answer_risk` | 1 |

## Stage Breakdown

| pipeline_stage | count |
| --- | ---: |
| `query_type_classifier` | 3 |
| `retrieval` | 3 |
| `chunking_retrieval_generation` | 1 |
| `generation` | 1 |
| `retrieval_generation_contract` | 1 |
| `retrieval_router` | 1 |

## Failure Cases

| case_id | query_id | query_type | stage | primary_failure_category | risk | observed_signal | next_action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pf-failure-001` | `q-dev-place-fact-004` | `place_fact` | `query_type_classifier` | `query_type_misroute` | `medium` | place_fact가 relationship으로 분류되어 route policy가 바뀐 사례 | active route 적용 전 guarded route dry-run 결과를 더 누적한다. |
| `pf-failure-002` | `q-dev-overview-009` | `overview` | `query_type_classifier` | `query_type_misroute` | `medium` | overview가 relationship으로 분류되어 hybrid route로 이동할 수 있는 사례 | relationship route는 score margin과 관계 표현 guard를 함께 요구한다. |
| `pf-failure-003` | `q-dev-place-fact-009` | `place_fact` | `query_type_classifier` | `query_type_misroute` | `low` | default route 내부 query type 경계가 흐린 사례 | classifier label 개선은 active route보다 후순위로 둔다. |
| `pf-failure-004` | `q-dev-place-story-001` | `place_story` | `chunking_retrieval_generation` | `chunk_boundary_risk` | `high` | target doc은 잡지만 target child와 parent grain이 빠지고 generation regression도 동반된 사례 | HD-CHUNK-AUDIT-001 결과 전역 재청킹은 열지 않고 HyDE/retrieval 실험으로 넘긴다. |
| `pf-failure-005` | `q-dev-route-context-009` | `route_context` | `retrieval` | `retrieval_miss` | `medium` | route_context query에서 target child miss가 남은 사례 | route_context는 HyDE보다 route-level query rewrite와 packing audit을 먼저 비교한다. |
| `pf-failure-006` | `q-dev-place-story-008` | `place_story` | `retrieval` | `retrieval_miss` | `medium` | current retrieval 후보에서 target doc까지 miss한 hard case | HyDE 또는 place-aware rewrite 후보를 place_story hard subset에서만 비교한다. |
| `pf-failure-007` | `q-dev-relationship-008` | `relationship` | `retrieval_router` | `retrieval_miss` | `medium` | global dense candidate에서는 relationship target miss가 남은 사례 | HyDE relationship subset은 hybrid reference와 paired comparison으로만 연다. |
| `pf-failure-008` | `q-dev-overview-010` | `overview` | `retrieval` | `retrieval_miss` | `medium` | overview query에서 target doc miss가 남고 RAPTOR-lite도 기본값으로 승격하지 못한 사례 | HyDE overview subset은 RAPTOR-lite reference와 함께 비교한다. |
| `pf-failure-009` | `q-dev-relationship-001` | `relationship` | `generation` | `generation_contract_gap` | `medium` | repaired v2에서 citation recall regression이 발생한 사례 | generation prompt 수정은 citation recall gate를 먼저 통과해야 한다. |
| `pf-failure-010` | `q-dev-no-answer-001` | `no_answer` | `retrieval_generation_contract` | `no_answer_risk` | `high` | retriever 단독으로는 no-answer query에도 후보가 생길 수 있는 사례 | HyDE 실험 전 no-answer hallucination guard를 고정한다. |

## 판단

청킹은 `C0 current parent-child`를 유지한다. 실패 10건 중 청킹 자체가 원인으로 강하게 확인된 사례는 없다. `q-dev-place-story-001`은 target doc은 잡지만 child/parent grain을 놓치는 사례였고, targeted audit 결과 target child/parent는 chunk artifact에 존재했다. 따라서 전역 청킹 변경 근거는 아니다.

Retrieval 실패는 `place_story`, `relationship`, `overview`, `route_context`에 분포한다. 이 문제는 청킹 후보를 다시 늘리는 것보다 query type route, HyDE subset, hard-case retrieval audit으로 분리해야 한다.

Generation 실패는 Solar Pro 3 repaired v2의 기본값 승격을 막는 근거다. citation precision 개선만으로 채택하지 않고 citation recall, correctness, unsupported claim risk를 같이 봐야 한다.

No-answer는 검색기 단독으로는 후보를 반환할 수 있으므로 retrieval metric과 answer abstain contract를 분리해서 봐야 한다.

## 다음 작업

| priority | work_id | 작업 | 이유 |
| ---: | --- | --- | --- |
| 1 | `HD-HYDE-001C` | HyDE larger dev subset readiness | 5개 subset 결과만으로는 HyDE 채택 근거가 약하므로 확대 평가 범위와 call budget을 먼저 고정한다. |
| 2 | `HD-API-ROUTER-003` | active routing 적용 판단 계획 | guard dry-run은 완료됐지만 active route 적용은 별도 gate가 필요하다. |

## Claim Boundary

허용 표현:

- 실패 10건을 public-safe 방식으로 분류했다.
- 현재 증거로는 전체 청킹 재실험을 열지 않는 것이 적절하다.
- `place_story` 1건 targeted audit에서 target child/parent chunk 존재를 확인했다.
- HyDE는 5개 live-dev-subset에서 larger eval 후보로 남았지만 아직 최종 개선을 입증하지 않았다.

금지 표현:

- 청킹 문제가 해결됐다.
- HyDE로 성능이 개선됐다.
- locked test 최종 성능 개선을 입증했다.
- production route 품질을 검증했다.
