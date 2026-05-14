# Solar Pro 3 Guarded Boost 추가 Dev Hard-case 검증 계획

## 결론

지금은 청킹 비교 테스트를 다시 열지 않는다.

다음 단계는 `parent_doc_context_boost_guarded`를 production 기본값으로 채택하는 것이 아니라, HD-SOLAR-016에서 확인된 route decision과 paired delta를 기준으로 추가 dev hard-case 검증 범위를 고정하는 것이다.

이번 계획은 Solar Pro 3 추가 호출을 포함하지 않는다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 public artifact에 기록하지 않는다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | 현재 증거는 chunk boundary 문제가 아니라 `place_story` router 적용 조건 문제다. 청킹 재실험은 보류한다. |
| Retrieval | hard-case는 candidate를 통과시킨 query뿐 아니라 guardrail이 차단한 query도 함께 봐야 한다. |
| Generation | Solar Pro 3 추가 호출 전에 input evidence quality와 route safety를 먼저 검증한다. |
| Evaluation | dev-only live 결과를 최종 개선 주장으로 쓰지 않고, query bucket별 pass/fail gate를 새로 고정한다. |
| Data warehouse | fact grain은 `validation_id + query_id + hard_case_bucket + strategy_id + router_policy_id + answer_policy_id`로 둔다. |
| Security | public report에는 query id, bucket, metric delta, route decision label, leakage count만 허용한다. |
| Portfolio | “성능 개선”이 아니라 “위험한 후보를 guardrail로 제한하고 추가 검증 gate를 설계했다”를 메시지로 쓴다. |
| 외부 감사 | 추가 실험 전 계획으로는 타당하다. 단, locked test 통과 또는 통계적 유의성 주장은 금지한다. |

## 현재 근거

HD-SOLAR-016 live paired comparison 결과:

| metric | baseline | guarded candidate | delta |
| --- | ---: | ---: | ---: |
| eval_count | 10 | 10 | 0 |
| Correct-with-Evidence | 0.900000 | 0.900000 | 0.000000 |
| citation_precision | 0.580000 | 0.580000 | 0.000000 |
| citation_recall | 0.481309 | 0.509881 | 0.028572 |
| unsupported_claim_rate | 0.100000 | 0.100000 | 0.000000 |
| latency_p95_ms | 5066.690100 | 5455.679600 | 388.989500 |

Route decision 분포:

| route_decision | count |
| --- | ---: |
| `use_candidate_direct_gain` | 1 |
| `use_baseline_correctness_guardrail` | 1 |
| `use_baseline_doc_guardrail` | 1 |
| `use_baseline_precision_guardrail` | 2 |
| `use_baseline_no_candidate_gain` | 3 |
| `manual_review_required` | 2 |

Live call과 공개 경계:

| metric | value |
| --- | ---: |
| baseline_live_call_count | 10 |
| candidate_live_call_count | 1 |
| reused_candidate_count | 9 |
| actual_solar_call_count | 11 |
| live_call_hard_cap | 20 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

해석:

- 안전 지표는 하락하지 않았다.
- citation recall은 소폭 상승했다.
- candidate가 실제로 선택된 query는 1건뿐이다.
- manual review query 2건은 recall gain과 evidence order regression이 공존해 자동 채택하면 안 된다.
- 따라서 다음 검증은 “candidate를 더 많이 통과시킬 것인가”가 아니라 “현 guardrail이 차단해야 할 query를 계속 차단하는가”를 확인해야 한다.

## Hard-case Bucket

| bucket | 포함 기준 | 검증 목적 |
| --- | --- | --- |
| `candidate_direct_gain` | candidate가 guardrail을 통과한 query | 자동 선택된 candidate가 실제로 안전한지 확인 |
| `correctness_guardrail` | correctness proxy regression으로 차단된 query | 차단 조건이 과도하지 않은지 확인 |
| `doc_guardrail` | doc coverage 손실로 차단된 query | doc 연결 손실이 generation 위험인지 확인 |
| `precision_guardrail` | precision/order 하락 위험으로 차단된 query | citation precision regression 방지 확인 |
| `manual_review_required` | recall gain과 order regression이 공존한 query | 자동 채택 금지 유지 여부 확인 |
| `no_candidate_gain_control` | candidate 이득이 없는 query | baseline 유지가 합리적인지 control로 확인 |

public 문서에는 bucket count와 query id만 기록한다. raw query와 evidence text는 기록하지 않는다.

## 검증 순서

| 순서 | 작업 | Solar Pro 3 호출 | 산출물 |
| --- | --- | ---: | --- |
| 1 | HD-SOLAR-016 paired delta와 route decision row 재검토 | 0 | hard-case bucket summary |
| 2 | input-only route safety 재검증 | 0 | query bucket별 metric delta |
| 3 | evidence packing 영향 재검토 | 0 | duplicate parent, evidence order, citation recoverability |
| 4 | manual review bucket 차단 유지 판단 | 0 | route decision 유지/수정 제안 |
| 5 | 추가 live call 필요 여부 판단 | 0 | 별도 승인용 call budget |

이번 단계에서 실제 Solar Pro 3 live call은 수행하지 않는다.

## 정량 Gate

