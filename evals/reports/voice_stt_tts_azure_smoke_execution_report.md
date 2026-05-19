# Voice STT/TTS Azure Smoke Execution Report

`HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-001`는 PASS다.

이번 report는 Azure AI Speech 실제 smoke 품질 결과가 아니라 실행 gate 결과다.

## Execution Info

| field | value |
| --- | --- |
| report_version | `voice-stt-tts-azure-smoke-execution-report/v1` |
| execution_id | `azure-smoke-execution-0f4a2d16e083ff94` |
| work_id | `HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-001` |
| depends_on | `HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-APPROVAL-001` |
| next_work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| provider_candidate_id | `managed_azure_ai_speech` |
| generated_at_utc | `2026-05-19T13:48:30+00:00` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_stt_tts_azure_smoke_execution_rows.jsonl>` |
| source_fingerprint | `baefba3bdd2c64cd` |

## Quantitative Evaluation

| metric | value |
| --- | --- |
| provider_candidate_count | 1 |
| first_provider_candidate_is_azure | true |
| selected_script_count | 3 |
| planned_stt_call_count | 3 |
| planned_tts_call_count | 3 |
| call_cap_enforced | true |
| azure_credential_ready | false |
| credential_present_count | 0 |
| credential_missing_count | 2 |
| credential_value_public_exposure_count | 0 |
| source_recheck_required_before_execution_count | 5 |
| source_recheck_completed_for_execution_count | 0 |
| region_confirmation_completed | false |
| retention_confirmation_completed | false |
| cost_confirmation_completed | false |
| user_external_call_approval_recorded | false |
| azure_smoke_execution_requested_count | 0 |
| azure_smoke_execution_allowed | false |
| azure_smoke_execution_approved | false |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| stt_eval_row_count | 0 |
| tts_eval_row_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_payload_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| execution_decision | `blocked_missing_azure_credentials` |

## Source Recheck

| source_check_type | recheck_required | recheck_completed |
| --- | --- | --- |
| `region_resource_binding` | true | false |
| `pricing_billing_unit` | true | false |
| `korean_language_support` | true | false |
| `stt_data_privacy_security` | true | false |
| `tts_data_privacy_security` | true | false |

## Script Plan

| script_id | query_type | planned_stt | planned_tts | actual_stt | actual_tts | status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `voice-script-place-fact-001` | `place_fact` | 1 | 1 | 0 | 0 | `blocked_not_executed` |
| `voice-script-place-fact-002` | `place_fact` | 1 | 1 | 0 | 0 | `blocked_not_executed` |
| `voice-script-place-fact-003` | `place_fact` | 1 | 1 | 0 | 0 | `blocked_not_executed` |

## Metric Plan

| metric | family | status |
| --- | --- | --- |
| `wer` | `stt` | `planned_not_executed` |
| `cer` | `stt` | `planned_not_executed` |
| `place_name_accuracy` | `stt` | `planned_not_executed` |
| `stt_latency_p50_ms` | `stt` | `planned_not_executed` |
| `stt_latency_p95_ms` | `stt` | `planned_not_executed` |
| `stt_error_rate` | `stt` | `planned_not_executed` |
| `tts_character_count` | `tts` | `planned_not_executed` |
| `tts_latency_p50_ms` | `tts` | `planned_not_executed` |
| `tts_latency_p95_ms` | `tts` | `planned_not_executed` |
| `tts_error_rate` | `tts` | `planned_not_executed` |
| `spoken_answer_length_violation_rate` | `tts` | `planned_not_executed` |
| `estimated_stt_cost` | `security_cost` | `planned_not_executed` |
| `estimated_tts_cost` | `security_cost` | `planned_not_executed` |

## Public Safety

| metric | value |
| --- | ---: |
| result_row_count | 22 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Data Mart Grain

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_azure_smoke_execution` | `execution_id + provider_candidate_id` | public aggregate |
| `fact_voice_azure_smoke_source_recheck` | `execution_id + source_check_type` | public aggregate |
| `fact_voice_azure_smoke_script_plan` | `execution_id + provider_candidate_id + script_id` | public aggregate |
| `fact_voice_azure_smoke_private_stt_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_private_tts_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_public_summary` | `run_id + provider_candidate_id + metric_name` | public aggregate |

## Qualitative Evaluation

| item | result |
| --- | --- |
| security_boundary | credential 값, raw audio, raw transcript, provider payload를 public artifact에 기록하지 않는다. |
| eval_boundary | 이번 결과는 실행 gate이며 Azure STT/TTS 품질 비교가 아니다. |
| data_mart_boundary | execution summary, source recheck, script plan, private metric grain을 분리했다. |
| operations_boundary | Azure credential이 준비되지 않아 실제 smoke를 실행하지 않는다. |

## External Audit

| audit_item | result |
| --- | --- |
| Azure API call 0 유지 | PASS |
| external audio transmission 0 유지 | PASS |
| credential 값 미기록 | PASS |
| raw audio/transcript/payload public artifact 금지 | PASS |
| source/region/retention/cost/user approval 미충족 시 실행 차단 | PASS |
