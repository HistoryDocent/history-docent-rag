# Voice STT/TTS Plan

## 결론

`HD-VOICE-STT-TTS-PLAN-001`의 결론은 실제 STT/TTS를 바로 구현하지 않는 것이다.

현재 portfolio 제출 기준은 이미 `spoken_answer`를 포함한 RAG API, browser voice-ready UI skeleton, contract smoke, visual QA까지 완료했다. 다음 제품 개발은 실제 음성 입출력을 붙이기 전에 provider, 개인정보, 비용, failure mode, 평가 metric을 별도 gate로 고정해야 한다.

이번 문서는 planning gate다. live STT 호출, live TTS 호출, live Solar Pro 3 호출, production 음성 서비스 성공, STT/TTS 품질 검증을 주장하지 않는다.

## 범위

포함:

- STT/TTS 사용자 흐름
- `/api/v1/chat` text-first 계약과 voice adapter 경계
- provider 선택 기준
- 개인정보 및 로그 정책
- 비용 gate와 latency gate
- failure mode와 fallback
- 정량/정성 평가 기준
- 다음 구현 work order

제외:

- 실제 microphone capture 구현
- 실제 STT provider 호출
- 실제 TTS provider 호출
- private audio 저장
- provider 최종 선정
- production voice app claim
- live Solar Pro 3 voice demo claim

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| 제품 | 사용자는 서울 현장에서 짧게 묻고 듣는 흐름이 중요하다. STT/TTS 자체보다 답변 길이, 실패 fallback, citation 확인이 먼저다. |
| API | `/api/v1/chat`은 text-first로 유지한다. 음성은 transcript 생성과 playback adapter로 분리해야 RAG 평가 기준이 흔들리지 않는다. |
| 보안 | microphone consent, 외부 전송 고지, secret client 노출 금지, raw transcript/public report 금지가 gate다. |
| 평가 | STT, TTS, RAG answer quality를 한 metric으로 섞지 않는다. 각 stage별 metric과 e2e metric을 분리한다. |
| 데이터 | fact grain은 `work_id + voice_stage + scenario_id + claim_boundary`로 고정한다. |
| 운영 | provider timeout, quota, browser permission, autoplay block이 실제 demo 실패 원인이 될 수 있다. fallback-first 설계가 필요하다. |
| 외부 감사 | 현재 문서는 실행 결과가 아니라 안전한 구현 전 계획이다. provider나 품질을 확정한 표현은 금지한다. |

## 목표 사용자 흐름

| step | stage | 설명 | 현재 상태 |
| --- | --- | --- | --- |
| 1 | consent | 사용자가 microphone 사용을 명시적으로 허용한다. | plan-only |
| 2 | stt | 음성을 transcript draft로 변환한다. | 미구현 |
| 3 | confirmation | 사용자가 transcript를 확인하거나 수정한다. | 미구현 |
| 4 | chat | 확인된 text query를 `/api/v1/chat`에 전달한다. | text contract 구현 완료 |
| 5 | answer | RAG API가 `answer`, `spoken_answer`, `citations`, `abstained`를 반환한다. | contract 구현 완료 |
| 6 | tts | `spoken_answer`를 음성으로 재생한다. | 미구현 |
| 7 | fallback | 실패하면 text answer와 citation drawer로 복귀한다. | UI fallback skeleton 존재 |

## Architecture Boundary

기본 원칙은 RAG core와 voice adapter를 분리하는 것이다.

```text
browser mic
-> STT adapter
-> transcript draft
-> user confirmation
-> /api/v1/chat text request
-> answer + spoken_answer + citations
-> TTS adapter
-> playback + text fallback
```

`/api/v1/chat`는 음성 binary를 직접 받지 않는다. 음성 입력은 transcript로 정규화된 뒤 기존 text-first contract를 호출한다. 이렇게 해야 retrieval/generation 평가와 STT 품질 평가가 섞이지 않는다.

## Provider 선택 기준

provider는 아직 확정하지 않는다. 실제 구현 전에 공식 문서, SDK, pricing, browser 지원, 데이터 처리 조건을 다시 확인한다.

| 후보군 | 장점 | 리스크 | 선택 조건 |
| --- | --- | --- | --- |
| Browser/native STT/TTS | demo 구현이 빠르고 client secret이 필요 없다. | browser별 지원 차이와 한국어 인식 편차가 있다. | 포트폴리오 demo가 최우선이고 저장/전송 리스크를 줄일 때 |
| Local STT/TTS | private audio 외부 전송을 줄일 수 있다. CUDA 실험이 가능하다. | 모델 다운로드, GPU memory, latency, packaging 부담이 있다. | local GPU에서 p95 latency와 품질이 gate를 통과할 때 |
| External API STT/TTS | 품질과 운영 안정성이 높을 수 있다. | 비용, quota, 외부 전송, secret 관리가 필요하다. | 개인정보 고지와 비용 cap, retry/timeout 정책이 준비될 때 |

