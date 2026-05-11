# Retrieval Eval Review Rubric

## 목적

retrieval dev/test 평가셋을 실험에 사용하기 전에 `draft`, `reviewed`, `locked` 상태의 의미와 승격 기준을 고정한다.

이 문서는 성능 개선 결과가 아니다. 질문과 gold judgment가 비교 평가에 사용할 수 있는지 판단하는 검수 기준이다.

## 상태 정의

| status | 의미 | 사용 가능 범위 |
| --- | --- | --- |
| `draft` | 작성은 되었지만 검수 전 | report와 target 검증만 가능 |
| `reviewed` | dev tuning에 사용할 수 있도록 검수 통과 | chunking, retriever, reranker 비교의 dev set |
| `locked` | 최종 test set으로 고정 | 최종 ablation 확인에만 사용 |

금지:

- `draft` 항목으로 성능 개선 주장.
- `test` 항목을 dev tuning에 사용.
- `locked` 이후 query text, target, answerability 수정.
- 원문 PDF, parser text, chunk text를 public report에 포함.

## 검수 단위

검수 grain은 `RetrievalEvalItem` 1개다.

필수 key:

- `query.query_id`
- `query.query_type`
- `query.query_text`
- `query.expected_behavior`
- `judgments`
- `metadata.split`
- `metadata.difficulty`
- `metadata.place_ids`
- `metadata.requires_context`
- `metadata.answerability`
- `metadata.review_status`

## Hard Gate

다음 항목 중 하나라도 실패하면 `reviewed` 또는 `locked`로 승격하지 않는다.

| gate | 통과 기준 |
| --- | --- |
| schema | `dataset_version=retrieval-eval-dataset/v2` |
| split | dev 검수는 `split=dev`, test 검수는 `split=test` |
| review status | dev는 `reviewed`, test는 `locked` |
| query type | 7개 query type 모두 포함 |
| answerability | `answerability`와 `expected_behavior` 일치 |
| answerable target | answerable query는 positive judgment와 child target 포함 |
| no-answer | `no_answer`는 positive judgment 없음 |
| voice followup | `voice_followup`은 `requires_context=true`와 `user_context` 포함 |
| target resolvability | child, parent, doc target 누락 0 |
| public safety | 원문 필드, private path, secret-like 값 0 |

## Query Type별 검수 기준

| query_type | 검수 질문 |
| --- | --- |
| `place_fact` | 특정 장소에 대한 사실 질문이며, 답이 단일 문서/근거에만 과도하게 의존하지 않는가 |
| `place_story` | 관광객에게 들려줄 이야기형 답변의 근거를 요구하는가 |
| `relationship` | 장소, 인물, 사건, 제도 중 최소 2개 이상의 관계를 요구하는가 |
| `overview` | 단편 사실보다 상위 흐름과 요약 문맥을 요구하는가 |
| `route_context` | 여러 장소를 하나의 동선으로 연결하는 질문인가 |
| `voice_followup` | 질문 단독으로는 불완전하고 이전 발화 복원이 필요한가 |
| `no_answer` | corpus 밖 실시간 정보, 예약, 추천, 운영 정보 등을 요구하는가 |

## Gold Judgment 기준

우선순위:

1. `relevant_child_ids`
2. `relevant_parent_ids`
3. `relevant_doc_ids`

규칙:

- metric 계산은 child target을 우선한다.
- child target이 없으면 parent target을 fallback으로 쓴다.
- child와 parent target이 모두 없을 때만 doc target을 fallback으로 쓴다.
- answerable query는 최소 child target 1개를 가져야 한다.
- 여러 chunk가 같은 답을 담으면 최대 3~4개 수준으로 유지한다.
- target resolvability는 ID 존재만 검증한다. 역사적 정답성은 이후 실패 분석에서 별도 확인한다.

## Public Safety 기준

public artifact 허용:

- query text
- query type
- public-safe rationale summary
- target id
- aggregate metric

public artifact 금지:

- 원본 PDF
- 전체 parser JSON
- OCR/parser/chunk 원문
- raw answer text
- private absolute path
- API key, token, secret
- vector index와 embedding cache

자동 gate 한계:

- private path, secret-like pattern, 긴 raw text는 자동 탐지한다.
- 짧은 원문 직접 인용과 near-verbatim paraphrase는 자동 탐지만으로 충분하지 않다.
- `reviewed` 승격 시 public-safe rationale이 원문 요약이 아니라 직접 작성한 판단 요약인지 수동 확인한다.

## Private Dev 검수 기준

대상:

```text
<private retrieval eval dataset: retrieval_eval_dev.jsonl>
```

공통 승격 조건:

- split = `dev`
- review_status = `reviewed`
- target missing count = 0
- public leakage count = 0
- no_answer positive target count = 0
- voice_followup context missing count = 0

1차 검수 결과:

- query_count = 35
- dev_query_count = 35
- query type별 dev 5개
- reviewed_query_count = 35
- target missing count = 0
- public leakage count = 0

최종 dev 검수 조건:

- query_count = 70
- dev_query_count = 70
- query type별 dev 10개
- draft_query_count = 0
- reviewed_query_count = 70
- target missing count = 0
- public leakage count = 0
- no_answer positive target count = 0
- voice_followup context missing count = 0

## Private Test Lock 기준

대상:

```text
<private retrieval eval dataset: retrieval_eval_test.jsonl>
```

lock 조건:

- split = `test`
- review_status = `locked`
- query_count = 35
- test_query_count = 35
- query type별 test 5개
- answerable_query_count = 30
- no_answer_query_count = 5
- draft_query_count = 0
- reviewed_query_count = 0
- locked_query_count = 35
- target missing count = 0
- public leakage count = 0
- no_answer positive target count = 0
- voice_followup context missing count = 0

현재 private dev 70개는 `reviewed`, private test 35개는 `locked` 상태다. 성능 개선 주장은 chunking/retrieval/generation ablation 실행 전까지 금지한다.
