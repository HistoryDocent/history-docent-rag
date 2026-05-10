# 데이터 정책

## Public Repository 원칙

이 저장소는 public repository다. 저작권이 있는 원문 데이터를 대량 포함하지 않는다.

## 금지

- 원본 PDF
- 전체 parser JSON outputs
- 전체 OCR text
- 전체 generated chunks
- vector database files
- source text가 포함된 전체 raw evaluation CSV 또는 JSONL
- API keys
- local `.env` files

## 허용

- 코드
- schema
- config
- aggregate metrics
- 소량의 redacted samples
- 문서
- 긴 원문 복사 없이 직접 작성한 evaluation examples

## Benchmark 공개 범위

retrieval benchmark는 public sample과 private full benchmark를 분리한다.

public repository에 허용:

- `evals/datasets/retrieval_eval_seed.jsonl`
- `evals/datasets/retrieval_eval_public_sample.jsonl`
- `evals/reports/*.md`
- aggregate metrics
- public-safe schema, config, test code

public repository에 금지:

- `evals/datasets/retrieval_eval_dev*.jsonl`
- `evals/datasets/retrieval_eval_test*.jsonl`
- full benchmark 전체 원본
- raw judgment 작성 메모
- source text가 포함될 수 있는 evaluation artifact

full benchmark 기본 경로:

```text
private_data/evals/datasets/retrieval_eval_dev.jsonl
private_data/evals/datasets/retrieval_eval_test.jsonl
```

public report는 private benchmark의 집계값만 기록한다.

## Sample Data 규칙

sample은 schema와 동작 확인 용도로만 사용한다.

권장 제한:

- parser sample: 1~2 pages
- chunk sample: 5~10 chunks
- evaluation sample: 10~20 examples

## Evaluation 작성 규칙

public evaluation example은 직접 작성한 질문과 public-safe rationale만 허용한다.

금지:

- 원문 문장 직접 인용
- OCR/parser/chunk text 복사
- 책 본문을 짧게 잘라 넣은 단일 라인
- source page의 표현을 거의 그대로 옮긴 문장
- private absolute path
- API key, token, secret

허용:

- 사용자가 실제 관광지에서 물어볼 법한 직접 작성 질문
- 원문 표현이 아닌 paraphrase rationale
- `child_id`, `parent_id`, `doc_id` 같은 target identifier
- query type, split, difficulty, answerability 같은 metadata

자동 leakage gate는 private path, secret-like pattern, 긴 raw text, 금지 field를 탐지한다.
짧은 원문 인용 여부는 자동 검출만으로 충분하지 않으므로 human review에서 확인한다.

## 문서 언어 규칙

README와 docs 문서는 한글로 작성한다.

다음은 영어를 유지한다.

- code identifier
- API field
- config key
- metric name
- file name

## Commit Check

push 전 확인:

```bash
git status
git diff --cached --stat
git diff --cached
```

다음 항목이 포함된 commit은 거부한다.

- secrets
- source PDFs
- bulk parser output
- bulk OCR text
- vector DB artifacts
