# 프로젝트 재설계

## 최종 제품 정체성

History Docent RAG는 서울을 방문한 한국인과 외국인에게 한양의 역사 맥락을 설명하는 관광 도슨트 서비스의 근거 중심 RAG 백엔드다.

포트폴리오에서 주장할 내용은 좁게 잡는다.

> 한국사 도서 parser 결과를 기반으로 서울 주요 장소와 한양 역사 맥락을 연결하고, 근거 기반 관광 도슨트 답변을 생성하는 RAG backend를 설계했다.

RAG 백엔드가 검증되기 전까지 완성형 음성 관광 앱으로 포장하지 않는다.

## 설계 원칙

1. 답변보다 근거를 먼저 설계한다.
2. parser 품질을 RAG 품질의 일부로 본다.
3. 모든 답변은 문서, 페이지, 섹션, chunk로 역추적 가능해야 한다.
4. 현대 서울 장소명과 한양 시대의 역사 개념을 연결하는 place layer를 둔다.
5. retrieval metric과 generation metric을 분리한다.
6. 새로운 RAG 기법은 narrative가 아니라 query type별 metric으로 판단한다.
7. public repo에는 저작권 원문을 대량 포함하지 않는다.

## 핵심 Pipeline

```text
source documents
-> parser outputs
-> canonical elements
-> quality flags
-> place catalog
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

### 2. Place Catalog

서울 관광 도슨트에는 문서 검색만으로 부족하다.

현대 장소명, 역사 명칭, 관련 인물, 사건, 제도를 연결하는 catalog가 필요하다.

필수 field:

- `place_id`
- `modern_name`
- `historical_names`
- `district`
- `coordinates`
- `related_periods`
- `related_people`
- `related_events`
- `related_institutions`
- `related_chunk_ids`
- `public_description`

초기 장소 후보:

- 경복궁
- 광화문
- 북촌
- 종로
- 한양도성
- 창덕궁
- 사직단

### 3. Chunking

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

### 4. Retrieval

Baseline:

- BM25

Main candidate:

- hybrid retrieval: BM25 + dense retrieval
- place-aware query rewrite
- parent context expansion
- citation backtracking

Experimental candidates:

- overview 질문용 RAPTOR-lite
- relationship 질문용 GraphRAG-lite

### 5. Generation

Provider:

- provider abstraction을 통한 Upstage Solar Pro 3

Answer contract:

- `answer`
- `spoken_answer`
- `citations`
- `unsupported_claims`
- `retrieval_trace`
- `latency_ms`
- `estimated_cost`

### 6. API

초기 endpoint:

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `POST /api/v1/chat`
- `POST /api/v1/places/search`

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
Place-aware Hybrid + Query Rewrite + Parent-Child + Citation RAG
```

이유:

- 관광 질문은 “여기”, “이 궁”, “광화문 근처”처럼 장소 의존성이 강하다.
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
- query rewrite, place layer, answer style control 검증 전 voice UI 금지
- GraphRAG-first architecture 금지
- confidence interval 없는 성능 개선 주장 금지
