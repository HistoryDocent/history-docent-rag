# Normalization

## 목적

Upstage Parser의 `document_analysis_results.json`을 RAG 전처리 단위인 `NormalizedBlock`으로 변환한다.

이 단계는 청킹이 아니다. 청킹 전에 parser element를 안정적인 block 계약으로 바꾸고, page/provenance/text hash를 고정하는 단계다.

## 입력

입력 source:

```text
SOURCE_ROOT/01_Data_Preprocessing/{doc_title}/document_analysis_results.json
```

사용하는 parser field:

- `page_elements`
- `text_elements`
- `table_elements`
- `content.text`
- `content.markdown`
- `content.html`
- `category`
- `id`
- `page`

`image_elements`는 이번 단계에서 제외한다.

## 출력

private report:

```text
private_data/reports/normalized_blocks.json
```

public sample:

```text
data_samples/normalized_blocks_sample.json
```

public sample에는 원문 text를 저장하지 않는다. `text_hash`, `text_length`, `page_span`, `element_refs`, `provenance`만 공개한다.

## 변환 규칙

1. 문서별 `document_analysis_results.json`을 읽는다.
2. page key를 숫자로 정렬한다.
3. `text_elements`, `table_elements`만 순회한다.
4. `content.text`, `content.markdown`, `content.html` 순서로 usable text를 찾는다.
5. HTML만 존재하는 경우 tag를 제거하고 whitespace를 정규화한다.
6. 비어 있는 text element는 block으로 만들지 않고 skip count에 기록한다.
7. `element_id`, `element_type`, `page_span`, `provenance`를 보존한다.
8. 원문 text 대신 `text_hash`, `text_length`만 저장한다.

## Page 정책

현재 `page_local`은 parser page number를 그대로 사용한다.

`page_global`은 문서 순서 기준 누적 offset을 더해 계산한다.

```text
page_global = document_page_offset + page_local
```

이 방식은 chunking 전 citation recoverability와 page range 검증을 위한 임시 전역 page 기준이다.

## Gate

통과 기준:

- `normalized_block_count > 0`
- `duplicate_block_id_count == 0`
- `negative_page_global_count == 0`
- `invalid_page_range_count == 0`
- `empty_element_refs_count == 0`
- `missing_text_hash_count == 0`
- `negative_text_length_count == 0`
- `private_path_leakage_count == 0`
- public sample 내 원문 text 0
- public sample 내 private absolute path 0

## 현재 결과

canonical source 기준:

```text
documents=12
blocks=13685
skipped_empty_text=61
failures=0
status=PASS
```

## 감사 메모

첫 실행에서 block이 0개 생성됐다. 원인은 parser의 `content.text`, `content.markdown`이 비어 있고 실제 텍스트가 `content.html`에 들어 있었기 때문이다.

수정 사항:

- `content.html` fallback 추가
- HTML tag 제거
- whitespace 정규화

이 수정 후 13,685개 block이 생성됐고 gate가 통과했다.

## 다음 단계

다음 단계는 chunking이 아니라 parser quality report와 normalized block validation notebook을 먼저 작성하는 것이 더 안전하다.

그 다음 parent-child chunking으로 넘어간다.
