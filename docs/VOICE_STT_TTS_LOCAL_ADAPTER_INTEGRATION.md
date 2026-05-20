# Voice STT/TTS Local Adapter Integration

## 결론

`HD-VOICE-STT-TTS-LOCAL-ADAPTER-INTEGRATION-001`는 무료 로컬 STT/TTS 우선 전략을 실제 adapter smoke로 연결한 결과다.

이 gate는 `local Whisper 후보 -> transcript boundary -> /api/v1/chat -> spoken_answer -> Windows SAPI TTS fallback` 흐름을 검증한다. production voice app 완성이나 TTS 품질 우수 claim은 하지 않는다.

## Scope

| type | item |
| --- | --- |
| include | local voice adapter module |
| include | local Whisper STT 후보와 CUDA 가용성 기록 |
| include | `/api/v1/chat` contract answer와 `spoken_answer` 연결 |
| include | Windows SAPI Korean TTS fallback private wav 생성 |
| exclude | microphone capture |
| exclude | managed STT/TTS provider 호출 |
| exclude | Solar Pro 3 호출 |
| exclude | raw audio/transcript public artifact |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| local_voice_adapter_module_count | 1 |
| local_stt_provider_candidate_count | 1 |
| local_tts_provider_candidate_count | 1 |
| local_stt_runtime_available_count | 1 |
| local_stt_execution_requested_count | 5 |
| local_stt_execution_count | 5 |
| local_cuda_whisper_call_count | 5 |
| local_tts_execution_requested_count | 5 |
| local_tts_execution_count | 5 |
| private_tts_audio_generated_count | 5 |
| chat_contract_execution_count | 5 |
| citation_response_count | 5 |
| stt_wer_avg | 0.080000 |
| stt_cer_avg | 0.053333 |
| stt_place_name_accuracy_avg | 0.800000 |
| stt_latency_p95_ms | 1154.533780 |
| chat_latency_p95_ms | 1.312780 |
| tts_latency_p95_ms | 170.331560 |
| voice_round_trip_latency_p95_ms | 1323.607100 |
| audio_duration_total_ms | 48138.548755 |
| audio_file_size_total_bytes | 2123140 |
| resolved_device | `cuda` |
| cuda_device_count | 1 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| integration_decision | `completed_local_voice_adapter_smoke` |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_adapter_smoke` | `integration_id + script_id + provider_candidate_id + metric_name` | public-safe summary |
| `fact_voice_local_audio_private` | `integration_id + script_id + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | local voice adapter가 STT 후보, chat contract, SAPI TTS fallback을 연결했다. |
| allowed | external provider call과 external audio transmission은 0이다. |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | STT/TTS 품질 최종 검증 완료 |
| forbidden | MeloTTS가 최종 provider로 확정 |
| forbidden | Windows SAPI가 최종 provider로 확정 |
