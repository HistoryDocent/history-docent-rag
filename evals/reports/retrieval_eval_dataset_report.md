# Retrieval Eval Dataset Report

## 목적

retrieval 평가셋 v2 contract와 split gate를 검증한다.

이 리포트는 성능 개선 결과가 아니다. Dense/Hybrid/Reranker 비교 전에 평가셋의 grain, split, judgment, 공개 정책을 고정하기 위한 정량/정성 보고서다.

full dev/test benchmark는 public repository에 직접 저장하지 않는다. public에는 seed/sample과 집계 report만 남기고, full benchmark path는 public report에서 alias로만 표기한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `retrieval-eval-dataset-report/v1` |
| dataset_path | `evals/datasets/retrieval_eval_seed.jsonl` |
| dataset_version | `retrieval-eval-dataset/v2` |
| contract_status | `PASS` |
| split_readiness_status | `FAIL` |

## v2 Contract

`RetrievalEvalItem`의 grain은 질문 1개다.

필수 metadata:

| field | 설명 |
| --- | --- |
| `split` | `seed`, `dev`, `test` 중 하나 |
| `difficulty` | `easy`, `medium`, `hard` 중 하나 |
| `place_ids` | public-safe place catalog id 목록 |
| `requires_context` | user_context 또는 대화 맥락 필요 여부 |
| `answerability` | `answerable` 또는 `unanswerable` |
| `review_status` | `draft`, `reviewed`, `locked` 중 하나 |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 14 |
| judgment_count | 12 |
| retrieve_query_count | 12 |
| abstain_query_count | 2 |
| dataset_version_mismatch_count | 0 |
| query_type_min_shortfall_count | 0 |
| dev_query_count | 0 |
| test_query_count | 0 |
| dev_target_shortfall_count | 70 |
| test_target_shortfall_count | 35 |
| duplicate_query_id_count | 0 |
| missing_metadata_count | 0 |
| answerability_mismatch_count | 0 |
| voice_followup_context_missing_count | 0 |
| requires_context_count | 4 |
| place_id_count | 7 |
| missing_required_query_type_count | 0 |
| missing_expected_target_count | 0 |
| judgment_query_mismatch_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |

## Split Distribution

| split | query_count |
| --- | ---: |
| seed | 14 |

## Query Type Coverage

| query_type | current_seed | current_dev | current_test | target_dev | target_test |
| --- | ---: | ---: | ---: | ---: | ---: |
| place_fact | 2 | 0 | 0 | 10 | 5 |
| place_story | 2 | 0 | 0 | 10 | 5 |
| relationship | 2 | 0 | 0 | 10 | 5 |
| overview | 2 | 0 | 0 | 10 | 5 |
| route_context | 2 | 0 | 0 | 10 | 5 |
| voice_followup | 2 | 0 | 0 | 10 | 5 |
| no_answer | 2 | 0 | 0 | 10 | 5 |

## Query Type by Split

| split | query_type | query_count |
| --- | --- | ---: |
| seed | no_answer | 2 |
| seed | overview | 2 |
| seed | place_fact | 2 |
| seed | place_story | 2 |
| seed | relationship | 2 |
| seed | route_context | 2 |
| seed | voice_followup | 2 |

## Metadata Distribution

| field | distribution |
| --- | --- |
| difficulty | `{'easy': 3, 'hard': 8, 'medium': 3}` |
| answerability | `{'answerable': 12, 'unanswerable': 2}` |
| review_status | `{'reviewed': 14}` |

## Gate Result

```text
contract_failures=[]
split_readiness_failures=['missing_dev_split', 'missing_test_split', 'dev_query_type_target_shortfall', 'test_query_type_target_shortfall']
```

## 정성 리포트

- 현재 `seed` split은 smoke test다. 최종 성능 주장에는 사용하지 않는다.
- dev/test split readiness는 아직 FAIL이다. 이 리포트의 PASS/FAIL은 contract와 readiness를 분리해 해석한다.
- v2 metadata는 dev/test 확장 전에 query grain과 judgment 정책을 고정하기 위한 장치다.
- `voice_followup`은 `requires_context=true`를 강제해 대화 맥락 없는 검색과 구분한다.
- `no_answer`는 `answerability=unanswerable`과 positive judgment 없음으로 환각 방지 평가에 사용한다.
- public dataset에는 원문 answer, chunk text, OCR text, parser text, private path를 포함하지 않는다.
- public evaluation example은 원문 직접 인용 없이 직접 작성한 paraphrase만 허용한다.

## 다음 단계

1. query type별 private dev 10개, private test 5개 목표를 채운다.
2. test split은 최종 ablation 전까지 튜닝에 사용하지 않는다.
3. Dense/Hybrid 비교는 이 v2 contract가 유지된 상태에서만 진행한다.
