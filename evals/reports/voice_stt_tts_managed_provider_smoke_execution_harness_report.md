# Voice STT/TTS Managed Provider Smoke Execution Harness Report

`HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-EXECUTION-HARNESS-001`는 PASS다.

이번 report는 managed provider 실제 smoke 결과가 아니라 dry-run execution harness 검증 결과다.

## Execution Info

| field | value |
| --- | --- |
| report_version | `voice-stt-tts-managed-provider-smoke-execution-harness-report/v1` |
| harness_id | `managed-smoke-harness-a351e9c2939bfcb4` |
| work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-EXECUTION-HARNESS-001` |
| depends_on | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-APPROVAL-001` |
| next_work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| generated_at_utc | `2026-05-19T12:47:46+00:00` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_stt_tts_managed_provider_smoke_execution_harness_rows.jsonl>` |
| source_fingerprint | `df996de0d00ec006` |

## Quantitative Evaluation

| metric | value |
| --- | --- |
| dry_run_default | true |
| managed_provider_execution_requested_count | 0 |
| provider_candidate_count | 3 |
| selected_script_count | 3 |
| planned_max_stt_calls_per_provider | 3 |
| planned_max_tts_calls_per_provider | 3 |
| planned_stt_call_count_total | 9 |
| planned_tts_call_count_total | 6 |
| planned_external_audio_transmission_if_executed_count | 9 |
| call_cap_enforced | true |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| official_source_count | 9 |
| pricing_source_recheck_required_count | 4 |
| privacy_source_recheck_required_count | 5 |
| region_recheck_required_count | 3 |
| retention_recheck_required_count | 3 |
| source_recheck_completed_count | 0 |
| credential_env_var_name_count | 7 |
| credential_present_count | 0 |
| credential_value_public_exposure_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_payload_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| harness_decision | `ready_for_separate_managed_smoke_execution_approval` |

## Provider Plan

| provider_candidate_id | modality | STT cap | TTS cap | source recheck |
| --- | --- | ---: | ---: | --- |
| `managed_google_cloud_speech_to_text` | stt | 3 | 0 | true |
| `managed_azure_ai_speech` | stt_tts | 3 | 3 | true |
| `managed_aws_transcribe_polly` | stt_tts | 3 | 3 | true |

## Planned Rows

| provider_candidate_id | script_id | query_type | planned STT | planned TTS | actual API calls |
| --- | --- | --- | ---: | ---: | ---: |
| `managed_google_cloud_speech_to_text` | `voice-script-place-fact-001` | place_fact | 1 | 0 | 0 |
| `managed_google_cloud_speech_to_text` | `voice-script-place-fact-002` | place_fact | 1 | 0 | 0 |
| `managed_google_cloud_speech_to_text` | `voice-script-place-fact-003` | place_fact | 1 | 0 | 0 |
| `managed_azure_ai_speech` | `voice-script-place-fact-001` | place_fact | 1 | 1 | 0 |
| `managed_azure_ai_speech` | `voice-script-place-fact-002` | place_fact | 1 | 1 | 0 |
| `managed_azure_ai_speech` | `voice-script-place-fact-003` | place_fact | 1 | 1 | 0 |
| `managed_aws_transcribe_polly` | `voice-script-place-fact-001` | place_fact | 1 | 1 | 0 |
| `managed_aws_transcribe_polly` | `voice-script-place-fact-002` | place_fact | 1 | 1 | 0 |
| `managed_aws_transcribe_polly` | `voice-script-place-fact-003` | place_fact | 1 | 1 | 0 |

## Public Safety

| metric | value |
| --- | ---: |
| result_row_count | 16 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Qualitative Evaluation

| item | result |
| --- | --- |
| security_boundary | credential 값과 provider payload를 public artifact에 기록하지 않는다. |
| eval_boundary | 이번 결과는 harness 검증이며 STT/TTS 품질 비교가 아니다. |
| data_mart_boundary | private payload grain과 public summary grain을 분리했다. |
| operations_boundary | 기본 실행은 dry-run이고 실제 provider call은 별도 work order로 차단했다. |

## External Audit

| audit_item | result |
| --- | --- |
| managed provider API call 0 유지 | PASS |
| external audio transmission 0 유지 | PASS |
| credential 값 미기록 | PASS |
| raw audio/transcript/payload public artifact 금지 | PASS |
| 다음 실제 smoke 실행 별도 승인 필요 | PASS |
