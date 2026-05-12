# Solar Pro 3 Generation Failure Analysis

## 목적

Solar Pro 3 generation baseline에서 확인된 실패 유형을 query grain으로 분해한다.

이 문서는 성능 개선 주장이 아니다. 다음 prompt/answer contract 개선과 retrieval hard-case 실험의 우선순위를 정하기 위한 public-safe 진단 문서다.

원문 chunk text, raw answer, raw query text, private path, secret은 기록하지 않는다.

## 담당 관점 회의 결과

| 담당 관점 | 결론 |
| --- | --- |
| RAG 아키텍처 | 청킹 전체 재실험보다 generation failure root cause 분해가 먼저다. |
| Retrieval | `place_story`는 여러 retrieval 후보에서도 child/parent target을 못 잡은 hard case다. |
| Generation | `place_fact`, `overview`는 target evidence가 들어왔지만 citation 선택과 coverage가 약하다. |
| 평가 | query type별 1건 baseline이므로 통계적 개선 주장은 금지한다. 같은 query set paired comparison만 허용한다. |
| 보안 | public report에는 aggregate metric과 failure tag만 남긴다. |
| 포트폴리오 | “기법 나열”보다 “실패 원인 분해 -> 개선 가설 -> paired comparison” 흐름을 보여준다. |

## 사용 근거

| artifact | grain | public-safe 사용 범위 |
| --- | --- | --- |
| `solar_generation_baseline_report.md` | query_type summary | metric, failure tag |
| `solar_generation_baseline_results.jsonl` | query | metric, count, fingerprint field only |
| `retrieval_experiment_*_results.jsonl` | query-result | top-k count와 target hit boolean만 사용 |
| `evidence_packing_comparison_results.jsonl` | query-policy-evidence | target coverage boolean과 packed count만 사용 |

## 정량 진단

| query_id | query_type | retrieved_top_k | packed_evidence | target_child | target_parent | target_doc | citation_count | citation_precision | citation_recall | latency_ms | primary_failure |
| --- | --- | ---: | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `q-dev-place-fact-001` | `place_fact` | 5 | 5 | true | true | true | 5 | 0.200000 | 0.500000 | 13144.776600 | citation selection + latency |
| `q-dev-place-story-001` | `place_story` | 5 | 5 | false | false | true | 5 | 0.200000 | 0.125000 | 2935.956800 | retrieval/evidence coverage |
| `q-dev-overview-001` | `overview` | 5 | 5 | true | true | true | 5 | 0.600000 | 0.333333 | 4676.336600 | citation coverage |
| `q-dev-relationship-001` | `relationship` | 5 | 5 | true | true | true | 5 | 1.000000 | 1.000000 | 3618.264500 | none |
| `q-dev-route-context-001` | `route_context` | 5 | 5 | true | true | true | 5 | 0.600000 | 0.500000 | 2942.061200 | monitor |
| `q-dev-voice-followup-001` | `voice_followup` | 5 | 5 | true | true | true | 5 | 0.800000 | 0.600000 | 2441.724600 | none |
| `q-dev-no-answer-001` | `no_answer` | 0 | 0 | false | false | false | 0 | 1.000000 | 1.000000 | 0.068200 | none |

`no_answer`의 generation baseline path는 retrieval-backed abstain guard로 evidence를 pack하지 않는다. 이전 retrieval experiment artifact에는 no-answer 후보가 존재할 수 있지만, generation baseline에서는 Solar Pro 3를 호출하지 않고 abstain한다.

## Retrieval 후보 교차 확인

실패 3건에 대해 child/parent/doc target hit 여부만 비교했다. 본문과 raw score는 공개하지 않는다.

| method | place_fact child/parent/doc | place_story child/parent/doc | overview child/parent/doc |
| --- | --- | --- | --- |
| `bm25` | false / false / true | false / false / true | false / false / true |
| `dense_e5` | true / true / true | false / false / true | true / true / true |
| `dense_voice` | true / true / true | false / false / true | true / true / true |
| `hybrid_e5_a03` | false / false / true | false / false / true | true / true / true |
| `rerank_bge_top20` | true / true / true | false / false / true | true / true / true |

판단:

