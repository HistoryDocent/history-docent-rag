# Checklist

## 공통 제출 전 검수

- [ ] `git status`가 의도한 변경만 보여준다.
- [ ] 원본 PDF가 포함되지 않았다.
- [ ] 전체 parser JSON이 포함되지 않았다.
- [ ] 전체 OCR text가 포함되지 않았다.
- [ ] 전체 chunk text가 포함되지 않았다.
- [ ] raw eval CSV/JSONL이 포함되지 않았다.
- [ ] full dev/test benchmark JSONL이 public repo에 포함되지 않았다.
- [ ] `.env` 또는 API key가 포함되지 않았다.
- [ ] public sample에 private absolute path가 없다.
- [ ] public evaluation example에 원문 직접 인용이 없다.
- [ ] README와 docs는 한글이다.
- [ ] 코드 identifier, API field, metric 이름은 영어다.

## Parser Gate

- [ ] 문서 누락 0
- [ ] `doc_id` 중복 0
- [ ] 필수 field null 0
- [ ] `page_global` 역전 0
- [ ] base64 잔존 0
- [ ] private path leakage 0
- [ ] parser quality report 생성
- [ ] redacted parser sample 생성

## Chunking Gate

- [ ] orphan child 0
- [ ] invalid page range 0
- [ ] unknown element id 0
- [ ] chunk id 중복 0
- [ ] citation recoverability 99% 이상
- [ ] too short/too long chunk 집계
- [ ] redacted chunk sample 생성

## Place Catalog Gate

- [ ] 초기 장소 8개 이상 등록
- [ ] `place_id` 중복 0
- [ ] canonical name 중복 0
- [ ] alias 중복 0
- [ ] alias 20개 이상 등록
- [ ] unknown related place 0
- [ ] self relation 0
- [ ] 장소별 related place 존재
- [ ] 장소별 context tag 존재
- [ ] seed/manual relation과 automatic link 구분
- [ ] public raw text leakage 0
- [ ] private path leakage 0
- [ ] secret-like leakage 0

## Retrieval Gate

- [ ] BM25, Dense, Hybrid 동일 평가셋 비교
- [ ] `Recall@1`, `Recall@3`, `Recall@5` 기록
- [ ] `MRR`, `nDCG@5` 기록
- [ ] `latency_p50`, `latency_p95` 기록
- [ ] query type별 breakdown 존재
- [ ] 실패 유형 분류 존재

## Generation Gate

- [ ] `Correct-with-Evidence` 측정
- [ ] `citation_precision` 측정
- [ ] `citation_recall` 측정
- [ ] `place_relevance` 측정
- [ ] `unsupported_claim_rate` 측정
- [ ] no-answer 질문 환각 여부 확인
- [ ] `spoken_answer`가 20~40초 분량으로 제한됨

## API/Ops Gate

- [ ] `/api/v1/health/live` 구현
- [ ] `/api/v1/health/ready` 구현
- [ ] `/api/v1/places/search` 구현
- [ ] `/api/v1/chat` 구현
- [ ] request schema validation
- [ ] provider timeout
- [ ] 429/5xx retry
- [ ] 400/401/403/422 retry 금지
- [ ] rate limit
- [ ] cache hit 시 provider 미호출
- [ ] structured logging
- [ ] stack trace 비노출

## 개선 주장 Gate

- [ ] paired comparison 수행
- [ ] bootstrap 10,000회 수행
- [ ] 95% confidence interval 보고
- [ ] query type별 결과 보고
- [ ] latency/cost delta 보고
- [ ] external_human 또는 stress_set에서 유지
- [ ] CI가 0을 지나면 개선 주장 금지

## Portfolio Gate

- [ ] README 첫 화면에 문제 정의가 있다.
- [ ] 본인 역할이 드러난다.
- [ ] 기술 선택 이유가 있다.
- [ ] 평가 지표가 있다.
- [ ] 한계가 있다.
- [ ] 데이터 공개 정책이 있다.
- [ ] notebook과 report 링크가 있다.
- [ ] 미검증 성과 표현이 없다.

## Submission Ready Gate

- [ ] README local markdown link missing 0
- [ ] numbered notebook skeleton 14개 존재
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public env assignment leakage 0
- [ ] raw payload public artifact 0
- [ ] 제출용 허용 문장 1개 고정
- [ ] 금지 claim이 성공 claim으로 쓰이지 않음
- [ ] `pytest -q` 통과
- [ ] `ruff check .` 통과
- [ ] `git diff --check` 통과

