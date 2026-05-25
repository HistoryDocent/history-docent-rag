# Portfolio Demo Runbook

## 결론

`HD-PORTFOLIO-DEMO-001`은 통과이며, `HD-VOICE-DEMO-RUNBOOK-REFRESH-001` 기준으로 최신화했다.

이 문서는 HistoryDocent를 취업 포트폴리오로 설명할 때 사용할 local demo 순서와 claim boundary를 고정한다. 목적은 “production 서비스 시연”이 아니라 “평가 기반 RAG 의사결정 구조, `/api/v1/chat` 계약, browser voice-ready UI, 무료 로컬 음성 route smoke를 안전하게 재현하는 방법”을 보여주는 것이다.

## Demo 범위

| 포함 | 제외 |
| --- | --- |
| README 결과 요약 확인 | 원본 PDF 공개 |
| final ablation report 확인 | 전체 parser JSON 공개 |
| `/api/v1/chat` contract-only 응답 확인 | 전체 chunk text 공개 |
| frontend fixture mode 확인 | private vector index 공개 |
| frontend backend mode smoke 확인 | production 배포 claim |
| voice UI visual QA screenshot 확인 | STT/TTS production 품질 검증 claim |
| local voice demo stack decision 확인 | 실제 관광객 음성 품질 검증 claim |
| local voice playback smoke 결과 확인 | microphone capture 구현 완료 claim |
| local voice API route smoke 결과 확인 | speaker playback 구현 완료 claim |

## 준비 기준

| check | 기준 |
| --- | --- |
| Python dependency | repo의 기존 Python 환경에서 `pytest` 실행 가능 |
| Frontend dependency | `frontend/package-lock.json` 기준 `npm install` 완료 |
| Secret | contract-only demo에는 API key 불필요 |
| Private data | demo runbook은 private corpus 경로를 요구하지 않음 |
| Browser | local `127.0.0.1` 접근 가능 |
| Voice route | 기본 비활성화 상태이며 explicit local flag에서만 contract smoke로 확인 |

## 1. 빠른 검증

repo root에서 다음 명령을 실행한다.

```powershell
pytest -q
ruff check .
pytest tests/test_portfolio_demo_runbook.py tests/test_voice_demo_playback_smoke.py tests/test_voice_api_local_runtime_route_smoke.py -q
```

frontend 검증:

```powershell
cd frontend
npm run check
npm audit --audit-level=high
```

이 단계가 실패하면 demo를 시작하지 않는다.

## 2. API Contract Demo

backend dev server:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

별도 terminal에서 contract-only request:

```powershell
$body = @{
  request_id = "portfolio-demo-contract"
  query = "경복궁을 한양 맥락에서 짧게 설명해줘"
  language = "ko"
  query_type = "place_story"
  place_context = @("gyeongbokgung")
  voice_mode = $true
  retrieval_mode = "contract_only"
  provider_mode = "contract_only"
  active_route_mode = "disabled"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

확인할 포인트:

- `spoken_answer`가 존재한다.
- `citations`가 존재한다.
- `usage.solar_call_count`는 0이다.
- `classifier_router_dry_run.active_route_applied`는 false다.

## 3. Frontend Fixture Demo

frontend 단독 fixture mode:

```powershell
cd frontend
$env:VITE_HISTORY_DOCENT_CHAT_MODE="fixture"
npm run dev -- --port 5173
```

브라우저에서 `http://127.0.0.1:5173`을 연다.

확인할 포인트:

- answerable 상태에서 `spoken_answer`와 citation drawer가 보인다.
- `근거 없음` 시나리오에서 no-answer 상태가 보인다.
- `오류` 시나리오에서 sanitized error만 보인다.
- microphone/speaker control이 화면에 표시된다.

## 4. Frontend Backend Mode Demo

backend dev server를 먼저 실행한다.

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

frontend backend mode:

```powershell
cd frontend
$env:VITE_HISTORY_DOCENT_CHAT_MODE="backend"
npm run dev -- --port 5173
```

smoke script:

```powershell
cd frontend
npm run smoke:contract
```

확인할 포인트:

- frontend는 Vite proxy를 통해 `/api/v1/chat`을 호출한다.
- answerable/no-answer contract-only 응답이 통과한다.
- live Solar Pro 3 호출은 0이다.
- retrieval execution은 0이다.

## 5. Local Voice Route Evidence 확인

로컬 음성 API route smoke:

```powershell
python -m pipelines.voice_api_local_runtime_route_smoke
```

확인할 artifact:

