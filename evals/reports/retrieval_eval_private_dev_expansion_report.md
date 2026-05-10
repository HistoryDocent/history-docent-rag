# Retrieval Eval Expansion Report

## 목적

retrieval 평가셋을 seed smoke test에서 dev/test 비교 평가셋으로 확장하기 위한 작업 현황을 고정한다.

이 리포트는 성능 개선 결과가 아니다. 청킹, Dense, Hybrid, Reranker 비교 전에 질문 수량, split, review status, target resolvability, 공개 안전성을 확인하는 정량/정성 보고서다.

full dev/test benchmark는 public repository에 직접 저장하지 않는다. public에는 seed/sample과 집계 report만 남기고, full benchmark path는 public report에서 alias로만 표기한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-eval-expansion/v1` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_version | `retrieval-eval-dataset/v2` |
| authoring_status | `PASS` |
| expansion_readiness_status | `INCOMPLETE` |
| target_resolvability_status | `PASS` |

## 정량 리포트

| metric | value |
| --- | ---: |
| target_query_count | 105 |
| current_query_count | 35 |
| overall_shortfall_count | 70 |
| seed_query_count | 0 |
| dev_query_count | 35 |
| test_query_count | 0 |
| dev_test_target_query_count | 105 |
| dev_test_current_query_count | 35 |
| dev_test_shortfall_count | 70 |
| draft_query_count | 35 |
| reviewed_query_count | 0 |
| locked_query_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

## Query Type Expansion Matrix

| query_type | seed | dev | test | target_dev | target_test | dev_shortfall | test_shortfall | total_current | target_total | total_shortfall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| place_fact | 0 | 5 | 0 | 10 | 5 | 5 | 5 | 5 | 15 | 10 |
| place_story | 0 | 5 | 0 | 10 | 5 | 5 | 5 | 5 | 15 | 10 |
| relationship | 0 | 5 | 0 | 10 | 5 | 5 | 5 | 5 | 15 | 10 |
| overview | 0 | 5 | 0 | 10 | 5 | 5 | 5 | 5 | 15 | 10 |
| route_context | 0 | 5 | 0 | 10 | 5 | 5 | 5 | 5 | 15 | 10 |
| voice_followup | 0 | 5 | 0 | 10 | 5 | 5 | 5 | 5 | 15 | 10 |
| no_answer | 0 | 5 | 0 | 10 | 5 | 5 | 5 | 5 | 15 | 10 |

## Target Resolvability Snapshot

| metric | value |
| --- | ---: |
| searchable_child_count | 3141 |
| searchable_parent_count | 1882 |
| searchable_doc_count | 12 |
| judgment_target_count | 197 |
| missing_child_target_count | 0 |
| missing_parent_target_count | 0 |
| missing_doc_target_count | 0 |
| answerable_without_child_or_parent_target_count | 0 |
| no_answer_with_positive_target_count | 0 |

## Gate Result

```text
contract_failures=[]
expansion_readiness_failures=['overall_query_target_shortfall', 'missing_test_split', 'dev_query_type_target_shortfall', 'test_query_type_target_shortfall']
target_resolvability_failures=[]
blocking_failures=[]
```

## 정성 리포트

- 현재 입력 평가셋은 dev 35개로 구성되어 있으며 총 35개다.
- 목표는 query type별 dev 10개, test 5개로 총 105개다.
- 현재 전체 부족분은 70개이고, dev/test split 기준 부족분은 70개다. seed는 smoke test로 유지하고 최종 비교 튜닝에는 사용하지 않는다.
- 다음 작성 우선순위는 dev 부족분이 남은 `place_fact`, `place_story`, `relationship`, `overview`, `route_context`, `voice_followup`, `no_answer`다.
- test split은 최종 ablation 확인 전까지 튜닝에 사용하지 않는다.
- public dataset에는 원문 answer, chunk text, OCR text, parser text, private path, secret-like 값을 넣지 않는다.
- public evaluation example은 원문 인용 없이 직접 작성한 paraphrase만 허용한다.
- gold judgment는 가능한 한 `relevant_child_ids`를 우선하고, child 판단이 어려울 때만 parent/doc target을 보조로 둔다.

## 다음 단계

1. query type별 private dev 부족분을 채워 dev 10개씩 맞춘다.
2. target resolvability gate를 통과한 항목만 reviewed로 승격한다.
3. private test 후보 5개는 dev 튜닝 후 별도 locked 상태로 고정한다.
4. 이후 chunking ablation runner를 BM25 기준으로 실행한다.
