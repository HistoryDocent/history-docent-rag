# Voice UI MVP Plan

## 결론

`HD-VOICE-UI-001`은 frontend/voice UI를 바로 구현하는 작업이 아니다.

목표는 `/api/v1/chat`의 `spoken_answer`, `answer`, `citations`, `abstained`, `unsupported_claim_risk` 계약을 기준으로 브라우저 기반 voice-ready 관광 도슨트 UI의 MVP 범위, 화면, 보안 경계, 평가 기준을 고정하는 것이다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| Product | 1차 UI는 서울/한양 관광 도슨트 경험을 보여주는 browser MVP로 제한한다. 모바일 앱, GPS, AR, production 음성 서비스는 제외한다. |
| Frontend | 첫 구현은 입력 fallback이 있는 chat surface, 장소 선택, citation drawer, `spoken_answer` 재생 후보 버튼까지로 제한한다. |
| API | 새 endpoint를 만들지 않고 기존 `/api/v1/chat` contract를 사용한다. |
| RAG | UI는 검색 알고리즘을 바꾸지 않는다. retrieval/generation 품질 개선 claim은 기존 평가 문서만 근거로 한다. |
| Security | frontend에는 secret, 원문 evidence, private path, raw prompt를 두지 않는다. microphone permission과 transcript는 client-local 기본값으로 둔다. |
| Evaluation | 이번 gate는 plan-only다. `frontend_implementation_count=0`, `live_solar_call_count=0`을 명시한다. |
| Portfolio | “RAG API를 실제 관광 사용 화면으로 연결할 수 있게 설계했다”가 포트폴리오 메시지다. “음성 앱 완성”은 금지한다. |
| 외부 감사 | UI를 먼저 만들기 전에 API field mapping과 public-safe boundary를 고정하는 순서가 타당하다. |

## 사용자와 사용 상황

| journey_id | 사용자 | 상황 | UI 목표 |
| --- | --- | --- | --- |
| `journey_ko_place` | 서울을 여행하는 한국인 | 경복궁, 광화문, 북촌, 한양도성 등 현장에서 짧게 듣고 싶다. | 장소 chip과 질문 입력으로 `spoken_answer`를 먼저 보여주고, 상세 `answer`와 citation을 펼쳐본다. |
| `journey_foreign_visitor` | 서울을 방문한 외국인 | 한국어 지명과 역사 용어가 낯설다. | `language=en` 또는 `mixed` 요청을 보낼 수 있게 하되, backend 지원 범위와 citation을 화면에 분리한다. |
| `journey_no_answer` | 근거 없는 질문을 하는 사용자 | 도서 corpus에 없는 내용을 묻는다. | `abstained=true`일 때 추측 답변 대신 모르는 상태와 다른 질문 제안을 보여준다. |

## MVP 화면

| screen_id | 화면 | 필수 요소 |
| --- | --- | --- |
| `screen_chat` | 도슨트 chat surface | 질문 입력, 장소 선택, 언어 선택, 전송 버튼, 응답 상태 |
| `screen_voice` | voice-ready control | microphone 버튼 후보, speaker 버튼 후보, typed fallback, captions |
| `screen_answer` | 답변 영역 | `spoken_answer` 우선 표시, 상세 `answer` 접기/펼치기 |
| `screen_citations` | citation drawer | citation id, source rank, recoverable 표시. 원문 chunk text는 표시하지 않음 |
| `screen_status` | 신뢰/상태 strip | `abstained`, `unsupported_claim_risk`, retrieval mode, route dry-run 상태 |

## API 연결 원칙

UI는 기존 `/api/v1/chat`을 호출한다.

요청 최소값:

| field | UI source | 비고 |
| --- | --- | --- |
| `query` | 질문 입력 또는 speech transcript 후보 | 1,000자 이하 |
| `language` | 언어 toggle | `ko`, `en`, `mixed` |
| `query_type` | 기본값 또는 고급 설정 | 기본 `place_story` |
| `place_context` | 장소 chip | 최대 10개 |
| `voice_mode` | speaker/microphone control | 짧은 답변 우선 렌더링 |
| `retrieval_mode` | 환경 설정 | MVP 기본은 backend default 또는 명시된 안전 모드 |
| `provider_mode` | 환경 설정 | public demo 기본은 `contract_only`; live는 별도 승인 |
| `active_route_mode` | 실험 flag | 기본 `disabled`; shadow만 표시 후보 |

