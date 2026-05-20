# Voice Local Faster Whisper STT Comparison

## 결론

`HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001`는 `openai-whisper small CUDA` baseline과 `faster-whisper small CUDA` 후보를 같은 5개 private wav fixture로 비교한다.

이번 gate는 STT provider 최종 선택이 아니다. public artifact에는 raw audio와 raw transcript를 저장하지 않는다.

## Provider Summary

| provider_candidate_id | executed | load_ms | wer_avg | cer_avg | place_acc_avg | latency_p95_ms | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| local_openai_whisper_small_cuda_current | 5 | 0.000000 | 0.080000 | 0.053333 | 0.800000 | 360.612560 | `kept_as_comparison_candidate` |
| local_faster_whisper_small_cuda | 5 | 2006.830700 | 0.040000 | 0.026667 | 1.000000 | 327.688120 | `recommended_current` |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| baseline_execution_count | 5 |
| faster_whisper_execution_count | 5 |
| paired_script_count | 5 |
| faster_whisper_runtime_available_count | 1 |
| package_install_attempted_count | 1 |
| model_download_attempted_count | 1 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| resolved_device | `cuda` |
| compute_type | `float16` |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| baseline_cer_avg | 0.053333 |
| faster_whisper_cer_avg | 0.026667 |
| cer_delta_baseline_minus_faster | 0.026666 |
| place_accuracy_delta_faster_minus_baseline | 0.200000 |
| latency_p95_delta_faster_minus_baseline_ms | -32.924440 |
| recommended_stt_candidate_id | `local_faster_whisper_small_cuda` |
| comparison_decision | `completed_faster_whisper_comparison` |

## Claim Boundary

허용 claim:

- 같은 private wav fixture 기준으로 local STT 후보를 비교했다.
- external provider call과 external audio transmission은 0이다.
- raw audio와 raw transcript는 public artifact에 저장하지 않았다.

금지 claim:

- `faster-whisper`가 production 최종 provider라는 주장
- STT/TTS 품질 최종 검증 완료
- 실제 관광객 음성 품질 검증 완료
- 음성 관광 앱 완성
