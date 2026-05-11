# Retrieval Eval Target Resolvability Report

## 목적

retrieval 평가셋의 judgment target이 실제 검색 corpus에 존재하는지 검증한다.

이 리포트는 성능 개선 결과가 아니다. dev/test 평가셋 확장과 retrieval ablation 전에 정답 target의 corpus 매핑 가능성을 고정하기 위한 정량/정성 보고서다.

full dev/test benchmark는 public repository에 직접 저장하지 않는다. public에는 seed/sample과 집계 report만 남기고, full benchmark path는 public report에서 alias로만 표기한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-eval-target-resolvability/v1` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| target_resolvability_status | `PASS` |

## Grain

`RetrievalEvalItem`의 grain은 질문 1개다.

target resolvability의 검증 grain은 judgment target 1개다.

검증 대상:

- `relevant_child_ids`
- `relevant_parent_ids`
- `relevant_doc_ids`

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 70 |
| judgment_count | 60 |
| answerable_query_count | 60 |
| no_answer_query_count | 10 |
| searchable_child_count | 3141 |
| searchable_parent_count | 1882 |
| searchable_doc_count | 12 |
| judgment_target_count | 393 |
| child_target_count | 171 |
| resolved_child_target_count | 171 |
| missing_child_target_count | 0 |
| parent_target_count | 140 |
| resolved_parent_target_count | 140 |
| missing_parent_target_count | 0 |
| doc_target_count | 82 |
| resolved_doc_target_count | 82 |
| missing_doc_target_count | 0 |
| answerable_without_child_or_parent_target_count | 0 |
| no_answer_with_positive_target_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

## Gate Result

```text
target_resolvability_failures=[]
```

## 정성 리포트

- target ID는 실제 검색 가능한 child corpus 기준으로 검증한다.
- answerable query는 최소 child 또는 parent target을 가져야 한다.
- `no_answer` query는 positive target을 가지면 안 된다.
- public report에는 원문 chunk text, parser text, OCR text, private path, secret-like 값을 포함하지 않는다.
- 이 gate를 통과해야 dev/test 평가셋 확장과 chunking ablation을 신뢰할 수 있다.

## 다음 단계

1. private test 평가 문항 35개를 locked 상태로 작성한다.
2. private test target resolvability와 public-safety gate를 통과시킨다.
3. chunking ablation은 동일 target contract를 유지한 상태에서 실행한다.