응답 핵심값:

| field | UI 사용 |
| --- | --- |
| `answer` | 상세 텍스트 답변 |
| `spoken_answer` | 음성 재생/짧은 답변 영역 |
| `citations` | citation drawer |
| `evidence_ids` | 내부 trace id count만 표시 가능 |
| `place_ids` | 장소 chip highlight |
| `abstained` | no-answer state |
| `unsupported_claim_risk` | caution badge |
| `usage.retrieval_mode` | debug/portfolio panel |
| `usage.route_policy_id` | debug/portfolio panel |
| `usage.retrieval_candidate_count` | debug/portfolio panel |
| `classifier_router_dry_run.active_route_applied` | active route 미적용 표시 |
| `classifier_router_dry_run.guarded_route_candidate.guard_applied` | route guard 적용 표시 |

## Voice 기능 경계

이번 MVP 계획의 voice는 “서비스 완성”이 아니라 “voice-ready surface”다.

허용:

- browser-native speech 입력 후보를 붙일 수 있는 button state 설계
- `spoken_answer`를 화면에 우선 렌더링
- speaker button으로 `spoken_answer` 재생 후보 설계
- typed fallback을 항상 제공

금지:

- production STT/TTS 완성 주장
- 모바일 앱 완성 주장
- 음성 transcript 저장 기본값
- backend secret을 frontend에 전달
- raw evidence, raw prompt, chunk text 표시

## 접근성과 UX 기준

- microphone이 없어도 typed input으로 동일 flow가 가능해야 한다.
- speaker 재생이 실패해도 `spoken_answer` text가 보여야 한다.
- citation drawer는 keyboard로 열고 닫을 수 있어야 한다.
- `abstained=true`는 실패가 아니라 안전 응답으로 표현한다.
- 긴 `answer`는 접기/펼치기로 처리하고, 첫 화면은 `spoken_answer` 중심으로 둔다.

## 보안과 공개 경계

| 항목 | 기준 |
| --- | --- |
| secret | frontend bundle, docs, report, sample에 기록 금지 |
| private path | public 문서와 UI sample에 기록 금지 |
| raw evidence | citation id와 집계만 표시, 원문 chunk text 금지 |
| raw prompt | 표시 금지 |
| transcript | 기본 저장 금지, 저장 기능은 별도 승인 후 설계 |
| provider mode | public demo 기본은 `contract_only`; live provider는 별도 승인 |
| error | stack trace와 provider detail 노출 금지 |

## 성공 기준

| metric | target |
| --- | ---: |
| planned_user_journey_count | 3 |
| planned_screen_count | 5 |
| required_api_field_mapping_count | 12 |
| optional_voice_capability_count | 2 |
| frontend_implementation_count | 0 |
| stt_tts_production_claim_count | 0 |
| live_solar_call_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Non-goal

- 실서비스 배포
- production voice app
- GPS/AR route guide
- user account
- 결제/예약
- frontend에서 RAG 검색 알고리즘 변경
- GraphRAG/RAPTOR/HyDE를 UI 기본값으로 새로 채택
- live Solar Pro 3 호출 실행

## 다음 작업

`HD-VOICE-UI-002`에서 browser frontend skeleton을 구현한다.

완료 기준은 다음이다.

- `/api/v1/chat` mock/contract response를 렌더링한다.
- `spoken_answer`, `answer`, `citations`, `abstained`, `unsupported_claim_risk`가 화면에 분리되어 보인다.
- microphone/speaker control은 지원 여부에 따라 disabled/fallback state를 가진다.
- frontend bundle에 secret, private path, raw evidence가 없다.
- E2E 또는 component test에서 answerable/no-answer/error state를 검증한다.
