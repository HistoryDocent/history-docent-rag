# Place Story Target Grain 및 Top-rank Coverage 개선 계획

## 결론

지금은 청킹 비교 테스트로 바로 돌아가지 않는다.

`place_story` hard-case의 현재 증거는 전체 청킹 실패가 아니라 `target_grain_mismatch`와 낮은 top-rank coverage다. target doc은 검색됐지만 target child와 parent는 빠졌고, doc도 rank 5에 있었다. 따라서 다음 작업은 청킹 재실험이 아니라 `place_story` 평가 target grain을 명확히 하고, retrieval top-rank coverage를 개선할 후보를 분리해서 검증하는 것이다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | 청킹, retrieval, evidence packing, generation prompt를 한 번에 바꾸면 원인 추적이 불가능하다. 이번 단계는 retrieval 입력 품질을 먼저 고정한다. |
| Retrieval | 현재 문제는 target doc이 rank 5에만 들어온 상태다. child/parent coverage와 rank를 먼저 올려야 한다. |
| Evaluation | `place_story`는 서사형 질문이라 child-only 정답 기준이 과도하게 엄격할 수 있다. child, parent, doc grain을 분리해 기록해야 한다. |
| Data warehouse | query 단위 fact에 target grain별 coverage metric을 저장해야 이후 ablation 비교가 가능하다. |
| Security | public 문서에는 raw query, raw evidence, raw answer, private path를 남기지 않는다. |
| Portfolio | 실패 원인을 청킹 탓으로 단정하지 않고 평가 grain과 retrieval 품질을 분해한 과정을 보여주는 것이 더 설득력 있다. |

## 현재 근거

| 항목 | 값 |
| --- | ---: |
| 대상 query | `q-dev-place-story-001` |
| target_child_covered_count | 0 |
| target_parent_covered_count | 0 |
| target_doc_covered_count | 1 |
| target_min_retrieval_rank | 5 |
| target_min_pack_rank | 5 |
| citation_recoverability | 1.000000 |
| evidence_order_relevance_proxy | 0.200000 |
| generation_regression_count | 1 |
| root_cause_decision | `target_grain_mismatch` |

해석:

1. citation 복구성은 깨지지 않았다.
2. 문서 단위로는 관련 corpus에 닿았지만, generation에 직접 쓰기 좋은 child/parent evidence가 빠졌다.
3. v2 prompt repair를 먼저 하면 입력 evidence 품질 문제를 prompt 문제로 오판할 수 있다.

## Target Grain 정책

`place_story` query는 다음 세 grain을 동시에 기록한다.

| grain | 의미 | 평가상 사용 |
| --- | --- | --- |
| child | 답변 citation으로 바로 쓰기 좋은 최소 근거 | strict success |
| parent | 서사 맥락을 제공하는 상위 묶음 | context success |
| doc | 같은 원천 문서에 도달한 약한 신호 | weak success |

채택 기준:

- 최종 `Correct-with-Evidence` 개선 주장은 child 또는 parent coverage 개선이 있어야 한다.
- doc coverage만 개선된 경우 retrieval이 완전히 빗나가지 않았다는 보조 신호로만 사용한다.
- `place_story`는 child strict metric과 parent relaxed metric을 함께 공개하고, 둘 중 하나만 선택해서 성능 개선을 주장하지 않는다.

## 개선 후보

1. `place_story` deterministic rewrite v2
   - 장소 alias, 시대 단서, 서사형 의도 토큰을 query에 추가한다.
   - LLM 호출 없이 reproducible하게 만든다.
   - 측정: `target_child_recall@5`, `target_parent_recall@5`, `MRR`, `nDCG@5`, `latency_p95_ms`.

2. parent/doc context boost
   - parent title, doc title, place alias가 query와 맞는 child candidate에 제한적으로 boost를 준다.
   - target label을 scoring에 사용하지 않는다.
   - 측정: top-3 안에 child 또는 parent가 들어오는지 본다.

3. story-aware evidence packing
   - retrieval 결과가 같은 doc에 낮은 rank로만 닿는 경우 같은 parent/doc의 상위 sibling evidence를 보강 후보로 둔다.
   - citation은 여전히 child 기준으로만 생성한다.
   - 측정: citation recoverability와 duplicate parent rate를 함께 본다.

4. judgment target grain review
   - private 평가셋에서 `place_story` target이 child로 너무 좁게 잡힌 항목을 점검한다.
   - target을 느슨하게 바꾸는 작업이 아니라 child/parent/doc label을 분리해 평가 해석을 정교화하는 작업이다.

## 실험 순서

