# Chunking Gates

## 목적

parent-child chunking 구현 후 통과해야 하는 정량 gate를 정의한다.

이 gate를 통과하기 전에는 BM25, dense, hybrid retrieval 구현으로 넘어가지 않는다.

## 평가 단위

| Report field | 의미 |
|---|---|
| `chunking_run_id` | chunking 설정과 입력 normalized block 기준 run id |
| `parent_chunk_count` | 생성된 parent chunk 수 |
| `child_chunk_count` | 생성된 child chunk 수 |
| `source_block_count` | 입력 normalized block 수 |
| `retrievable_block_count` | header/footer 등 제외 후 검색 대상 block 수 |
| `covered_retrievable_block_count` | child가 참조한 검색 대상 unique block 수 |
| `filtered_parent_count` | 검색 대상 block이 없어 발행하지 않은 parent 후보 수 |
| `citation_recoverability` | child에서 원천 block citation을 복구할 수 있는 비율 |

## Hard Gate

다음 항목은 1개라도 실패하면 chunking 단계 실패다.

| Gate | 통과 기준 |
|---|---:|
| `duplicate_parent_id_count` | 0 |
| `duplicate_child_id_count` | 0 |
| `orphan_child_count` | 0 |
| `parent_without_child_count` | 0 |
| `empty_child_count` | 0 |
| `missing_source_block_ref_count` | 0 |
| `unknown_element_ref_count` | 0 |
| `invalid_page_range_count` | 0 |
| `cross_document_parent_count` | 0 |
| `cross_document_child_count` | 0 |
| `header_footer_retrieval_child_count` | 0 |
| `table_provenance_loss_count` | 0 |
| `private_path_leakage_count` | 0 |
| `public_sample_raw_text_count` | 0 |
| `public_sample_private_path_count` | 0 |
| `public_candidate_path_secret_leakage_count` | 0 |

## Blocking Quality Gate

다음 항목은 retrieval 구현 전 반드시 통과해야 한다.

| Metric | 기준 |
|---|---:|
| `citation_recoverability` | 1.00 |
| `retrievable_block_coverage` | 1.00 |
| `child_length_p95` | `child_max_chars` 이하 |
| `short_standalone_child_count` | 0 |

## Report-Only Metric

다음 항목은 pass/fail 판정에 사용하지 않고 retrieval 실패 분석에만 사용한다.

| Metric | 기준 |
|---|---|
| `child_length_p50` | 보고 필수 |
| `replacement_char_child_rate` | 보고 필수 |
| `duplicate_child_text_hash_count` | 보고 필수 |
| `parent_length_p50` | 보고 필수 |
| `parent_length_p95` | 보고 필수 |
| `micro_parent_count` | 보고 필수 |

`replacement_char_child_rate`와 `duplicate_child_text_hash_count`는 현재 parser 품질상 0을 강제하지 않는다. 대신 retrieval 평가에서 실패 원인 분석 대상으로 추적한다.

## Retrievable Block Coverage 계산

overlap 때문에 block occurrence 기준으로 계산하지 않는다. unique `source_block_id` 기준으로만 계산한다.

분모:

```text
retrievable_block_count
= normalized blocks
  - blocks where element_type in excluded_from_retrieval_element_types
  - blocks where element_type in context_metadata_element_types
  - blocks with empty normalized text
```

분자:

```text
covered_retrievable_block_count
= unique source_block_ids referenced by at least one child chunk
  where source block is included in retrievable_block_count
```

공식:

```text
retrievable_block_coverage = covered_retrievable_block_count / retrievable_block_count
```

목표:

```text
retrievable_block_coverage == 1.00
```

1.00 기준은 deterministic chunking에서 검색 대상 본문 block 손실을 허용하지 않기 위한 무손실 gate다. `header`, `footer`, `heading1`, 비어 있는 block은 분모에서 제외하므로 검색 대상 본문 block은 모두 child에서 회수되어야 한다.

## Citation Recoverability 계산

분모:

```text
all child chunks
```

분자:

