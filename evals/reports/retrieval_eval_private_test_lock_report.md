# Retrieval Eval Private Test Lock Report

## 목적

private test 평가셋 35개가 최종 retrieval ablation 검증에 사용할 수 있는 `locked` 상태인지 검수한다.

이 리포트는 성능 개선 결과가 아니다. test split을 튜닝에 사용하지 않기 위해 수량, query type, answerability, context 필요성, target ID 매핑, 공개 안전성을 고정하는 정량/정성 gate다.

full dev/test benchmark는 public repository에 직접 저장하지 않는다. public에는 seed/sample과 집계 report만 남기고, full benchmark path는 public report에서 alias로만 표기한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-eval-test-lock/v1` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_test.jsonl>` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_version | `retrieval-eval-dataset/v2` |
| test_lock_gate_status | `PASS` |
| target_resolvability_status | `PASS` |
| public_safety_status | `PASS` |

## Lock Rubric

검수 단위는 `RetrievalEvalItem` 1개다.

통과 기준:

1. `dataset_version`은 `retrieval-eval-dataset/v2`다.
2. `split=test`이고 `review_status=locked`다.
3. query type은 7개 모두 포함하고, query type별 test 5개다.
4. answerable query는 30개, `no_answer` query는 5개다.
5. `voice_followup`은 `requires_context=true`와 `user_context`를 모두 가진다.
6. `no_answer`는 `expected_behavior=abstain`, `answerability=unanswerable`, positive judgment 없음이다.
7. answerable query는 positive judgment와 child target을 가진다.
8. 모든 child/parent/doc target은 검색 가능한 corpus에 존재한다.
9. public-safe field에 원문 직접 인용, private path, secret-like 값이 없다.

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 35 |
| dev_query_count | 0 |
| test_query_count | 35 |
| answerable_query_count | 30 |
| no_answer_query_count | 5 |
| draft_query_count | 0 |
| reviewed_query_count | 0 |
| locked_query_count | 35 |
| voice_followup_query_count | 5 |
| voice_followup_context_missing_count | 0 |
| requires_context_without_user_context_count | 0 |
| answerable_without_child_target_count | 0 |
| answerable_without_child_or_parent_target_count | 0 |
| no_answer_with_positive_target_count | 0 |
| judgment_target_count | 90 |
| child_target_count | 30 |
| parent_target_count | 30 |
| doc_target_count | 30 |
| missing_child_target_count | 0 |
| missing_parent_target_count | 0 |
| missing_doc_target_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

## Query Type Lock Matrix

| query_type | test | draft | reviewed | locked | target_test | remaining_test_shortfall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| place_fact | 5 | 0 | 0 | 5 | 5 | 0 |
| place_story | 5 | 0 | 0 | 5 | 5 | 0 |
| relationship | 5 | 0 | 0 | 5 | 5 | 0 |
| overview | 5 | 0 | 0 | 5 | 5 | 0 |
| route_context | 5 | 0 | 0 | 5 | 5 | 0 |
| voice_followup | 5 | 0 | 0 | 5 | 5 | 0 |
| no_answer | 5 | 0 | 0 | 5 | 5 | 0 |

## Gate Result

```text
contract_failures=[]
review_readiness_failures=[]
target_resolvability_failures=[]
public_safety_failures=[]
rubric_failures=[]
gate_failures=[]
```

## 정성 리포트

- private test 35개는 query type별 test 5개로 균형이 맞는다.
- 30개 answerable query는 child target을 포함한다. 이후 metric 계산은 child target을 우선한다.
- 5개 `no_answer` query는 `expected_behavior=abstain`이며 positive judgment가 없다.
- 5개 `voice_followup` query는 `requires_context=true`와 `user_context`를 가진다.
- test split은 최종 비교와 회귀 확인에만 사용하고, chunking/embedding/retriever 튜닝 의사결정에는 사용하지 않는다.
- target resolvability는 ID 존재를 검증한다. 역사적 정답성의 최종 보장은 이후 retrieval 실패 분석과 generation review에서 다시 확인해야 한다.
- 자동 gate는 query wording이 실제 지시어형인지, `no_answer`가 실제 corpus 밖인지, rationale이 near-verbatim이 아닌지를 의미론적으로 증명하지 않는다. 이 항목은 lock rubric의 수동 검수 범위로 남긴다.

## 한계

- 이 리포트는 locked test 35개의 데이터 준비 상태를 검수한다.
- retrieval/generation 성능 개선을 주장하지 않는다.
- 성능 개선 주장은 동일 test set에서 paired comparison과 bootstrap confidence interval 조건을 통과한 뒤에만 허용한다.
