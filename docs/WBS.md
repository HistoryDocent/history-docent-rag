# WBS

## Phase 0. 재시작 문서화

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 0.1 | PRD 작성 | `docs/PRD.md` | 제품 목적, MVP, non-goal 명시 | `docs: add restart plan docs` |
| 0.2 | WBS 작성 | `docs/WBS.md` | phase, 산출물, commit 단위 명시 | `docs: add restart plan docs` |
| 0.3 | Checklist 작성 | `docs/CHECKLIST.md` | 평가 gate, 공개 금지 항목 명시 | `docs: add restart plan docs` |
| 0.4 | TODO 작성 | `docs/TODO.md` | 즉시 작업과 후속 작업 분리 | `docs: add restart plan docs` |
| 0.5 | Notebook guide 작성 | `docs/NOTEBOOK_GUIDE.md` | numbered notebook 규칙 명시 | `docs: add restart plan docs` |
| 0.6 | Portfolio strategy 작성 | `docs/PORTFOLIO_STRATEGY.md` | README/이력서/면접 메시지 명시 | `docs: add restart plan docs` |
| 0.7 | Eval gates 작성 | `docs/EVAL_GATES.md` | 정량/정성 gate 명시 | `docs: add restart plan docs` |
| 0.8 | Notebook skeleton 생성 | `notebooks/*.ipynb` | 00~13 단계 생성 | `docs: add restart plan docs` |

## Phase 1. 데이터 계약

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 1.1 | data manifest schema | `app/domain/schemas.py` | Pydantic schema와 unit test 통과 | `feat: add data manifest schema` |
| 1.2 | normalized block schema | `app/domain/schemas.py` | block 필수 field 검증 | `feat: add normalized block schema` |
| 1.3 | sample data 정책 | `data_samples/*` | private path와 원문 과다 노출 없음 | `test: add public sample leakage checks` |
| 1.4 | parser normalization test | `tests/test_parser_normalization.py` | page/global/field 검증 | `test: add parser normalization validation` |

## Phase 2. Parser Normalization

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 2.1 | parser loader | `pipelines/normalize_parser_output.py` | private input에서 block 생성 | `feat: add parser normalization pipeline` |
| 2.2 | global page 복구 | normalization module | `page_global` 역전 0 | `feat: recover global page provenance` |
| 2.3 | quality flags | normalization module | OCR/base64/empty text flag 집계 가능 | `feat: add parser quality flags` |
| 2.4 | quality report | report generator | 집계 report 생성 | `feat: add parser quality report` |
| 2.5 | notebook 검증 | `02`, `03` notebooks | 집계표와 failure case 출력 | `docs: add parser quality notebooks` |

## Phase 3. Place Catalog

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 3.1 | seed catalog | `configs/place_catalog.seed.yaml` | 초기 7개 장소 등록 | `feat: add seoul place catalog seed` |
| 3.2 | place schema | domain schema | place id/name/alias 검증 | `feat: add place schema` |
| 3.3 | place search | place service | alias 검색 테스트 통과 | `feat: add place search` |
| 3.4 | notebook 검증 | `05_place_catalog_validation.ipynb` | 장소별 alias/related term 확인 | `docs: add place catalog validation notebook` |

## Phase 4. Chunking

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 4.1 | chunk schema | domain schema | child/parent 검증 | `feat: add chunk schemas` |
| 4.2 | parent-child builder | chunking pipeline | orphan child 0 | `feat: add parent child chunking` |
| 4.3 | citation backtracking | chunk metadata | citation recoverability 99% 이상 | `test: add chunk provenance tests` |
| 4.4 | notebook 분석 | `04_chunking_quality_analysis.ipynb` | chunk 품질 집계표 | `docs: add chunk quality notebook` |

