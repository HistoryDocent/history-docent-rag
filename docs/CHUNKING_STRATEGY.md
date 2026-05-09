# Parent-Child Chunking Strategy

## 목적

이 문서는 `NormalizedBlock`을 검색 가능한 chunk로 바꾸기 전에 청킹 전략을 고정한다.

이번 단계는 구현이 아니다. 다음 구현 단계에서 따라야 할 grain, boundary, filtering, provenance, public/private 정책을 정의한다.

## 입력

입력 artifact:

```text
private_data/reports/normalized_blocks.json
private_data/reports/parser_quality_report.json
```

사용 근거:

```text
documents=12
blocks=13685
short_blocks=3121
long_blocks=0
duplicate_hashes=1228
replacement_char_blocks=1273
text_length_p90=257
text_length_p95=298
text_length_max=1016
heading1=2503
paragraph=10296
header=108
footer=724
table=20
```

## 결론

기본 청킹 방식은 다음으로 고정한다.

```text
Heading-aware Parent Chunk
+ Block-merge Child Chunk
+ Citation Provenance Recovery
```

fixed-size character chunking은 기본 전략으로 사용하지 않는다.

이유:

- parser block 길이 p95가 298자로 짧다.
- `heading1` block이 2,503개 존재해 문서 구조 boundary로 사용할 수 있다.
- `header`, `footer`, 중복 text hash가 검색 노이즈를 만들 가능성이 높다.
- 관광 도슨트 답변은 문맥 단위 검색과 근거 citation을 동시에 요구한다.

## Grain

| 계약 | Grain | 설명 |
|---|---|---|
| `ParentChunk` | 한 문서 안의 heading section 또는 story section 1개 | retrieval 후 context expansion 단위 |
| `ChildChunk` | 한 parent 안의 검색 단위 1개 | BM25, dense, hybrid index의 기본 row |
| `ChunkSourceRef` | child가 참조하는 normalized block 1개 | citation recoverability 검증 단위 |
| `ChunkingQualityReport` | chunking run 1회 | gate와 품질 지표 보고 단위 |

하나의 `ChildChunk`는 하나의 `ParentChunk`에만 속한다.

하나의 `ParentChunk` 또는 `ChildChunk`는 문서 경계를 넘지 않는다.

## ParentChunk 정책

`ParentChunk`는 문맥 확장 단위다.

필수 필드:

- `parent_id`
- `doc_id`
- `doc_title`
- `parser_run_id`
- `title`
- `heading_block_id`
- `source_block_ids`
- `page_span`
- `child_ids`
- `quality_flags`
- `public_allowed`

생성 규칙:

1. `doc_id`별로 block을 page/order 기준 정렬한다.
2. `heading1`을 primary parent boundary로 사용한다.
3. 문서 시작부터 첫 `heading1` 전까지의 block은 `front_matter` parent로 묶는다.
4. parent는 다음 `heading1` 직전까지의 block을 포함한다.
5. parent는 문서 경계를 넘지 않는다.
6. parent가 `soft_max_chars`를 초과하면 같은 parent 내부에서 page 또는 다음 heading-like block 기준으로 분할한다.
7. `header`, `footer` block은 provenance에는 남기되 retrieval child 생성 대상에서는 제외한다.
8. 검색 대상 block이 없는 parent는 최종 `ParentChunk`로 발행하지 않고 `filtered_parent_count`에 기록한다.

## ChildChunk 정책

`ChildChunk`는 검색 index의 기본 단위다.

필수 필드:

- `child_id`
- `parent_id`
- `doc_id`
- `parser_run_id`
- `source_block_ids`
- `page_span`
- `text_hash`
- `text_length`
- `element_type_mix`
- `citation_refs`
- `quality_flags`
- `public_allowed`

생성 규칙:

1. child는 parent 내부 block만 사용한다.
2. child는 `child_target_chars`에 가깝게 block을 병합한다.
3. `child_min_chars`보다 짧은 block은 단독 child로 만들지 않고 인접 paragraph/list/table 설명과 병합한다.
4. `child_max_chars`를 초과하면 block boundary 기준으로 분할한다.
5. `heading1`은 parent title과 child context metadata로 사용하고, 단독 검색 child로 만들지 않는다.
6. `table`은 별도 provenance를 보존한다. table text가 child에 포함되면 `has_table=true` flag를 부여한다.
7. `header`, `footer`는 retrieval child에 포함하지 않는다.
8. 원문 text는 private chunk artifact에만 저장한다.
9. public sample은 chunk id, block id, hash, length, page span, metric만 저장한다.

## 기본 수치

기본 설정은 [chunking.default.yaml](../configs/chunking.default.yaml)을 따른다.

| 설정 | 값 | 근거 |
|---|---:|---|
| `short_block_threshold_chars` | 20 | parser quality report의 short block 기준 |
| `child_min_chars` | 250 | p90 257자 근처로 짧은 단독 chunk 방지 |
| `child_target_chars` | 700 | p95 298자 기준 2-4개 block 병합 |
| `child_max_chars` | 1100 | 현재 max block 1016자보다 약간 큰 상한 |
| `child_overlap_blocks` | 1 | 문맥 손실 완화 |
| `parent_soft_max_chars` | 6000 | retrieval 후 context packing 가능 범위 유지 |

`parent_soft_max_chars=6000`은 parser 품질 수치가 아니라 context expansion을 위한 engineering parameter다. `child_target_chars=700` 기준 약 8개 child 이내로 parent를 유지해 retrieval 후 evidence packing이 과도하게 커지는 것을 막는다.

`child_min_chars=250`은 `text_length_p90=257`, `text_length_p95=298` 근처의 값이다. 짧은 heading/footer성 block이 단독 검색 단위가 되는 것을 막기 위한 하한이다.

## Citation 정책

최종 citation은 child text가 아니라 원천 `NormalizedBlock` 기준으로 회수한다.

필수 조건:

- `source_block_ids`가 모두 존재해야 한다.
- `page_span`은 참조 block들의 page range를 포함해야 한다.
- `citation_refs`는 `block_id`, `doc_id`, `source_file_name`, `page_span`, `element_refs`를 복구할 수 있어야 한다.
- answer generation 단계의 citation은 parent summary나 graph node가 아니라 원문 block 기준만 허용한다.

## Public/Private 정책

private 허용:

- full chunk text
- parser artifact alias
- chunk generation intermediate
- failure sample with text

public 허용:

- chunk schema
- config
- aggregate metric
- hash
- id
- page span
- text length
- 소량의 익명화 sample

public 금지:

- 원본 PDF
- 전체 parser JSON
- 전체 OCR text
- 전체 chunk text
- private absolute path
- API key 또는 secret

## 실험과의 관계

이 전략은 기본 retrieval pipeline의 기준선이다.

RAPTOR-lite와 GraphRAG-lite는 이 chunking 결과 위에서만 비교한다.

- RAPTOR-lite는 `overview`, `place_story`, `route_context` 질문에 한해 비교한다.
- GraphRAG-lite는 `relationship` 질문에 한해 비교한다.
- 두 실험 모두 최종 citation은 원문 `NormalizedBlock` 기준만 허용한다.

## 다음 구현 작업

1. `ChunkSourceRef`, `ParentChunk`, `ChildChunk`, `ChunkingQualityReport` schema를 구현한다.
2. `build_parent_child_chunks.py` pipeline을 만든다.
3. `04_chunking_quality_analysis.ipynb`에서 chunking report를 검증한다.
4. `CHUNKING_GATES.md` 기준으로 gate를 통과시킨다.
