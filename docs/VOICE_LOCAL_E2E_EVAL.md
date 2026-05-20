# Voice Local E2E Eval

## 결론

`HD-VOICE-LOCAL-E2E-EVAL-001`는 무료 로컬 STT/TTS 우선 전략을 30개 public-safe script 기준 regression gate로 확장한 결과다.

이 gate는 synthetic local voice loop다. 실제 관광객 음성 품질 검증이나 production 음성 앱 완성 claim은 하지 않는다.

## Scope

| type | item |
| --- | --- |
| include | local question TTS private wav generation |
| include | CUDA local Whisper STT |
| include | `/api/v1/chat` contract-only bridge |
| include | local spoken answer TTS private wav generation |
| include | query type별 metric breakdown |
| exclude | microphone capture |
| exclude | managed STT/TTS provider call |
| exclude | Solar Pro 3 call |
| exclude | raw audio/transcript public artifact |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 30 |
| query_type_count | 6 |
| script_per_query_type_min_count | 5 |
| input_tts_generation_count | 30 |
| local_stt_execution_count | 30 |
| local_cuda_whisper_call_count | 30 |
| chat_contract_execution_count | 30 |
| expected_behavior_pass_count | 30 |
| output_tts_generation_count | 30 |
| private_input_audio_generated_count | 30 |
| private_output_audio_generated_count | 30 |
| stt_wer_avg | 0.066045 |
| stt_cer_avg | 0.028262 |
| stt_place_name_accuracy_avg | 0.740000 |
| input_tts_latency_p95_ms | 93.819120 |
| stt_latency_p95_ms | 268.553150 |
| chat_latency_p95_ms | 0.518885 |
| output_tts_latency_p95_ms | 98.918350 |
| voice_round_trip_latency_p95_ms | 444.628360 |
| resolved_device | `cuda` |
| cuda_device_count | 1 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| e2e_decision | `completed_local_voice_e2e_regression` |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_e2e_eval_public_summary` | `e2e_id + script_id + stage + metric_name` | public-safe summary |
| `fact_voice_local_e2e_audio_private` | `e2e_id + script_id + audio_role + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 30개 script 기준 local voice E2E regression gate를 실행했다. |
| allowed | external provider call과 external audio transmission은 0이다. |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | STT/TTS 품질 최종 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | Windows SAPI가 최종 provider로 확정 |