## Phase 5. Retrieval Baseline

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 5.1 | BM25 baseline | retrieval module | Recall@k/MRR 측정 | `feat: add bm25 retrieval baseline` |
| 5.2 | 평가셋 확장 workflow | expansion report | 목표 105개 대비 부족분과 public gate 기록 | `평가: retrieval 평가셋 확장 리포트 추가` |
| 5.3 | benchmark 공개 범위 정책 | data policy, gitignore | full dev/test는 private, public은 sample/report만 허용 | `문서: benchmark 공개 범위 정책 고정` |
| 5.4 | private dev/test 평가셋 확장 | retrieval eval dataset | query type별 private dev/test split 고정 | `test: expand retrieval eval dataset` |
| 5.5 | chunking ablation | chunking experiment runner | C0-C6 비교와 winner 기록 | `test: add chunking ablation runner` |
| 5.6 | Dense retrieval | retrieval module | 동일 평가셋 비교 가능 | `feat: add dense retrieval baseline` |
| 5.7 | Hybrid retrieval | retrieval module | weighted/RRF 비교 가능 | `feat: add hybrid retrieval experiment` |
| 5.8 | Neural embedding comparison | retrieval module | BGE-M3, multilingual-E5, multilingual-MiniLM 비교 | `평가: neural embedding 검색 비교 실험 추가` |
| 5.9 | Neural dense Hybrid comparison | retrieval module/report | E5-small/BGE-M3 dense leg 기반 RRF/Weighted 비교 | `평가: neural dense Hybrid 검색 비교 실험 추가` |
| 5.10 | Reranker comparison | retrieval module/report | BGE reranker top20 v1 비교와 top30/top50 실험군 구현 | `평가: reranker 검색 비교 실험 추가` |
| 5.11 | evaluation harness | evals module | query type별 metric과 latency 출력 | `test: add retrieval evaluation harness` |
| 5.12 | notebooks | `06`, `07`, `09` notebooks | baseline/chunking/dense/hybrid 비교표 생성 | `docs: add retrieval evaluation notebooks` |

## Phase 6. Query Rewrite와 Citation RAG

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 6.1 | rewrite contract | application module/report | invalid JSON 0, voice-only 후보 기록 | `평가: 장소 인식 쿼리 재작성 검색 비교 실험 추가` |
| 6.2 | evidence packing | application module/report | policy별 coverage, duplicate, citation gate 기록 | `평가: evidence packing 비교 실험 추가` |
| 6.3 | answer contract | schema/service/report | answer/spoken_answer/citations 반환, abstain 계약 검증 | `기능: citation RAG 답변 계약 추가` |
| 6.4 | Solar provider | provider abstraction | fake provider와 real provider 분리 | `feat: add solar provider abstraction` |
| 6.5 | generation eval | eval harness | Correct-with-Evidence와 unsupported claim 측정 | `test: add generation evaluation harness` |
| 6.6 | notebook | `08`, `10` notebooks | rewrite/evidence/generation ablation | `docs: add citation rag notebooks` |

## Phase 7. FastAPI 백엔드

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 7.1 | API contract | FastAPI routers | `/health`, `/places/search`, `/chat` | `feat: add fastapi chat contract` |
| 7.2 | rate limit | core module | 429 test 통과 | `feat: add api rate limiter` |
| 7.3 | cache | cache interface | cache hit 시 provider 미호출 | `feat: add response cache interface` |
| 7.4 | retry/timeout | provider policy | 429/5xx retry, 4xx retry 금지 | `feat: add provider retry policy` |
| 7.5 | security tests | tests | raw error/secret 노출 0 | `test: add api resilience tests` |

