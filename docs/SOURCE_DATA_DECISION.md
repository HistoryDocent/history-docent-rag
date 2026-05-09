# Source Data Decision

## 결정

`History_Docent` 폴더를 canonical source로 사용한다.

다른 복제본은 원본 데이터 기준으로 사용하지 않는다.

## 사용 데이터 별칭

| 별칭 | 의미 | Git 추적 |
|---|---|---|
| `SOURCE_ROOT` | canonical source root | 금지 |
| `PDF_DIR` | 원본 PDF 12권 위치 | 금지 |
| `PARSER_DIR` | Upstage Parser 전처리 산출물 위치 | 금지 |
| `LEGACY_CHUNK_FILE` | 기존 chunk 결과 참고 파일 | 금지 |

실제 절대 경로는 local 실행 환경에서만 주입한다. 공개 문서와 sample에는 기록하지 않는다.

## 제외 데이터

| 후보 | 제외 사유 |
|---|---|
| `git_repo` | parser 산출물 일부가 0바이트 |
| `git_repo_2` | parser 산출물과 기존 chunk 파일에 0바이트 파일 존재 |

## 데이터 Grain

| Grain | 정의 | 후속 사용 |
|---|---|---|
| `document` | PDF 1권 | manifest, 평가 breakdown |
| `parser_run` | parser 실행 결과 1회 | lineage |
| `page` | 문서 내 페이지 1개 | citation page range |
| `element` | parser element 1개 | normalization 원천 |
| `normalized_block` | RAG 전처리용 정규화 블록 1개 | chunk 생성 |
| `chunk` | 검색 단위 1개 | retrieval/generation |
| `eval_query` | 평가 질문 1개 | retrieval/generation 평가 |

하나의 fact 안에서 서로 다른 grain을 섞지 않는다.

## 첫 번째 Gate

`source_inventory` gate는 청킹 전에 통과해야 한다.

통과 기준:

- 원본 PDF 12권 확인
- parser document 12개 확인
- `document_analysis_results.json` 12개 확인
- parser 산출물 0바이트 파일 0개 확인
- 문서별 batch JSON 수 기록
- 문서별 `page_elements` 수 기록
- 기존 `all_chunks.json`의 chunk 수와 노이즈 신호 기록
- public sample 내 private absolute path 0개
- public sample 내 원문 긴 텍스트 0개

## 공개 정책

공개 허용:

- 집계 count
- 파일명
- 파일 크기
- hash prefix
- schema field 목록
- 품질 warning

공개 금지:

- 원본 PDF
- 전체 parser JSON
- 전체 OCR text
- 전체 chunk text
- private absolute path
- API key 또는 `.env`

## 다음 단계

`source_inventory` 결과가 통과하면 `data_manifest`와 `normalized_blocks` schema 구현으로 이동한다.

청킹은 그 다음 단계다.
