# Retrieval Eval Expansion Report

## 목적

retrieval 평가셋을 seed smoke test에서 dev/test 비교 평가셋으로 확장하기 위한 작업 현황을 고정한다.

이 리포트는 성능 개선 결과가 아니다. 청킹, Dense, Hybrid, Reranker 비교 전에 질문 수량, split, review status, target resolvability, 공개 안전성을 확인하는 정량/정성 보고서다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-eval-expansion/v1` |
| dataset_path | `evals/datasets/retrieval_eval_seed.jsonl` |
| chunks_path_alias | `<private parent_child_chunks report>` |
| dataset_version | `retrieval-eval-dataset/v2` |
| authoring_status | `PASS` |
| expansion_readiness_status | `INCOMPLETE` |
| target_resolvability_status | `PASS` |

## 정량 리포트

| metric | value |
| --- | ---: |
| target_query_count | 105 |
| current_query_count | 14 |
| overall_shortfall_count | 91 |
| seed_query_count | 14 |
| dev_query_count | 0 |
| test_query_count | 0 |
| dev_test_target_query_count | 105 |
| dev_test_current_query_count | 0 |
| dev_test_shortfall_count | 105 |
| draft_query_count | 0 |
| reviewed_query_count | 14 |
| locked_query_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

## Query Type Expansion Matrix

| query_type | seed | dev | test | target_dev | target_test | dev_shortfall | test_shortfall | total_current | target_total | total_shortfall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| place_fact | 2 | 0 | 0 | 10 | 5 | 10 | 5 | 2 | 15 | 13 |
| place_story | 2 | 0 | 0 | 10 | 5 | 10 | 5 | 2 | 15 | 13 |
| relationship | 2 | 0 | 0 | 10 | 5 | 10 | 5 | 2 | 15 | 13 |
| overview | 2 | 0 | 0 | 10 | 5 | 10 | 5 | 2 | 15 | 13 |
| route_context | 2 | 0 | 0 | 10 | 5 | 10 | 5 | 2 | 15 | 13 |
| voice_followup | 2 | 0 | 0 | 10 | 5 | 10 | 5 | 2 | 15 | 13 |
| no_answer | 2 | 0 | 0 | 10 | 5 | 10 | 5 | 2 | 15 | 13 |

## Target Resolvability Snapshot

| metric | value |
| --- | ---: |
| searchable_child_count | 3141 |
| searchable_parent_count | 1882 |
| searchable_doc_count | 12 |
| judgment_target_count | 81 |
| missing_child_target_count | 0 |
| missing_parent_target_count | 0 |
| missing_doc_target_count | 0 |
| answerable_without_child_or_parent_target_count | 0 |
| no_answer_with_positive_target_count | 0 |

## Gate Result

```text
contract_failures=[]
expansion_readiness_failures=['overall_query_target_shortfall', 'missing_dev_split', 'missing_test_split', 'dev_query_type_target_shortfall', 'test_query_type_target_shortfall']
target_resolvability_failures=[]
blocking_failures=[]
```

## 정성 리포트

- 현재 평가셋은 query type별 seed 2개씩 총 14개다.
- 목표는 query type별 dev 10개, test 5개로 총 105개다.
- 현재 전체 부족분은 91개지만, dev/test split 기준 부족분은 105개다. seed는 smoke test로 유지하고 최종 비교 튜닝에는 사용하지 않는다.
- 다음 작성 우선순위는 `voice_followup`, `relationship`, `route_context`, `no_answer`다. 이 네 유형이 실제 도슨트 서비스 실패를 가장 많이 드러낸다.
- test split은 최종 ablation 확인 전까지 튜닝에 사용하지 않는다.
- public dataset에는 원문 answer, chunk text, OCR text, parser text, private path, secret-like 값을 넣지 않는다.
- gold judgment는 가능한 한 `relevant_child_ids`를 우선하고, child 판단이 어려울 때만 parent/doc target을 보조로 둔다.

## 다음 단계

1. query type별 dev 후보 10개를 먼저 draft로 작성한다.
2. target resolvability gate를 통과한 항목만 reviewed로 승격한다.
3. test 후보 5개는 dev 튜닝 후 별도 locked 상태로 고정한다.
4. 이후 chunking ablation runner를 BM25 기준으로 실행한다.
