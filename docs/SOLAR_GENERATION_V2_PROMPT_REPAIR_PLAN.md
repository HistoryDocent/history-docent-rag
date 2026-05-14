# Solar Pro 3 Generation v2 Prompt Repair 계획

## 결론

청킹 비교 테스트는 지금 재개하지 않는다.

`CitationRagDraftV2` selected evidence contract는 citation 수를 줄여 precision을 올릴 가능성을 보였지만, 현재 prompt policy는 충분한 근거 선택을 보장하지 못했다. 따라서 다음 작업은 live 재호출이 아니라 `Solar Pro 3 generation v2 prompt repair` 계획을 고정하고, no-live-call 조건에서 input/schema/metric gate를 먼저 통과시키는 것이다.

이 문서는 실행 계획이다. Solar Pro 3 추가 호출, live 품질 개선, production 채택 주장이 아니다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | v2 contract 자체는 폐기하지 않는다. 다만 기본값 채택 전 query type별 coverage floor를 추가해야 한다. |
| Retrieval | locked `place_story` guarded boost는 production 근거가 부족하다. 청킹 재실험보다 generation prompt repair로 복귀한다. |
| Generation | v2 prompt는 evidence를 적게 고르는 방향으로 과보정됐다. 이제는 "적게"보다 "충분하고 검증 가능하게"를 우선한다. |
| Evaluation | 다음 단계는 live 재실험이 아니라 repaired prompt 후보의 dry-run/input-only gate 정의다. |
| Data warehouse | prompt repair 결과 grain은 `repair_id + query_type + prompt_policy_id + eval_stage + metric_family`로 고정한다. |
| Security | public artifact에는 raw prompt, raw query, raw answer, raw evidence, chunk text, private path, secret을 기록하지 않는다. |
| Portfolio | 기법 추가 후 지표로 채택 보류하고, 실패 원인을 다시 가설화하는 흐름을 보여준다. |
| 외부 감사 | 청킹 재개 보류와 v2 prompt repair 우선순위는 현재 근거와 일치한다. |

## 사용 근거

HD-GEN-V2 live paired comparison 결과:

| metric | v1 baseline | v2 candidate | delta |
| --- | ---: | ---: | ---: |
| Correct-with-Evidence | 1.000000 | 0.833333 | -0.166667 |
| citation_precision | 0.566667 | 0.750000 | 0.183333 |
| citation_recall | 0.509722 | 0.461111 | -0.048611 |
| docent_usefulness | 1.000000 | 0.857143 | -0.142857 |
| unsupported_claim_rate | 0.000000 | 0.142857 | 0.142857 |
| abstention_accuracy | 1.000000 | 1.000000 | 0.000000 |
| latency_p95_ms | 13743.580900 | 4372.871200 | -9370.709700 |
| solar_call_count | 6 | 6 | 0 |

HD-GEN-V2 trade-off analysis 결과:

| metric | value |
| --- | ---: |
| row_count | 7 |
| answerable_row_count | 6 |
| precision_gain_count | 3 |
| precision_regression_count | 2 |
| recall_regression_count | 2 |
| correctness_regression_count | 1 |
| unsupported_regression_count | 1 |
| citation_count_reduction_count | 6 |
| adoption_blocker_count | 1 |
| mean_citation_count_delta | -3.166667 |
| mean_latency_ms_delta | -2558.989700 |
| adoption_decision | `reject_default_contract` |

HD-SOLAR-023 locked readiness next gate 결과:

| metric | value |
| --- | ---: |
| locked_place_story_query_count | 5 |
| selected_candidate_count | 0 |
| candidate_live_call_count | 0 |
| target_resolvability_fail_count | 0 |
| citation_recoverability_min | 1.000000 |
| solar_call_count | 0 |
| next_action | `generation_v2_prompt_repair_plan` |

## 문제 정의

현재 v2 실패는 청킹 실패로 단정할 수 없다.

확인된 문제는 다음이다.

- v2는 citation count를 줄였고 precision은 올렸다.
- 그러나 일부 answerable query에서 correctness, recall, unsupported claim이 악화됐다.
- `place_story`는 retrieval hard-case와 generation over-pruning이 함께 나타난다.
- `relationship`, `voice_followup`은 기존 좋은 citation 성능을 보존하지 못할 수 있다.
- 따라서 v2 prompt repair는 citation 최소화가 아니라 coverage-aware citation selection으로 설계해야 한다.

## Prompt Repair 후보

이 문서에는 prompt 전문을 기록하지 않는다. public에는 prompt policy id와 검증 규칙만 남긴다.

