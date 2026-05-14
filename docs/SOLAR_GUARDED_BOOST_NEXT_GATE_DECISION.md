# Solar Pro 3 Guarded Boost Next Gate 판단

## 결론

`parent_doc_context_boost_guarded`는 next gate로 승격한다.

단, 승격 의미는 production 기본값 채택이 아니다. 현재 근거는 private `place_story` dev 10개 live paired comparison 결과이며, locked test 성능 개선 주장으로 쓰면 안 된다.

다음 단계는 청킹 비교 테스트가 아니라 `guarded_boost`를 제한 적용 후보로 유지하면서 router 정책과 추가 검증 범위를 문서화하는 것이다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | 청킹을 다시 열지 않는다. 현재 이득은 chunk boundary가 아니라 `place_story` 전용 guarded router에서 발생했다. |
| Retrieval | `parent_doc_context_boost` 자체는 전역 적용 불가지만, guardrail이 안전한 1건만 통과시킨 점은 유효하다. |
| Generation | Solar Pro 3 live 답변에서 Correct-with-Evidence와 citation precision이 하락하지 않았으므로 다음 gate로 보낼 수 있다. |
| Evaluation | dev 10건, changed input 1건이라 최종 개선 주장으로는 부족하다. paired delta와 failure tag를 유지해야 한다. |
| Data warehouse | fact grain은 `run_id + query_id + baseline_strategy_id + candidate_strategy_id + router_policy_id + answer_policy_id`로 유지한다. |
| Security | raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 public artifact에 기록하지 않는다. |
| Portfolio | “기법 추가”보다 “부작용 발견 -> guardrail 설계 -> live 검증 -> 제한 승격” 흐름을 강조한다. |
| 외부 감사 | next gate 승격은 타당하지만 production 채택, locked test 통과, 통계적 유의성 주장은 금지한다. |

## 근거 요약

HD-SOLAR-016에서 private `place_story` dev 10개를 대상으로 Solar Pro 3 live paired comparison을 실행했다.

| metric | baseline | guarded candidate | delta |
| --- | ---: | ---: | ---: |
| eval_count | 10 | 10 | 0 |
| Correct-with-Evidence | 0.900000 | 0.900000 | 0.000000 |
| citation_precision | 0.580000 | 0.580000 | 0.000000 |
| citation_recall | 0.481309 | 0.509881 | 0.028572 |
| place_relevance | 1.000000 | 1.000000 | 0.000000 |
| docent_usefulness | 0.800000 | 0.800000 | 0.000000 |
| spoken_answer_naturalness | 0.900000 | 0.900000 | 0.000000 |
| unsupported_claim_rate | 0.100000 | 0.100000 | 0.000000 |
| latency_p95_ms | 5066.690100 | 5455.679600 | 388.989500 |

Live call과 공개 경계:

| metric | value |
| --- | ---: |
| baseline_live_call_count | 10 |
| candidate_live_call_count | 1 |
| reused_candidate_count | 9 |
| changed_candidate_input_count | 1 |
| expected_total_live_call_count | 11 |
| actual_solar_call_count | 11 |
| live_call_hard_cap | 20 |
| total_tokens | 29737 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

정성 tag:

| tag | count |
| --- | ---: |
| citation_recall_gain | 1 |
| citation_precision_regression | 0 |
| unsupported_regression | 0 |
| no_material_change | 9 |

## 판단

승격 근거:

- Correct-with-Evidence 하락이 없다.
- citation precision 하락이 없다.
- unsupported claim 증가가 없다.
- citation recall이 `+0.028572` 개선됐다.
- candidate가 1건만 선택되어 guardrail이 과도한 전역 변경을 막았다.
- public-safe output gate가 모두 0이다.

보류 근거:

- changed input query가 1건뿐이라 일반화 근거가 약하다.
- latency p95가 `+388.989500ms` 증가했다.
- `unsupported_claim_rate=0.100000` 자체는 baseline과 동일하게 남아 있어 generation 품질 문제가 완전히 해결된 것은 아니다.
- private dev 10건 결과이므로 locked test와 bootstrap confidence interval이 없다.

최종 판단:

| 항목 | 결정 |
| --- | --- |
| next gate 승격 | 승인 |
| production 기본값 채택 | 보류 |
| locked test 실행 | 아직 보류 |
| 청킹 비교 재개 | 보류 |
| 추가 Solar Pro 3 반복 호출 | 보류 |
| 포트폴리오 개선 주장 | 제한적으로 허용 |

## Next Gate 조건

다음 gate에서 검증할 질문:

