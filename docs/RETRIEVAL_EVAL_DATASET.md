# Retrieval Eval Dataset

## 목적

BM25, Dense, Hybrid retrieval을 같은 질문 집합에서 비교하기 위한 seed 평가셋을 고정한다.

이 문서는 성능 개선 결과가 아니라 평가 계약과 데이터셋 품질 보고서다.

## 파일

| 항목 | 경로 |
| --- | --- |
| seed dataset | `evals/datasets/retrieval_eval_seed.jsonl` |
| contract module | `app/domain/retrieval.py` |
| notebook | `notebooks/06_bm25_baseline_evaluation.ipynb` |
| tests | `tests/test_retrieval_eval_dataset.py` |

## Query Type

| query_type | 의도 |
| --- | --- |
| `place_fact` | 장소에 대한 사실 근거 검색 |
| `place_story` | 관광객에게 들려줄 짧은 이야기 근거 검색 |
| `relationship` | 장소, 인물, 사건의 관계 검색 |
| `overview` | 큰 흐름 요약을 위한 상위 문맥 검색 |
| `route_context` | 여러 장소를 이어 설명하는 코스 문맥 검색 |
| `voice_followup` | 지시어와 이전 발화를 복원해야 하는 음성형 후속 질문 |
| `no_answer` | corpus 밖 질문을 거절해야 하는 질문 |

## 정량 리포트

| metric | value |
| --- | ---: |
| dataset_version | `retrieval-eval-dataset/v1` |
| query_count | 14 |
| judgment_count | 12 |
| retrieve_query_count | 12 |
| abstain_query_count | 2 |
| query_type_count | 7 |
| query_per_type | 2 |
| missing_required_query_type_count | 0 |
| missing_expected_target_count | 0 |
| judgment_query_mismatch_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |

## 정성 리포트

현재 seed는 서울/한양 도슨트 서비스의 핵심 실패 유형을 먼저 덮는다.

- `place_fact`: 경복궁, 종묘처럼 장소명이 명확한 질문.
- `place_story`: 광화문/세종, 북촌/남촌처럼 현장 설명성이 필요한 질문.
- `relationship`: 경복궁-한양 천도-정도전, 창덕궁-왕자의 난-이방원처럼 관계 추론이 필요한 질문.
- `overview`: 한양 천도와 조선 궁궐의 정치적 의미처럼 상위 문맥이 필요한 질문.
- `route_context`: 광화문-경복궁-종묘, 한양도성-북촌처럼 이동 경로가 들어간 질문.
- `voice_followup`: "거기", "그 사람"처럼 이전 발화 없이는 검색 의도가 불완전한 질문.
- `no_answer`: 현대 카페 추천, 실시간 막차 시간처럼 corpus 밖 질문.

판정값은 원문 텍스트를 공개하지 않고 `child_id`, `parent_id`, `doc_id`만 포함한다. 따라서 public repository에서는 저작권 원문 없이 평가 계약과 데이터셋 품질만 검증한다.

Metric 계산에서는 가장 세밀한 target을 우선한다.

- `relevant_child_ids`가 있으면 child hit만 relevance로 본다.
- child target이 없고 `relevant_parent_ids`가 있으면 parent hit를 relevance로 본다.
- child/parent target이 없을 때만 `relevant_doc_ids`를 fallback relevance로 본다.
- 동일 `method + query_id` run result가 중복되면 계산을 실패 처리한다.

## 한계

현재 dataset은 seed다. 최종 성능 주장에는 부족하다.

- 질문 수가 14개라 통계적 개선 주장을 할 수 없다.
- judgment는 1차 seed라 single-annotator 기준이다.
- 일부 질문은 여러 문서가 정답이 될 수 있으므로 최종 평가 전 `child_id` 단위 판정을 보강해야 한다.
- `voice_followup`은 user_context를 명시했지만 실제 대화 memory resolver는 아직 구현하지 않았다.

## 통과 기준

초기 gate는 다음을 모두 만족해야 한다.

- 필수 query type 7개 모두 포함.
- 각 query type 최소 2개 이상.
- `retrieve` 질문은 최소 하나의 expected target 포함.
- `no_answer` 질문은 positive judgment 없음.
- public dataset에 원문 필드 없음.
- public dataset에 private path 없음.

## 개선 주장 규칙

이 평가셋으로는 "BM25 baseline을 측정했다"까지만 주장한다.

성능 개선 주장은 다음 조건 이후에만 가능하다.

- 평가셋 50개 이상.
- query type별 최소 5개 이상.
- BM25, Dense, Hybrid를 같은 질문과 같은 judgment로 비교.
- paired comparison.
- bootstrap 10,000회.
- 95% confidence interval.
- `Correct-with-Evidence +3%p` 이상 또는 retrieval metric의 명확한 개선.
- latency/cost 악화 설명 포함.
