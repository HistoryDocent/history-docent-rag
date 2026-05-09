# 프로젝트 재설계

## 최종 제품 정체성

History Docent RAG는 한국사 질의응답을 위한 근거 중심 RAG 백엔드다.

포트폴리오에서 주장할 내용은 좁게 잡는다.

> 한국사 장문 PDF 기반 RAG pipeline을 parser 품질, citation provenance, retrieval 평가, grounded answer generation 중심으로 재설계했다.

RAG 백엔드가 검증되기 전까지 완성형 소비자 챗봇으로 포장하지 않는다.

## 설계 원칙

1. 답변보다 근거를 먼저 설계한다.
2. parser 품질을 RAG 품질의 일부로 본다.
3. 모든 답변은 문서, 페이지, 섹션, chunk로 역추적 가능해야 한다.
4. retrieval metric과 generation metric을 분리한다.
5. 새로운 RAG 기법은 narrative가 아니라 query type별 metric으로 판단한다.
6. public repo에는 저작권 원문을 대량 포함하지 않는다.

## 핵심 Pipeline

```text
source documents
-> parser outputs
-> canonical elements
-> quality flags
-> parent/child chunks
-> retrieval indexes
-> query rewrite
-> retrieval router
-> evidence packer
-> answer generator
-> citations and eval logs
```

## 모듈 계획

### 1. Parser Normalization

입력:

- 원본 PDF metadata
- Upstage Parser JSON outputs

출력:

- `normalized_blocks.jsonl`
- `data_manifest.json`
- `parser_quality_report.md`

필수 field:

- `doc_id`
- `doc_title`
- `parser_run_id`
- `page_global`
- `page_in_batch`
- `batch_file`
- `element_id`
- `element_type`
- `bbox`
- `raw_text`
- `normalized_text`
- `quality_flags`

### 2. Chunking

기본 chunk 구조:

- child chunk: paragraph-level search unit
- parent chunk: section-level context unit

필수 metadata:

- `chunk_id`
- `parent_chunk_id`
- `doc_id`
- `page_start`
- `page_end`
- `section_path`
- `element_ids`
- `quality_flags`

### 3. Retrieval

Baseline:

- BM25

Main candidate:

- hybrid retrieval: BM25 + dense retrieval
- query rewrite
- parent context expansion
- citation backtracking

Experimental candidates:

- overview 질문용 RAPTOR-lite
- relationship 질문용 GraphRAG-lite

### 4. Generation

Provider:

- provider abstraction을 통한 Upstage Solar Pro 3

Answer contract:

- `answer`
- `citations`
- `unsupported_claims`
- `retrieval_trace`
- `latency_ms`
- `estimated_cost`

### 5. API

초기 endpoint:

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `POST /api/v1/chat`

필수 요구사항:

- schema validation
- timeout
- provider 429/5xx 한정 retry
- rate limit
- stack trace 비노출
- structured logging

## RAG 기법 결정

기본 구조:

```text
Hybrid + Query Rewrite + Parent-Child + Citation RAG
```

이유:

- 한국사 질문은 인물, 연도, 왕조, 사건처럼 정확한 용어가 많다.
- BM25는 정확한 역사 용어 검색에 강하다.
- dense retrieval은 추상 질문과 paraphrase 질문을 보완한다.
- parent-child chunking은 prompt를 과도하게 키우지 않고 문맥을 복구한다.
- citation RAG는 답변의 검증 가능성을 만든다.

RAPTOR-lite:

- 전체 흐름, 배경, 비교 질문에 유리하다.
- 기본 구조가 아니라 실험군으로 둔다.
- summary는 탐색용 node이며 최종 답변 근거가 아니다.

GraphRAG-lite:

- 인물, 사건, 제도 간 관계 질문에 유리하다.
- 기본 구조가 아니라 실험군으로 둔다.
- graph triple은 retrieval hint이며 최종 답변 근거가 아니다.

## 명시적 Non-Goals

- 전체 저작권 원문 공개 금지
- 백엔드 검증 전 대형 frontend 금지
- query rewrite와 answer style control 검증 전 voice UI 금지
- GraphRAG-first architecture 금지
- confidence interval 없는 성능 개선 주장 금지