```text
source_block_ids가 모두 존재하고,
page_span이 원천 block page range를 포함하고,
citation_refs에서 doc_id, source_file_name, page_span, element_refs를 복구할 수 있는 child chunks
```

공식:

```text
citation_recoverability = recoverable_child_count / child_chunk_count
```

목표:

```text
citation_recoverability == 1.00
```

1.00 기준은 citation RAG에서 근거 회수 실패를 허용하지 않기 위한 무손실 gate다. parser 특이 case 때문에 1.00을 달성하지 못하면 retrieval 구현으로 넘어가지 않고 실패 sample을 분리해 계약 또는 normalization 단계를 수정한다.

## Public Sample 검수

public sample은 다음 필드만 허용한다.

- `parent_id`
- `child_id`
- `doc_id`
- `doc_title`
- `source_block_ids`
- `page_span`
- `text_hash`
- `text_length`
- `element_type_mix`
- `quality_flags`
- `public_allowed`

public sample에는 다음 필드가 있으면 실패다.

- `text`
- `raw_text`
- `content`
- `markdown`
- `html`
- Windows drive path
- user home path
- API key
- token
- password

## Leakage Scan 범위

path와 secret 의심 pattern은 다음 공개 후보 전체를 대상으로 scan한다.

- `data_samples/*.json`
- `configs/*.yaml`
- `docs/*.md`
- `README.md`
- `notebooks/*.ipynb`
- `app/**/*.py`
- `pipelines/**/*.py`
- `tests/**/*.py`
- `pyproject.toml`
- `.env.example`
- `git ls-files -co --exclude-standard`로 얻은 tracked/untracked 공개 후보 파일의 본문
- `git diff`
- `git diff --cached`

검출 규칙:

```text
Windows drive path: [A-Za-z]:\\
user home path: Windows user-home absolute path
secret-like key: sk-[A-Za-z0-9]
credential fields: api_key, apikey, password, token, secret
```

raw text field name은 public sample artifact만 대상으로 검사한다. 문서와 config에는 정책 설명을 위해 `text`, `content`, `html` 같은 단어가 등장할 수 있으므로 field leakage 판정 대상에서 제외한다.

public sample 금지 field:

```text
text, raw_text, content, markdown, html
```

`private_data/...`처럼 repository-relative private artifact alias는 허용한다. 실제 absolute source path는 금지한다.

## Threshold 근거

| Threshold | 값 | 근거 |
|---|---:|---|
| `short_block_threshold_chars` | 20 | parser quality report의 short block 기준 |
| `child_min_chars` | 250 | `text_length_p90=257` 근처로 단독 short child 억제 |
| `child_target_chars` | 700 | `text_length_p95=298` 기준 2-4개 block 병합 |
| `child_max_chars` | 1100 | 현재 `text_length_max=1016`보다 약간 큰 상한 |
| `parent_soft_max_chars` | 6000 | child target 기준 약 8개 child 이내의 context expansion 단위 |
| `citation_recoverability` | 1.00 | citation RAG 근거 회수 무손실 기준 |
| `retrievable_block_coverage` | 1.00 | 검색 대상 본문 block 무손실 기준 |

## 구현 검증 명령

chunking 구현 후 최소 검증 명령은 다음이다.

```bash
python -m pytest -q
python -m ruff check .
python -m mypy app pipelines tests
python -m pipelines.build_parent_child_chunks --source-root "<private-source-root>"
```

`--source-root` 값은 문서에 기록하지 않고 로컬 실행에서만 사용한다.

## 외부 감사 기준

감사 담당자는 다음만 본다.

1. gate가 측정 가능한가.
2. threshold의 근거가 parser quality report 또는 RAG 품질 요구로 명시됐는가.
3. public repo에 원문 또는 private path가 들어가지 않는가.
4. retrieval 성능 개선 주장 전에 chunk 품질 gate가 먼저 고정됐는가.

현재 설계는 chunking 구현 전 gate를 먼저 고정했기 때문에 평가 순서가 맞다.
