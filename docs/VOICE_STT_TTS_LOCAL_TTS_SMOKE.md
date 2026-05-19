# Voice STT/TTS Local TTS Smoke

## 결론

`HD-VOICE-STT-TTS-LOCAL-TTS-SMOKE-001`는 무료 로컬 TTS 후보인 `MeloTTS Korean`을 우선 smoke 대상으로 둔다.

이번 gate는 TTS provider 최종 선택이 아니다. public artifact에는 raw audio, raw transcript, provider payload, private path를 저장하지 않는다.

## Scope

| type | item |
| --- | --- |
| include | `local_melotts_korean` local TTS smoke |
| include | CUDA 가능 시 `cuda:0` device 사용 시도 |
| include | 5개 public-safe spoken answer script 합성 |
| include | latency, duration, file size, success/failure count |
| include | private audio와 public-safe summary 분리 |
| exclude | Azure, Google, AWS STT/TTS 호출 |
| exclude | browser Web Speech 자동 benchmark |
| exclude | Solar Pro 3 호출 |
| exclude | TTS 품질 검증 완료 주장 |
| exclude | provider 최종 선택 |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| public_safe_script_fixture_count | 5 |
| primary_local_tts_candidate_count | 1 |
| melotts_runtime_available_count | 0 |
| tts_execution_requested_count | 5 |
| local_tts_execution_count | 0 |
| local_cuda_tts_call_count | 0 |
| private_audio_generated_count | 0 |
| private_audio_saved_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_audio_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| tts_model_load_time_ms | 0.000000 |
| tts_latency_p50_ms | 0.000000 |
| tts_latency_p95_ms | 0.000000 |
| audio_duration_total_ms | 0.000000 |
| audio_file_size_total_bytes | 0 |
| resolved_device | `cuda` |
| melotts_device | `cuda:0` |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| tts_smoke_decision | `blocked_missing_runtime_or_audio` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_tts_local_smoke_private` | `smoke_id + script_id + provider_candidate_id + metric_name` | private |
| `fact_voice_tts_local_smoke_public_summary` | `smoke_id + provider_candidate_id + metric_name` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | local MeloTTS Korean smoke runner를 구현했다. |
| allowed | external provider call 없이 local TTS smoke metric을 기록했다. |
| allowed | public artifact에는 raw audio와 raw transcript를 저장하지 않았다. |
| forbidden | MeloTTS가 최종 provider로 확정 |
| forbidden | 무료 로컬 TTS 품질 검증 완료 |
| forbidden | Azure보다 local TTS가 품질 우수 |
| forbidden | 음성 관광 앱 완성 |
