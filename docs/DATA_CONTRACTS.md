# Data Contracts

## 목적

Upstage Parser 산출물을 바로 chunk로 변환하지 않는다.

먼저 문서, parser 실행, parser artifact, normalized block의 데이터 계약을 고정한다. 이 계약은 이후 parser normalization, chunking, retrieval, citation 평가의 기준선이다.

## Grain

| 계약 | Grain | 설명 |
|---|---|---|
| `SourceDocument` | PDF 1권 | 원본 문서 단위 |
| `ParserRun` | parser 실행 1회 | 동일 parser 설정과 source set 기준 실행 단위 |
| `ParserArtifact` | parser 산출물 파일 1개 | `document_analysis_results.json`, batch JSON/PDF 등 |
| `NormalizedBlock` | 정규화 텍스트 블록 1개 | chunk 전 단계의 RAG 원천 블록 |
| `PageSpan` | block의 page 범위 1개 | local/global page 검증 기준 |
| `ElementReference` | parser element 참조 1개 | block과 parser element 연결 |
| `BlockProvenance` | block provenance 1개 | citation recoverability 기준 |

하나의 계약 안에서 서로 다른 grain을 섞지 않는다.

## SourceDocument

필수 필드:

- `doc_id`
- `doc_title`
- `source_file_name`
- `source_sha256_prefix`
- `source_size_bytes`
- `public_allowed`

정책:

- `source_file_name`은 파일명만 저장한다.
- 원본 PDF 절대 경로는 저장하지 않는다.
- public repo에 PDF 원문은 포함하지 않는다.

## ParserRun

필수 필드:

- `parser_run_id`
- `parser_model`
- `source_alias`
- `document_count`
- `artifact_count`
- `created_at_utc`

정책:

- `parser_run_id`는 source document hash prefix와 artifact 크기 기반 digest로 생성한다.
- parser 실행 단위가 달라지면 `parser_run_id`도 달라진다.

## ParserArtifact

필수 필드:

- `parser_run_id`
- `doc_id`
- `artifact_kind`
- `parser_artifact_path_alias`
- `file_name`
- `size_bytes`
- `sha256_prefix`
- `top_level_keys`
- `page_count`
- `private_path_reference_count`
- `public_allowed`

정책:

- `parser_artifact_path_alias`는 `PARSER_DIR/...` 형식만 허용한다.
- Windows drive path, absolute path는 schema validation에서 거부한다.
- parser artifact의 원문 text는 manifest에 저장하지 않는다.

## NormalizedBlock

필수 필드:

- `block_id`
- `doc_id`
- `doc_title`
- `parser_run_id`
- `element_type`
- `page_span`
- `element_refs`
- `text_hash`
- `text_length`
- `provenance`
- `quality_flags`
- `public_allowed`

정책:

- `NormalizedBlock`은 원문 text를 직접 저장하지 않는다.
- `text_hash`와 `text_length`로 추적한다.
- 최종 citation은 `BlockProvenance`와 `ElementReference`를 통해 원문 parser artifact로 회수한다.

## PageSpan

필수 필드:

- `page_local_start`
- `page_local_end`
- `page_global_start`
- `page_global_end`

검증:

- `page_local_start >= 0`
- `page_local_end >= page_local_start`
- `page_global_start >= 0`
- `page_global_end >= page_global_start`

## Gate

`data_manifest` gate 통과 기준:

- `source_document_count == 12`
- `parser_artifact_count >= 12`
- `duplicate_doc_id_count == 0`
- `required_field_null_count == 0`
- `private_path_leakage_count == 0`
- `negative_page_global_count == 0`
- public sample 내 원문 text 0
- public sample 내 private absolute path 0

## 현재 결과

canonical source 기준 `data_manifest` 결과:

```text
source_documents=12
parser_artifacts=12
normalized_blocks=0
failures=0
warnings=0
status=PASS
```

`normalized_blocks=0`은 의도된 상태다. 이번 단계는 block 생성이 아니라 block 계약 고정이다.

## 다음 단계

다음 작업은 parser normalization pipeline이다.

목표:

- `document_analysis_results.json`에서 RAG용 `NormalizedBlock`을 생성한다.
- page/local-global mapping을 고정한다.
- element id와 provenance를 보존한다.
- 원문 text는 private artifact에만 둔다.
