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

## Sample Data 규칙

sample은 schema와 동작 확인 용도로만 사용한다.

권장 제한:

- parser sample: 1~2 pages
- chunk sample: 5~10 chunks
- evaluation sample: 10~20 examples

## 문서 언어 규칙

README와 docs 문서는 한글로 작성한다.

다음은 영어를 유지한다.

- code identifier
- API field
- config key
- metric name
- file name
- commit message

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