| prompt_policy_id | 목적 | 핵심 규칙 | 예상 효과 | 주요 위험 |
| --- | --- | --- | --- | --- |
| `v2_repair_coverage_floor` | over-pruning 방지 | query type별 최소 evidence 선택 수를 둔다. | recall, correctness 회복 | citation count 증가로 precision 하락 |
| `v2_repair_risk_aware_selection` | unsupported claim 억제 | 선택 근거가 부족하면 risk를 높이거나 abstain한다. | unsupported claim 감소 | 답변 보수화 |
| `v2_repair_query_type_router` | regression 방지 | v2가 유리한 query type에만 repaired v2를 적용한다. | positive case 보존, blocker 회피 | router 복잡도 증가 |

## Query Type별 정책

| query_type | 기본 판단 | repaired v2 정책 |
| --- | --- | --- |
| `place_fact` | v2 positive case | 핵심 evidence 1-2개 허용. precision 유지 여부를 본다. |
| `overview` | v2 positive case | coverage intent가 있으면 evidence 2개 이상을 요구한다. |
| `place_story` | blocker case | repaired v2 성공률 계산에서 분리하고 monitor-only로 둔다. 필요 시 v1 fallback을 우선한다. |
| `relationship` | recall regression risk | 관계 설명은 evidence 2개 이상 또는 v1 fallback을 요구한다. |
| `route_context` | latency monitor | precision gain과 latency regression을 함께 본다. |
| `voice_followup` | precision regression risk | 짧은 답변이어도 selected evidence 최소 2개 또는 v1 fallback을 둔다. |
| `no_answer` | 정상 | 기존 abstain path 유지. Solar Pro 3 호출 없이 처리한다. |

## 평가 순서

1. `prompt_policy_id`와 query type별 evidence floor를 문서로 고정한다.
2. Solar Pro 3 호출 없이 fake provider와 validator로 output contract를 검증한다.
3. 기존 private 7건 dev subset의 input fingerprint와 metric grain이 유지되는지 dry-run한다.
4. repaired v2 후보가 live 재실험 가치가 있는지 readiness report로 판단한다.
5. 별도 승인 후에만 Solar Pro 3 live paired comparison을 실행한다.

## 정량 Gate

| gate | 기준 |
| --- | --- |
| live call boundary | 계획/validator 단계 Solar Pro 3 호출 0 |
| prompt leakage | raw prompt 공개 0 |
| private leakage | raw query, raw answer, raw evidence, chunk text, private path, secret 공개 0 |
| schema validity | invalid `used_evidence_pack_ranks` 0 |
| evidence floor | query type별 최소 evidence 선택 규칙 위반 0 |
| no-answer regression | abstain path 유지, live call 0 |
| v1 fallback rule | blocker/risk query type은 fallback 가능해야 함 |
| readiness decision | `ready_for_live_repair_comparison` 또는 `reject_live_repair_comparison` 중 하나 |

future live comparison gate:

| metric | 기준 |
| --- | --- |
| Correct-with-Evidence | v1보다 하락하지 않음 |
| citation_precision | v1보다 하락하지 않음 |
| citation_recall | v1보다 하락하지 않음 |
| unsupported_claim_rate | v1보다 증가하지 않음 |
| abstention_accuracy | 1.000000 유지 |
| latency_p95_ms | 악화 시 원인 기록 |
| claim boundary | 7건 dev 결과를 최종 개선으로 표현하지 않음 |

## 정성 Gate

| 항목 | 확인 기준 |
| --- | --- |
| coverage | 답변에 필요한 근거를 과도하게 줄이지 않는다. |
| minimality | 답변에 쓰지 않은 evidence를 citation으로 붙이지 않는다. |
| risk discipline | 근거가 부족하면 unsupported risk를 높이거나 abstain한다. |
| voice style | `spoken_answer`는 짧고 citation marker를 포함하지 않는다. |
| regression guard | 기존 안정 query type의 성능을 깨지 않는다. |

정성 리뷰에는 raw answer와 raw evidence를 public 문서에 기록하지 않는다. 필요하면 private review note에 sanitized tag만 저장한다.

## Data Mart 설계

`fact_generation_prompt_repair_eval`의 grain은 `repair_id + query_type + prompt_policy_id + eval_stage + metric_family`다.

| field | 설명 |
| --- | --- |
| `repair_id` | prompt repair 실험 id |
| `source_comparison_id` | 기존 v1/v2 comparison id |
| `query_type` | 평가 query type |
| `prompt_policy_id` | repaired prompt policy id |
| `eval_stage` | plan, validator, dry_run, live_comparison |
| `metric_family` | correctness, citation, unsupported, latency, safety, cost |
| `metric_value` | public-safe aggregate value |
| `decision_tag` | sanitized decision tag |
| `claim_boundary` | plan-only, dev-only, locked-only 등 |

