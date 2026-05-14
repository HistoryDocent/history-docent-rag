# Solar Pro 3 Guarded Boost Live 비교 계획

## 결론

다음 단계는 청킹 비교 테스트가 아니라 `parent_doc_context_boost_guarded`의 Solar Pro 3 live paired comparison이다.

단, 이 문서는 실행 계획이다. Solar Pro 3를 호출하지 않았고 live 품질 개선을 주장하지 않는다.

HD-012 input-only 결과에서 `guarded_boost`는 baseline safety metric을 유지하면서 candidate 1건만 통과시켰다. 따라서 live 호출 전에는 query set, 중복 호출 방지, 비용 상한, 중단 조건, public-safe report 구조를 먼저 고정해야 한다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | `guarded_boost`는 전역 retrieval 기본값이 아니라 `place_story` 전용 router 후보로만 검증한다. |
| Generation | baseline과 guarded 입력이 동일한 query는 중복 live 호출하지 않고 baseline 결과를 재사용한다. |
| Evaluation | query 단위 paired comparison으로만 해석한다. dev 10건 결과를 전체 성능 개선으로 주장하지 않는다. |
| Data warehouse | live 결과 fact grain은 `run_id + query_id + strategy_id + answer_contract_version + router_policy_id`다. |
| Security | public report에는 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 남기지 않는다. |
| Portfolio | “candidate 부작용 발견 -> guardrail 설계 -> input-only 검증 -> live 비교 계획” 흐름을 보여준다. |
| 외부 감사 | 비용과 외부 API 호출이 있으므로 실행 전 별도 승인이 필요하다. |

## 비교 목적

검증 질문:

1. `guarded_boost`가 Solar Pro 3 실제 답변에서도 baseline의 correctness와 citation precision을 유지하는가.
2. input-only에서 보인 citation recall 소폭 개선이 live answer citation metric으로 이어지는가.
3. guarded router가 live generation의 unsupported claim 또는 spoken answer 품질을 악화시키지 않는가.

검증하지 않는 것:

- 전체 RAG 시스템의 최종 성능
- locked test split 성능
- GraphRAG/RAPTOR 대비 우위
- 청킹 전략 변경 효과
- frontend 또는 voice UI 품질

## 비교 대상

| 항목 | baseline | candidate |
| --- | --- | --- |
| query scope | private `place_story` dev 10개 | 동일 |
| retrieval label | `baseline_dense_e5_voice_rewrite` | `parent_doc_context_boost_guarded` |
| router policy | 없음 | `place_story_guarded_boost_v1` |
| packing policy | `P0_rank_order` | `P0_rank_order` |
| answer contract | `citation-rag-answer/v1` | 동일 |
| LLM model | `solar-pro3` | 동일 |
| temperature | 기존 provider 기본값 또는 0 계열 deterministic 설정 | 동일 |
| max context chars | 11000 | 동일 |

`parent_doc_context_boost_always`는 live 비교 대상에서 제외한다. HD-012에서 correctness, precision, doc coverage, evidence order regression이 확인됐기 때문이다.

## 호출 예산과 중복 호출 정책

기본 정책:

- baseline 10건은 live 호출한다.
- guarded 입력을 생성한 뒤 baseline 입력 fingerprint와 비교한다.
- prompt/evidence/context fingerprint가 동일한 query는 baseline generation 결과를 재사용한다.
- fingerprint가 다른 query만 candidate live 호출한다.

예상 호출 수:

| 조건 | 예상 call |
| --- | ---: |
| baseline 전체 실행 | 10 |
| HD-012 기준 guarded changed input | 1 |
| 총 예상 call | 11 |
| reuse 비활성화 시 상한 | 20 |

중단 조건:

- `UPSTAGE_API_KEY`가 없거나 provider health check가 실패하면 실행하지 않는다.
- total live call 예상치가 20을 넘으면 실행하지 않는다.
- candidate changed input이 0건이면 live candidate 호출 없이 계획을 재검토한다.
- Solar response schema invalid가 발생하면 즉시 중단하고 private failure row만 남긴다.

## 정량 평가 기준

Primary metric:

- `Correct-with-Evidence`
- `citation_precision`
- `citation_recall`
- `unsupported_claim_rate`