| gate | 기준 |
| --- | --- |
| query coverage | HD-SOLAR-016 `place_story` dev 10개가 모두 bucket에 매핑됨 |
| selected candidate safety | 자동 선택 bucket의 `Correct-with-Evidence delta >= 0` |
| citation precision | 자동 선택 bucket의 `citation_precision delta >= 0` |
| citation recall | 자동 선택 bucket의 `citation_recall delta >= 0` |
| unsupported claim | 자동 선택 bucket의 `unsupported_claim delta <= 0` |
| manual review block | `manual_review_required` bucket은 자동 candidate 선택 금지 |
| doc guardrail block | doc coverage 손실 query는 자동 candidate 선택 금지 |
| citation recoverability | input-only 검증에서 `citation_recoverability >= 0.990000` |
| evidence order | 자동 선택 query의 evidence order 하락 없음 |
| latency/cost | 추가 live call 0, 향후 call 필요 시 hard cap 별도 승인 |
| public safety | raw/private/secret leakage count 0 |

## 정성 Gate

정성 평가는 다음 tag만 public report에 남긴다.

| tag | 의미 |
| --- | --- |
| `safe_direct_gain` | candidate가 직접 근거를 보강하고 안전 지표 하락이 없음 |
| `blocked_correctness_risk` | correctness regression 가능성 때문에 baseline 유지 |
| `blocked_doc_loss` | doc coverage 손실 때문에 baseline 유지 |
| `blocked_precision_or_order_risk` | precision 또는 evidence order 하락 때문에 baseline 유지 |
| `manual_review_kept_blocked` | recall gain이 있어도 자동 채택하지 않음 |
| `control_no_gain` | candidate 이득이 없어 baseline 유지 |
| `needs_router_threshold_tuning` | 적용 조건이 과도하게 보수적이거나 느슨함 |
| `needs_live_call_approval` | input-only로 판단 불가해 별도 live call 승인이 필요함 |

## Data Mart 설계

`fact_guarded_boost_hard_case_validation`의 grain은 `validation_id + query_id + hard_case_bucket + strategy_id + router_policy_id + answer_policy_id`다.

| field | 설명 |
| --- | --- |
| `validation_id` | hard-case 검증 실행 id |
| `query_id` | public-safe query id |
| `query_type` | `place_story` |
| `hard_case_bucket` | bucket label |
| `strategy_id` | baseline 또는 guarded strategy |
| `router_policy_id` | `place_story_guarded_boost_v1` |
| `answer_policy_id` | generation 평가 정책 id |
| `route_decision` | sanitized route decision |
| `reuse_decision` | live result reuse 여부 |
| `selected_candidate` | candidate 자동 선택 여부 |
| `blocked` | guardrail 차단 여부 |
| `metric_delta_json` | public-safe metric delta |
| `qualitative_tags` | public-safe tag list |

dimension 후보:

- `dim_validation_run`
- `dim_query`
- `dim_hard_case_bucket`
- `dim_retrieval_strategy`
- `dim_router_policy`
- `dim_answer_policy`

free-text query, raw answer, raw evidence, prompt, chunk text는 fact에 저장하지 않는다.

## 다음 구현 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-SOLAR-019 | HD-SOLAR-018 | guarded boost hard-case validation runner 구현 | public-safe report 생성, Solar call 0, bucket coverage 10/10, leakage count 0, pytest 통과 | Medium | runner/report revert |
| HD-SOLAR-020 | HD-SOLAR-019 | hard-case validation 결과 기반 router threshold 수정 여부 판단 | 정량/정성 report, claim boundary, 추가 live call 필요 여부 기록 | Medium | router config revert |

## Non-goal

- 이번 단계에서 청킹 ablation을 다시 실행하지 않는다.
- 이번 단계에서 Solar Pro 3를 추가 호출하지 않는다.
- 이번 단계에서 `guarded_boost`를 production 기본값으로 채택하지 않는다.
- 이번 단계에서 locked test split을 사용하지 않는다.
- 이번 단계에서 GraphRAG, RAPTOR-lite, HyDE를 시작하지 않는다.

## Commit 기준

이번 문서 작업의 commit 후보 메시지:

```text
문서: guarded boost 추가 hard-case 검증 계획 추가
```

## 외부 감사 결론

| 감사 항목 | 결과 |
| --- | --- |
| 변수 통제 | PASS. 다음 단계는 동일 dev query set과 기존 route decision을 기준으로 한다. |
| 비용 통제 | PASS. 이번 계획은 Solar Pro 3 추가 호출 0회다. |
| 공개 경계 | PASS. public artifact 허용 필드와 금지 필드를 분리했다. |
| 결과 해석 | PASS with caution. dev-only next gate 계획이며 개선 확정 주장이 아니다. |
| 청킹 재개 판단 | PASS. 현재 재개 조건을 충족하지 않는다. |
| 다음 action | PASS. HD-SOLAR-019 runner 구현 전 gate가 명확하다. |

## 결정

다음 실제 구현 작업은 HD-SOLAR-019다.

HD-SOLAR-019에서는 추가 Solar Pro 3 호출 없이, 기존 private dev `place_story` 10개와 HD-SOLAR-016 route decision을 사용해 hard-case bucket validation runner와 public-safe report를 구현한다.
