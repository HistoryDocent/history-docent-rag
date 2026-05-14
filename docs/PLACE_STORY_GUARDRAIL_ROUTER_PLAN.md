# Place Story Guardrail/Router 계획

## 결론

`parent_doc_context_boost`는 전체 기본 retrieval strategy로 채택하지 않는다.

HD-008, HD-009, HD-010 결과를 종합하면 이 후보는 `place_story` 일부 query에서 direct evidence와 citation recall을 개선하지만, 동시에 citation precision, evidence order, Correct-with-Evidence를 악화시키는 query가 있다.

따라서 다음 단계는 청킹 재실험이나 Solar Pro 3 live 호출이 아니다. 먼저 `parent_doc_context_boost`를 언제 적용하고 언제 baseline을 유지할지 결정하는 guardrail/router를 설계한다.

## 근거

| 실험 | 핵심 결과 | 판단 |
| --- | --- | --- |
| HD-008 full dev retrieval 재검증 | `child_or_parent@5` 0.600000 -> 0.700000 | direct evidence 개선은 있음 |
| HD-009 input-only 평가 | `citation_recall` 0.481309 -> 0.565953, `Correct-with-Evidence` 0.900000 -> 0.800000 | recall 개선과 correctness 하락이 공존 |
| HD-010 query별 regression 분석 | `guardrail_required_count=1`, `citation_precision_regression_count=3`, `evidence_order_regression_count=3` | 전체 기본값 채택 불가 |

해석:

- candidate는 완전 실패가 아니다.
- candidate는 무조건 좋은 것도 아니다.
- 가장 위험한 지점은 direct evidence를 늘리면서 evidence order와 precision을 흐리는 경우다.
- Solar Pro 3 live generation에 넣기 전에 retrieval 단계에서 적용 조건을 제한해야 한다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | boost를 전역 적용하지 않고 query type, baseline confidence, candidate delta를 기준으로 router 처리한다. |
| Retrieval | candidate는 baseline이 child/parent target을 놓친 경우에만 제한적으로 시도한다. |
| Generation | evidence order가 낮아진 입력은 Solar Pro 3가 citation 선택을 더 어렵게 만들 수 있다. |
| Evaluation | `Correct-with-Evidence` regression이 있는 후보는 live call 전에 차단 조건을 가져야 한다. |
| Data warehouse | query-strategy-router grain으로 route decision, block reason, metric delta를 기록한다. |
| Security | raw query, raw evidence, prompt, answer text를 public artifact에 남기지 않는다. |
| Portfolio | 성능 후보의 부작용을 발견하고 guardrail로 통제하는 흐름을 보여준다. |

## Router 정책 초안

Router는 `place_story` query에만 적용한다.

기본 원칙:

- baseline retrieval 결과를 먼저 만든다.
- candidate retrieval 결과를 별도로 만든다.
- query별 sanitized metric delta를 계산한다.
- 적용 조건을 모두 만족할 때만 candidate를 선택한다.
- 하나라도 hard block 조건에 걸리면 baseline을 유지한다.

## 적용 조건

candidate를 선택하려면 다음 조건을 모두 만족해야 한다.

| 조건 | 의미 |
| --- | --- |
| `candidate_child_or_parent_covered=true` | candidate가 child 또는 parent direct evidence를 확보해야 함 |
| `baseline_child_or_parent_covered=false OR candidate_any_rank_better=true` | baseline이 놓쳤거나 candidate가 명확히 rank를 개선해야 함 |
| `candidate_doc_covered=true` | doc 단위 연결은 유지해야 함 |
| `candidate_evidence_order >= 0.4` | evidence order가 너무 나빠지면 차단 |
| `candidate_duplicate_parent_rate <= baseline_duplicate_parent_rate + 0.2` | 같은 parent 과밀을 제한 |
| `candidate_context_buildable=true` | prompt 입력 구성 가능해야 함 |

## 차단 조건

하나라도 만족하면 baseline을 유지한다.

