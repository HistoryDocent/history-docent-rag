# Voice STT/TTS Local TTS Smoke Report

## 결론

`HD-VOICE-STT-TTS-LOCAL-TTS-SMOKE-001`는 무료 로컬 TTS 후보인 `MeloTTS Korean`을 smoke 대상으로 검증한다.

이 리포트는 TTS 품질 최종 검증이 아니다. raw audio와 raw transcript는 public artifact에 저장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-stt-tts-local-tts-smoke-report/v1` |
| smoke_id | `voice-local-tts-smoke-s5-128f72bc` |
| work_id | `HD-VOICE-STT-TTS-LOCAL-TTS-SMOKE-001` |
| depends_on | `HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001` |
| generated_at_utc | `2026-05-19T14:52:01+00:00` |
| scripts_path | `data_samples/voice_tts_smoke_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_stt_tts_local_tts_smoke_rows.jsonl>` |
| private_audio_path_alias | `<private artifact: local_tts_melotts_audio>` |
| provider_candidate_id | `local_melotts_korean` |
| source_fingerprint | `7a70293a1b95d81b` |
| tts_smoke_status | `blocked_missing_runtime_or_audio` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| public_safe_script_fixture_count | 5 |
| primary_local_tts_candidate_count | 1 |
| melotts_runtime_available_count | 0 |
| tts_execution_requested_count | 5 |
| local_tts_execution_count | 0 |
| local_cuda_tts_call_count | 0 |
| private_audio_generated_count | 0 |
| private_audio_saved_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_audio_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| tts_model_load_time_ms | 0.000000 |
| tts_latency_p50_ms | 0.000000 |
| tts_latency_p95_ms | 0.000000 |
| audio_duration_total_ms | 0.000000 |
| audio_file_size_total_bytes | 0 |
| resolved_device | `cuda` |
| melotts_device | `cuda:0` |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Result Row Summary

| script_id | language | status | latency_ms | duration_ms | file_size_bytes | chars | place_count | error_code |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| tts-smoke-docent-001 | ko | `blocked_missing_runtime` | 0.000000 | 0.000000 | 0 | 49 | 1 | `melotts_not_available` |
| tts-smoke-docent-002 | ko | `blocked_missing_runtime` | 0.000000 | 0.000000 | 0 | 53 | 1 | `melotts_not_available` |
| tts-smoke-docent-003 | ko | `blocked_missing_runtime` | 0.000000 | 0.000000 | 0 | 51 | 1 | `melotts_not_available` |
| tts-smoke-docent-004 | ko | `blocked_missing_runtime` | 0.000000 | 0.000000 | 0 | 51 | 1 | `melotts_not_available` |
| tts-smoke-docent-005 | ko | `blocked_missing_runtime` | 0.000000 | 0.000000 | 0 | 52 | 1 | `melotts_not_available` |

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
local_tts_smoke_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 무료 로컬 TTS 후보만 대상으로 두고 managed provider는 호출하지 않았다. |
| runtime | MeloTTS runtime 또는 model load 조건이 충족되지 않아 실행이 차단됐다. |
| cuda | CUDA 가능 시 사용하며 resolved_device=cuda로 기록했다. |
| metric | success count, latency, duration, file size를 public-safe aggregate로 기록한다. |
| privacy | audio artifact는 private output이며 public report에는 raw audio를 저장하지 않는다. |
| cost | managed cloud TTS 호출이 없어 external provider 비용은 발생하지 않는다. |
| data_mart | private script-level fact와 public provider summary grain을 분리했다. |
| portfolio | TTS 최종 선정이 아니라 local-first 후보 검증 gate로 설명한다. |
| external_audit | managed provider 전송 전 local TTS를 먼저 검증하는 순서는 타당하다. |

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_tts_local_smoke_private | smoke_id + script_id + provider_candidate_id + metric_name |
| fact_voice_tts_local_smoke_public_summary | smoke_id + provider_candidate_id + metric_name |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
