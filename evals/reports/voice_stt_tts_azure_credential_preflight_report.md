# Voice STT/TTS Azure Credential Preflight Report

`HD-VOICE-STT-TTS-AZURE-CREDENTIAL-PREFLIGHT-001`는 PASS다.

이번 report는 Azure AI Speech 실제 smoke 결과가 아니라 credential/source preflight 결과다.

## Execution Info

| field | value |
| --- | --- |
| report_version | `voice-stt-tts-azure-credential-preflight-report/v1` |
| preflight_id | `azure-credential-preflight-a7fad29b78e39855` |
| work_id | `HD-VOICE-STT-TTS-AZURE-CREDENTIAL-PREFLIGHT-001` |
| depends_on | `HD-VOICE-STT-TTS-AZURE-MANAGED-SMOKE-READINESS-001` |
| next_work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| provider_candidate_id | `managed_azure_ai_speech` |
| generated_at_utc | `2026-05-19T13:22:59+00:00` |
| env_path_status | `present` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_stt_tts_azure_credential_preflight_rows.jsonl>` |
| source_fingerprint | `762cf7f49c8124d6` |

## Quantitative Evaluation

| metric | value |
| --- | --- |
| provider_candidate_count | 1 |
| first_provider_candidate_is_azure | true |
| planned_script_count | 3 |
| planned_stt_call_count | 3 |
| planned_tts_call_count | 3 |
| call_cap_enforced | true |
| azure_credential_ready | false |
| credential_env_var_name_count | 2 |
| credential_present_count | 0 |
| credential_missing_count | 2 |
| credential_value_public_exposure_count | 0 |
| managed_provider_execution_requested_count | 0 |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| official_source_reference_count | 5 |
| source_recheck_required_before_execution_count | 5 |
| source_recheck_completed_for_execution_count | 0 |
| region_recheck_required_count | 1 |
| retention_recheck_required_count | 1 |
| cost_confirmation_required_count | 1 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_payload_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| preflight_decision | `blocked_missing_azure_credentials` |

## Credential Check

| env name | status | value exposure |
| --- | --- | ---: |
| `AZURE_SPEECH_KEY` | `missing` | 0 |
| `AZURE_SPEECH_REGION` | `missing` | 0 |

## Source Check

| source_check_type | recheck_required | recheck_completed |
| --- | --- | --- |
| `region_resource_binding` | true | false |
| `pricing_billing_unit` | true | false |
| `korean_language_support` | true | false |
| `stt_data_privacy_security` | true | false |
| `tts_data_privacy_security` | true | false |

## Public Safety

| metric | value |
| --- | ---: |
| result_row_count | 8 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Qualitative Evaluation

| item | result |
| --- | --- |
| security_boundary | credential 값, raw audio, raw transcript, provider payload를 public artifact에 기록하지 않는다. |
| eval_boundary | 이번 결과는 credential/source preflight이며 Azure STT/TTS 품질 비교가 아니다. |
| data_mart_boundary | preflight, credential check, source check, private payload grain을 분리했다. |
| operations_boundary | Azure credential이 준비되지 않아 실제 managed smoke는 보류 상태다. |

## External Audit

| audit_item | result |
| --- | --- |
| Azure API call 0 유지 | PASS |
| external audio transmission 0 유지 | PASS |
| credential 값 미기록 | PASS |
| raw audio/transcript/payload public artifact 금지 | PASS |
| source/region/retention/cost 재확인 필요 상태 기록 | PASS |
