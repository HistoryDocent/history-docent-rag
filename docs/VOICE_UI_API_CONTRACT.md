# Voice UI API Contract

## 결론

Voice UI MVP는 새 backend endpoint를 요구하지 않는다.

기존 `POST /api/v1/chat`의 request/response contract를 frontend 표시 단위로 매핑하고, UI가 표시해도 되는 값과 숨겨야 하는 값을 분리한다.

## Request Mapping

| API field | required | UI control | validation note |
| --- | --- | --- | --- |
| `request_id` | no | client request trace | 없으면 backend가 생성 |
| `query` | yes | text input 또는 speech transcript 후보 | blank 금지, max 1000 |
| `language` | yes | language toggle | `ko`, `en`, `mixed` |
| `query_type` | yes | query type selector 또는 default | MVP 기본 `place_story` |
| `place_context` | no | selected place chips | catalog place id만 허용, max 10 |
| `voice_mode` | no | voice-ready toggle | `spoken_answer` 우선 UI에 사용 |
| `user_context` | no | optional context input | max 600 |
| `retrieval_mode` | yes | environment/debug setting | public demo는 안전 설정 우선 |
| `provider_mode` | yes | environment setting | 기본 `contract_only`, live는 별도 승인 |
| `active_route_mode` | yes | experiment setting | 기본 `disabled` |

## Response Mapping

| API field | UI target | display policy |
| --- | --- | --- |
| `answer` | detailed answer panel | 표시 가능 |
| `spoken_answer` | primary spoken answer area, TTS text source | 표시 가능 |
| `citations` | citation drawer | citation metadata만 표시 |
| `evidence_ids` | debug count, trace-only label | 원문 연결 없이 count/id만 제한 표시 |
| `place_ids` | place chip highlight | 표시 가능 |
| `abstained` | no-answer state | 표시 가능 |
| `unsupported_claim_risk` | risk badge | 표시 가능 |
| `usage.retrieval_mode` | portfolio/debug panel | default collapsed |
| `usage.route_policy_id` | portfolio/debug panel | default collapsed |
| `usage.retrieval_candidate_count` | portfolio/debug panel | default collapsed |
| `classifier_router_dry_run.active_route_applied` | route status | active route 미적용 표시 |
| `classifier_router_dry_run.guarded_route_candidate.guard_applied` | route guard status | guard 적용 여부 표시 |

`required_api_field_mapping_count=12`로 고정한다.

## UI State Contract

| state_id | condition | UI behavior |
| --- | --- | --- |
| `idle` | initial state | place selector와 query input 표시 |
| `loading` | request in-flight | input disable, cancel/retry 후보 표시 |
| `answerable` | `abstained=false` | `spoken_answer`, `answer`, `citations` 표시 |
| `no_answer` | `abstained=true` | 추측 답변 금지, 다른 질문 제안 |
| `risk_warn` | `unsupported_claim_risk`가 낮지 않음 | caution badge와 citation 확인 유도 |
| `mic_unavailable` | browser speech input unsupported | microphone control disabled, typed fallback |
| `speaker_unavailable` | browser speech output unsupported | speaker control disabled, text 유지 |
| `api_error` | 4xx/5xx response | stack trace 없이 요약 오류 |

## Citation Display Contract

표시 가능:

- `citation_id`
- `doc_id`
- `source_rank`
- `pack_rank`
- `citation_recoverable`
- citation count

표시 금지:

- raw evidence text
- raw chunk text
- raw prompt
- private local path
- secret
- full parser payload

## Provider and Cost Boundary

`provider_mode=contract_only`가 public demo의 기본값이다.

`provider_mode=solar_pro_3`은 실제 비용과 외부 호출이 발생할 수 있으므로 별도 승인, `.env` 로컬 주입, public-safe report 정책을 통과한 경우에만 사용한다.

이번 `HD-VOICE-UI-001`에서는 live provider 호출이 없다.

## Security Checklist

- frontend bundle에 provider credential을 포함하지 않는다.
- network request에는 사용자가 입력한 query와 선택한 context만 보낸다.
- transcript 저장은 기본 비활성화한다.
- public log에는 query 원문과 answer 원문을 남기지 않는다.
- error response는 stack trace와 provider detail을 표시하지 않는다.
- citation drawer는 원문 노출이 아니라 provenance metadata 표시로 제한한다.

## 다음 구현 Gate

`HD-VOICE-UI-002`는 다음 acceptance test를 가져야 한다.

- answerable fixture에서 `spoken_answer`, `answer`, `citations`가 분리 렌더링된다.
- no-answer fixture에서 `abstained=true`가 안전 상태로 렌더링된다.
- microphone unsupported 환경에서 typed fallback이 남는다.
- speaker unsupported 환경에서 `spoken_answer` text가 남는다.
- frontend artifact에 secret-like value, private path, raw evidence가 없다.
