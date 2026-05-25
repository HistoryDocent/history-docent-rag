# Voice Demo Playback Smoke Report

## 결론

`HD-VOICE-DEMO-PLAYBACK-SMOKE-001`는 `completed_local_voice_demo_playback_smoke`이다.

private wav 5개는 playback-ready 상태다. 자동 speaker playback은 수행하지 않았고, 외부 provider 호출도 0이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-demo-playback-smoke-report/v1` |
| playback_smoke_id | `voice-demo-playback-smoke-s5-e4e35cb6` |
| work_id | `HD-VOICE-DEMO-PLAYBACK-SMOKE-001` |
| depends_on | `HD-VOICE-DEMO-STACK-DECISION-001` |
| generated_at_utc | `2026-05-25T11:12:48+00:00` |
| scripts_path | `data_samples/voice_tts_smoke_scripts.sample.jsonl` |
| audio_path_alias | `<private artifact: sherpa_onnx_supertonic3_ko_audio>` |
| private_score_input_alias | `<private artifact: voice_local_tts_human_scores.jsonl>` |
| result_path | `<private artifact: voice_demo_playback_smoke_rows.jsonl>` |
| source_fingerprint | `120f5e652b756cb9` |
| playback_smoke_decision | `completed_local_voice_demo_playback_smoke` |

## 정량 리포트

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
| private_score_input_available_count | 1 |
| tts_human_score_completed_count | 30 |
| tts_human_score_expected_count | 30 |
| tts_human_score_completed_script_count | 5 |
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
| public_raw_payload_leakage_count | 0 |
| production_voice_claim_count | 0 |

## Result Row Summary

| script_id | language | audio_status | playback_status | duration_ms | file_size_bytes | sample_rate_hz | error_code |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| tts-smoke-docent-001 | ko | `accepted_private_wav` | `ready_for_manual_demo_playback` | 8453.333333 | 745628 | 44100 | `` |
| tts-smoke-docent-002 | ko | `accepted_private_wav` | `ready_for_manual_demo_playback` | 8585.124717 | 757252 | 44100 | `` |
| tts-smoke-docent-003 | ko | `accepted_private_wav` | `ready_for_manual_demo_playback` | 8436.802721 | 744170 | 44100 | `` |
| tts-smoke-docent-004 | ko | `accepted_private_wav` | `ready_for_manual_demo_playback` | 8244.761905 | 727232 | 44100 | `` |
| tts-smoke-docent-005 | ko | `accepted_private_wav` | `ready_for_manual_demo_playback` | 8178.321995 | 721372 | 44100 | `` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 5 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
voice_demo_playback_smoke_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| product | 포트폴리오 demo에서 들려줄 수 있는 private wav 후보가 준비됐는지 확인하는 gate다. |
| voice_ml | STT/TTS 최종 품질 검증이 아니라 현재 로컬 demo 후보의 playback readiness만 확인한다. |
| evaluation | 사람 청취 점수 30/30 완료와 private wav 5개 존재를 함께 확인했다. |
| privacy | raw audio, raw transcript, raw script, 개별 score detail은 public artifact에 포함하지 않는다. |
| cost | 외부 STT/TTS provider 호출, 외부 음성 전송, Solar 호출은 모두 0이다. |
| data_mart | public playback smoke fact와 private audio artifact fact를 분리했다. |
| claim_boundary | demo playback-ready는 주장 가능하지만 production final provider 확정은 금지한다. |
| external_audit | 실제 speaker 자동 재생을 수행하지 않은 점은 로컬 부작용을 줄이는 판단으로 타당하다. |
| decision | completed_local_voice_demo_playback_smoke |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