dimension 후보:

- `dim_prompt_policy`
- `dim_query_type`
- `dim_eval_stage`
- `dim_metric_family`
- `dim_claim_boundary`

free-text query, raw answer, raw evidence, raw prompt, chunk text는 fact에 저장하지 않는다.

## 작업 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-SOLAR-024 | HD-SOLAR-023 | Solar Pro 3 generation v2 prompt repair 계획 작성 | 계획 문서, 평가 리포트, TODO/README 갱신, Solar call 0, leakage scan 0 | Medium | 문서 revert |
| HD-SOLAR-025 | HD-SOLAR-024 | repaired v2 prompt policy validator 구현 | 완료. unit test, fake provider test, evidence floor violation test, Solar call 0, public-safe report | Medium | validator와 report revert |
| HD-SOLAR-026 | HD-SOLAR-025 | repaired v2 dry-run/readiness runner 구현 | 기존 7건 dev subset 기준 call budget, fallback route, public-safe report | High | runner/report revert |
| HD-SOLAR-027 | HD-SOLAR-026 + 별도 승인 | repaired v2 Solar Pro 3 live paired comparison | live call cap 준수, paired metric report, public leakage 0 | High | candidate 미채택, public report revert |

## Non-goal

- 이번 단계에서 청킹 ablation을 다시 실행하지 않는다.
- 이번 단계에서 Solar Pro 3를 호출하지 않는다.
- 이번 단계에서 repaired v2를 production 기본값으로 채택하지 않는다.
- 이번 단계에서 GraphRAG/RAPTOR-lite를 시작하지 않는다.
- raw prompt, raw answer, raw evidence, raw query를 public artifact에 기록하지 않는다.

## 포트폴리오 메시지

쓸 수 있는 표현:

- selected evidence contract가 precision을 올렸지만 coverage와 hallucination guard trade-off를 만들었음을 paired metric으로 확인했다.
- locked readiness에서 retrieval repair가 production 근거를 만들지 못하자, generation prompt repair로 실험선을 되돌렸다.
- prompt 전문을 공개하지 않고 policy id, metric, gate만 남기는 방식으로 public/private 경계를 지켰다.
- 청킹 재실험은 근거 없이 반복하지 않고, 실패 원인에 맞춰 다음 실험을 설계했다.

쓰면 안 되는 표현:

- v2 prompt가 성능을 개선했다.
- Solar Pro 3 generation 품질이 최종 개선됐다.
- repaired v2가 production-ready다.
- 청킹이 최적임을 최종 증명했다.
- locked test에서 generation 성능 개선을 확인했다.

## 외부 감사 결론

| 감사 항목 | 결과 |
| --- | --- |
| 실험 순서 | PASS. retrieval repair stop gate 이후 generation repair로 복귀했다. |
| 비용 통제 | PASS. 이번 계획 단계 Solar Pro 3 호출은 0회다. |
| claim boundary | PASS. 성능 개선 주장을 하지 않는다. |
| public boundary | PASS. prompt/raw/private/secret 공개 금지를 명시했다. |
| 청킹 재개 판단 | PASS. 현재 근거로 청킹 재실험을 재개하지 않는다. |
| 다음 구현 가능성 | PASS. validator, dry-run, live comparison 순서가 분리됐다. |

## 결정

HD-SOLAR-024는 문서 gate로 통과한다.

## HD-SOLAR-025 실행 결과

repaired v2 prompt policy validator를 구현했다. 실행은 fake provider/validator 단계이며 Solar Pro 3 live 호출은 수행하지 않았다.

| metric | value |
| --- | ---: |
| row_count | 7 |
| query_type_policy_count | 7 |
| prompt_policy_count | 3 |
| pass_count | 6 |
| fallback_required_count | 1 |
| fail_count | 0 |
| invalid_rank_count | 0 |
| evidence_floor_violation_count | 0 |
| coverage_intent_violation_count | 0 |
| unsupported_risk_violation_count | 0 |
| no_answer_abstain_pass_count | 1 |
| live_solar_call_count | 0 |
| readiness_decision | `ready_for_repaired_prompt_dry_run` |

판단:

- 청킹 비교는 계속 보류한다.
- `place_story`는 v1 fallback monitor case로 분리한다.
- repaired v2는 live comparison이 아니라 dry-run/readiness runner로만 다음 gate에 보낸다.
- 다음 구현 후보는 `HD-SOLAR-026 repaired v2 dry-run/readiness runner`다.
