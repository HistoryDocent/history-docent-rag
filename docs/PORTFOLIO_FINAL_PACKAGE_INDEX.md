# Portfolio Final Package Index

## 결론

`HD-PORTFOLIO-FINAL-PACKAGE-INDEX-001`은 통과다.

이 문서는 HistoryDocent를 취업 포트폴리오로 제출할 때 확인할 최종 index다. 목적은 새 실험이나 production 성공 주장이 아니라, README, 핵심 평가 결과, demo runbook, voice evidence, 제출 감사, 금지 claim을 한 화면에서 따라갈 수 있게 고정하는 것이다.

## 제출 메시지

한 줄 요약:

```text
서울/한양 관광 도슨트용 citation RAG 백엔드를 설계하고, 청킹/검색/생성/음성 demo 후보를 동일한 평가 gate와 claim boundary 안에서 비교한 프로젝트입니다.
```

30초 설명:

```text
이 프로젝트는 한국사 도서 parser 결과를 기반으로 서울 주요 장소를 한양 역사 맥락과 연결해 설명하는 RAG 백엔드입니다. 핵심은 모델을 많이 붙인 것이 아니라, parent-child chunking, dense retrieval, hybrid route, query rewrite, evidence packing, GraphRAG/RAPTOR/HyDE/ColBERT-style 후보를 같은 평가 체계로 비교하고 채택/보류/기각을 문서화한 점입니다. 음성은 production 앱이 아니라 무료 로컬 STT/TTS demo 후보와 route smoke까지만 public-safe하게 검증했습니다.
```

## 제출자가 먼저 열 문서

| 순서 | artifact | 목적 | 말할 수 있는 claim |
| ---: | --- | --- | --- |
| 1 | `README.md` | 전체 프로젝트 목적, 현재 stack, 핵심 수치 확인 | 평가 기반 RAG 의사결정 구조를 구현했다 |
| 2 | `docs/FINAL_ABLATION_REPORT.md` | 채택/보류/기각 결정 확인 | GraphRAG/RAPTOR/HyDE 등을 무조건 채택하지 않고 비교 후 기각/보류했다 |
| 3 | `docs/API_RESPONSE_SAMPLE.md` | `/api/v1/chat` 응답 계약 확인 | `spoken_answer`, citation, no-answer 계약을 정의했다 |
| 4 | `docs/PORTFOLIO_DEMO_RUNBOOK.md` | local demo 순서 확인 | contract-only API와 frontend fixture/backend mode demo가 가능하다 |
| 5 | `docs/VOICE_DEMO_STACK_DECISION.md` | 무료 로컬 음성 demo 후보 확인 | STT/TTS demo 후보를 정리했지만 final provider는 확정하지 않았다 |
| 6 | `docs/VOICE_DEMO_PLAYBACK_SMOKE.md` | private wav playback-ready evidence 확인 | private wav 5개가 playback-ready임을 확인했다 |
| 7 | `docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md` | local voice route smoke 확인 | route는 기본 비활성화이며 explicit flag에서 contract smoke를 통과했다 |
| 8 | `docs/SUBMISSION_REFRESH_AUDIT_V2.md` | 제출 전 public-safe 감사 확인 | secret/private path/raw audio/transcript 공개 노출을 막았다 |

## 최종 제출 evidence map

| evidence family | primary docs | primary reports |
| --- | --- | --- |
| 제품 정의 | `docs/PRD.md`, `docs/PORTFOLIO_STRATEGY.md` | `evals/reports/portfolio_qa_report.md` |
| RAG 최종 판단 | `docs/FINAL_ABLATION_REPORT.md`, `docs/RAG_DECISION_LEDGER.md` | `evals/reports/final_ablation_report.md` |
| API 계약 | `docs/API_RESPONSE_SAMPLE.md`, `docs/VOICE_UI_API_CONTRACT.md` | `evals/reports/api_response_sample_report.md`, `evals/reports/voice_ui_contract_smoke_report.md` |
| Demo 실행 | `docs/PORTFOLIO_DEMO_RUNBOOK.md`, `docs/VOICE_UI_VISUAL_QA.md` | `evals/reports/portfolio_demo_runbook_refresh_report.md`, `evals/reports/voice_ui_visual_qa_report.md` |
| 무료 로컬 음성 | `docs/VOICE_DEMO_STACK_DECISION.md`, `docs/VOICE_DEMO_PLAYBACK_SMOKE.md`, `docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md` | `evals/reports/voice_demo_stack_decision_report.md`, `evals/reports/voice_demo_playback_smoke_report.md`, `evals/reports/voice_api_local_runtime_route_smoke_report.md` |
| 제출 감사 | `docs/SUBMISSION_READY_CHECKLIST.md`, `docs/SUBMISSION_REFRESH_AUDIT_V2.md` | `evals/reports/submission_ready_report.md`, `evals/reports/submission_refresh_audit_v2_report.md` |

## 면접에서 말할 순서