| 조건 | 차단 이유 |
| --- | --- |
| candidate가 child/parent를 확보하지 못함 | direct evidence 개선이 없음 |
| baseline은 Correct-with-Evidence proxy positive인데 candidate가 negative | correctness regression 위험 |
| `citation_precision_delta < 0`이고 `citation_recall_delta <= 0` | precision만 잃고 recall 보상이 없음 |
| `evidence_order_delta < -0.5` | generation 입력 순서 훼손 가능성 큼 |
| `candidate_doc_covered=false` | 관련 문서 연결 자체가 약해짐 |
| context budget 초과 또는 truncation 발생 | prompt 입력 안정성 부족 |

## Router Decision Label

공개 리포트에는 다음 label만 남긴다.

| label | 의미 |
| --- | --- |
| `use_baseline_no_candidate_gain` | candidate 개선 없음 |
| `use_candidate_direct_gain` | direct evidence 개선이 있고 hard block 없음 |
| `use_baseline_precision_guardrail` | precision/order 하락 때문에 baseline 유지 |
| `use_baseline_correctness_guardrail` | correctness regression proxy 때문에 baseline 유지 |
| `use_baseline_doc_guardrail` | doc coverage가 약해져 baseline 유지 |
| `manual_review_required` | recall gain과 precision/order regression이 공존 |

## 평가 설계

비교 대상:

1. `baseline_dense_e5_voice_rewrite`
2. `parent_doc_context_boost_always`
3. `parent_doc_context_boost_guarded`

같은 조건:

- 같은 private `place_story` dev query 10개
- 같은 chunk corpus
- 같은 embedding cache
- 같은 top_k 5
- 같은 candidate_k 20
- Solar Pro 3 호출 0
- CUDA 사용 가능 시 CUDA 사용

정량 metric:

- `selected_candidate_rate`
- `guardrail_block_rate`
- `direct_ready_rate`
- `Correct-with-Evidence proxy`
- `citation_precision`
- `citation_recall`
- `evidence_order_relevance_proxy`
- `doc_coverage_rate`
- `latency_p95_ms`
- `solar_call_count`
- public leakage counts

통과 기준:

| gate | 기준 |
| --- | --- |
| safety | `correct_with_evidence_rate`가 baseline보다 낮아지지 않음 |
| precision | `citation_precision`이 baseline보다 낮아지지 않음 |
| recall | `citation_recall`이 baseline 이상 |
| direct evidence | `direct_ready_rate`가 baseline 이상 |
| order | `evidence_order_relevance_proxy`가 always-boost보다 개선 |
| cost | Solar Pro 3 호출 0 |
| public policy | raw text/private path/secret leakage 0 |

## Data Mart 설계

fact grain은 `query_id + router_policy_id + candidate_strategy_id`다.

| fact field | 설명 |
| --- | --- |
| `analysis_id` | 실행 id |
| `query_id` | 공개 가능한 평가 query id |
| `router_policy_id` | router/guardrail 정책 id |
| `baseline_strategy_id` | baseline retrieval 전략 |
| `candidate_strategy_id` | candidate retrieval 전략 |
| `route_decision` | 최종 선택 label |
| `blocked` | candidate 차단 여부 |
| `block_reason_tags` | 차단 이유 tag |
| `direct_ready_delta` | direct evidence delta |
| `correct_with_evidence_delta` | input-only correctness delta |
| `citation_precision_delta` | citation precision delta |
| `citation_recall_delta` | citation recall delta |
| `evidence_order_delta` | evidence order delta |
| `latency_delta_ms` | latency delta |

dimension 후보:

- `dim_router_policy`
- `dim_retrieval_strategy`
- `dim_query_type`
- `dim_eval_split`
- `dim_run`

## 보안 정책

public artifact 금지:

- raw query
- raw evidence
- prompt
- answer text
- chunk text
- private path
- secret/API key

public artifact 허용:

- query id
- aggregate metric
- metric delta
- route decision label
- block reason tag
- public-safe report

## HD-PLACE-STORY-012 실행 결과

`baseline_dense_e5_voice_rewrite`, `parent_doc_context_boost_always`, `parent_doc_context_boost_guarded`를 같은 `place_story` dev query 10개에서 비교했다. Solar Pro 3는 호출하지 않았다.