- `place_fact`: dense와 reranker에서는 target evidence가 들어온다. generation 단계의 citation selection 문제가 1차 원인이다.
- `overview`: target evidence가 들어온다. 여러 근거를 균형 있게 쓰는 coverage instruction이 약한 것이 1차 원인이다.
- `place_story`: 비교한 모든 후보에서 doc-level만 맞고 child/parent target은 miss다. prompt 개선 전에 retrieval hard-case 분석이 필요하다.

## Root Cause 분류

| query_type | 사실 | 판단 | 다음 액션 |
| --- | --- | --- | --- |
| `place_fact` | target child/parent/doc이 packed evidence에 포함됐지만 citation_precision이 0.2다. latency가 13초를 넘었다. | 검색보다 answer contract와 citation selection 문제가 우선이다. latency는 provider outlier 또는 context 처리 비용 가능성이 있다. | citation 최소화, target evidence 우선 citation, latency repeat 측정 |
| `place_story` | target doc은 맞지만 child/parent target은 여러 retrieval 후보에서 모두 miss다. citation_recall이 0.125다. | prompt만 고쳐도 필요한 근거가 없으면 개선 폭이 제한된다. retrieval hard-case다. | query rewrite, story/episode 질문용 retrieval target 재검토, parent expansion 후보 실험 |
| `overview` | target child/parent/doc은 들어왔지만 citation_recall이 0.333333이다. | overview 답변에서 필요한 근거 범위를 일부만 사용한다. | multi-evidence coverage instruction, citation coverage constraint |
| `route_context` | failure tag는 없지만 citation_recall이 0.5다. | 현재는 통과지만 route 설명에서는 누락 위험을 추적해야 한다. | v2 비교에서 monitor metric으로 유지 |
| `voice_followup` | precision 0.8, recall 0.6으로 baseline 중 안정적이다. | voice rewrite 경로는 유지한다. | spoken_answer 품질 유지 여부 확인 |
| `no_answer` | Solar Pro 3 호출 없이 abstain했다. | corpus 밖 질문 환각 guard는 baseline에서 정상 동작했다. | no-answer set 확장 후 재검증 |

## 청킹 재실험 판단

지금 전체 청킹 비교를 다시 하지 않는다.

근거:

- C0-C6 chunking ablation v2에서 C0 current parent-child가 선택됐다.
- `place_fact`, `overview`는 target evidence가 들어왔으므로 청킹보다 citation selection 문제가 먼저다.
- `place_story`는 retrieval hard case지만, 여러 retrieval 후보가 모두 child/parent target을 못 잡은 상태라 바로 청킹을 바꾸기보다 query rewrite, target judgment, story retrieval 전략을 먼저 분해해야 한다.

청킹을 다시 여는 조건:

- `place_story` hard case에서 raw review 결과 “정답 근거가 chunk 경계 밖에 분산되어 있다”는 증거가 확인된다.
- parent expansion 또는 hierarchical retrieval이 동일 query에서 child/parent target coverage를 올린다.
- generation v2 paired comparison 이후에도 target evidence가 들어온 query의 citation 지표가 개선되지 않는다.

## 다음 실험 설계

1. `answer_policy_id=solar-generation-contract-v2` 후보를 만든다.
2. 같은 7개 query set에서 baseline v1과 v2를 paired comparison한다.
3. `place_fact`, `overview`는 prompt/answer contract 개선군에 넣는다.
4. `place_story`는 retrieval hard-case side experiment로 분리한다.
5. 개선 주장은 `Correct-with-Evidence`, `citation_precision`, `citation_recall`, `unsupported_claim_rate`, `latency_p95_ms`를 함께 보고 판단한다.

## 통과 기준

| gate | 기준 |
| --- | --- |
| public safety | raw answer, raw query, chunk text, private path, secret-like value 0 |
| failure diagnosis | 실패 query type마다 primary cause가 있어야 한다 |
| next action | prompt/contract 개선과 retrieval hard-case 실험이 분리되어야 한다 |
| claim boundary | 통계적 성능 개선 표현 금지 |

## 결론

다음 작업은 청킹 비교 재실행이 아니라 `Solar Pro 3 prompt/answer contract v2` 설계와 paired comparison이다.

단, `place_story`는 generation 개선군에 섞지 말고 retrieval hard-case로 분리한다. 이 분리를 해야 포트폴리오에서 “무작위 실험”이 아니라 “실패 원인별 실험 설계”로 설명할 수 있다.
