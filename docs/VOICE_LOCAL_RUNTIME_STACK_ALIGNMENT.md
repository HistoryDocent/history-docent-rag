# Voice Local Runtime Stack Alignment

## 결론

`HD-VOICE-LOCAL-RUNTIME-STACK-ALIGN-001`는 무료 로컬 음성 stack lock 결과를 실제 런타임 provider id와 API 공개 필드에 맞춘 gate다.

STT runtime 기본 후보는 `local_faster_whisper_small_cuda`이고, TTS는 `local_windows_sapi_pyttsx3_korean_fallback` fallback 상태로만 노출한다.

## Scope

| type | item |
| --- | --- |
| include | voice adapter/provider id 정렬 |
| include | faster-whisper default transcriber contract |
| include | TTS final provider 0건을 API field로 명시 |
| include | public-safe 정량/정성 리포트 |
| exclude | 신규 음성 전사 실행 |
| exclude | 신규 음성 합성 실행 |
| exclude | managed STT/TTS provider 호출 |

## Quantitative Gate

| metric | value |
| --- | ---: |
| provider_id_mismatch_count | 0 |
| primary_local_stt_candidate_count | 1 |
| primary_local_tts_candidate_count | 0 |
| tts_fallback_candidate_count | 1 |
| tts_final_provider_count | 0 |
| runtime_default_faster_whisper_transcriber_count | 1 |
| api_provider_status_field_count | 5 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| alignment_decision | `aligned_local_stt_tts_blocked` |

## Runtime Provider Contract

| modality | provider_candidate_id | role | status | runtime_family |
| --- | --- | --- | --- | --- |
| stt | `local_faster_whisper_small_cuda` | primary | locked_for_demo | faster-whisper via CTranslate2 |
| tts | `local_windows_sapi_pyttsx3_korean_fallback` | fallback | fallback_not_quality_candidate | Windows SAPI via pyttsx3 |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_runtime_stack_alignment` | `alignment_id + provider_candidate_id + metric_name` | public-safe |

## Claim Boundary

허용 claim:

- local runtime의 STT provider id를 stack lock 결정과 정렬했다.
- local runtime 기본 transcriber는 `faster-whisper small` 계약으로 맞췄다.
- TTS는 fallback이며 final provider가 아니다.

금지 claim:

- 무료 로컬 TTS 최종 provider 확정
- 실제 관광객 음성 품질 검증 완료
- production 음성 관광 앱 완성