| 항목 | 값 |
| --- | ---: |
| selected_candidate_count | 1 |
| guardrail_block_count | 9 |
| guarded_Correct-with-Evidence | 0.900000 |
| guarded_citation_precision | 0.580000 |
| guarded_citation_recall | 0.509881 |
| guarded_doc_coverage | 0.900000 |
| guarded_evidence_order | 0.770000 |
| solar_call_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

Route decision 분포:

| route_decision | count |
| --- | ---: |
| `manual_review_required` | 2 |
| `use_baseline_correctness_guardrail` | 1 |
| `use_baseline_doc_guardrail` | 1 |
| `use_baseline_no_candidate_gain` | 3 |
| `use_baseline_precision_guardrail` | 2 |
| `use_candidate_direct_gain` | 1 |

판단:

- `always_boost`는 recall 이득이 있지만 correctness와 precision/order regression이 있어 기본값으로 부적합하다.
- `guarded_boost`는 baseline safety metric을 유지하면서 안전한 candidate 1건만 통과시켰다.
- 결과 label은 `promote_guarded_to_live_plan_review`다.
- 이 결과는 live generation 품질 개선 주장이 아니라 live paired comparison 계획으로 넘어갈 수 있다는 input-only gate 통과다.

## HD-SOLAR-013 계획 결과

[Solar Pro 3 Guarded Boost Live Comparison Plan](SOLAR_GUARDED_BOOST_LIVE_COMPARISON_PLAN.md)에 live paired comparison 실행 전 조건을 고정했다.

핵심 결정:

- 비교 범위는 private `place_story` dev 10개로 제한한다.
- baseline과 guarded 입력 fingerprint가 동일한 query는 baseline generation 결과를 재사용한다.
- 예상 live call은 11회, hard cap은 20회다.
- public report에는 raw query, raw answer, raw evidence, prompt, private path, secret을 기록하지 않는다.
- live 실행은 별도 승인 후 진행한다.

## HD-SOLAR-014 실행 결과

Solar Pro 3를 호출하지 않는 dry-run runner를 실행했다.

| metric | value |
| --- | ---: |
| query_count | 10 |
| expected_total_live_call_count | 11 |
| baseline_live_call_count | 10 |
| candidate_live_call_count | 1 |
| reused_candidate_count | 9 |
| live_call_hard_cap | 20 |
| solar_call_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

판단:

- guarded router가 차단한 9건은 baseline generation 결과를 재사용한다.
- candidate가 선택된 1건만 추가 live call이 필요하다.
- live 호출 전 call budget과 public-safe gate가 계획과 일치한다.

## 작업 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-PLACE-STORY-011 | HD-PLACE-STORY-010 | guardrail/router 계획 문서화 | 계획 문서, README/TODO 링크, leakage scan 통과 | Low | 문서 revert |
| HD-PLACE-STORY-012 | HD-PLACE-STORY-011 | guarded boost comparison runner 구현 | 완료. baseline/always/guarded 3-way report, pytest, ruff, leakage 0 | Medium | runner/report revert |
| HD-SOLAR-013 | HD-PLACE-STORY-012 | Solar Pro 3 live 재비교 계획 | 완료. live call 전 query set, cost, pass/fail gate 문서화 | Medium | 문서 revert |
| HD-SOLAR-014 | HD-SOLAR-013 | Solar Pro 3 guarded boost live comparison dry-run runner | 완료. input fingerprint, 예상 call count, public-safe dry-run report | High | runner/report revert |
| HD-SOLAR-015 | HD-SOLAR-014 | Solar Pro 3 guarded boost live paired comparison runner | live 실행 전 dry-run 재검증, call cap 확인 | High | runner/report revert |

## Non-goal

- 이번 단계에서 청킹 ablation을 다시 실행하지 않는다.
- 이번 단계에서 Solar Pro 3를 호출하지 않는다.
- 이번 단계에서 candidate를 production 기본값으로 채택하지 않는다.
- 이번 단계에서 GraphRAG/RAPTOR-lite를 시작하지 않는다.

## 결정

다음 구현 작업은 `HD-SOLAR-015` live paired comparison runner다.

목표는 실제 live call을 바로 실행하지 않고, live runner 안에서도 dry-run 재검증과 call cap 확인을 강제하는 것이다.
