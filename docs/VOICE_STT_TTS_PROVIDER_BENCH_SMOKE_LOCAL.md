# Voice STT/TTS Provider Benchmark Local Smoke

## 결론

`HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-LOCAL-001`는 external provider 호출 없이 local CUDA Whisper 후보만 smoke로 검증한다.

이번 gate는 STT provider 최종 선택이 아니다. public artifact에는 raw audio, raw transcript, raw provider payload를 저장하지 않는다.

## Scope

포함:

- `local_cuda_whisper` 후보의 local smoke 실행
- CUDA 사용 가능 시 CUDA device 사용
- private wav fixture 생성 또는 사용
- WER, CER, place name accuracy, latency metric 기록
- private fact와 public summary 분리

제외:

- Google, Azure, AWS STT/TTS 호출
- browser Web Speech 자동 benchmark
- Solar Pro 3 호출
- STT/TTS 품질 검증 완료 주장
- provider 최종 선택

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| public_safe_script_fixture_count | 5 |
| local_provider_candidate_count | 1 |
| local_whisper_runtime_available_count | 1 |
| local_tts_generation_requested_count | 5 |
| private_audio_generated_count | 5 |
| audio_fixture_available_count | 5 |
| local_stt_execution_requested_count | 5 |
| local_stt_execution_count | 5 |
| local_cuda_whisper_call_count | 5 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| private_audio_saved_count | 5 |
| raw_transcript_public_artifact_count | 0 |
| raw_audio_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| wer_avg | 0.553333 |
| cer_avg | 0.164183 |
| place_name_accuracy_avg | 0.600000 |
| stt_latency_p50_ms | 83.296100 |
| stt_latency_p95_ms | 651.099660 |
| resolved_device | `cuda` |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| smoke_decision | `completed_local_smoke` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_stt_local_smoke_private` | `smoke_id + script_id + provider_candidate_id + model_id + metric_name` | private |
| `fact_voice_stt_local_smoke_public_summary` | `smoke_id + provider_candidate_id + model_id + metric_name` | public-safe |

## Claim Boundary

허용 claim:

- local CUDA Whisper smoke runner를 구현했다.
- external provider call 없이 local STT smoke metric을 기록했다.
- public artifact에는 raw audio와 raw transcript를 저장하지 않았다.

금지 claim:

- provider 최종 선택 완료
- STT/TTS 품질 검증 완료
- 음성 관광 앱 완성
- external provider benchmark 성능 개선 입증