Secondary metric:

- `place_relevance`
- `docent_usefulness`
- `spoken_answer_naturalness`
- `abstention_accuracy`
- `latency_p50_ms`
- `latency_p95_ms`
- `solar_call_count`
- `total_tokens`
- `estimated_cost`

통과 기준:

| gate | 기준 |
| --- | --- |
| public safety | raw text/private path/secret leakage count 0 |
| schema validity | Solar structured output invalid count 0 |
| correctness | candidate `Correct-with-Evidence`가 baseline보다 낮아지지 않음 |
| citation precision | candidate `citation_precision`이 baseline보다 낮아지지 않음 |
| citation recall | candidate `citation_recall`이 baseline 이상 |
| unsupported claim | candidate `unsupported_claim_rate`가 baseline보다 높아지지 않음 |
| spoken answer | candidate `spoken_answer_naturalness`가 baseline보다 낮아지지 않음 |
| latency/cost | 악화 시 delta와 원인을 report에 기록 |
| claim boundary | dev 10건 결과를 최종 개선 주장으로 표현하지 않음 |

개선 주장 후보로만 인정하려면 다음 조건을 모두 만족해야 한다.

- `Correct-with-Evidence` 하락 없음
- `citation_precision` 하락 없음
- `citation_recall` 상승
- public leakage 0
- changed input query에서 정성적으로 evidence 사용이 더 좋아진 tag 존재

## 정성 평가 기준

정성 평가는 raw answer를 public에 쓰지 않고 sanitized tag만 기록한다.

| tag | 의미 |
| --- | --- |
| `evidence_used_better` | candidate가 더 직접적인 evidence를 사용함 |
| `citation_minimality_better` | 불필요한 citation이 줄어듦 |
| `story_context_better` | 장소와 역사 맥락 연결이 더 자연스러움 |
| `answer_too_broad` | 답변이 evidence보다 넓게 일반화됨 |
| `citation_overselect` | 답변에 쓰지 않은 evidence까지 citation으로 붙음 |
| `unsupported_detail` | evidence에 없는 세부 주장이 생김 |
| `spoken_answer_regression` | 음성 답변이 길거나 현장성이 떨어짐 |
| `no_material_change` | 의미 있는 차이가 없음 |

## Data Mart 설계

`fact_solar_guarded_boost_live_eval`의 grain은 `run_id + query_id + strategy_id + answer_contract_version + router_policy_id`다.

| field | 설명 |
| --- | --- |
| `run_id` | live 비교 실행 id |
| `query_id` | public-safe query id |
| `query_type` | `place_story` |
| `strategy_id` | baseline 또는 guarded strategy |
| `router_policy_id` | candidate는 `place_story_guarded_boost_v1`, baseline은 `none` |
| `answer_contract_version` | `citation-rag-answer/v1` |
| `input_fingerprint` | prompt/evidence/context fingerprint |
| `reused_from_strategy_id` | 중복 입력 재사용 여부 |
| `solar_call_count` | query-strategy 단위 live call 수 |
| `latency_ms` | live call latency |
| `total_tokens` | provider usage token |
| `correct_with_evidence` | query-level correctness metric |
| `citation_precision` | query-level citation precision |
| `citation_recall` | query-level citation recall |
| `unsupported_claim` | unsupported claim 여부 |
| `qualitative_tags` | public-safe failure/success tag |

`fact_solar_guarded_boost_paired_delta`의 grain은 `run_id + query_id + baseline_strategy_id + candidate_strategy_id`다.

dimension 후보:

- `dim_generation_strategy`
- `dim_router_policy`
- `dim_answer_contract`
- `dim_query_type`
- `dim_eval_split`
- `dim_run`

## 산출물

| 산출물 | 공개 여부 | 설명 |
| --- | --- | --- |
| `docs/SOLAR_GUARDED_BOOST_LIVE_COMPARISON_PLAN.md` | public | 실행 전 계획 문서 |
| `evals/reports/solar_guarded_boost_live_comparison_report.md` | public 가능 | aggregate metric, paired delta, public-safe gate |
| `private_data/evals/results/solar_guarded_boost_live_comparison_rows.jsonl` | private | raw text 없는 query-level metric row |

public report에 기록할 수 있는 것:

- query id
- strategy id
- aggregate metric
- paired delta
- qualitative tag
- latency/call/token aggregate
- leakage count

public report에 기록하지 않는 것:

- raw query
- raw answer
- raw spoken answer
- raw evidence/context
- prompt
- chunk text
- private file path
- API key 또는 credential

## 실행 전 승인 Gate

실제 live 호출 전 사용자가 승인해야 하는 항목:

| 항목 | 승인 기준 |
| --- | --- |
| query scope | private `place_story` dev 10개로 제한 |
| call budget | 예상 11회, hard cap 20회 |
| duplicate reuse | 동일 fingerprint는 baseline 결과 재사용 |
| public boundary | raw text와 private path public 저장 금지 |
| stop condition | schema invalid, leakage, call cap 초과 시 중단 |
| claim boundary | 결과를 final benchmark로 주장하지 않음 |

## 구현 단위

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-SOLAR-013 | HD-PLACE-STORY-012 | guarded boost live comparison 계획 문서화 | README/TODO 링크, leakage scan, live call 0 | Medium | 문서 revert |
| HD-SOLAR-014 | HD-SOLAR-013 승인 | Solar Pro 3 guarded boost live comparison dry-run runner 구현 | 완료. unit test, dry-run, public-safe report, Solar call 0 | High | runner/report revert |
| HD-SOLAR-015 | HD-SOLAR-014 | Solar Pro 3 guarded boost live paired comparison runner 구현 | 완료. readiness mode, dry-run 재검증, call cap 확인, Solar call 0 | High | runner/report revert |
| HD-SOLAR-016 | HD-SOLAR-015 승인 | 승인 후 live paired comparison 실행 | 완료. live report, public leakage 0, call count/cost 기록 | High | candidate 미채택, public report revert |
| HD-SOLAR-017 | HD-SOLAR-016 | guarded boost next gate 판단 문서화 | 완료. dev-only 승격 판단, claim boundary, 청킹 재개 조건 정리 | Low | 문서 revert |
| HD-SOLAR-018 | HD-SOLAR-017 | 추가 dev hard-case 검증 계획 문서화 | 완료. hard-case bucket, 정량/정성 gate, data mart grain 정리, Solar call 0 | Low | 문서 revert |
| HD-SOLAR-019 | HD-SOLAR-018 | guarded boost hard-case validation runner 구현 | 완료. bucket coverage 10/10, route mismatch 0, Solar call 0, public leakage 0 | Medium | runner/report revert |
| HD-SOLAR-020 | HD-SOLAR-019 | router threshold 유지/수정 판단 문서화 | 완료. threshold 유지, 완화/강화 기각, production 채택 보류 | Low | 문서 revert |

## HD-SOLAR-014 실행 결과

Solar Pro 3를 호출하지 않고 dry-run runner를 실행했다. 실행 device는 `cuda`다.

| metric | value |
| --- | ---: |
| query_count | 10 |
| baseline_live_call_count | 10 |
| candidate_live_call_count | 1 |
| expected_total_live_call_count | 11 |
| live_call_hard_cap | 20 |
| reused_candidate_count | 9 |
| changed_candidate_input_count | 1 |
| selected_candidate_count | 1 |
| guardrail_block_count | 9 |
| solar_call_count | 0 |
| hard_cap_exceeded | False |

Reuse decision:

| reuse_decision | count |
| --- | ---: |
| `candidate_live_call_required` | 1 |
| `reuse_baseline_result` | 9 |

Public output gate:

| metric | value |
| --- | ---: |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

판단:

- live 실행 전 input fingerprint와 call budget이 계획 범위 안에 있다.
- candidate live call은 1건만 필요하다.
- 이 결과는 live 품질 개선 주장이 아니다.
- 다음 단계는 live 호출이 아니라 live paired comparison runner 구현 및 실행 전 승인이다.

## HD-SOLAR-015 실행 결과

Solar Pro 3 guarded boost live paired comparison readiness runner를 구현했다. 기본 실행은 live 호출을 수행하지 않고 dry-run 재검증, call cap 확인, public-safe readiness report 생성까지만 수행한다. 실행 device는 `cuda`다.

