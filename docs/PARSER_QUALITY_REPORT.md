# Parser Quality Report

## 목적

청킹 전에 `NormalizedBlock` 품질을 정량 검증한다.

이 문서는 parser 결과가 RAG 입력으로 사용 가능한지 확인하고, 다음 단계의 parent-child chunking 기준을 정하기 위한 근거다.

## 입력

private input:

```text
<private normalized_blocks report>
<private data_manifest report>
```

public output:

```text
data_samples/parser_quality_sample.json
```

private output:

```text
<private parser_quality report>
```

## 지표

| 지표 | 의미 |
|---|---|
| `document_count` | 정규화 블록이 생성된 문서 수 |
| `normalized_block_count` | 생성된 `NormalizedBlock` 수 |
| `block_count_by_doc` | 문서별 block 수 |
| `block_count_by_element_type` | element type별 block 수 |
| `page_count_by_doc` | 문서별 block이 존재하는 page 수 |
| `page_coverage_by_doc` | parser page 대비 block page coverage |
| `text_length_stats` | block 길이 분포 |
| `short_block_count` | threshold 미만의 짧은 block 수 |
| `long_block_count` | threshold 초과의 긴 block 수 |
| `duplicate_text_hash_count` | 동일 text hash 중복 수 |
| `duplicate_block_id_count` | block id 중복 수 |
| `replacement_char_block_count` | OCR replacement character 포함 block 수 |
| `empty_element_refs_count` | element 참조가 없는 block 수 |
| `invalid_page_range_count` | page range 오류 block 수 |
| `missing_provenance_count` | provenance 누락 block 수 |
| `private_path_leakage_count` | private path 누출 수 |

## Gate

통과 기준:

- `document_count == 12`
- `normalized_block_count > 0`
- `duplicate_block_id_count == 0`
- `invalid_page_range_count == 0`
- `empty_element_refs_count == 0`
- `missing_provenance_count == 0`
- `private_path_leakage_count == 0`
- public sample 내 원문 text 0
- public sample 내 private absolute path 0

## 현재 결과

canonical source 기준:

```text
status=PASS
documents=12
blocks=13685
short_blocks=3121
long_blocks=0
duplicate_hashes=1228
failures=0
```

text length:

```text
min=1
max=1016
mean=120.57
p50=111
p90=257
p95=298
```

element type:

```text
paragraph=10296
heading1=2503
footer=724
header=108
list=22
table=20
```

## 해석

청킹으로 바로 넘어가도 되는 최소 gate는 통과했다.

하지만 품질 관점에서 다음 리스크가 있다.

- `short_block_count=3121`: 매우 짧은 heading/footer/header성 block이 많다.
- `duplicate_text_hash_count=1228`: 반복 footer/header/목차성 텍스트가 검색 노이즈가 될 수 있다.
- `replacement_char_block_count=1273`: OCR 깨짐 문자가 포함된 block이 있다.
- `p95=298`, `max=1016`: 대부분 block은 짧고, 긴 block은 많지 않다.

## 청킹 전략 영향

권장 방향:

- 단순 fixed-size character chunking 금지
- `heading1`을 parent boundary 후보로 사용
- `footer`, `header`는 chunking 전 filtering 후보로 분리
- 짧은 block은 단독 chunk보다 인접 paragraph와 병합
- `table`은 별도 metadata와 함께 보존
- 최종 citation은 `block_id`, `page_span`, `provenance` 기반으로 회수

## 다음 단계

다음 작업은 parent-child chunking 설계가 맞다.

단, chunking 구현 전에 다음 결정을 문서화해야 한다.

- parent boundary 기준
- child target token/character 범위
- short block merge 기준
- header/footer filtering 기준
- table 처리 방식
- citation recoverability gate