## ColBERT Plan Gate

- [ ] hard subset query type 고정
- [ ] baseline candidate 고정
- [ ] planned candidate count 기록
- [ ] `Recall@5`, `MRR`, `nDCG@5`, `latency_p95_ms` 기록 계획
- [ ] CUDA availability 확인
- [ ] Solar Pro 3 call count 0
- [ ] locked test execution count 0
- [ ] retrieval execution count 0
- [ ] public raw payload leakage 0
- [ ] ColBERT 성능 개선 claim 금지

## ColBERT Execution Approval Gate

- [ ] expected retrieval execution scope is dev-hard-subset-only
- [ ] actual retrieval execution count 0
- [ ] locked test execution count 0
- [ ] Solar Pro 3 call count 0
- [ ] CUDA availability recorded
- [ ] candidate_k 20/50 fixed
- [ ] target resolvability required fail count 0
- [ ] public raw payload leakage 0
- [ ] ColBERT execution result claim forbidden

## ColBERT Hard Subset Gate

- [ ] selected query count 21
- [ ] target query type count 3
- [ ] target resolvability fail count 0
- [ ] locked test execution count 0
- [ ] Solar Pro 3 call count 0
- [ ] CUDA memory peak recorded
- [ ] `Recall@5`, `MRR`, `nDCG@5`, `latency_p95_ms` recorded
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] ColBERT default route adoption claim forbidden

## Voice UI MVP Plan Gate

- [ ] planned user journey count 3
- [ ] planned screen count 5
- [ ] `/api/v1/chat` required API field mapping count 12
- [ ] frontend implementation count 0
- [ ] STT/TTS production claim count 0
- [ ] live Solar Pro 3 call count 0
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] voice UI skeleton next gate 분리

## Voice UI Skeleton Gate

- [ ] Vite React TypeScript frontend package 1개 존재
- [ ] answerable fixture UI test 통과
- [ ] no-answer fixture UI test 통과
- [ ] sanitized API error UI test 통과
- [ ] microphone unsupported fallback test 통과
- [ ] speaker unsupported fallback test 통과
- [ ] frontend build 통과
- [ ] backend endpoint added count 0
- [ ] live Solar Pro 3 call count 0
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0

## Voice UI Contract Smoke Gate

- [ ] Vite `/api` proxy configured
- [ ] frontend backend mode configured
- [ ] same-origin `/api/v1/chat` endpoint resolution test 통과
- [ ] explicit backend base URL endpoint resolution test 통과
- [ ] FastAPI answerable contract-only smoke HTTP 200
- [ ] FastAPI no-answer contract-only smoke HTTP 200
- [ ] backend active route applied count 0
- [ ] live Solar Pro 3 call count 0
- [ ] retrieval execution count 0
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0

## Voice UI Visual QA Gate

- [ ] browser visual scenario count 3
- [ ] viewport class count 2
- [ ] screenshot artifact count 3
- [ ] desktop answerable citation item count 1
- [ ] mobile no-answer single-column layout 확인
- [ ] mobile no-answer citation item count 0
- [ ] sanitized error visible
- [ ] raw error leakage false
- [ ] voice control visible count 2
- [ ] live Solar Pro 3 call count 0
- [ ] retrieval execution count 0
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0

## Portfolio Demo Runbook Gate

- [ ] demo runbook document count 1
- [ ] demo step count 6
- [ ] runbook command block count 8
- [ ] required artifact link count 3
- [ ] forbidden claim count 8
- [ ] troubleshooting case count 5
- [ ] contract-only demo count 2
- [ ] fixture demo count 1
- [ ] live Solar Pro 3 call count 0
- [ ] retrieval execution count 0
- [ ] private corpus required count 0
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0

## Submission Refresh Audit Gate

- [ ] submission refresh audit document count 1
- [ ] submission refresh report count 1
- [ ] required README link count 2
- [ ] required demo artifact count 3
- [ ] forbidden claim count 8
- [ ] verification command count 8
- [ ] markdown link missing count 0
- [ ] screenshot artifact missing count 0
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public env assignment leakage 0
- [ ] public raw payload leakage 0
- [ ] live Solar Pro 3 call count 0
- [ ] retrieval execution count 0
- [ ] private corpus required count 0