## Phase 8. 고급 RAG 실험

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 8.1 | RAPTOR-lite | experiment module/report | overview/place_story input-only 비교 완료 | `실험: RAPTOR-lite input-only 비교 추가` |
| 8.2 | GraphRAG-lite | experiment module | relationship만 비교 | `feat: add graphrag lite experiment` |
| 8.3 | final report | docs/notebook | query type별 최종 판단 | `docs: add final ablation report` |
| 8.4 | ColBERT-style plan | docs/report/test | late interaction hard subset 실행 전 gate 고정 | `문서: ColBERT late interaction 실험 계획 추가` |
| 8.5 | ColBERT-style execution approval | docs/report/test | dev hard subset 실행 전 scope, CUDA, locked/Solar 금지 gate 고정 | `문서: ColBERT hard subset 실행 승인 기준 추가` |
| 8.6 | ColBERT-style hard subset | scorer/runner/docs/report/test | CUDA 기반 dev hard subset 비교와 기본 route 기각 판단 | `실험: ColBERT hard subset 비교 실행` |

## Phase 9. 제출 패키징

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 9.1 | portfolio QA | `docs/PORTFOLIO_QA.md`, report | 이력서 한 줄, 면접 답변, 금지 claim 정리 | `문서: 포트폴리오 제출 문구 정리` |
| 9.2 | submission ready audit | `docs/SUBMISSION_READY_CHECKLIST.md`, report | 제출 전 링크, notebook, public-safe, claim boundary gate 통과 | `문서: 포트폴리오 제출 전 최종 감사 추가` |
| 9.3 | voice UI MVP plan | `docs/VOICE_UI_MVP_PLAN.md`, `docs/VOICE_UI_API_CONTRACT.md`, report | `/api/v1/chat` field mapping, voice-ready UI 범위, non-goal, public-safe gate 고정 | `문서: voice UI MVP 계획 추가` |
| 9.4 | frontend/voice UI skeleton | frontend skeleton, UI test | `spoken_answer`, `answer`, `citations`, no-answer, voice fallback state 렌더링 | `기능: voice UI skeleton 추가` |
| 9.5 | frontend/backend contract smoke | dev server smoke, UI smoke report | FastAPI contract-only response가 frontend에 표시됨, live provider 호출 0 | `테스트: voice UI contract smoke 추가` |
| 9.6 | real browser visual QA | screenshot/checklist report | desktop/mobile layout, no-answer, citation drawer, voice fallback visual 검증 | `테스트: voice UI visual QA 추가` |
| 9.7 | portfolio demo runbook | `docs/PORTFOLIO_DEMO_RUNBOOK.md`, report | backend/frontend local demo 순서, 금지 claim, public-safe gate 정리 | `문서: 포트폴리오 데모 런북 추가` |
| 9.8 | public repository audit refresh | `docs/SUBMISSION_REFRESH_AUDIT.md`, report, test | README 링크, demo runbook, screenshot artifact, 금지 claim, public-safe scan 재검증 | `감사: 공개 저장소 제출 전 재검증 추가` |
| 9.9 | portfolio submission rehearsal | `docs/PORTFOLIO_REHEARSAL.md`, report, test | 30초 요약, 3분 설명, 면접 답변, 기각 후보 설명, 금지 claim 회피 고정 | `문서: 포트폴리오 설명 리허설 추가` |
| 9.10 | voice STT/TTS planning | `docs/VOICE_STT_TTS_PLAN.md`, report, test | 실제 음성 입출력 구현 전 provider, 개인정보, 비용, failure mode, eval gate 고정 | `문서: 음성 STT TTS 계획 추가` |
| 9.11 | voice STT/TTS contract skeleton | frontend adapter, `docs/VOICE_STT_TTS_CONTRACT.md`, report, test | provider 호출 없는 adapter/interface, disabled voice control, zero-call metric 검증 | `기능: 음성 STT TTS contract skeleton 추가` |
| 9.12 | voice STT/TTS provider benchmark plan | `docs/VOICE_STT_TTS_PROVIDER_BENCH_PLAN.md`, report, test | 공식 문서, 비용/개인정보 source, CUDA local 후보, live call budget, no-live-call gate 고정 | `문서: 음성 STT TTS provider benchmark 계획 추가` |
| 9.13 | voice STT/TTS provider benchmark readiness | config, sample script, runner, docs/report/test | provider 후보 5개, script 30개, CUDA preflight, live call 0, public-safe gate 통과 | `기능: 음성 STT TTS provider benchmark readiness 추가` |
| 9.14 | voice STT/TTS provider benchmark execution approval | `docs/VOICE_STT_TTS_PROVIDER_BENCH_EXECUTION_APPROVAL.md`, report, test | smoke 실행 전 call cap, 비용, region, privacy, data mart grain, no-live-call gate 고정 | `문서: 음성 STT TTS provider benchmark 실행 승인 기준 추가` |
| 9.15 | voice STT/TTS provider benchmark local smoke | local smoke runner, `docs/VOICE_STT_TTS_PROVIDER_BENCH_SMOKE_LOCAL.md`, report, test | local CUDA Whisper 5건 실행, external provider call 0, raw audio/transcript public artifact 0 | `실험: 음성 STT TTS local smoke benchmark 추가` |
| 9.16 | voice STT/TTS local model ablation | local model ablation runner, `docs/VOICE_STT_TTS_LOCAL_MODEL_ABLATION.md`, report, test | tiny/base/small CUDA 비교, external provider call 0, model별 WER/CER/place/latency 기록 | `실험: 로컬 STT 모델 크기 비교 추가` |
| 9.17 | voice STT/TTS managed provider smoke approval | `docs/VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_APPROVAL.md`, report, test | managed provider smoke 전 source recheck, provider별 call cap, privacy, raw artifact public 금지, zero-call gate 고정 | `문서: 음성 STT TTS managed provider smoke 승인 기준 추가` |
| 9.18 | voice STT/TTS managed provider smoke execution harness | dry-run runner, `docs/VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_EXECUTION_HARNESS.md`, report, test | managed provider 실제 호출 전 dry-run default, call cap enforcement, credential preflight, public-safe rows 검증 | `기능: 음성 STT TTS managed provider smoke 실행 harness 추가` |
| 9.19 | voice STT/TTS managed provider smoke preflight | preflight runner, `docs/VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_PREFLIGHT.md`, report, test | provider별 credential 존재 여부, source/region/retention/cost 재확인 필요성, 추천 provider 1개 이하, zero-call gate 검증 | `점검: 음성 STT TTS managed provider smoke preflight 추가` |
| 9.20 | voice STT/TTS Azure managed smoke readiness | `docs/VOICE_STT_TTS_AZURE_MANAGED_SMOKE_READINESS.md`, report, test, `.env.example` | Azure first candidate, env key names only, source/region/retention/cost recheck, zero-call gate 검증 | `문서: Azure managed STT TTS smoke readiness 추가` |
| 9.21 | voice STT/TTS Azure credential preflight | preflight runner, `docs/VOICE_STT_TTS_AZURE_CREDENTIAL_PREFLIGHT.md`, report, test | Azure credential 존재 여부만 점검, source 재확인 조건 유지, zero-call gate 검증 | `문서: Azure credential preflight gate 추가` |
| 9.22 | voice STT/TTS Azure smoke execution approval | `docs/VOICE_STT_TTS_AZURE_SMOKE_EXECUTION_APPROVAL.md`, report, test | Azure smoke 실행 전 credential, source, region, retention, cost 승인 gate와 zero-call 검증 | `문서: Azure smoke 실행 승인 gate 추가` |
| 9.23 | voice STT/TTS Azure smoke execution | execution runner, `docs/VOICE_STT_TTS_AZURE_SMOKE_EXECUTION.md`, report, test | Azure smoke 실행 조건 미충족 시 zero-call 차단 리포트와 public-safe gate 검증 | `점검: Azure smoke 실행 차단 리포트 추가` |
| 9.24 | voice STT/TTS Azure credential ready smoke approval | approval runner, `docs/VOICE_STT_TTS_AZURE_CREDENTIAL_READY_AND_SMOKE_APPROVAL.md`, report, test | Azure credential ready와 source/region/retention/cost/user approval zero-call gate 검증 | `점검: Azure credential ready smoke 승인 gate 추가` |
| 9.25 | voice STT/TTS managed provider smoke execution gate | execution runner, `docs/VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_EXECUTION.md`, report, test | selected Azure managed provider smoke 실행 조건 미충족 시 zero-call 차단 리포트와 public-safe gate 검증 | `실험: Azure managed STT TTS smoke 실행 gate 추가` |
| 9.26 | voice STT/TTS local-first strategy decision | `docs/VOICE_PROVIDER_DECISION.md`, report | 무료 로컬 STT/TTS를 기본 전략으로 지정하고 Azure/Google/AWS는 optional paid comparison으로 격하 | `문서: 무료 로컬 STT TTS 우선 전략으로 변경` |
| 9.27 | voice STT/TTS local TTS smoke | local TTS smoke runner, docs/report/test | `MeloTTS Korean` 후보를 public-safe script 5개로 점검, 현재 runtime missing 차단 기록, external provider call 0 | `실험: 로컬 TTS smoke 추가` |
| 9.28 | voice local runtime matrix | local runtime matrix runner, docs/report/test | 무료 로컬 STT/TTS 후보 5개 import/runtime/CUDA preflight, 설치/다운로드/외부 호출 0 | `문서: 무료 로컬 음성 런타임 후보 매트릭스 추가` |
| 9.29 | voice STT/TTS local TTS runtime install retry | local runtime setup evidence, rerun report | MeloTTS 설치/CUDA/import/model load 통과, Korean synthesis Windows `eunjeon` blocker 기록, SAPI Korean fallback private wav 5개 생성 | `점검: 로컬 TTS 런타임 설치 재시도` |
| 9.30 | voice STT/TTS local adapter integration | local adapter module, docs/report/test | local Whisper STT 5건, `/api/v1/chat` contract 5건, SAPI TTS fallback 5건, external provider call 0 | `구현: 로컬 STT TTS 어댑터 연결` |
| 9.31 | voice local E2E eval | local voice E2E runner, docs/report/test | 30개 public-safe script에서 input TTS, CUDA Whisper STT, `/api/v1/chat`, output TTS를 실행하고 external provider call 0 기록 | `평가: 로컬 음성 E2E 검증 리포트 추가` |
| 9.32 | voice local runtime contract | local-only runtime service, disabled API route, docs/report/test | private wav 입력 검증 5건, validation reject 3건, `/api/v1/chat` 연결 5건, local TTS 5건, external provider call 0 기록 | `기능: 로컬 음성 런타임 계약 추가` |
| 9.33 | voice local free STT/TTS bench v2 | local-free candidate decision runner, docs/report/test | current STT/TTS baseline과 faster-whisper/Piper next target 분리, external provider call 0 기록 | `평가: 무료 로컬 음성 후보 기준선 정리` |
| 9.34 | voice local faster-whisper STT comparison | faster-whisper comparison runner, docs/report/test | openai-whisper small CUDA baseline과 faster-whisper small CUDA를 같은 5개 fixture로 비교, external provider call 0 기록 | `평가: 로컬 faster-whisper STT 비교` |
| 9.35 | voice local Piper TTS smoke | Piper TTS smoke runner, docs/report/test | `piper-tts` runtime과 공식 voice manifest Korean voice availability를 검증하고 external provider call 0 기록 | `평가: 로컬 Piper TTS smoke 추가` |
| 9.36 | voice local Korean TTS alternative review | Korean TTS alternative review runner, docs/report/test | Piper Korean voice 부재 이후 무료 로컬 한국어 TTS 후보 7개를 source 기반으로 검토하고 다음 smoke 후보 1개 선정, external provider call 0 기록 | `문서: 무료 로컬 한국어 TTS 대안 검토` |
