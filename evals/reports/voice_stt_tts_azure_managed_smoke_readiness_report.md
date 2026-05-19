# Voice STT/TTS Azure Managed Smoke Readiness Report

`HD-VOICE-STT-TTS-AZURE-MANAGED-SMOKE-READINESS-001`는 PASS다.

이번 report는 Azure AI Speech 실제 smoke 결과가 아니라 실행 전 readiness gate 결과다.

## Execution Info

| field | value |
| --- | --- |
| report_version | `voice-stt-tts-azure-managed-smoke-readiness-report/v1` |
| readiness_id | `azure-managed-smoke-readiness-v1` |
| work_id | `HD-VOICE-STT-TTS-AZURE-MANAGED-SMOKE-READINESS-001` |
| depends_on | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-PREFLIGHT-001` |
| next_work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| first_managed_provider_candidate | `managed_azure_ai_speech` |
| source_reference_checked_date | `2026-05-19` |
| readiness_decision | `ready_for_azure_credential_setup` |

## Quantitative Evaluation

| metric | value |
| --- | --- |
| provider_candidate_count | 1 |
| first_provider_candidate_is_azure | true |
| planned_script_count | 3 |
| planned_stt_call_count | 3 |
| planned_tts_call_count | 3 |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| credential_env_var_name_count | 2 |
| credential_value_public_exposure_count | 0 |
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

## Source Check

| source_check_type | status |
| --- | --- |
| region_resource_binding | recheck_before_execution |
| pricing_billing_unit | recheck_before_execution |
| korean_language_support | recheck_before_execution |
| stt_data_privacy_security | recheck_before_execution |
| tts_data_privacy_security | recheck_before_execution |

## Data Mart

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_azure_smoke_readiness` | `readiness_id + provider_candidate_id` | public aggregate |
| `fact_voice_azure_smoke_source_check` | `readiness_id + source_check_type` | public aggregate |
| `fact_voice_managed_smoke_private_payload` | `run_id + provider_candidate_id + script_id` | private only |

## Qualitative Evaluation

| item | result |
| --- | --- |
| security_boundary | credential 값, raw audio, raw transcript, provider payload를 public artifact에 기록하지 않는다. |
| eval_boundary | 이번 결과는 Azure smoke 준비 gate이며 STT/TTS 품질 비교가 아니다. |
| operations_boundary | 실제 Azure API 호출은 credential 설정, source 재확인, 사용자 별도 승인 이후에만 가능하다. |
| portfolio_boundary | local CUDA `small`과 Azure managed smoke를 같은 3개 script로 비교할 준비 기준만 고정했다. |

## External Audit

| audit_item | result |
| --- | --- |
| Azure API call 0 유지 | PASS |
| external audio transmission 0 유지 | PASS |
| credential 값 미기록 | PASS |
| raw audio/transcript/payload public artifact 금지 | PASS |
| Azure first-provider candidate 고정 | PASS |
| source/region/retention/cost 재확인 필요 상태 기록 | PASS |
