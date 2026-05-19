# Voice STT/TTS Contract Skeleton

## 결론

`HD-VOICE-STT-TTS-CONTRACT-001`은 provider 호출 없는 voice adapter/interface skeleton이다.

이번 구현은 실제 STT/TTS 품질 검증이 아니다. microphone capture, audio upload, external STT/TTS API call, browser TTS playback을 모두 실행하지 않는다. 목적은 `/api/v1/chat`의 text-first RAG 계약을 유지하면서 voice control의 상태, fallback, public-safe metric을 고정하는 것이다.

## 구현 범위

포함:

- frontend voice adapter contract module
- STT/TTS disabled-by-contract 상태
- live STT/TTS call count 0 metric
- private audio 저장 0 metric
- raw transcript public artifact 0 metric
- UI voice control disabled state
- unsupported/fallback 상태 unit test

제외:

- 실제 microphone capture
- 실제 speech recognition
- 실제 browser `speechSynthesis` playback
- 외부 STT/TTS provider call
- provider 최종 선정
- STT/TTS 품질 비교
- production voice app claim

## 구현 파일

| file | 역할 |
| --- | --- |
| `frontend/src/lib/voiceAdapters.ts` | provider 호출 없는 `VoiceAdapterContract`와 zero-call metric |
| `frontend/src/lib/voiceAdapters.test.ts` | capability가 있어도 contract-only 단계에서는 STT/TTS가 비활성화됨을 검증 |
| `frontend/src/components/DocentApp.tsx` | Mic/Volume button을 voice adapter 상태와 zero-call metric에 연결 |
| `frontend/src/App.test.tsx` | UI가 contract-only voice control과 fallback metric을 렌더링하는지 검증 |

## Adapter Contract

`VoiceAdapterContract`는 다음 경계를 가진다.

| field | 의미 |
| --- | --- |
| `mode` | `contract_only` |
| `stt.status` | `disabled_by_contract` |
| `tts.status` | `disabled_by_contract` |
| `metrics.liveSttCallCount` | 항상 0 |
| `metrics.liveTtsCallCount` | 항상 0 |
| `metrics.providerFinalizedCount` | 항상 0 |
| `metrics.privateAudioSavedCount` | 항상 0 |
| `metrics.rawTranscriptPublicArtifactCount` | 항상 0 |

`createTranscriptDraft()`와 `playSpokenAnswer()`는 모두 `reason=contract_only`를 반환한다. 이 함수들은 provider나 browser playback API를 호출하지 않는다.

## UI Contract

| control | 상태 | aria label | claim boundary |
| --- | --- | --- | --- |
| Mic button | disabled | 음성 입력 contract only | no live STT call |
| Volume button | disabled | 음성 재생 contract only | no live TTS call |
| Initial status strip | visible | `voice contract_only`, `voice live calls: 0` | public-safe |
| Answer status strip | visible | `voice calls: 0/0` | public-safe |

## 보안 경계

- client bundle에 STT/TTS provider secret을 넣지 않는다.
- microphone permission을 요청하지 않는다.
- raw audio를 생성하거나 저장하지 않는다.
- raw transcript를 public artifact에 기록하지 않는다.
- provider raw error를 노출하지 않는다.
- `/api/v1/chat`는 계속 text request만 받는다.

## 정량 Gate

| metric | expected |
| --- | ---: |
| frontend_adapter_module_count | 1 |
| frontend_adapter_unit_test_count | 2 |
| frontend_ui_voice_contract_test_count | 1 |
| provider_finalized_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| private_audio_saved_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| mic_capture_implemented_count | 0 |
| browser_tts_playback_call_count | 0 |

## Data Mart Grain

`fact_voice_stt_tts_contract`의 grain은 `work_id + adapter_surface + ui_state + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-VOICE-STT-TTS-CONTRACT-001` |
| `adapter_surface` | stt, tts, ui_control, metric |
| `ui_state` | disabled_by_contract, contract_only, fallback |
| `claim_boundary` | frontend-contract-only, no-live-call, public-safe-summary |
| `metric_family` | privacy, provider, reliability, ui |

금지 필드:

- raw audio
- raw transcript
- raw answer
- raw evidence
- prompt
- chunk text
- private path
- secret

## 다음 작업

`HD-VOICE-STT-TTS-PROVIDER-BENCH-PLAN-001`은 완료됐다.

다음 후보는 `HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001`이다.

provider benchmark를 하려면 먼저 browser/native, local CUDA STT, external API 후보의 공식 문서, 비용, 데이터 처리 조건, evaluation subset, live call budget을 별도 계획으로 고정해야 한다.

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
