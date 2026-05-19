# Voice STT/TTS Local Model Ablation

## 결론

`HD-VOICE-STT-TTS-LOCAL-MODEL-ABLATION-001`는 external provider 호출 없이 local CUDA Whisper 모델 크기 후보를 비교한다.

이번 gate는 provider 최종 선택이 아니다. public artifact에는 raw audio, raw transcript, raw provider payload를 저장하지 않는다.

## Scope

포함:

- `local_cuda_whisper` 후보 내 `tiny`, `base`, `small` 모델 비교
- CUDA 사용 가능 시 CUDA device 사용
- 같은 5개 public-safe script와 private wav fixture 사용
- WER, CER, place name accuracy, STT latency p95, model load time 기록
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
| model_candidate_count | 3 |
| selected_script_count | 5 |
| public_safe_script_fixture_count | 5 |
| runtime_available_count | 1 |
| audio_fixture_available_count | 5 |
| local_stt_execution_requested_count | 15 |
| total_local_stt_execution_count | 15 |
| total_local_cuda_whisper_call_count | 15 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_audio_public_artifact_count | 0 |
| resolved_device | `cuda` |
| best_cer_model_id | `small` |
| best_place_name_accuracy_model_id | `small` |
| recommended_model_id | `small` |
| ablation_decision | `completed_local_model_ablation` |

## Model Summary

| model_id | executed | load_ms | wer_avg | cer_avg | place_name_accuracy_avg | latency_p95_ms | cer_delta_from_tiny | place_delta_from_tiny | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| tiny | 5 | 689.723900 | 0.553333 | 0.164183 | 0.600000 | 386.957040 | 0.000000 | 0.000000 | `baseline` |
| base | 5 | 13515.711300 | 0.266667 | 0.088628 | 0.400000 | 207.024420 | 0.075555 | -0.200000 | `quality_candidate_check_latency` |
| small | 5 | 44491.524000 | 0.080000 | 0.053333 | 0.800000 | 360.612560 | 0.110850 | 0.200000 | `quality_candidate_check_latency` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_stt_local_model_ablation_private` | `ablation_id + script_id + provider_candidate_id + model_id + metric_name` | private |
| `fact_voice_stt_local_model_ablation_public_summary` | `ablation_id + provider_candidate_id + model_id + metric_name` | public-safe |

## Claim Boundary

허용 claim:

- local CUDA Whisper 모델 크기별 smoke metric을 비교했다.
- external provider call 없이 local STT 모델 후보를 비교했다.
- public artifact에는 raw audio와 raw transcript를 저장하지 않았다.

금지 claim:

- provider 최종 선택 완료
- STT/TTS 품질 검증 완료
- 음성 관광 앱 완성
- external provider benchmark 성능 개선 입증