## Portfolio Rehearsal Gate

- [ ] portfolio rehearsal document count 1
- [ ] portfolio rehearsal report count 1
- [ ] thirty second script count 1
- [ ] three minute section count 6
- [ ] interview answer count 12
- [ ] rejected candidate explained count 8
- [ ] demo step count 5
- [ ] allowed claim count 8
- [ ] forbidden claim count 8
- [ ] rehearsal rubric check count 5
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] live Solar Pro 3 call count 0
- [ ] retrieval execution count 0
- [ ] private corpus required count 0

## Voice STT/TTS Plan Gate

- [ ] voice STT/TTS plan document count 1
- [ ] voice STT/TTS plan report count 1
- [ ] planned voice flow count 7
- [ ] provider candidate group count 3
- [ ] privacy control count 9
- [ ] failure mode count 12
- [ ] eval metric count 12
- [ ] provider finalized count 0
- [ ] live STT call count 0
- [ ] live TTS call count 0
- [ ] live Solar Pro 3 call count 0
- [ ] private audio saved count 0
- [ ] retrieval execution count 0
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] voice STT/TTS contract skeleton next gate 분리

## Voice STT/TTS Contract Gate

- [ ] voice STT/TTS contract document count 1
- [ ] voice STT/TTS contract report count 1
- [ ] frontend adapter module count 1
- [ ] frontend adapter unit test count 2
- [ ] frontend UI voice contract test count 1
- [ ] provider finalized count 0
- [ ] live STT call count 0
- [ ] live TTS call count 0
- [ ] live Solar Pro 3 call count 0
- [ ] private audio saved count 0
- [ ] raw transcript public artifact count 0
- [ ] client secret exposure count 0
- [ ] mic capture implemented count 0
- [ ] browser TTS playback call count 0
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] voice STT/TTS provider benchmark plan next gate 분리

## Voice STT/TTS Provider Benchmark Plan Gate

- [ ] voice STT/TTS provider benchmark plan document count 1
- [ ] voice STT/TTS provider benchmark plan report count 1
- [ ] provider candidate group count 5
- [ ] official source checked count 14
- [ ] pricing source link count 5
- [ ] privacy source link count 4
- [ ] benchmark query type count 6
- [ ] planned public-safe script min count 30
- [ ] local CUDA available count 1
- [ ] CUDA device count 1
- [ ] provider finalized count 0
- [ ] provider benchmark execution count 0
- [ ] live STT call count 0
- [ ] live TTS call count 0
- [ ] live Solar Pro 3 call count 0
- [ ] private audio saved count 0
- [ ] raw transcript public artifact count 0
- [ ] client secret exposure count 0
- [ ] pricing claim without source count 0
- [ ] privacy policy unknown count 0
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] voice STT/TTS provider benchmark readiness next gate 분리

## Voice STT/TTS Provider Benchmark Readiness Gate

- [ ] voice STT/TTS provider benchmark readiness document count 1
- [ ] voice STT/TTS provider benchmark readiness report count 1
- [ ] provider candidate config count 1
- [ ] public-safe script fixture count 30
- [ ] provider candidate group count 5
- [ ] official source checked count 14
- [ ] pricing source link count 5
- [ ] privacy source link count 4
- [ ] benchmark query type count 6
- [ ] script per query type min count 5
- [ ] local CUDA available count 1
- [ ] CUDA device count 1
- [ ] provider finalized count 0
- [ ] provider benchmark execution count 0
- [ ] live STT call count 0
- [ ] live TTS call count 0
- [ ] live Solar Pro 3 call count 0
- [ ] private audio saved count 0
- [ ] raw transcript public artifact count 0
- [ ] client secret exposure count 0
- [ ] pricing claim without source count 0
- [ ] privacy policy unknown count 0
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] provider benchmark execution approval next gate 분리

## Voice STT/TTS Provider Benchmark Execution Approval Gate

