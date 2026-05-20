# Voice Local Piper TTS Smoke Report

## 결론

`HD-VOICE-LOCAL-PIPER-TTS-SMOKE-001`는 Piper를 무료 로컬 Korean TTS 후보로 검증한 리포트다.

현재 결과는 `blocked_missing_korean_voice`다. Piper runtime은 설치됐지만 공식 voice manifest에서 Korean voice가 확인되지 않아 Korean synthesis는 실행하지 않았다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-piper-tts-smoke-report/v1` |
| smoke_id | `voice-local-piper-tts-smoke-s5-88573e1a` |
| work_id | `HD-VOICE-LOCAL-PIPER-TTS-SMOKE-001` |
| depends_on | `HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001` |
| generated_at_utc | `2026-05-20T11:32:50+00:00` |
| scripts_path | `data_samples/voice_tts_smoke_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_local_piper_tts_smoke_rows.jsonl>` |
| private_audio_path_alias | `<private artifact: local_piper_tts_audio>` |
| source_fingerprint | `0951a23fb75b14df` |
| piper_source | `official_piper_source` |
| piper_voice_source | `official_piper_voice_manifest` |
| piper_version | `1.4.2` |
| piper_tts_decision | `blocked_missing_korean_voice` |

## Voice Manifest

| metric | value |
| --- | ---: |
| manifest_checked | true |
| manifest_voice_count | 161 |
| manifest_language_count | 49 |
| korean_voice_count | 0 |
| selected_voice_id | `` |
| selected_voice_language | `` |
| selected_voice_quality | `` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| public_safe_script_fixture_count | 5 |
| provider_candidate_count | 1 |
| piper_runtime_available_count | 1 |
| piper_distribution_installed_count | 1 |
| package_install_attempted_count | 1 |
| voice_manifest_checked_count | 1 |
| voice_manifest_available_count | 1 |
| manifest_voice_count | 161 |
| manifest_language_count | 49 |
| korean_voice_available_count | 0 |
| model_download_attempted_count | 0 |
| model_download_success_count | 0 |
| tts_execution_requested_count | 0 |
| local_tts_execution_count | 0 |
| private_audio_generated_count | 0 |
| private_audio_saved_count | 0 |
| tts_latency_p50_ms | 0.000000 |
| tts_latency_p95_ms | 0.000000 |
| audio_duration_total_ms | 0.000000 |
| audio_file_size_total_bytes | 0 |
| resolved_device | `cuda` |
| piper_cuda_requested_count | 0 |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| selected_voice_id | `` |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Result Row Summary

| script_id | status | latency_ms | duration_ms | file_size | error_code |
| --- | --- | ---: | ---: | ---: | --- |
| tts-smoke-docent-001 | `blocked_missing_korean_voice` | 0.000000 | 0.000000 | 0 | `piper_korean_voice_missing` |
| tts-smoke-docent-002 | `blocked_missing_korean_voice` | 0.000000 | 0.000000 | 0 | `piper_korean_voice_missing` |
| tts-smoke-docent-003 | `blocked_missing_korean_voice` | 0.000000 | 0.000000 | 0 | `piper_korean_voice_missing` |
| tts-smoke-docent-004 | `blocked_missing_korean_voice` | 0.000000 | 0.000000 | 0 | `piper_korean_voice_missing` |
| tts-smoke-docent-005 | `blocked_missing_korean_voice` | 0.000000 | 0.000000 | 0 | `piper_korean_voice_missing` |

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
piper_tts_smoke_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | Piper를 무료 로컬 Korean TTS 후보로 검증했다. |
| runtime | piper-tts runtime availability=1로 기록했다. |
| voice_manifest | 공식 voice manifest 161개 voice 중 Korean voice 0개로 기록했다. |
| decision | Korean voice 부재로 Piper는 현재 Korean TTS 기본 provider가 아니다. |
| privacy | raw audio와 raw transcript는 public artifact에 저장하지 않았다. |
| cost | cloud TTS provider 호출과 외부 음성 전송은 모두 0이다. |
| data_mart | script-level public row와 private audio artifact grain을 분리했다. |
| portfolio | 무료 로컬 후보를 검증하고 부적합 사유를 evidence로 남기는 단계다. |
| external_audit | Piper를 억지로 채택하지 않고 Korean voice 부재를 blocker로 기록한 판단은 타당하다. |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
