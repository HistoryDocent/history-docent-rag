# Voice UI Contract Smoke

## 결론

`HD-VOICE-UI-003`은 frontend/backend contract smoke 단계다.

이번 작업은 frontend skeleton이 fixture-only에서 끝나지 않고 FastAPI `/api/v1/chat`의 `contract_only` 응답을 받을 수 있는 연결 경로를 검증한다. live Solar Pro 3 호출, retrieval 실행, production voice service, STT/TTS 품질 검증은 범위가 아니다.

## 구현 범위

| 영역 | 구현 |
| --- | --- |
| Vite proxy | local `/api` 요청을 `http://127.0.0.1:8000` FastAPI dev server로 전달 |
| frontend mode | `VITE_HISTORY_DOCENT_CHAT_MODE=fixture` 기본, `backend`일 때 backend 호출 |
| endpoint resolution | base URL이 없으면 same-origin `/api/v1/chat`, 있으면 explicit backend base URL 사용 |
| contract smoke script | `npm run smoke:contract`로 frontend URL 200과 backend answerable/no-answer 응답 검증 |
| frontend unit test | backend mode가 fixture branch를 우회하고 `/api/v1/chat`를 호출하는지 검증 |
| backend regression | FastAPI `TestClient`로 answerable/no-answer contract-only 응답 검증 |
| public report | 정량/정성 smoke 결과와 claim boundary 기록 |

## 실행 방법

backend dev server:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

frontend dev server:

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

## Smoke 기준

| check | expected |
| --- | --- |
| frontend URL | HTTP 200 |
| answerable `/api/v1/chat` | HTTP 200 |
| answerable `abstained` | false |
| answerable citation count | 1 |
| no-answer `/api/v1/chat` | HTTP 200 |
| no-answer `abstained` | true |
| no-answer citation count | 0 |
| `live_solar_call_count` | 0 |
| `active_route_applied` | false |

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| Product | UI skeleton 다음에는 실제 backend contract 연결 증거가 필요하다. |
| Frontend | fixture mode와 backend mode를 분리해 portfolio demo와 local smoke를 모두 지원한다. |
| API | 새 endpoint 없이 기존 `/api/v1/chat`만 사용한다. |
| Security | CORS를 넓히지 않고 local Vite proxy를 사용한다. |
| Evaluation | frontend unit, backend TestClient, local smoke script를 분리했다. |
| Data warehouse | `fact_voice_ui_contract_smoke` grain으로 서버, request type, UI transport, claim boundary를 기록한다. |
| 외부 감사 | live provider 없이 contract-only 연결을 먼저 검증하는 순서가 타당하다. |

## Non-goal

- production 배포
- live Solar Pro 3 호출
- retrieval-backed private corpus 실행
- real browser microphone transcript 수집
- STT/TTS 품질 검증
- raw evidence 또는 raw chunk text 표시

## 다음 작업

`HD-VOICE-UI-004`는 real browser visual QA다.

다음 gate에서는 browser screenshot 또는 Playwright 기반으로 desktop/mobile layout, button state, citation drawer, no-answer state를 확인한다.
