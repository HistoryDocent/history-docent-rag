# Query Type Classifier Plan

## 결론

`HD-ROUTER-003`에서는 query type classifier를 production 완료로 주장하지 않는다.

이번 단계의 목적은 실제 API 입력에 query type label이 없다는 문제를 닫기 위한 deterministic baseline과 평가 gate를 만드는 것이다. classifier는 Solar Pro 3 호출 없이 동작하고, router skeleton에 넣을 `predicted_query_type`을 생성한다.

공개 문서와 리포트에는 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | router skeleton만으로는 실제 API에 연결할 수 없다. classifier baseline이 필요하다. |
| Retrieval | exact label accuracy와 route policy accuracy를 분리해야 한다. default route 내부 오분류보다 relationship/no_answer 오분류가 더 위험하다. |
| Evaluation | 7개 query type coverage, macro F1, confusion matrix, fallback count를 고정 metric으로 둔다. |
| Data warehouse | 평가 row grain은 `run_id + query_id + classifier_id`로 둔다. |
| Security | 결과 row와 report에는 query id, label, metric, rule count만 남긴다. |
| 운영 | deterministic baseline은 CUDA와 LLM이 필요 없다. latency와 비용 기준선을 만들기 좋다. |
| 포트폴리오 | 강점은 classifier를 붙였다는 사실이 아니라 label 정확도와 routing 영향도를 따로 본 점이다. |
| 외부 감사 | private dev 통과는 production claim이 아니다. locked set과 실제 API 로그 검증은 별도다. |

## Input Contract

| field | 설명 | 공개 가능 |
| --- | --- | --- |
| `query_text` | 사용자 발화 본문 | 아니오 |
| `user_context` | 이전 대화 요약 또는 위치 맥락 | 아니오 |
| `place_ids` | 감지된 장소 id 목록 | 제한적 |
| `has_dialog_context` | 이전 대화가 있는지 여부 | 예 |

원칙:

- 일반 query type 판정은 사용자 발화 본문을 우선한다.
- 이전 맥락은 `voice_followup` 판단에만 강하게 사용한다.
- no-answer는 실시간, 예약, 결제, 현재 상태 요청을 우선 감지한다.
- relationship/no_answer 오분류는 route policy가 바뀌므로 별도 metric으로 추적한다.

## Output Contract

| field | 설명 |
| --- | --- |
| `classifier_id` | classifier stable id |
| `predicted_query_type` | router 입력 label |
| `confidence` | deterministic score 기반 confidence |
| `fallback_used` | rule hit이 없을 때 fallback 사용 여부 |
| `matched_rule_ids` | rule id 목록 |
| `candidate_scores` | query type별 score |
| `latency_ms` | CPU 실행 시간 |

## Evaluation Gate

| gate | 기준 |
| --- | ---: |
| query type coverage | 7개 |
| accuracy | 0.800000 이상 |
| macro_f1 | 0.800000 이상 |
| route_policy_accuracy | 0.950000 이상 |
| fallback_rate | 0.300000 이하 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| live_solar_call_count | 0 |

## 현재 결과

근거 리포트:

- `evals/reports/query_type_classifier_eval_report.md`

| metric | value |
| --- | ---: |
| query_count | 70 |
| query_type_count | 7 |
| correct_count | 67 |
| accuracy | 0.957143 |
| macro_precision | 0.963203 |
| macro_recall | 0.957143 |
| macro_f1 | 0.956818 |
| route_policy_correct_count | 68 |
| route_policy_accuracy | 0.971429 |
| fallback_count | 0 |
| fallback_rate | 0.000000 |
| public_raw_text_leakage_count | 0 |
| live_solar_call_count | 0 |

## Data Mart 설계

`fact_query_type_classification`의 grain은 `run_id + query_id + classifier_id`다.

| field | 설명 |
| --- | --- |
| `run_id` | classifier eval run id |
| `query_id` | public-safe query id |
| `classifier_id` | classifier stable id |
| `expected_query_type` | 평가셋 label |
| `predicted_query_type` | classifier 예측 label |
| `correct` | exact label 일치 여부 |
| `confidence` | confidence score |
| `fallback_used` | fallback 여부 |
| `matched_rule_count` | rule count |
| `route_expected_policy_id` | expected label 기준 route |
| `route_predicted_policy_id` | predicted label 기준 route |
| `route_policy_correct` | route policy 일치 여부 |

금지 필드:

- raw query
- raw answer
- raw evidence
- prompt
- chunk text
- private path
- secret

