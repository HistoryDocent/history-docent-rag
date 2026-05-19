# Voice STT/TTS Managed Provider Smoke Preflight Report

`HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-PREFLIGHT-001`는 PASS다.

이번 report는 managed provider 실제 smoke 결과가 아니라 실행 직전 preflight 검증 결과다.

## Execution Info

| field | value |
| --- | --- |
| report_version | `voice-stt-tts-managed-provider-smoke-preflight-report/v1` |
| preflight_id | `managed-smoke-preflight-a6f4270e4e36eed4` |
| work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-PREFLIGHT-001` |
| depends_on | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-EXECUTION-HARNESS-001` |
| next_work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| generated_at_utc | `2026-05-19T13:00:41+00:00` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_stt_tts_managed_provider_smoke_preflight_rows.jsonl>` |
| source_fingerprint | `85b85b2e269f6f9a` |

## Quantitative Evaluation

| metric | value |
| --- | --- |
| provider_candidate_count | 3 |
| selected_script_count | 3 |
| planned_max_stt_calls_per_provider | 3 |
| planned_max_tts_calls_per_provider | 3 |
| call_cap_enforced | true |
| executable_provider_candidate_count | 0 |
| recommended_first_provider_count | 0 |
| managed_provider_execution_requested_count | 0 |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| official_source_count | 9 |
| source_recheck_required_count | 9 |
| pricing_source_recheck_required_count | 4 |
| privacy_source_recheck_required_count | 5 |
| region_recheck_required_count | 3 |
| retention_recheck_required_count | 3 |
| cost_confirmation_required_count | 3 |
| source_recheck_completed_count | 0 |
| credential_env_var_name_count | 7 |
| credential_present_count | 0 |
| credential_missing_count | 7 |
| credential_value_public_exposure_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_payload_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| preflight_decision | `preflight_complete_missing_credentials` |

## Provider Preflight

| provider_candidate_id | modality | credential present/missing | source recheck | feasibility |
| --- | --- | ---: | ---: | --- |
| `managed_google_cloud_speech_to_text` | stt | 0/2 | 3 | `blocked_missing_credentials` |
| `managed_azure_ai_speech` | stt_tts | 0/2 | 2 | `blocked_missing_credentials` |
| `managed_aws_transcribe_polly` | stt_tts | 0/3 | 4 | `blocked_missing_credentials` |

## Recommendation

| provider_candidate_id | planned scripts | planned STT | planned TTS | reason |
| --- | ---: | ---: | ---: | --- |
| none | 0 | 0 | 0 | credential 준비 후 재실행 필요 |

## Public Safety

| metric | value |
| --- | ---: |
| result_row_count | 4 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Qualitative Evaluation

| item | result |
| --- | --- |
| security_boundary | credential 값, raw audio, raw transcript, provider payload를 public artifact에 기록하지 않는다. |
| eval_boundary | 이번 결과는 preflight 검증이며 STT/TTS 품질 비교가 아니다. |
| data_mart_boundary | provider grain, recommendation grain, private payload grain을 분리했다. |
| operations_boundary | credential이 준비된 managed provider가 없어 실제 smoke는 보류 상태다. |

## External Audit

| audit_item | result |
| --- | --- |
| managed provider API call 0 유지 | PASS |
| external audio transmission 0 유지 | PASS |
| credential 값 미기록 | PASS |
| raw audio/transcript/payload public artifact 금지 | PASS |
| recommended first provider 1개 이하 유지 | PASS |
| source/region/retention/cost 재확인 필요 상태 기록 | PASS |
