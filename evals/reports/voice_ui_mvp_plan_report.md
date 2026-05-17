# Voice UI MVP Plan Report

## 결론

`HD-VOICE-UI-001`은 통과다.

다만 이 결과는 frontend 구현, production voice service, STT/TTS 성공, live Solar Pro 3 호출 성공을 의미하지 않는다. 이번 report는 browser voice-ready MVP를 구현하기 전 API mapping, 화면 범위, 보안 경계, portfolio claim boundary를 고정한 plan-only gate다.

## 정량 결과

| metric | value |
| --- | ---: |
| planned_user_journey_count | 3 |
| planned_screen_count | 5 |
| required_api_field_mapping_count | 12 |
| optional_voice_capability_count | 2 |
| frontend_implementation_count | 0 |
| stt_tts_production_claim_count | 0 |
| live_solar_call_count | 0 |
| locked_test_execution_count | 0 |
| retrieval_execution_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## 정성 평가

| gate | result | 근거 |
| --- | --- | --- |
| Product scope | PASS | browser MVP와 non-goal을 분리했다. |
| API contract | PASS | 기존 `/api/v1/chat` field 12개를 UI 표시 단위로 매핑했다. |
| RAG boundary | PASS | 검색 전략 변경이나 성능 개선 주장을 하지 않는다. |
| Voice boundary | PASS | voice-ready control 계획이며 STT/TTS 완성 claim이 없다. |
| Accessibility | PASS | typed fallback, caption, keyboard citation drawer 기준을 포함했다. |
| Security | PASS | secret, raw evidence, raw prompt, private path 표시 금지를 고정했다. |
| Portfolio | PASS | “RAG API를 관광 UI로 연결할 수 있게 설계”로 메시지를 제한했다. |
| External audit | PASS | 구현 전 계약 고정 순서가 타당하다. |

## Data Mart Grain

`fact_voice_ui_mvp_plan`의 grain은 `work_id + journey_id + screen_id + api_field + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-VOICE-UI-001` |
| `journey_id` | 사용자 journey 식별자 |
| `screen_id` | UI 화면 식별자 |
| `api_field` | `/api/v1/chat` request/response field |
| `claim_boundary` | plan-only, contract-only, no-live-call |
| `security_gate` | public-safe 노출 기준 |

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

- `HD-VOICE-UI-001`에서 voice UI MVP 계획과 API mapping을 고정했다.
- `/api/v1/chat`의 `spoken_answer`, `answer`, `citations`, `abstained`, `unsupported_claim_risk`를 UI 표시 단위로 매핑했다.
- 후속 frontend skeleton 구현 조건을 정의했다.

금지:

- production voice app 완성
- STT/TTS 품질 검증 완료
- live Solar Pro 3 기반 voice demo 성공
- retrieval 성능 개선
- generation 품질 개선
- locked test 개선 입증

## 다음 Gate

`HD-VOICE-UI-002`에서 browser frontend skeleton을 구현한다.

승인 전 작업지시서에는 다음을 포함해야 한다.

- `id`: `HD-VOICE-UI-002`
- `depends_on`: `HD-VOICE-UI-001`
- `scope`: frontend skeleton, contract fixture, UI state test
- `acceptance_tests`: answerable/no-answer/error/mic fallback/speaker fallback/security scan
- `risk_level`: medium
- `rollback_plan`: frontend files와 UI test만 revert