## 한계

- deterministic rule baseline이라 표현 변화에 취약하다.
- private dev 70개 기준 통과이며 production 사용자 로그 검증이 아니다.
- 현재 결과는 classifier 평가이지 retrieval/generation 품질 개선 주장이 아니다.
- `relationship`과 `overview` 경계는 여전히 혼동 가능성이 있다.

## Failure Analysis 결과

`HD-CLASSIFIER-004`에서 classifier baseline의 오분류 3건을 route impact 기준으로 분리했다.

근거 리포트:

- `evals/reports/query_type_classifier_failure_analysis_report.md`

| metric | value |
| --- | ---: |
| query_count | 70 |
| failure_count | 3 |
| failure_rate | 0.042857 |
| route_risk_failure_count | 2 |
| route_risk_failure_rate | 0.028571 |
| default_route_internal_failure_count | 1 |
| false_hybrid_route_count | 2 |
| missed_hybrid_route_count | 0 |
| false_abstain_count | 0 |
| missed_abstain_count | 0 |
| no_answer_failure_count | 0 |
| public_raw_text_leakage_count | 0 |

해석:

- no-answer 관련 오분류는 없다.
- 위험은 default query가 relationship hybrid route로 잘못 이동하는 false hybrid route다.
- `/chat`에 바로 active route로 연결하지 말고, 먼저 classifier/router dry-run field로 노출한다.
- active routing은 relationship guard를 추가한 뒤 별도 gate로 판단한다.

## API Dry-run 연결 결과

`HD-API-ROUTER-001`에서 `/api/v1/chat` 응답에 `classifier_router_dry_run` field를 추가했다.

근거 리포트:

- `evals/reports/chat_api_contract_report.md`
- `evals/reports/chat_retrieval_integration_report.md`

| metric | chat contract | retrieval integration |
| --- | ---: | ---: |
| classifier_dry_run_count | 3 | 3 |
| classifier_route_policy_changed_count | 2 | 1 |
| classifier_active_route_applied_count | 0 | 0 |
| classifier_fallback_count | 0 | 1 |
| classifier_guarded_route_candidate_count | 3 | 3 |
| classifier_guard_applied_count | 1 | 0 |
| live_solar_call_count | 0 | 0 |
| public_raw_text_leakage_count | 0 | 0 |

해석:

- classifier/router 판단은 API 응답에서 관찰 가능하다.
- active retrieval route는 아직 바꾸지 않는다.
- `route_policy_changed`는 운영 전 guard 설계를 위한 관찰 지표이지 성능 개선 지표가 아니다.
- `guarded_route_candidate`는 relationship guard 결과를 관찰하기 위한 dry-run field이며 active route에는 적용하지 않는다.

## Relationship Route Guard 평가 결과

`HD-CLASSIFIER-005`에서 `relationship` 예측에만 적용하는 보수적 guard를 추가했다.

근거 리포트:

- `evals/reports/relationship_route_guard_eval_report.md`

| metric | baseline | guarded |
| --- | ---: | ---: |
| correct_count | 67 | 69 |
| accuracy | 0.957143 | 0.985714 |
| route_policy_correct_count | 68 | 70 |
| route_policy_accuracy | 0.971429 | 1.000000 |
| false_hybrid_route_count | 2 | 0 |
| missed_hybrid_route_count | 0 | 0 |

추가 gate:

- `no_answer_route_regression_count=0`
- `active_route_applied_count=0`
- `public_raw_text_leakage_count=0`
- `live_solar_call_count=0`

해석:

- 이번 guard는 active routing 적용이 아니다.
- false hybrid route를 dev 70 기준 2건에서 0건으로 줄였지만, production routing 완료로 표현하면 안 된다.
- API dry-run field에는 guarded route 후보 노출을 완료했다.
- failure analysis 10개 제출용 정리, `place_story` targeted chunk audit, HyDE subset readiness, HyDE live paired retrieval comparison, HyDE larger dev subset readiness, HyDE larger dev live paired retrieval comparison도 완료했다. 다음 단계는 HyDE가 아니라 active routing 적용 여부 판단 계획이다.

## 다음 작업 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-HYDE-001D | HD-HYDE-001C | HyDE larger dev live paired retrieval comparison | Solar call budget 준수, no-answer guard, public report | High | 완료, HyDE 기본 route 기각 |
| HD-API-ROUTER-003 | query type classifier/router docs | active routing 적용 여부 판단 계획 | route-risk, guard, locked gate 기준 정리 | Medium | active route 미적용 |
