# Roadmap

## Phase 0. Repository Foundation

- public repository 생성
- 안전 중심 `.gitignore` 추가
- project scope 정의
- data policy 정의
- evaluation plan 정의

## Phase 1. Parser Normalization

- private local path에서 Upstage Parser outputs 로드
- global page number 복구
- element-level metadata 보존
- parser quality report 생성

## Phase 2. Seoul/Hanyang Place Catalog

- 서울 주요 관광지 seed catalog 작성
- 현대 장소명과 역사 명칭 연결
- 장소별 관련 인물, 사건, 제도 mapping
- `place_id`와 관련 chunk 연결 구조 정의

## Phase 3. Structure-Preserving Chunking

- parent chunk와 child chunk 생성
- section path와 page provenance 보존
- OCR noise와 invalid summary artifacts 필터링
- public sample chunks 생성

## Phase 4. Retrieval Baselines

- BM25 baseline 구현
- dense retrieval 구현
- hybrid retrieval 구현
- Recall@k, MRR, nDCG, latency 기록

## Phase 5. Place-Aware Citation RAG

- evidence packing 구현
- Solar Pro 3 provider 구현
- 장소 기반 query rewrite 구현
- citation 기반 답변 생성
- 음성용 짧은 답변 field 생성
- unsupported claims 탐지

## Phase 6. API

- FastAPI chat endpoint 구현
- place search endpoint 구현
- readiness health check 추가
- validation, rate limit, retry, timeout, structured logs 추가

## Phase 7. Evaluation Harness

- dev, holdout, external, stress eval set 생성
- retrieval grader와 generation grader 구현
- confidence interval 보고
- ablation report 생성

## Phase 8. Advanced Retrieval Experiments

- overview 질문용 RAPTOR-lite 추가
- relationship 질문용 GraphRAG-lite 추가
- metric이 정당화할 때만 query-type router 추가

## Phase 9. Voice Demo

- voice UI MVP 계획과 API field mapping 고정
- browser voice-ready frontend skeleton 구현
- FastAPI contract-only 응답과 frontend backend mode 연결 smoke
- 실제 browser desktop/mobile visual QA
- 포트폴리오 local demo runbook 정리
- public repository audit refresh
- portfolio submission rehearsal
- 실제 STT/TTS demo 전 provider, 개인정보, 비용, failure mode, eval gate 계획
- provider 호출 없는 STT/TTS contract skeleton
- provider benchmark 계획과 CUDA local STT 후보 검토
- 짧은 답변과 citation display 동작 보존
- 규모가 커지면 voice UI를 RAG backend와 분리
