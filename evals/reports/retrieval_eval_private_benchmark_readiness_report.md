# Retrieval Eval Private Benchmark Readiness Report

## 목적

private dev 70개와 private test 35개가 같은 retrieval ablation benchmark로 사용할 준비가 되었는지 검수한다.

이 리포트는 성능 개선 결과가 아니다. dev/test split, review status, target resolvability, public-safety gate를 통과했는지 확인하는 benchmark readiness report다.

full dev/test benchmark는 public repository에 직접 저장하지 않는다. public에는 seed/sample과 집계 report만 남기고, full benchmark path는 public report에서 alias로만 표기한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-eval-private-benchmark-readiness/v1` |
| dev_dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| test_dataset_path | `<private retrieval eval dataset: retrieval_eval_test.jsonl>` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_version | `retrieval-eval-dataset/v2` |
| benchmark_readiness_status | `PASS` |
| expansion_readiness_status | `PASS` |
| review_readiness_status | `PASS` |
| target_resolvability_status | `PASS` |
| public_safety_status | `PASS` |

## Benchmark Contract

검수 단위는 `RetrievalEvalItem` 1개다.

통과 기준:

1. 전체 query 수는 105개다.
2. query type별 dev 10개, test 5개다.
3. dev split은 70개이고 모두 `review_status=reviewed`다.
4. test split은 35개이고 모두 `review_status=locked`다.
5. answerable query는 90개, `no_answer` query는 15개다.
6. answerable query는 child target을 가진다.
7. 모든 child/parent/doc target은 검색 가능한 corpus에 존재한다.
8. public-safe field에 원문 직접 인용, private path, secret-like 값이 없다.

## 정량 리포트

| metric | value |
| --- | ---: |
| target_query_count | 105 |
| current_query_count | 105 |
| overall_shortfall_count | 0 |
| dev_query_count | 70 |
| test_query_count | 35 |
| dev_test_current_query_count | 105 |
| dev_test_shortfall_count | 0 |
| answerable_query_count | 90 |
| no_answer_query_count | 15 |
| draft_query_count | 0 |
| reviewed_query_count | 70 |
| locked_query_count | 35 |
| voice_followup_query_count | 15 |
| voice_followup_context_missing_count | 0 |
| requires_context_without_user_context_count | 0 |
| answerable_without_child_target_count | 0 |
| answerable_without_child_or_parent_target_count | 0 |
| no_answer_with_positive_target_count | 0 |
| judgment_target_count | 483 |
| child_target_count | 201 |
| parent_target_count | 170 |
| doc_target_count | 112 |
| missing_child_target_count | 0 |
| missing_parent_target_count | 0 |
| missing_doc_target_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

## Query Type Benchmark Matrix

| query_type | dev | test | draft | reviewed | locked | target_dev | target_test | dev_shortfall | test_shortfall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| place_fact | 10 | 5 | 0 | 10 | 5 | 10 | 5 | 0 | 0 |
| place_story | 10 | 5 | 0 | 10 | 5 | 10 | 5 | 0 | 0 |
| relationship | 10 | 5 | 0 | 10 | 5 | 10 | 5 | 0 | 0 |
| overview | 10 | 5 | 0 | 10 | 5 | 10 | 5 | 0 | 0 |
| route_context | 10 | 5 | 0 | 10 | 5 | 10 | 5 | 0 | 0 |
| voice_followup | 10 | 5 | 0 | 10 | 5 | 10 | 5 | 0 | 0 |
| no_answer | 10 | 5 | 0 | 10 | 5 | 10 | 5 | 0 | 0 |

## Gate Result

```text
contract_failures=[]
expansion_readiness_failures=[]
review_readiness_failures=[]
target_resolvability_failures=[]
public_safety_failures=[]
rubric_failures=[]
gate_failures=[]
```

## 정성 리포트

- private benchmark는 dev 70개, test 35개로 구성된다.
- dev는 chunking/embedding/retriever tuning과 실패 분석에 사용한다.
- test는 최종 비교와 회귀 확인에만 사용하고, 실험 중간 의사결정에는 사용하지 않는다.
- 90개 answerable query는 child target을 포함한다. 이후 metric 계산은 child target을 우선한다.
- 15개 `no_answer` query는 `expected_behavior=abstain`이며 positive judgment가 없다.
- target resolvability는 ID 존재를 검증한다. 역사적 정답성의 최종 보장은 이후 retrieval 실패 분석과 generation review에서 다시 확인해야 한다.

## 다음 단계

1. BM25 기준 chunking ablation runner를 구현한다.
2. dev split에서 chunking 후보를 비교하고, test split은 최종 확인 전까지 열지 않는다.
3. winner 선정 시 `Recall@1/3/5`, `MRR`, `nDCG@5`, `latency_p95`와 query type breakdown을 함께 기록한다.