- [ ] voice STT/TTS provider benchmark execution approval document count 1
- [ ] voice STT/TTS provider benchmark execution approval report count 1
- [ ] provider candidate group count 5
- [ ] public-safe script fixture count 30
- [ ] planned smoke script count per low-risk provider 5
- [ ] planned smoke script count per external provider 3
- [ ] planned full benchmark script count 30
- [ ] pricing recheck required count 5
- [ ] privacy recheck required count 5
- [ ] region recheck required count 5
- [ ] provider benchmark execution approved false
- [ ] provider benchmark execution count 0
- [ ] live STT call count 0
- [ ] live TTS call count 0
- [ ] live Solar Pro 3 call count 0
- [ ] private audio saved count 0
- [ ] raw transcript public artifact count 0
- [ ] client secret exposure count 0
- [ ] STT/TTS metric plan includes WER, CER, place name accuracy
- [ ] TTS metric plan includes playback success and latency p95
- [ ] E2E metric plan includes voice round trip latency and RAG answer contract preservation
- [ ] private fact grain and public summary grain 분리
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] provider benchmark smoke execution next gate 분리

## Voice STT/TTS Provider Benchmark Local Smoke Gate

- [ ] voice STT/TTS provider benchmark local smoke document count 1
- [ ] voice STT/TTS provider benchmark local smoke report count 1
- [ ] local provider candidate count 1
- [ ] selected public-safe script count 5
- [ ] local TTS private wav generation count 5
- [ ] local CUDA Whisper STT execution count 5
- [ ] resolved device cuda
- [ ] external provider call count 0
- [ ] external audio transmission count 0
- [ ] live STT call count 0
- [ ] live TTS call count 0
- [ ] live Solar Pro 3 call count 0
- [ ] raw transcript public artifact count 0
- [ ] raw audio public artifact count 0
- [ ] WER, CER, place name accuracy, STT latency p95 기록
- [ ] private fact grain and public summary grain 분리
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] managed provider smoke approval next gate 분리

## Voice STT/TTS Local Model Ablation Gate

- [ ] voice STT/TTS local model ablation document count 1
- [ ] voice STT/TTS local model ablation report count 1
- [ ] model candidate count 3
- [ ] selected public-safe script count 5
- [ ] total local CUDA Whisper STT execution count 15
- [ ] resolved device cuda
- [ ] external provider call count 0
- [ ] external audio transmission count 0
- [ ] live STT call count 0
- [ ] live TTS call count 0
- [ ] live Solar Pro 3 call count 0
- [ ] raw transcript public artifact count 0
- [ ] raw audio public artifact count 0
- [ ] model별 WER, CER, place name accuracy, STT latency p95, model load time 기록
- [ ] best CER model and best place name accuracy model 기록
- [ ] private fact grain and public summary grain 분리
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] managed provider smoke approval next gate 유지

## Voice STT/TTS Managed Provider Smoke Approval Gate

- [ ] voice STT/TTS managed provider smoke approval document count 1
- [ ] voice STT/TTS managed provider smoke approval report count 1
- [ ] planned provider count 3
- [ ] planned max STT calls per provider 3 이하
- [ ] planned max TTS calls per provider 3 이하
- [ ] official source count 9
- [ ] pricing source recheck required count 4
- [ ] privacy source recheck required count 5
- [ ] region recheck required count 3
- [ ] retention recheck required count 3
- [ ] managed provider execution approved false
- [ ] managed provider API call count 0
- [ ] external audio transmission count 0
- [ ] live STT call count 0
- [ ] live TTS call count 0
- [ ] live Solar Pro 3 call count 0
- [ ] raw audio public artifact count 0
- [ ] raw transcript public artifact count 0
- [ ] raw payload public artifact count 0
- [ ] client secret exposure count 0
- [ ] private fact grain and public summary grain 분리
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] managed provider smoke execution next gate 분리

## Voice STT/TTS Managed Provider Smoke Execution Harness Gate

- [ ] voice STT/TTS managed provider smoke execution harness document count 1
- [ ] voice STT/TTS managed provider smoke execution harness report count 1
- [ ] dry run default true
- [ ] provider candidate count 3
- [ ] selected script count 3
- [ ] planned max STT calls per provider 3 이하
- [ ] planned max TTS calls per provider 3 이하
- [ ] call cap enforced true
- [ ] managed provider execution requested count 0
- [ ] managed provider API call count 0
- [ ] external audio transmission count 0
- [ ] live STT call count 0
- [ ] live TTS call count 0
- [ ] live Solar Pro 3 call count 0
- [ ] credential value public exposure count 0
- [ ] raw audio public artifact count 0
- [ ] raw transcript public artifact count 0
- [ ] raw payload public artifact count 0
- [ ] public private path leakage 0
- [ ] public secret-like leakage 0
- [ ] public raw payload leakage 0
- [ ] managed provider smoke execution next gate 유지
