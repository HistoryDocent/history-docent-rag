# PRD

## 1. Summary

HistoryDocent는 서울을 방문한 한국인과 외국인에게 한양의 역사 맥락을 짧고 근거 있게 설명하는 관광 도슨트 RAG 백엔드다.

1차 제품은 음성 앱이 아니라 `spoken_answer`를 포함한 place-aware citation RAG API와 평가 체계다.

## 2. Contacts

| 이름 | 역할 | 책임 |
| --- | --- | --- |
| 제품 담당 | Product/UX | MVP 범위, 사용자 여정, non-goal 관리 |
| 데이터 담당 | Data Pipeline | parser 결과 정규화, provenance, 품질 리포트 |
| RAG 담당 | Retrieval/Generation | retrieval 비교, citation RAG, Solar Pro 3 연동 |
| 평가 담당 | Evaluation | 정량/정성 평가 gate, ablation, 유의성 판단 |
| 백엔드 담당 | Backend/Ops | FastAPI contract, rate limit, cache, retry, health check |
| 포트폴리오 담당 | Portfolio | README, 이력서, 면접 답변 메시지 정렬 |

## 3. Background

서울 관광지는 역사적 맥락이 많지만 현장에서 즉시 이해하기 어렵다.

기존 프로젝트는 한국사 도서 parser 결과와 RAG 실험 자산을 갖고 있으나, 다음 한계가 있다.

- chunk metadata가 citation RAG에 부족하다.
- 테스트가 smoke test 중심이다.
- 문서와 실제 평가 결과가 충돌한다.
- RAG 기법 선택 근거가 일관되지 않다.
- frontend와 음성 서비스를 완성했다고 주장하기 어렵다.

따라서 새 repo에서는 기존 프로젝트를 참고 자료로만 사용하고, 데이터 계약부터 다시 개발한다.

## 4. Objective

목표:

- 서울 장소 기반 질문을 한양 역사 맥락과 연결한다.
- 원문 근거를 추적 가능한 citation RAG를 만든다.
- retrieval/generation 품질을 query type별로 평가한다.
- 성능 개선 여부를 통계적으로 판단한다.

Key Results:

- parser normalization 필수 field null 0
- parent-child chunk citation recoverability 99% 이상
- BM25/Dense/Hybrid 동일 평가셋 비교 완료
- `Correct-with-Evidence` 기준 최종 후보 선정
- public repo에 원문/secret/private path leakage 0

## 5. Market Segments

대상 사용자:

- 서울을 여행하는 한국인
- 서울을 방문한 외국인
- 경복궁, 광화문, 북촌, 종로, 한양도성 등에서 역사 설명을 듣고 싶은 사용자

1차 개발 대상:

- 실제 관광객용 앱 사용자가 아니라 AI 백엔드/RAG 포트폴리오 평가자
- 평가자는 문제 정의, 역할, 구현 깊이, 테스트, 결과, 한계를 확인한다.

## 6. Value Propositions

사용자 가치:

- 장소와 역사 사건을 연결한 짧은 설명을 받는다.
- 근거 없는 역사 이야기가 아니라 citation 가능한 설명을 받는다.
- 후속 질문에서도 “여기”, “그 사람” 같은 표현을 처리할 수 있다.

포트폴리오 가치:

- RAG 구현뿐 아니라 parser 품질, chunking, retrieval 비교, generation 평가까지 증명한다.
- GraphRAG/RAPTOR를 무조건 쓰지 않고 query type별로 비교한다.
- 원본 저작권 데이터를 공개하지 않는 데이터 정책을 증명한다.

## 7. Solution

### 7.1 User Flow

```text
장소 선택 또는 place_id 입력
-> 짧은 질문 입력
-> place-aware query rewrite
-> evidence retrieval
-> parent context expansion
-> Solar Pro 3 answer generation
-> answer + spoken_answer + citations 반환
```

### 7.2 MVP Features

- Upstage Parser 결과 정규화
- 서울/한양 장소 catalog
- parent-child chunking
- BM25 baseline
- Dense/Hybrid retrieval 비교
- place-aware query rewrite
- citation RAG answer contract
- `spoken_answer` field
- no-answer 처리
- evaluation harness

### 7.3 Non-Goals

- 완성형 음성 앱
- STT/TTS
- route recommendation
- AR
- 사용자 계정
- 결제
- GraphRAG-first architecture
- RAPTOR-first architecture
- 원본 도서 데이터 공개

### 7.4 Technology

- Python
- FastAPI
- Pydantic
- Upstage Parser
- Upstage Solar Pro 3
- BM25
- Dense retrieval
- Hybrid retrieval
- pytest
- Jupyter Notebook

### 7.5 Assumptions

- 기존 원본 데이터와 parser 결과는 private path에서만 사용한다.
- public repo는 code, docs, aggregate metric, redacted sample만 포함한다.
- notebook은 분석 기록용이며 핵심 로직은 Python module에 둔다.

## 8. Release

### v0.1 Documentation Restart

- PRD, WBS, checklist, TODO, notebook guide 작성
- notebook skeleton 생성
- README 문서 링크 정리

### v0.2 Data Contract

- data manifest schema
- normalized block schema
- parser normalization test
- parser quality report

### v0.3 Retrieval Baseline

- place catalog
- parent-child chunking
- BM25 baseline
- Dense/Hybrid comparison

### v0.4 Citation RAG API

- citation answer contract
- Solar Pro 3 provider
- FastAPI `/chat`
- rate limit/cache/retry/health check

### v0.5 Advanced RAG Experiments

- RAPTOR-lite comparison
- GraphRAG-lite comparison
- final ablation report