| 순서 | 작업 | 통과 기준 |
| --- | --- | --- |
| 1 | `place_story` 전체 dev query의 target grain coverage 진단 | child/parent/doc coverage와 min rank가 query별로 기록됨 |
| 2 | hard-case subset 정의 | child+parent miss 또는 target rank 4 이상 query를 분리 |
| 3 | deterministic rewrite v2 비교 | hard subset에서 child 또는 parent `Recall@5` 개선 |
| 4 | parent/doc context boost 비교 | top-rank 지표가 좋아지고 latency 악화가 제한적임 |
| 5 | story-aware packing 비교 | citation recoverability 유지, duplicate parent rate 악화 없음 |
| 6 | Solar Pro 3 v2 prompt repair 재검토 | retrieval 입력 품질 개선 후에만 live paired comparison 수행 |

## 정량 Gate

최소 기록 metric:

- `target_child_recall@1/3/5`
- `target_parent_recall@1/3/5`
- `target_doc_recall@1/3/5`
- `MRR`
- `nDCG@5`
- `latency_p95_ms`
- `citation_recoverability`
- `duplicate_parent_rate`
- `public_raw_text_leakage_count`
- `private_path_leakage_count`
- `secret_like_leakage_count`

개선 주장 gate:

- 같은 private dev split, 같은 query set, 같은 chunk corpus에서 paired comparison을 수행한다.
- locked test split은 후보 선택 후 1회만 사용한다.
- child 또는 parent `Recall@5`가 개선되어야 한다.
- doc-only 개선은 최종 개선 주장으로 쓰지 않는다.
- latency/cost 악화가 있으면 포트폴리오 문서에 trade-off로 명시한다.

## 정성 Gate

각 hard-case는 다음을 수기로 분류한다.

- `target_too_narrow`: target child가 서사형 질문에 과도하게 좁음
- `retrieval_semantic_miss`: 같은 장소/사건 표현을 semantic retriever가 놓침
- `lexical_alias_miss`: 별칭, 지시어, 음성형 표현 때문에 놓침
- `evidence_rank_too_low`: 관련 근거가 있지만 rank가 낮음
- `packing_order_bad`: 검색은 됐지만 answer context 앞쪽에 배치되지 않음

정성 판단에는 raw text를 public 문서에 기록하지 않는다. public에는 label과 aggregate count만 남긴다.

## 분석용 Grain 설계

`fact_place_story_coverage`의 grain은 query-run-strategy 단위다.

| 필드 | 설명 |
| --- | --- |
| `run_id` | 실험 실행 id |
| `query_id` | 평가 query id |
| `strategy_id` | retrieval 또는 packing 전략 |
| `query_type` | `place_story` |
| `target_child_covered` | child hit 여부 |
| `target_parent_covered` | parent hit 여부 |
| `target_doc_covered` | doc hit 여부 |
| `target_child_min_rank` | child 최소 rank |
| `target_parent_min_rank` | parent 최소 rank |
| `target_doc_min_rank` | doc 최소 rank |
| `latency_ms` | query 단위 latency |
| `failure_tag` | hard-case 정성 label |

dimension 후보:

- `dim_retrieval_strategy`
- `dim_query_type`
- `dim_target_grain`
- `dim_eval_split`
- `dim_run`

## Non-goal

- 이번 단계에서 전체 청킹 ablation을 다시 실행하지 않는다.
- 이번 단계에서 Solar Pro 3 live call을 추가하지 않는다.
- 이번 단계에서 v2 contract를 기본값으로 채택하지 않는다.
- 이번 단계에서 GraphRAG/RAPTOR-lite를 시작하지 않는다.
- raw query, raw answer, raw evidence text를 public artifact에 기록하지 않는다.

## 다음 작업 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-PLACE-STORY-006 | `PLACE_STORY_HARD_CASE_ANALYSIS` | `place_story` 전체 dev query의 child/parent/doc coverage diagnostic runner 구현 | pytest 통과, public-safe report 생성, leakage count 0 | Medium | runner와 report만 revert |
| HD-PLACE-STORY-007 | HD-PLACE-STORY-006 | hard subset 정의 및 rewrite/boost 후보 비교 계획 확정 | hard-case count와 baseline metric 기록 | Medium | 문서와 config만 revert |
| HD-PLACE-STORY-008 | HD-PLACE-STORY-007 | deterministic rewrite v2 또는 parent/doc context boost 중 1개 후보 구현 | paired comparison report 생성, latency 기록 | Medium | strategy flag 비활성화 |
| HD-SOLAR-009 | HD-PLACE-STORY-008 | Solar Pro 3 v2 prompt repair 재검토 | retrieval 개선 후 live paired comparison 계획 승인 | High | live call 실행 전 중단 |

## 결정

다음 구현 우선순위는 `HD-PLACE-STORY-006`이다.

청킹 비교 테스트는 보류한다. 다만 `HD-PLACE-STORY-006` 결과에서 child/parent miss가 반복되고 parent/doc 안에 evidence가 묻히는 패턴이 확인되면, 그때 `place_story` hard subset 전용 chunking 비교를 재개한다.
