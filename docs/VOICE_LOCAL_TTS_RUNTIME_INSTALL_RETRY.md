# Voice Local TTS Runtime Install Retry

## 결론

`HD-VOICE-STT-TTS-LOCAL-TTS-RUNTIME-INSTALL-001`는 무료 로컬 TTS 우선 전략에서 `MeloTTS Korean` 설치/실행을 재시도하고, Windows SAPI 기반 `pyttsx3` 한국어 fallback으로 실제 private wav 생성 가능성을 확인한다.

이번 gate는 음성 품질 최종 평가가 아니다. public artifact에는 raw audio, raw transcript, provider payload, private path를 저장하지 않는다.

## Scope

| type | item |
| --- | --- |
| include | Python 3.11 격리 환경에서 MeloTTS 설치 재시도 |
| include | CUDA torch wheel 사용 가능성 확인 |
| include | MeloTTS Korean 합성 차단 원인 기록 |
| include | Windows SAPI Korean voice fallback smoke |
| include | 5개 public-safe spoken answer script의 private wav 생성 |
| exclude | Azure, Google, AWS STT/TTS 호출 |
| exclude | Solar Pro 3 호출 |
| exclude | TTS 품질 최종 검증 |
| exclude | provider 최종 확정 |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| runtime_install_attempt_count | 11 |
| package_install_attempted_count | 5 |
| package_install_success_count | 4 |
| package_install_blocked_count | 1 |
| cuda_wheel_install_success_count | 1 |
| dictionary_download_attempted_count | 1 |
| dictionary_download_success_count | 1 |
| model_load_attempted_count | 1 |
| model_load_success_count | 1 |
| melotts_import_available_count | 1 |
| melotts_synthesis_attempt_count | 1 |
| melotts_synthesis_success_count | 0 |
| melotts_blocker_count | 2 |
| sapi_korean_voice_detected_count | 1 |
| fallback_sapi_synthesis_attempt_count | 5 |
| local_tts_execution_count | 5 |
| private_audio_generated_count | 5 |
| private_audio_saved_count | 5 |
| tts_latency_p50_ms | 28.844340 |
| tts_latency_p95_ms | 28.844340 |
| audio_duration_total_ms | 40004.263038 |
| audio_file_size_total_bytes | 1764418 |
| resolved_device | `cuda` |
| cuda_device_count | 1 |
| local_cuda_available_count | 1 |
| isolated_cuda_torch_available_count | 1 |
| selected_provider_candidate_id | `local_windows_sapi_pyttsx3_korean_fallback` |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| retry_decision | `completed_local_sapi_tts_fallback` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_tts_runtime_install_attempt` | `retry_id + attempt_id + provider_candidate_id` | public-safe |
| `fact_voice_tts_local_synthesis_private` | `retry_id + script_id + provider_candidate_id + metric_name` | private |
| `fact_voice_tts_local_synthesis_public_summary` | `retry_id + provider_candidate_id + metric_name` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | MeloTTS 설치와 CUDA runtime 구성은 Python 3.11 격리 환경에서 확인했다. |
| allowed | MeloTTS Korean 합성은 Windows `eunjeon` build dependency에서 차단됐다. |
| allowed | Windows SAPI Korean voice fallback으로 private wav smoke를 실행했다. |
| allowed | external provider call과 external audio transmission은 0이다. |
| forbidden | MeloTTS가 최종 provider로 확정 |
| forbidden | pyttsx3가 최종 provider로 확정 |
| forbidden | 무료 로컬 TTS 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
