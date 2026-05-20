# Voice Local TTS Quality Listening Review Report

## 결론

`HD-VOICE-LOCAL-TTS-QUALITY-LISTENING-REVIEW-001`는 무료 로컬 TTS 품질 평가를 위한 자동 metric과 청취 rubric을 기록한다.

자동 sanity는 통과했더라도 사람 청취 평가는 아직 완료하지 않았다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-tts-quality-listening-review-report/v1` |
| review_id | `voice-local-tts-quality-review-s5-7a6ccda3` |
| work_id | `HD-VOICE-LOCAL-TTS-QUALITY-LISTENING-REVIEW-001` |
| depends_on | `HD-VOICE-LOCAL-SHERPA-ONNX-SUPERTONIC3-KO-SMOKE-001` |
| generated_at_utc | `2026-05-20T12:57:42+00:00` |
| scripts_path | `data_samples/voice_tts_smoke_scripts.sample.jsonl` |
| audio_path_alias | `<private artifact: sherpa_onnx_supertonic3_ko_audio>` |
| result_path | `<private artifact: voice_local_tts_quality_listening_review_rows.jsonl>` |
| provider_candidate_id | `local_sherpa_onnx_supertonic3_ko` |
| source_fingerprint | `362f47806b0b1649` |
| review_status | `automated_audio_sanity_passed_pending_human_review` |

## 정량 리포트

| metric | value |
| --- | ---: |
| expected_audio_count | 5 |
| selected_audio_count | 5 |
| audio_file_available_count | 5 |
| audio_metric_row_count | 5 |
| automated_metric_pass_count | 5 |
| automated_metric_fail_count | 0 |
| duration_gate_pass_count | 5 |
| clipping_gate_pass_count | 5 |
| silence_gate_pass_count | 5 |
| sample_rate_gate_pass_count | 5 |
| human_listening_rubric_criterion_count | 6 |
| human_listening_required_count | 5 |
| human_listening_completed_count | 0 |
| human_listening_score_public_artifact_count | 0 |
| duration_p50_ms | 8436.802721 |
| duration_p95_ms | 8558.766440 |
| rms_dbfs_p50 | -25.270905 |
| clipping_sample_ratio_max | 0.00000000 |
| silence_sample_ratio_max | 0.48578733 |
| leading_silence_ms_max | 604.195011 |
| trailing_silence_ms_max | 720.770975 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_audio_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| review_decision | `automated_audio_sanity_passed_pending_human_review` |

## Audio Metric Rows

| script_id | status | duration_ms | rms_dbfs | clipping_ratio | silence_ratio | leading_ms | trailing_ms | auto_pass | error_code |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| tts-smoke-docent-001 | `read` | 8453.333333 | -24.431994 | 0.00000000 | 0.46613125 | 603.877551 | 684.149660 | `True` | `` |
| tts-smoke-docent-002 | `read` | 8585.124717 | -25.270905 | 0.00000000 | 0.48024057 | 603.741497 | 527.278912 | `True` | `` |
| tts-smoke-docent-003 | `read` | 8436.802721 | -25.425076 | 0.00000000 | 0.47621236 | 531.836735 | 720.770975 | `True` | `` |
| tts-smoke-docent-004 | `read` | 8244.761905 | -24.882044 | 0.00000000 | 0.47175146 | 604.195011 | 645.600907 | `True` | `` |
| tts-smoke-docent-005 | `read` | 8178.321995 | -25.442833 | 0.00000000 | 0.48578733 | 541.904762 | 712.562358 | `True` | `` |

## Human Listening Rubric Template

| criterion_id | label | range | low_anchor | high_anchor |
| --- | --- | --- | --- | --- |
| pronunciation_clarity | 발음 명료도 | 1-5 | 고유명사와 문장 핵심어가 잘 들리지 않는다. | 고유명사와 문장 핵심어가 또렷하게 들린다. |
| korean_naturalness | 한국어 자연스러움 | 1-5 | 억양이나 띄어읽기가 한국어 안내로 부자연스럽다. | 한국어 문장 흐름과 억양이 자연스럽다. |
| docent_tone | 역사 도슨트 톤 | 1-5 | 관광 안내보다 기계 낭독에 가깝다. | 관광 도슨트 안내 톤으로 수용 가능하다. |
| speaking_rate | 말 속도 | 1-5 | 너무 빠르거나 느려서 관광 중 듣기 어렵다. | 이동 중 짧은 안내로 듣기 적절하다. |
| artifact_noise | 잡음/끊김 | 1-5 | 끊김, 왜곡, 잡음이 안내 이해를 방해한다. | 끊김과 잡음이 거의 느껴지지 않는다. |
| tourist_fit | 관광 안내 적합성 | 1-5 | 현장 관광객에게 들려주기 어렵다. | 짧은 현장 안내 음성 후보로 검토 가능하다. |

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
tts_quality_listening_review_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 실제 음질 판정이 아니라 자동 metric과 청취 rubric을 고정했다. |
| audio_metric | duration, RMS, clipping, silence, sample rate를 script 단위로 기록했다. |
| human_review | 사람 청취 평가는 required로 표시하고 completed count는 0으로 유지했다. |
| privacy | public artifact에는 raw audio, raw script text, private path를 저장하지 않았다. |
| cost | 외부 STT/TTS provider 호출이 없어 추가 API 비용은 없다. |
| cuda | CUDA preflight는 기록했지만 audio metric 계산 자체는 CPU file analysis다. |
| data_mart | 자동 metric public grain과 human score private grain을 분리했다. |
| portfolio | 합성 가능성 다음 단계로 품질 평가 체계를 만든 evidence로 설명한다. |
| external_audit | 음질 우수 claim을 금지하고 pending human review로 남긴 판단은 타당하다. |
| decision | automated_audio_sanity_passed_pending_human_review |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