Solar Pro 3는 RAG generation이 필요한 순간에만 사용한다. STT/TTS provider와 Solar Pro 3 generation provider는 같은 계층으로 묶지 않는다.

## 개인정보와 보안 정책

- microphone capture는 사용자 action 뒤에만 시작한다.
- audio 저장 기본값은 `off`다.
- public report에는 raw transcript, raw audio metadata, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다.
- client bundle에는 STT/TTS provider secret을 넣지 않는다.
- 외부 provider로 audio 또는 transcript를 전송하는 경우 UI와 문서에 전송 여부를 표시한다.
- transcript는 사용자가 확인한 뒤 `/api/v1/chat`으로 보낸다.
- error message는 provider raw error를 그대로 노출하지 않는다.
- rate limit, timeout, retry, cancellation을 STT/TTS adapter별로 둔다.
- 민감한 발화가 포함될 수 있으므로 debug logging은 기본 비활성화한다.

## 평가 기준

STT와 TTS는 각각 별도 gate를 가진다.

| stage | metric | 통과 기준 초안 |
| --- | --- | --- |
| STT | `wer` | 한국어 관광 질문 subset에서 기준 이하 |
| STT | `cer` | 장소명/인명 포함 query에서 기준 이하 |
| STT | `place_name_accuracy` | 경복궁, 광화문, 한양도성 등 place alias 인식률 기록 |
| STT | `transcript_confirmation_rate` | 사용자가 수정 없이 보낸 비율 기록 |
| STT | `stt_latency_p95_ms` | mobile/desktop 별도 기록 |
| STT | `stt_timeout_rate` | timeout과 retry 후 실패율 기록 |
| TTS | `tts_playback_success_rate` | desktop/mobile/browser별 재생 성공률 기록 |
| TTS | `tts_latency_p95_ms` | 첫 음성 재생까지 p95 기록 |
| TTS | `spoken_answer_length_violation_rate` | 긴 답변이 음성에 부적합한 비율 기록 |
| TTS | `tts_fallback_success_rate` | 실패 시 text fallback 노출률 기록 |
| E2E | `voice_round_trip_latency_p95_ms` | STT 확인부터 TTS 시작까지 기록 |
| E2E | `provider_call_count` | demo별 call count와 cost cap 기록 |

이번 planning gate의 실제 호출 수는 모두 0이다.

## Failure Mode

| failure mode | 대응 |
| --- | --- |
| microphone permission denied | text input으로 fallback |
| no speech detected | transcript draft를 만들지 않고 재시도 안내 |
| noisy input | transcript confirmation step에서 수정 가능하게 처리 |
| unsupported browser | voice control을 disabled state로 표시 |
| STT provider timeout | retry 1회 후 text fallback |
| STT provider quota exceeded | provider unavailable error를 sanitized message로 표시 |
| transcript hallucination | 사용자 확인 전에는 chat request를 보내지 않음 |
| sensitive spoken content | raw transcript public logging 금지 |
| TTS provider timeout | `spoken_answer` text display 유지 |
| autoplay blocked | 사용자 click으로 playback 재시도 |
| network offline | local UI error와 retry affordance 표시 |
| `/api/v1/chat` no-answer | TTS로 불확실한 답변을 꾸미지 않고 abstain message 재생 후보로 둠 |

## Data Mart Grain

`fact_voice_stt_tts_plan`의 grain은 `work_id + voice_stage + scenario_id + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-VOICE-STT-TTS-PLAN-001` |
| `voice_stage` | consent, stt, confirmation, chat, tts, fallback |
| `scenario_id` | permission_denied, noisy_input, answerable_query, no_answer_query 등 |
| `claim_boundary` | plan-only, contract-only, no-live-call, public-safe-summary |
| `metric_family` | privacy, latency, cost, reliability, quality |
| `status` | planned, blocked, deferred, ready_for_contract |

금지 필드:

- raw audio
- raw transcript
- raw answer
- raw evidence
- raw prompt
- chunk text
- private path
- secret

## 다음 구현 Work Order

- `id`: `HD-VOICE-STT-TTS-CONTRACT-001`
- `depends_on`: `HD-VOICE-STT-TTS-PLAN-001`
- `scope`: STT/TTS provider 호출 없이 browser voice control contract와 adapter interface skeleton을 만든다. 실제 audio capture와 provider call은 계속 막는다.
- `acceptance_tests`: provider secret client 노출 0, live STT call 0, live TTS call 0, raw transcript public artifact 0, text fallback test 통과, unsupported browser state test 통과
- `risk_level`: medium
- `rollback_plan`: voice adapter skeleton, UI contract test, 관련 문서/리포트만 되돌린다.

## 금지 Claim

- production 성능 검증 완료
- locked test에서 최종 성능 개선 입증
- GraphRAG로 성능 개선
- RAPTOR로 성능 개선
- HyDE로 최종 검색 성능 개선
- Solar Pro 3 답변 품질 최종 개선
- 음성 관광 앱 완성
- STT/TTS 품질 검증 완료
- 전체 도서 데이터 공개