1. `guarded_boost`가 추가 dev hard-case에서도 안전 지표를 유지하는가.
2. candidate 선택 조건이 너무 보수적이거나 과도하지 않은가.
3. latency 증가가 실제 사용자 경험 기준에서 허용 가능한가.
4. `unsupported_claim_rate=0.100000`의 남은 실패가 retrieval 문제인지 generation 문제인지 분리 가능한가.

통과 기준:

| gate | 기준 |
| --- | --- |
| safety | Correct-with-Evidence 하락 0 |
| citation precision | baseline 대비 하락 0 |
| citation recall | baseline 이상 |
| unsupported claim | baseline보다 증가하지 않음 |
| candidate selection | 선택 query의 route decision이 설명 가능 |
| latency | p95 증가 원인과 허용 여부 기록 |
| public safety | raw/private/secret leakage 0 |
| claim boundary | dev-only 결과와 locked-test 결과를 분리 |

## 청킹 비교 재개 조건

청킹 비교는 다음 중 하나가 확인될 때만 재개한다.

| 조건 | 의미 |
| --- | --- |
| 여러 query에서 target child/parent가 구조적으로 누락됨 | chunk boundary 자체가 retrieval 실패 원인일 가능성 |
| same parent/doc sibling 보강으로도 direct evidence가 반복 실패 | parent-child 설계 재검토 필요 |
| citation recoverability가 99% 아래로 하락 | chunk provenance 품질 문제 |
| `place_story` 외 query type에서도 동일한 target grain mismatch 반복 | 특정 router 문제가 아니라 corpus grain 문제 |

현재 HD-SOLAR-016 결과만으로는 위 조건을 충족하지 않는다.

## Data Mart 설계

fact table 후보:

| fact | grain | 목적 |
| --- | --- | --- |
| `fact_guarded_boost_live_eval` | `run_id + query_id + strategy_id + router_policy_id + answer_policy_id` | baseline/candidate live metric 저장 |
| `fact_guarded_boost_pair_delta` | `run_id + query_id + baseline_strategy_id + candidate_strategy_id` | query 단위 paired delta 저장 |
| `fact_guarded_boost_route_decision` | `run_id + query_id + router_policy_id` | route decision과 reuse decision 저장 |

dimension 후보:

| dimension | key | 설명 |
| --- | --- | --- |
| `dim_generation_run` | `run_id` | 실행 시점, model id, provider config alias |
| `dim_query` | `query_id` | query type, split, expected behavior |
| `dim_retrieval_strategy` | `strategy_id` | baseline, parent/doc boost, guarded boost |
| `dim_router_policy` | `router_policy_id` | 적용 조건과 차단 조건 버전 |
| `dim_answer_policy` | `answer_policy_id` | citation RAG answer contract 정책 |

free-text는 warehouse fact에 저장하지 않는다. raw answer와 raw evidence는 private debugging artifact로만 제한한다.

## 포트폴리오 메시지

쓸 수 있는 표현:

- `place_story` hard-case에서 retrieval 후보의 부작용을 발견하고 guardrail/router를 설계했다.
- input-only 평가와 live Solar Pro 3 paired comparison을 분리했다.
- dev 10건 live comparison에서 Correct-with-Evidence, citation precision, unsupported claim을 유지하면서 citation recall을 `+0.028572` 개선했다.
- 동일 input fingerprint는 baseline 결과를 재사용해 live call을 20회에서 11회로 줄였다.
- public report에는 raw text와 private path를 남기지 않는 평가 산출물 정책을 적용했다.

쓰면 안 되는 표현:

- 최종 RAG 성능을 개선했다.
- 통계적으로 유의미한 개선을 입증했다.
- `guarded_boost`를 production 기본값으로 채택했다.
- 청킹이 최적인 것으로 확정했다.
- GraphRAG/RAPTOR보다 우수하다고 검증했다.

## 외부 감사 결론

| 감사 항목 | 결과 |
| --- | --- |
| 변수 통제 | PASS. retrieval/router 외 generation 조건은 동일하게 유지했다. |
| 비용 통제 | PASS. expected 11회, hard cap 20회 안에서 실행했다. |
| 공개 경계 | PASS. public leakage count가 0이다. |
| 결과 해석 | PASS with caution. dev-only 결과임을 명시했다. |
| 통계적 유의성 | FAIL/Not applicable. sample size와 changed query 수가 부족하다. |
| next action | PASS. next gate 승격은 가능하지만 production 채택은 보류한다. |

## 결정

다음 작업은 `HD-SOLAR-018 guarded boost 추가 dev hard-case 검증 계획`이다.

추가 Solar Pro 3 호출 없이, 먼저 HD-SOLAR-016의 query-level paired delta와 route decision을 기준으로 어떤 query를 추가 검증할지 정한다. 그 뒤 별도 승인 시에만 추가 live call을 실행한다.
