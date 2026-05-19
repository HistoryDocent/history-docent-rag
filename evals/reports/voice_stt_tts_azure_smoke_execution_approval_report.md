# Voice STT/TTS Azure Smoke Execution Approval Report

`HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-APPROVAL-001`는 PASS다.

이번 report는 Azure AI Speech 실제 smoke 결과가 아니라 실행 승인 gate 결과다.

## Execution Info

| field | value |
| --- | --- |
| report_version | `voice-stt-tts-azure-smoke-execution-approval-report/v1` |
| approval_id | `azure-smoke-execution-approval-v1` |
| work_id | `HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-APPROVAL-001` |
| depends_on | `HD-VOICE-STT-TTS-AZURE-CREDENTIAL-PREFLIGHT-001` |
| next_work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| provider_candidate_id | `managed_azure_ai_speech` |
| approval_decision | `blocked_missing_azure_credentials` |

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
| azure_smoke_execution_approved | false |
| user_execution_approval_recorded | false |
| source_recheck_required_before_execution_count | 5 |
| source_recheck_completed_for_execution_count | 0 |
| region_recheck_required_count | 1 |
| retention_recheck_required_count | 1 |
| cost_confirmation_required_count | 1 |
| region_confirmation_completed | false |
| retention_confirmation_completed | false |
| cost_confirmation_completed | false |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| credential_value_public_exposure_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_payload_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Preconditions

| precondition | current_status | execution_allowed |
| --- | --- | --- |
| Azure credential ready | false | false |
| source recheck complete | false | false |
| region confirmation complete | false | false |
| retention confirmation complete | false | false |
| cost confirmation complete | false | false |
| user execution approval recorded | false | false |

## Metric Plan

| metric_family | metrics |
| --- | --- |
| STT | `wer`, `cer`, `place_name_accuracy`, `stt_latency_p95_ms`, `stt_error_rate` |
| TTS | `tts_character_count`, `tts_latency_p95_ms`, `tts_error_rate`, `spoken_answer_length_violation_rate` |
| security_cost | `managed_provider_api_call_count`, `external_audio_transmission_count`, `estimated_stt_cost`, `estimated_tts_cost`, `credential_value_public_exposure_count` |

## Data Mart

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_azure_smoke_execution_approval` | `approval_id + provider_candidate_id` | public aggregate |
| `fact_voice_azure_smoke_source_recheck` | `approval_id + source_check_type` | public aggregate |
| `fact_voice_azure_smoke_private_stt_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_private_tts_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_public_summary` | `run_id + provider_candidate_id + metric_name` | public aggregate |

## Qualitative Evaluation

| item | result |
| --- | --- |
| security_boundary | credential 값, raw audio, raw transcript, provider payload를 public artifact에 기록하지 않는다. |
| eval_boundary | 이번 결과는 실행 승인 gate이며 Azure STT/TTS 품질 비교가 아니다. |
| operations_boundary | credential missing과 source recheck 미완료 때문에 actual smoke는 blocked 상태다. |
| portfolio_boundary | external provider 실험을 비용, 개인정보, call cap gate로 통제한 근거로만 사용한다. |

## External Audit

| audit_item | result |
| --- | --- |
| Azure smoke execution approved false 유지 | PASS |
| Azure API call 0 유지 | PASS |
| external audio transmission 0 유지 | PASS |
| credential 값 미기록 | PASS |
| source/region/retention/cost 재확인 미완료 상태 기록 | PASS |
| raw audio/transcript/payload public artifact 금지 | PASS |
