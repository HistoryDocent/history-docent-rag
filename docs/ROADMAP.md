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
- provider benchmark readiness에서 public-safe fixture, config skeleton, no-live-call preflight 검증
- provider benchmark execution approval에서 call cap, 비용, region, privacy boundary 재확인
- provider benchmark local smoke execution에서 CUDA Whisper 후보 5건을 external provider call 없이 검증
- local STT model ablation에서 tiny, base, small 후보를 같은 private wav fixture로 비교
- voice provider decision에서 무료 로컬 STT/TTS를 기본 전략으로 변경하고 managed provider는 optional paid comparison으로 격하
- local TTS smoke runner에서 `MeloTTS Korean` 후보를 public-safe script와 private audio boundary로 검증하고 현재 runtime missing을 기록
- local runtime matrix에서 무료 로컬 STT/TTS 후보 5개의 import/runtime/CUDA 가능성을 zero-call로 기록
- local TTS runtime install retry에서 MeloTTS 설치/CUDA/import/model load와 Windows `eunjeon` blocker를 기록하고, Windows SAPI Korean fallback으로 private wav 5개를 생성
- local STT/TTS adapter integration에서 local Whisper STT 후보, `/api/v1/chat` contract, Windows SAPI TTS fallback을 5개 script로 연결
- local voice E2E eval에서 30개 public-safe script를 input TTS, CUDA Whisper STT, `/api/v1/chat`, output TTS 흐름으로 실행하고 external provider call 0을 기록
- local voice runtime contract에서 private wav 입력 검증, 기본 비활성화 API route, `/api/v1/chat` bridge, local TTS private artifact 경계를 고정
- local free STT/TTS bench v2에서 현재 실행 baseline과 `faster-whisper`/`Piper` next target을 분리하고 external provider call 0을 기록
- local faster-whisper STT comparison에서 openai-whisper small CUDA baseline과 faster-whisper small CUDA를 같은 5개 fixture로 비교하고 external provider call 0을 기록
- local whisper.cpp deployment smoke에서 CUDA preflight는 통과했지만 `whisper-cli` runtime과 `ggml` model file 부재를 blocker로 기록하고 기본 STT 후보는 faster-whisper로 유지
- local Piper TTS smoke에서 `piper-tts` runtime은 설치됐지만 공식 voice manifest 기준 Korean voice 0개로 확인되어 한국어 TTS 기본 후보에서 차단
- local Korean TTS alternative review에서 무료 로컬 한국어 TTS 후보 7개를 source 기반으로 검토하고 `sherpa-onnx + Supertonic 3 Korean`을 다음 smoke 후보로 선정
- local sherpa-onnx Supertonic 3 Korean TTS smoke에서 runtime 설치, private model 확인, 5개 public-safe script private wav 합성을 external provider call 0으로 기록
- local TTS quality listening review에서 sherpa-onnx private wav 5개에 대해 duration/RMS/clipping/silence/sample rate 자동 metric과 human listening rubric을 기록하고, human score는 pending으로 남김
- local TTS human score fill에서 5개 script x 6 rubric private scoring template과 public aggregate runner를 만들고, 실제 score 미입력 상태는 pending으로 남김
- local TTS human score collection에서 private wav 5개 청취 평가 manifest와 guide를 만들고, 실제 score 미입력 상태는 collection-ready로 남김
- local TTS human score entry에서 private score 입력 guide와 30행 draft를 만들고, 실제 score 미입력 상태는 pending manual entry로 남김
- local TTS human score entry completion에서 private score 입력 완료 여부를 검증하고, 현재 실제 score 미입력 상태를 missing human scores blocker로 남김
- local TTS human score manual scoring workspace에서 private HTML score sheet와 draft를 만들고, 실제 score 미입력 상태는 ready_for_human_manual_scoring으로 남김
- local TTS human score provider decision gate에서 score 30행 미완료 상태를 `blocked_missing_human_scores`로 기록하고, TTS 후보 채택을 차단함
- local TTS human score manual scoring runbook에서 private score sheet와 5개 wav 준비 상태, score 입력 대기 상태, 외부 호출 0을 기록하고 사람이 직접 채점해야 함을 명확히 함
- local TTS automated proxy evaluation에서 5개 private wav를 faster-whisper CUDA로 round-trip 전사했고, 자동 proxy threshold는 4/5 통과라서 사람 청취 점수 필요성을 유지함
- local free voice stack lock에서 `faster-whisper small CUDA`는 primary STT 후보로 고정하고, TTS는 final provider 0 상태로 차단하며 managed provider는 optional paid comparison으로 유지함
- local voice runtime stack alignment에서 stack lock의 `local_faster_whisper_small_cuda`를 실제 runtime/API provider id와 정렬하고, TTS fallback은 final provider가 아님을 명시함
- managed provider smoke approval에서 비용, region, retention, raw audio 전송 재승인 기준을 zero-call gate로 고정
- managed provider smoke execution harness에서 dry-run default, credential preflight, call cap enforcement를 구현
- managed provider smoke preflight에서 provider별 credential 존재 여부, source/region/retention/cost 재확인 필요성, 추천 provider 1개 이하를 zero-call gate로 검증
- managed provider smoke execution gate에서 selected Azure provider의 실행 조건 미충족 상태를 zero-call로 차단
- Azure managed smoke readiness에서 first managed provider 후보를 Azure로 제한하고 env key 이름, source/region/retention/cost 재확인, zero-call gate를 고정
- Azure credential preflight에서 `.env`/환경 변수의 Azure credential 존재 여부만 자동 점검하고 실제 호출은 0회로 유지
- Azure smoke execution approval에서 credential missing 상태를 반영해 실행 승인 false, source/region/retention/cost 재확인 gate를 고정
- Azure smoke execution에서 실행 runner를 추가하되 credential/source/user approval 미충족 상태를 반영해 실제 호출은 0회로 차단
- Azure credential ready smoke approval에서 credential/source/region/retention/cost/user approval 충족 여부를 zero-call로 재판정
- managed provider smoke execution은 optional paid comparison으로만 별도 승인 후 provider별 call cap 안에서 진행
- 짧은 답변과 citation display 동작 보존
- 규모가 커지면 voice UI를 RAG backend와 분리