1. 문제 정의: 서울/한양 관광 도슨트 RAG 백엔드다.
2. 데이터 경계: 원본 PDF, 전체 parser JSON, 전체 chunk text, vector index, secret은 공개하지 않는다.
3. 핵심 설계: parent-child chunking, E5-small voice rewrite, P0 evidence packing, citation answer contract를 기본 후보로 둔다.
4. 비교 결과: GraphRAG-lite, RAPTOR-lite, HyDE larger, ColBERT-style late interaction은 기본 route로 채택하지 않았다.
5. API: `/api/v1/chat`는 contract-only demo에서 `spoken_answer`, citation, no-answer를 확인할 수 있다.
6. UI: browser voice-ready frontend는 fixture/backend mode와 screenshot artifact로 검증했다.
7. 음성: 무료 로컬 STT/TTS demo 후보, playback smoke, route smoke까지만 주장한다.
8. 감사: public-safe scan과 금지 claim 검토를 통과했다.

## 최종 검증 명령

repo root:

```powershell
pytest -q
ruff check .
git diff --check
```

frontend:

```powershell
cd frontend
npm run check
npm audit --audit-level=high
```

targeted package index regression:

```powershell
pytest tests/test_portfolio_final_package_index.py tests/test_submission_refresh_audit_v2.py tests/test_portfolio_demo_runbook_refresh.py -q
```

public leak scan:

```powershell
rg -n "([A-Za-z]:\\|UPSTAGE_API_KEY\s*=|sk-[A-Za-z0-9]|private_data[/\\])" README.md docs evals\reports tests app pipelines retrieval configs frontend -g "*.md" -g "*.py" -g "*.toml" -g "*.ts" -g "*.tsx" -g "*.json" -g "*.css" -g "*.html" -g "*.mjs" -g "!frontend/node_modules/**" -g "!frontend/dist/**"
```

## 허용 Claim

- 평가 기반 RAG 의사결정 구조를 구현했다.
- 같은 평가 gate에서 후보를 비교하고 채택/보류/기각을 분리했다.
- `/api/v1/chat` contract와 citation/no-answer 응답 경계를 정의했다.
- browser voice-ready UI skeleton과 contract smoke를 검증했다.
- 무료 로컬 STT/TTS demo 후보, playback smoke, local voice route smoke를 public-safe하게 정리했다.
- 제출 전 public-safe audit v2를 통과했다.

## 금지 Claim

- production 성능 검증 완료
- locked test에서 최종 성능 개선 입증
- GraphRAG로 성능 개선
- RAPTOR로 성능 개선
- HyDE로 최종 검색 성능 개선
- Solar Pro 3 답변 품질 최종 개선
- 음성 관광 앱 완성
- STT/TTS production 품질 검증 완료
- STT/TTS provider 최종 확정
- 실제 관광객 음성 품질 검증 완료
- microphone capture 구현 완료
- speaker playback 구현 완료
- 전체 도서 데이터 공개

## 담당 관점 감사

| 담당 관점 | 판단 |
| --- | --- |
| 제품 | 최종 제출 경로가 문제 정의, RAG 판단, API, demo, 음성, 감사 순서로 정리되어 있다. |
| 아키텍처 | production claim 없이 contract-only demo와 evidence artifact를 분리했다. |
| 평가 | 실험 결과와 제출 메시지를 섞지 않고 각 문서의 gate를 참조하게 했다. |
| 보안 | raw audio/transcript, private path, secret, chunk text를 final index에 기록하지 않는다. |
| 데이터 | final index fact의 grain은 `package_id + evidence_family + artifact_id + claim_boundary`로 둔다. |
| 외부 감사 | v2 감사 이후 최종 제출자가 볼 index를 만든 순서는 타당하다. |

## Data Mart Grain

`fact_portfolio_final_package_index`의 grain은 `package_id + evidence_family + artifact_id + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `package_id` | `HD-PORTFOLIO-FINAL-PACKAGE-INDEX-001` |
| `evidence_family` | product, rag_decision, api_contract, demo, voice, audit |
| `artifact_id` | 문서 또는 리포트의 stable id |
| `claim_boundary` | public-safe, contract-only, route-smoke-only, no-production-claim |
| `status` | PASS, WARN, FAIL |

금지 필드:

- raw query
- raw answer
- raw evidence
- raw audio
- transcript
- prompt
- chunk text
- private path
- secret

## 다음 작업

필수 포트폴리오 제출 패키지는 이 index 기준으로 완료다.

후속 제출 운영 문서로 `HD-README-LANDING-POLISH-001`과 `HD-PORTFOLIO-WALKTHROUGH-SCRIPT-001`을 완료했다.

후속 제출 운영 문서로 `HD-DEMO-RECORDING-CHECKLIST-001`까지 완료했다. 실제 녹화 전 브라우저 화면, 터미널 출력, 금지 claim, raw artifact 노출 여부를 점검하는 기준이며, 새 기능이나 성능 claim은 추가하지 않았다.

다음은 `HD-GITHUB-PUSH-READINESS-001`을 권장한다. push 자체가 아니라, public repo에 push하기 전 remote, branch, commit 범위, secret scan, private/large artifact 추적 여부를 재검증하는 작업이다.
