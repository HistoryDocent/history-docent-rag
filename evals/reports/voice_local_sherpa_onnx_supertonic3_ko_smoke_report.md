# Voice Local Sherpa-ONNX Supertonic 3 Korean TTS Smoke Report

## 결론

`HD-VOICE-LOCAL-SHERPA-ONNX-SUPERTONIC3-KO-SMOKE-001`는 무료 로컬 한국어 TTS 후보의 실제 합성 smoke 리포트다.

5개 public-safe script를 local TTS로 합성하고 public report에는 raw audio, raw script text, private path를 저장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-sherpa-onnx-supertonic3-ko-smoke-report/v1` |
| smoke_id | `voice-sherpa-onnx-supertonic3-ko-smoke-s5-1893c2a3` |
| work_id | `HD-VOICE-LOCAL-SHERPA-ONNX-SUPERTONIC3-KO-SMOKE-001` |
| depends_on | `HD-VOICE-LOCAL-KOREAN-TTS-ALTERNATIVE-REVIEW-001` |
| generated_at_utc | `2026-05-20T12:32:17+00:00` |
| scripts_path | `data_samples/voice_tts_smoke_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_local_sherpa_onnx_supertonic3_ko_smoke_rows.jsonl>` |
| private_audio_path_alias | `<private artifact: sherpa_onnx_supertonic3_ko_audio>` |
| model_path_alias | `<private artifact: sherpa-onnx-supertonic-3-tts-int8-2026-05-11>` |
| archive_path_alias | `<private artifact: sherpa-onnx-supertonic-3-tts-int8-2026-05-11.tar.bz2>` |
| provider_candidate_id | `local_sherpa_onnx_supertonic3_ko` |
| source_fingerprint | `b1bd97ea4f4bea0c` |
| tts_smoke_status | `completed_local_sherpa_onnx_supertonic3_ko_smoke` |

## 정량 리포트

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
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| tts_smoke_decision | `completed_local_sherpa_onnx_supertonic3_ko_smoke` |

## Result Row Summary

| script_id | language | status | latency_ms | duration_ms | file_size_bytes | sample_rate_hz | chars | place_count | error_code |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| tts-smoke-docent-001 | ko | `executed` | 1225.968500 | 8453.333333 | 745628 | 44100 | 49 | 1 | `` |
| tts-smoke-docent-002 | ko | `executed` | 1211.148200 | 8585.124717 | 757252 | 44100 | 53 | 1 | `` |
| tts-smoke-docent-003 | ko | `executed` | 1237.738900 | 8436.802721 | 744170 | 44100 | 51 | 1 | `` |
| tts-smoke-docent-004 | ko | `executed` | 1211.611800 | 8244.761905 | 727232 | 44100 | 51 | 1 | `` |
| tts-smoke-docent-005 | ko | `executed` | 1182.169200 | 8178.321995 | 721372 | 44100 | 52 | 1 | `` |

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
sherpa_onnx_tts_smoke_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 무료 로컬 한국어 TTS 후보 하나만 대상으로 두고 managed provider는 호출하지 않았다. |
| runtime | sherpa-onnx runtime이 로컬에서 실행되어 private wav artifact를 생성했다. |
| model | Supertonic 3 Korean ONNX model file 존재와 license file 존재를 분리 기록했다. |
| cuda | local preflight는 resolved_device=cuda다. 다만 sherpa-onnx Supertonic smoke는 CPU provider로 실행했다. |
| metric | success count, latency, duration, sample rate, file size를 public-safe aggregate로 기록한다. |
| privacy | audio artifact는 private output이며 public report에는 raw audio와 raw script text를 저장하지 않는다. |
| cost | managed cloud TTS 호출이 없어 external provider 비용은 발생하지 않는다. |
| data_mart | public script-level metric grain과 private audio artifact grain을 분리했다. |
| portfolio | 후보 선정에서 실제 로컬 합성 smoke까지 한 단계 진전했지만 품질 우수 claim은 아직 금지한다. |
| external_audit | 무료 로컬 TTS 전략에서 실행 가능성을 먼저 확인한 순서는 타당하다. |

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_local_sherpa_onnx_supertonic3_ko_smoke_public | smoke_id + script_id + metric_name |
| fact_voice_local_tts_audio_artifact_private | smoke_id + script_id + audio_artifact_id |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
