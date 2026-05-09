# History Docent RAG

Upstage Parser 결과를 기반으로 한국사 장문 PDF를 구조화하고, 근거 중심 답변을 생성하는 RAG 백엔드 프로젝트.

## 프로젝트 정체성

이 저장소는 일반 챗봇 데모가 아니다.

목표는 다음이다.

- 한국사 장문 PDF의 parser 결과를 정규화한다.
- 문서 구조와 citation provenance를 보존한다.
- 검색 전략을 고정 평가셋으로 비교한다.
- 원문 근거 기반 답변을 생성한다.
- 성능 개선이 통계적으로 유의미한지 검증한다.

## 1차 범위

포함:

- Upstage Parser 결과 정규화
- 구조 보존 parent/child chunking
- BM25 baseline retrieval
- dense retrieval 및 hybrid retrieval 실험
- 짧거나 모호한 음성형 질문을 위한 query rewrite
- Solar Pro 3 기반 citation RAG 답변 생성
- retrieval/generation 평가 harness
- 실패 분석과 ablation report

1차 공개 버전에서 제외:

- 원본 PDF
- 전체 parser JSON
- 전체 chunk text
- 전체 vector database
- 전체 raw evaluation CSV
- frontend service
- voice UI
- 기본 pipeline으로서의 GraphRAG
- 기본 pipeline으로서의 full RAPTOR

## 기본 Pipeline

```text
PDF
-> Upstage Parser 결과
-> canonical element schema
-> parser 품질 검사
-> parent/child chunks
-> BM25 + vector indexes
-> query rewrite
-> hybrid retrieval
-> parent context expansion
-> evidence packing
-> Solar Pro 3 generation
-> answer with citations
-> evaluation logging
```

## RAG 전략

기본 production 후보:

```text
Hybrid Retrieval + Query Rewrite + Parent-Child Chunking + Citation RAG
```

RAPTOR-lite와 GraphRAG-lite는 초기 기본 구조가 아니라 비교 실험군으로 둔다.

## 공개 저장소 데이터 정책

이 public repository에는 저작권이 있는 원문 텍스트를 대량으로 포함하지 않는다.

허용:

- 코드
- 설정 파일
- 집계 metric
- 소량의 익명화 sample
- 문서

금지:

- 원본 도서 또는 PDF
- 전체 parser output
- 전체 OCR text
- 전체 chunk file
- 전체 vector index
- secret 또는 API key

## 문서 언어 정책

공개 README와 docs 하위 문서는 한글로 작성한다.

코드, API field, config key, metric 이름은 영어를 유지한다.

## 현재 상태

프로젝트 초기화 완료. 다음 단계는 parser normalization과 provenance 복구다.
