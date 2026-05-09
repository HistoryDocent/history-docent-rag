# History Docent RAG

서울을 방문한 한국인과 외국인에게 한양의 역사 맥락을 설명하는 역사 관광 도슨트 서비스의 RAG 백엔드 프로젝트.

원본 데이터는 `벌거벗은 한국사` 등 한국사 도서의 Upstage Parser 결과를 기반으로 한다.

## 프로젝트 정체성

이 저장소는 일반 챗봇 데모가 아니다.

목표는 다음이다.

- 서울 주요 관광지를 한양 역사 맥락과 연결한다.
- 한국사 도서 parser 결과를 정규화한다.
- 문서 구조와 citation provenance를 보존한다.
- 장소, 인물, 사건, 제도 중심으로 근거를 검색한다.
- 관광객에게 짧고 재미있게 설명할 수 있는 답변을 생성한다.
- 근거 기반 답변 품질을 고정 평가셋으로 검증한다.

## 포트폴리오 기준 역할

지원 직무:

- AI 백엔드
- RAG 엔지니어
- 데이터 기반 LLM 애플리케이션 개발

본인 역할:

- Upstage Parser 결과 정규화
- 서울/한양 장소 catalog 설계
- parent-child chunking 재설계
- BM25/Dense/Hybrid retrieval 비교
- citation RAG answer contract 설계
- 단계별 evaluation gate 구축

핵심 기술:

- Python
- FastAPI
- Pydantic
- Upstage Parser
- Solar Pro 3
- BM25
- Dense Retrieval
- Hybrid Retrieval
- Jupyter Notebook
- pytest

## 1차 범위

포함:

- Upstage Parser 결과 정규화
- 서울/한양 장소 catalog 설계
- 구조 보존 parent/child chunking
- BM25 baseline retrieval
- dense retrieval 및 hybrid retrieval 실험
- 장소명, 지시어, 짧은 음성형 질문을 위한 query rewrite
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
-> 서울/한양 장소 catalog
-> parent/child chunks
-> BM25 + vector indexes
-> place-aware query rewrite
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
Place-aware Hybrid Retrieval + Query Rewrite + Parent-Child Chunking + Citation RAG
```

RAPTOR-lite와 GraphRAG-lite는 초기 기본 구조가 아니라 비교 실험군으로 둔다.

## 제품 목표

최종 서비스는 서울 관광 중 사용할 수 있는 역사 도슨트다.

예상 사용자는 다음이다.

- 서울을 여행하는 한국인
- 서울을 방문한 외국인
- 경복궁, 광화문, 북촌, 종로, 한양도성 등에서 역사적 맥락을 알고 싶은 사용자

답변 스타일은 다음을 지향한다.

- 짧다.
- 현장에서 듣기 쉽다.
- 장소와 역사 사건을 연결한다.
- 과장된 이야기가 아니라 근거 있는 설명을 제공한다.
- 화면에는 citation을 표시하고, 음성 답변에는 자연스럽게 축약한다.

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

프로젝트 재시작 계획과 평가 gate 정리 완료.

canonical source를 `History_Docent`로 고정했고, 원본 PDF와 Upstage Parser 산출물의 `source_inventory` gate를 통과했다.

`data_manifest`와 `normalized_blocks` schema를 고정했고, parser normalization pipeline과 parser quality report도 통과했다.

다음 단계는 parent-child chunking 설계다.

## 실행 전략

단계별 구현 순서, 정량/정성 평가 기준, 포트폴리오 산출물 기준은 [실행 전략](docs/EXECUTION_STRATEGY.md)에 정리한다.

## 개발 문서

| 문서 | 목적 |
| --- | --- |
| [PRD](docs/PRD.md) | 제품 목적, MVP, non-goal, 성공 기준 |
| [Source Data Decision](docs/SOURCE_DATA_DECISION.md) | canonical source 선정과 첫 번째 데이터 gate |
| [Data Contracts](docs/DATA_CONTRACTS.md) | data manifest와 normalized block 계약 |
| [Normalization](docs/NORMALIZATION.md) | parser 결과를 NormalizedBlock으로 변환하는 규칙과 gate |
| [Parser Quality Report](docs/PARSER_QUALITY_REPORT.md) | 청킹 전 parser/block 품질 지표와 해석 |
| [WBS](docs/WBS.md) | 단계별 작업, 산출물, commit 단위 |
| [Checklist](docs/CHECKLIST.md) | 단계별 통과 기준과 공개 전 검수 |
| [TODO](docs/TODO.md) | 즉시 실행할 작업 목록 |
| [Notebook Guide](docs/NOTEBOOK_GUIDE.md) | numbered notebook 작성 규칙 |
| [Portfolio Strategy](docs/PORTFOLIO_STRATEGY.md) | README, 이력서, 면접 메시지 |
| [Eval Gates](docs/EVAL_GATES.md) | 정량/정성 평가와 개선 주장 규칙 |
| [Execution Strategy](docs/EXECUTION_STRATEGY.md) | 상세 실행 전략 |

## Notebook 체계

notebook은 분석과 검증 기록용이다. 핵심 구현은 Python module에 둔다.

경로:

```text
notebooks/
```

작성 규칙은 [Notebook Guide](docs/NOTEBOOK_GUIDE.md)를 따른다.
