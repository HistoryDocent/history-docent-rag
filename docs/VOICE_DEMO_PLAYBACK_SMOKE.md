# Voice Demo Playback Smoke

## 결론

`HD-VOICE-DEMO-PLAYBACK-SMOKE-001`는 무료 로컬 음성 demo stack을 실제 demo playback 후보로 열어도 되는지 확인하는 gate다.

결과는 `completed_local_voice_demo_playback_smoke`이다. private wav 5개는 playback-ready 상태이며, 이 gate는 speaker device를 자동 재생하지 않는다. 실제 관광객 품질 검증이나 production final provider 확정도 아니다.

## Scope

| type | item |
| --- | --- |
| include | `local_faster_whisper_small_cuda` STT demo 후보 유지 |
| include | `local_sherpa_onnx_supertonic3_ko` TTS demo review 후보의 private wav 존재 확인 |
| include | private wav metadata 기반 playback-ready smoke |
| include | 사람 청취 점수 완료 상태와 public-safe 집계 확인 |
| exclude | speaker device 자동 재생 |
| exclude | microphone capture |
| exclude | raw audio public artifact |
| exclude | raw transcript/script public artifact |
| exclude | managed STT/TTS provider call |
| exclude | Solar Pro 3 call |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| primary_local_stt_candidate_count | 1 |
| tts_demo_candidate_count | 1 |
| tts_final_provider_count | 0 |
| private_audio_expected_count | 5 |
| private_audio_available_count | 5 |
| private_audio_missing_count | 0 |
| accepted_private_wav_count | 5 |
| invalid_private_audio_count | 0 |
| playback_contract_step_count | 5 |
| playback_ready_count | 5 |
| playback_device_call_count | 0 |
| tts_human_score_completed_count | 30 |
| tts_human_score_expected_count | 30 |
| tts_human_score_overall_avg | 5.000000 |
| tts_human_score_reviewer_count | 1 |
| human_score_public_detail_row_count | 0 |
| audio_duration_total_ms | 41898.344671 |
| audio_file_size_total_bytes | 3695654 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_script_public_artifact_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| production_voice_claim_count | 0 |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_demo_playback_smoke_public` | `playback_smoke_id + script_id + provider_candidate_id + metric_name` | public-safe |
| `fact_voice_demo_audio_artifact_private` | `playback_smoke_id + script_id + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | private wav 5개가 demo playback 후보로 준비됐다. |
| allowed | 외부 STT/TTS provider 호출과 외부 음성 전송은 0이다. |
| allowed | public artifact에는 raw audio, raw transcript, raw script, 개별 score를 저장하지 않는다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | speaker device 자동 재생 검증 완료 |
| forbidden | managed provider보다 local TTS가 품질 우수하다는 주장 |
