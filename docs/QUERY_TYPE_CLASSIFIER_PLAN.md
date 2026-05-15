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

## 다음 작업 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-CLASSIFIER-004 | HD-ROUTER-003 | classifier 오분류 3개 failure analysis와 route impact 점검 | public-safe failure tag report, raw query 0, route-risk 분리 | Medium | report/module 변경 revert |
| HD-HYDE-001 | HD-ROUTER-003 | Solar Pro 3 기반 HyDE subset 비교 | 명시 승인, call budget, hallucination guard, public report | High | HyDE candidate 미채택 |
| HD-API-ROUTER-001 | HD-CLASSIFIER-004 | `/chat`에 classifier + router dry-run field 연결 | contract test, retrieval regression 0, raw output leakage 0 | Medium | API field 제거 |
