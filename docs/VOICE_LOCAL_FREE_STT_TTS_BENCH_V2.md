# Voice Local Free STT/TTS Bench v2

## 결론

`HD-VOICE-LOCAL-FREE-STT-TTS-BENCH-V2-001`는 무료 로컬 STT/TTS 우선 전략의 현재 baseline과 다음 target 후보를 분리한다.

현재 실행 근거가 있는 baseline은 STT `local_openai_whisper_small_cuda_current`, TTS `local_windows_sapi_pyttsx3_korean_fallback`이다. `faster-whisper`와 `Piper`는 다음 실행 target이며, 아직 현재 품질 우위나 최종 provider로 주장하지 않는다.

## Candidate Matrix

| provider_candidate_id | modality | role | family | runtime_status | execution_count | latency_p95_ms | next_action |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| local_openai_whisper_small_cuda_current | stt | current_stt_baseline | openai-whisper | `benchmarked_current` | 5 | 360.612560 | 현재 무료 로컬 STT baseline으로 유지하고 faster-whisper와 같은 조건에서 재비교한다. |
| local_faster_whisper_cuda_target | stt | target_stt_next | faster-whisper | `runtime_missing` | 0 | null | 별도 승인 후 설치/모델 cache를 고정하고 small 또는 distil-large-v3를 실행 비교한다. |
| local_whisper_cpp_cuda_deploy_candidate | stt | deployment_stt_candidate | whisper.cpp | `runtime_missing` | 0 | null | Python API baseline 이후 Windows 배포성 후보로 CLI smoke를 검토한다. |
| local_windows_sapi_pyttsx3_korean_fallback | tts | current_tts_fallback | Windows SAPI via pyttsx3 | `benchmarked_current` | 30 | 98.918350 | 무료 로컬 TTS target이 준비될 때까지 fallback으로만 유지한다. |
| local_piper_tts_target | tts | target_tts_next | Piper | `license_review_required` | 0 | null | 한국어 voice availability와 license를 확인한 뒤 private wav smoke를 실행한다. |
| local_melotts_korean_blocked | tts | blocked_tts_candidate | MeloTTS | `blocked_dependency` | 0 | null | optional Windows dependency fix로 분리하고 기본 TTS target에서 제외한다. |

## 정량 요약

| metric | value |
| --- | ---: |
| candidate_count | 6 |
| stt_candidate_count | 3 |
| tts_candidate_count | 3 |
| current_stt_benchmarked_count | 1 |
| current_tts_benchmarked_count | 1 |
| target_next_candidate_count | 2 |
| missing_runtime_candidate_count | 2 |
| license_review_candidate_count | 1 |
| blocked_dependency_candidate_count | 1 |
| package_install_attempted_count | 0 |
| model_download_attempted_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| recommended_current_stt_candidate_id | `local_openai_whisper_small_cuda_current` |
| recommended_current_tts_candidate_id | `local_windows_sapi_pyttsx3_korean_fallback` |
| next_stt_candidate_id | `local_faster_whisper_cuda_target` |
| next_tts_candidate_id | `local_piper_tts_target` |
| bench_decision | `local_first_current_baseline_ready_next_targets_pending` |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_free_candidate_public` | `bench_id + provider_candidate_id + metric_name` | public-safe |
| `fact_voice_local_free_execution_private` | `bench_id + provider_candidate_id + script_id + artifact_id` | private only |

## Claim Boundary

허용 claim:

- 무료 로컬 STT/TTS 전략의 현재 실행 baseline과 다음 target 후보를 분리했다.
- 현재 public evidence 기준 external provider call과 external audio transmission은 0이다.
- CUDA 사용 가능 여부와 후보별 실행 상태를 같은 candidate grain으로 기록했다.

금지 claim:

- `faster-whisper`가 현재 baseline보다 우수하다는 주장
- `Piper`가 최종 TTS provider라는 주장
- Windows SAPI fallback이 production 품질 provider라는 주장
- 무료 로컬 음성 관광 앱 완성
- 실제 관광객 음성 품질 검증 완료
