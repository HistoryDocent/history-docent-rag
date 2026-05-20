# Voice Local Sherpa-ONNX Supertonic 3 Korean TTS Smoke

## 결론

`HD-VOICE-LOCAL-SHERPA-ONNX-SUPERTONIC3-KO-SMOKE-001`는 `sherpa-onnx + Supertonic 3 Korean`을 무료 로컬 한국어 TTS smoke로 실행한다.

이번 gate는 실제 로컬 합성 가능성 확인이다. 최종 TTS provider 확정이나 음성 품질 우수 검증은 아니다.

## Scope

| type | item |
| --- | --- |
| include | `local_sherpa_onnx_supertonic3_ko` local TTS smoke |
| include | `sherpa-onnx` package install 시도와 성공 여부 기록 |
| include | Supertonic 3 Korean ONNX model private download 여부 기록 |
| include | 5개 public-safe spoken answer script 합성 |
| include | latency, duration, file size, sample rate, success/failure count |
| include | private audio와 public-safe summary 분리 |
| exclude | Azure, Google, AWS STT/TTS 호출 |
| exclude | Solar Pro 3 호출 |
| exclude | raw script text, raw audio, private path public 저장 |
| exclude | TTS 품질 검증 완료 주장 |
| exclude | provider 최종 선택 |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| public_safe_script_fixture_count | 5 |
| primary_local_tts_candidate_count | 1 |
| package_install_attempted_count | 1 |
| package_install_success_count | 1 |
| sherpa_runtime_available_count | 1 |
| model_download_attempted_count | 1 |
| model_download_success_count | 1 |
| model_file_available_count | 7 |
| expected_model_file_count | 7 |
| missing_model_file_count | 0 |
| model_license_recorded_count | 1 |
| tts_execution_requested_count | 5 |
| local_tts_execution_count | 5 |
| local_cuda_tts_call_count | 0 |
| private_audio_generated_count | 5 |
| private_audio_saved_count | 5 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_audio_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| tts_model_load_time_ms | 507.146900 |
| tts_latency_p50_ms | 1211.611800 |
| tts_latency_p95_ms | 1235.384820 |
| audio_duration_total_ms | 41898.344671 |
| audio_file_size_total_bytes | 3695654 |
| sample_rate_hz | 44100 |
| resolved_device | `cuda` |
| sherpa_tts_provider | `cpu` |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| tts_smoke_decision | `completed_local_sherpa_onnx_supertonic3_ko_smoke` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_sherpa_onnx_supertonic3_ko_smoke_public` | `smoke_id + script_id + metric_name` | public-safe |
| `fact_voice_local_tts_audio_artifact_private` | `smoke_id + script_id + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | `sherpa-onnx + Supertonic 3 Korean` local TTS smoke를 실행했다. |
| allowed | 5개 public-safe script 기준 private wav artifact를 생성했다. |
| allowed | external provider call 없이 local TTS smoke metric을 기록했다. |
| allowed | public artifact에는 raw audio와 raw transcript를 저장하지 않았다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | CUDA TTS acceleration 검증 완료 |