| metric | value |
| --- | ---: |
| dry_run_gate_passed | True |
| call_cap_passed | True |
| public_safety_passed | True |
| readiness_decision | `ready_for_live_execution_approval` |
| expected_total_live_call_count | 11 |
| baseline_live_call_count | 10 |
| candidate_live_call_count | 1 |
| reused_candidate_count | 9 |
| changed_candidate_input_count | 1 |
| live_call_hard_cap | 20 |
| live_execution_requested | False |
| live_execution_confirmed | False |
| live_call_executed | False |
| solar_call_count | 0 |

Reuse decision:

| reuse_decision | count |
| --- | ---: |
| `candidate_live_call_required` | 1 |
| `reuse_baseline_result` | 9 |

Public output gate:

| metric | value |
| --- | ---: |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

판단:

- runner는 실제 live 실행 전 readiness check까지 완료한다.
- 이번 단계에서 Solar Pro 3 실제 호출은 0회다.
- dev 10건 live 품질 개선 주장은 아직 없다.
- 다음 단계는 HD-SOLAR-016 실제 live 실행 승인 여부 결정이다.

## HD-SOLAR-016 실행 결과

Solar Pro 3 guarded boost live paired comparison을 private `place_story` dev 10개에서 실행했다.

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

Live call summary:

| metric | value |
| --- | ---: |
| baseline_live_call_count | 10 |
| candidate_live_call_count | 1 |
| reused_candidate_count | 9 |
| expected_total_live_call_count | 11 |
| actual_solar_call_count | 11 |
| live_call_hard_cap | 20 |
| total_tokens | 29737 |
| estimated_cost | 0.000000 |

Public output gate:

| metric | value |
| --- | ---: |
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

판단:

- `guarded_boost`는 live 답변에서도 Correct-with-Evidence, citation precision, unsupported claim을 악화시키지 않았다.
- citation recall은 `+0.028572` 개선됐다.
- candidate 1건에서만 실제 입력이 달라졌으므로 전체 성능 개선 주장으로 쓰면 안 된다.
- latency는 candidate changed query 기준 증가했고, 전체 p95도 `+388.989500ms` 증가했다.
- 결정은 `promote_guarded_candidate_for_next_gate`다.
- 다음 단계는 locked test가 아니라 dev-only 결과 해석과 next gate 판단 문서화다.

## HD-SOLAR-017 판단 결과

[Solar Pro 3 Guarded Boost Next Gate Decision](SOLAR_GUARDED_BOOST_NEXT_GATE_DECISION.md)에 HD-SOLAR-016 결과 해석과 다음 gate 조건을 고정했다.

결정:

- `parent_doc_context_boost_guarded`는 next gate로 승격한다.
- production 기본값 채택은 보류한다.
- 청킹 비교 재개는 보류한다.
- 추가 Solar Pro 3 반복 호출은 별도 승인 전까지 보류한다.
- 다음 작업은 추가 live call이 아니라 추가 dev hard-case 검증 계획 작성이다.

## 외부 감사 체크

| 감사 항목 | 기대 결과 |
| --- | --- |
| 변수 통제 | retrieval/router 외 generation 조건 동일 |
| 비용 통제 | call budget과 reuse 정책 존재 |
| 데이터 보안 | public artifact leakage count 0 |
| metric grain | query fact와 summary fact를 분리 |
| 결과 해석 | dev 10건 결과를 최종 성능으로 주장하지 않음 |
| 재현성 | strategy id, router policy id, fingerprint 기록 |

## 다음 액션

1. HD-SOLAR-021 locked test 승인 계획은 완료됐다.
2. HD-SOLAR-022 locked test readiness dry-run runner도 완료됐다.
3. locked `place_story` 5건에서 candidate live call 대상이 0건이라 locked live paired comparison은 보류한다.
4. HD-SOLAR-023 next gate 판단에서 `place_story_guarded_boost_v1` production 채택을 기각했다.
5. 다음 작업은 HD-SOLAR-024 Solar Pro 3 generation v2 prompt repair 계획 작성이다.
6. 추가 Solar Pro 3 호출이 필요하면 별도 승인과 call budget을 먼저 고정한다.
7. 최종 성능 개선 주장은 locked test와 bootstrap confidence interval 이후에만 작성한다.
