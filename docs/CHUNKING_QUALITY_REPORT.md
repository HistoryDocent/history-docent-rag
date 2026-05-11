# Chunking Quality Report

## 목적

`NormalizedBlock`을 parent-child chunk로 변환한 결과가 retrieval 단계로 넘어갈 수 있는지 정량/정성으로 검증한다.

이 단계는 BM25, dense, hybrid retrieval이 아니다. 검색 단위의 구조, coverage, citation recoverability를 고정하는 단계다.

## 입력

private input:

```text
<private normalized_blocks report>
configs/chunking.default.yaml
```

optional private source:

```text
SOURCE_ROOT/01_Data_Preprocessing/*/document_analysis_results.json
```

source root가 주어지면 private chunk artifact에 child text를 복구한다.

## 출력

private output:

```text
<private parent_child_chunks report>
<private chunking_quality report>
```

public output:

```text
data_samples/chunking_quality_sample.json
```

public sample에는 원문 text를 저장하지 않는다.

## 구현 방식

기본 전략:

```text
Heading-aware Parent Chunk
+ Block-merge Child Chunk
+ Citation Provenance Recovery
```

핵심 규칙:

- `heading1`은 parent boundary로 사용한다.
- `header`, `footer`, `heading1`은 retrieval coverage 분모에서 제외한다.
- child는 parent 내부에서만 만든다.
- child는 문서 경계를 넘지 않는다.
- short block은 가능한 경우 인접 block과 병합한다.
- 최종 citation은 `NormalizedBlock` 기준으로 복구한다.

## 정량 결과

canonical source 기준:

```text
status=PASS
source_blocks=13685
retrievable_blocks=10350
covered_retrievable_blocks=10350
parents=1882
children=3141
filtered_parent_candidates=624
retrievable_block_coverage=1.0000
citation_recoverability=1.0000
child_length_p50=717
child_length_p95=931
parent_length_p50=676
parent_length_p95=2413
micro_parent_count=369
short_standalone_child_count=0
replacement_char_child_rate=0.308819
duplicate_child_text_hash_count=7
```

Hard gate:

```text
duplicate_parent_id_count=0
duplicate_child_id_count=0
orphan_child_count=0
parent_without_child_count=0
empty_child_count=0
missing_source_block_ref_count=0
unknown_element_ref_count=0
invalid_page_range_count=0
cross_document_parent_count=0
cross_document_child_count=0
header_footer_retrieval_child_count=0
table_provenance_loss_count=0
private_path_leakage_count=0
public_sample_raw_text_count=0
public_sample_private_path_count=0
public_candidate_path_secret_leakage_count=0
```

## 정성 평가

| 항목 | 평가 |
|---|---|
| parent boundary | `heading1` 기준으로 parent를 만들었고 문서 경계를 넘지 않는다. |
| short block merge | `short_standalone_child_count=0`으로 검색 단독 노이즈를 줄였다. |
| citation recoverability | 모든 child가 원천 `NormalizedBlock`으로 복구된다. |
| table provenance | `table_provenance_loss_count=0`으로 table block 추적이 유지된다. |
| public data policy | public sample에 원문 text와 private absolute path를 포함하지 않는다. |

## 해석

이 결과는 retrieval 성능 개선을 입증하지 않는다.

입증한 것은 다음이다.

- retrieval 대상 본문 block을 100% child chunk로 회수했다.
- child chunk에서 citation 원천을 100% 복구할 수 있다.
- header/footer는 retrieval child에 섞이지 않았다.
- parent-child chunk가 문서 경계를 넘지 않는다.
- public sample에 원문 text를 노출하지 않았다.

## 남은 리스크

`replacement_char_child_rate=0.308819`가 높다.

이 값은 parser/OCR 품질 이슈가 child chunk까지 전달된다는 뜻이다. 현재 gate에서는 차단하지 않고 retrieval failure analysis 항목으로 추적한다.

`micro_parent_count=369`도 남아 있다.

이는 `heading1` 기반 parent boundary가 너무 촘촘한 구간이 있다는 뜻이다. retrieval 평가에서 short query나 place query의 recall이 낮으면 parent merge 정책을 비교 실험해야 한다.

`duplicate_child_text_hash_count=7`은 낮지만 0은 아니다.

반복되는 짧은 문장 또는 유사 metadata성 block이 child에 남아 있을 수 있다. BM25 baseline에서 false positive 원인으로 확인한다.

## 다음 단계

다음 작업은 place catalog seed가 아니라 BM25 baseline 구현 전 최소 retrieval input 점검이다.

우선순위:

1. `04_chunking_quality_analysis.ipynb`로 chunk 결과를 재현한다.
2. BM25 index 입력 contract를 정의한다.
3. BM25 baseline retrieval과 평가셋 초안을 만든다.
4. 그 다음 place catalog seed를 retrieval query type 분석과 연결한다.
