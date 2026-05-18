# Voice UI Contract Smoke Report

## 결론

`HD-VOICE-UI-003`은 통과다.

Frontend skeleton은 backend mode에서 FastAPI `/api/v1/chat`의 `contract_only` 응답을 받을 수 있는 경로를 갖는다. 이번 결과는 live Solar Pro 3 호출 성공, retrieval 성능 개선, production voice service, STT/TTS 품질 검증을 의미하지 않는다.

## 정량 결과

| metric | value |
| --- | ---: |
| frontend_proxy_route_count | 1 |
| frontend_backend_mode_count | 1 |
| frontend_backend_mode_unit_test_count | 4 |
| backend_contract_smoke_request_count | 2 |
| backend_answerable_status_code | 200 |
| backend_no_answer_status_code | 200 |
| backend_answerable_citation_count | 1 |
| backend_no_answer_citation_count | 0 |
| backend_active_route_applied_count | 0 |
| local_dev_server_smoke_count | 1 |
| live_solar_call_count | 0 |
| retrieval_execution_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## 정성 평가

| gate | result | 근거 |
| --- | --- | --- |
| Frontend transport | PASS | backend mode는 same-origin `/api/v1/chat` 또는 explicit backend base URL을 사용한다. |
| API contract | PASS | answerable/no-answer contract-only 응답을 검증한다. |
| Security | PASS | CORS 확장 없이 local Vite proxy를 사용한다. |
| Evaluation | PASS | frontend unit test, backend TestClient, local smoke script를 분리했다. |
| Claim boundary | PASS | live provider, retrieval execution, production voice claim이 없다. |
| External audit | PASS | fixture UI 다음에 contract smoke를 분리한 순서가 타당하다. |

## Data Mart Grain

`fact_voice_ui_contract_smoke`의 grain은 `work_id + server_id + request_type + transport_mode + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-VOICE-UI-003` |
| `server_id` | frontend dev server, FastAPI dev server |
| `request_type` | answerable, no_answer |
| `transport_mode` | fixture, backend_proxy, explicit_backend |
| `claim_boundary` | contract-only, no-live-call, local-dev-only |

금지 필드:

- raw query
- raw answer
- raw evidence
- raw prompt
- chunk text
- private path
- secret

## Claim Boundary

허용:

- frontend backend mode와 Vite proxy를 추가했다.
- FastAPI `/api/v1/chat` contract-only answerable/no-answer smoke를 검증했다.
- local dev server smoke script를 추가했다.

금지:

- production voice app 완성
- live Solar Pro 3 기반 demo 성공
- STT/TTS 품질 검증 완료
- retrieval 성능 개선
- generation 품질 개선
- locked test 개선 입증

## 다음 Gate

`HD-VOICE-UI-004`는 real browser visual QA다.

승인 전 작업지시서에는 다음을 포함해야 한다.

- `id`: `HD-VOICE-UI-004`
- `depends_on`: `HD-VOICE-UI-003`
- `scope`: browser visual QA, desktop/mobile screenshot, UI state click path
- `acceptance_tests`: answerable layout, no-answer layout, citation drawer, voice fallback button, no overlap
- `risk_level`: medium
- `rollback_plan`: visual QA docs/test artifacts만 revert