| artifact | 설명 |
| --- | --- |
| `docs/VOICE_DEMO_STACK_DECISION.md` | 무료 로컬 STT/TTS demo 후보와 production final 미확정 경계 |
| `docs/VOICE_DEMO_PLAYBACK_SMOKE.md` | private wav 5개 playback-ready, speaker 자동 재생 0 |
| `docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md` | `/api/v1/voice/local-runtime` 기본 비활성화와 explicit flag contract smoke |
| `evals/reports/voice_api_local_runtime_route_smoke_report.md` | default disabled 1, explicit flag contract 1, external provider call 0 |

확인할 포인트:

- local voice route는 기본 비활성화 상태다.
- explicit local flag에서만 contract-only 응답을 확인했다.
- route smoke는 local STT/TTS 실제 실행 품질 검증이 아니다.
- public artifact에는 raw audio, transcript, private path를 남기지 않는다.

## 6. Visual Evidence 확인

다음 artifact를 확인한다.

| artifact | 설명 |
| --- | --- |
| `evals/reports/assets/voice_ui_visual_qa_desktop_answerable.jpg` | desktop answerable, 상세 답변, citation drawer |
| `evals/reports/assets/voice_ui_visual_qa_mobile_no_answer.jpg` | mobile no-answer, single-column layout |
| `evals/reports/assets/voice_ui_visual_qa_desktop_error.jpg` | sanitized error |

## 7. 면접 Demo Script

권장 순서:

1. README 첫 화면에서 문제 정의와 현재 stack을 설명한다.
2. `docs/FINAL_ABLATION_REPORT.md`에서 채택, 보류, 기각을 설명한다.
3. `docs/API_RESPONSE_SAMPLE.md`에서 `/api/v1/chat` 응답 계약을 설명한다.
4. `docs/VOICE_DEMO_STACK_DECISION.md`에서 무료 로컬 STT/TTS demo 후보와 production final 미확정 경계를 설명한다.
5. `docs/VOICE_DEMO_PLAYBACK_SMOKE.md`에서 playback-ready 5개와 자동 speaker playback 0을 설명한다.
6. `docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md`에서 local voice route가 기본 비활성화이고 explicit flag에서만 contract smoke를 통과했음을 설명한다.
7. contract-only API request 또는 `npm run smoke:contract`를 실행한다.
8. voice UI 화면에서 `spoken_answer`, citation drawer, no-answer 상태를 보여준다.
9. 마지막에 금지 claim을 먼저 말한다.

면접에서 강조할 문장:

```text
이 프로젝트의 핵심은 최신 RAG 기법을 모두 붙인 것이 아니라, 같은 평가 gate에서 비교하고 성능, latency, citation risk, locked 결과를 기준으로 채택과 기각을 분리한 점입니다.
```

## 허용 Claim

- 평가 기반 RAG 의사결정 구조를 구현했다.
- `/api/v1/chat` contract-only demo와 frontend fixture/backend mode demo 절차를 정리했다.
- 무료 로컬 STT/TTS demo 후보를 정리했다.
- local voice playback smoke에서 private wav 5개가 playback-ready임을 확인했다.
- local voice API route smoke에서 기본 비활성화와 explicit local flag contract를 확인했다.
- 위 음성 demo evidence에서 external provider call과 external audio transmission은 0으로 유지했다.

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

## Troubleshooting

| 증상 | 대응 |
| --- | --- |
| port 8000 사용 중 | 기존 backend dev server를 종료하거나 다른 port로 실행하고 frontend proxy 설정은 별도 수정하지 않는다. |
| port 5173 사용 중 | `npm run dev -- --port 5174`로 임시 실행할 수 있다. 단, smoke script는 기본 5173을 기준으로 한다. |
| API key 없음 | contract-only demo에는 API key가 필요 없다. |
| private data 없음 | public demo는 private corpus 없이 API contract와 fixture UI만 보여준다. |
| frontend dependency 없음 | `frontend/package-lock.json` 기준으로 `npm install` 후 다시 실행한다. |

## Data Mart Grain

`fact_portfolio_demo_runbook`의 grain은 `work_id + demo_step_id + command_surface + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-PORTFOLIO-DEMO-001` |
| `demo_step_id` | quick_check, api_contract, frontend_fixture, frontend_backend, local_voice_route_evidence, visual_evidence, interview_script |
| `command_surface` | python, pytest, ruff, npm, browser, document |
| `claim_boundary` | public-safe, contract-only, fixture-only, no-live-call |

금지 필드:

- raw answer
- raw evidence
- raw prompt
- chunk text
- private path
- secret

## 다음 작업

다음 작업 후보는 public repository audit refresh v2다.

public repository audit refresh, portfolio submission rehearsal, voice STT/TTS planning, voice STT/TTS contract skeleton, provider benchmark plan, local voice demo stack decision, local voice playback smoke, local voice API route smoke, demo runbook refresh는 완료됐다. 후속 제출 준비를 이어간다면 갱신된 runbook과 README 링크 기준으로 public-safe scan을 한 번 더 실행한다.
