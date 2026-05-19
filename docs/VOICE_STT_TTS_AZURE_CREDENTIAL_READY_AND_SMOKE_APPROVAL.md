# Voice STT/TTS Azure Credential Ready And Smoke Approval

## 결론

`HD-VOICE-STT-TTS-AZURE-CREDENTIAL-READY-AND-SMOKE-APPROVAL-001`는 Azure credential 준비 여부와 실제 smoke 승인 가능성을 점검한다.

현재 `approval_decision=blocked_missing_azure_credentials`이며, Azure API call과 external audio transmission은 0회다.

이 gate는 실제 Azure STT/TTS smoke가 아니라, credential/source/region/retention/cost/user approval이 모두 충족됐는지 판정하는 마지막 zero-call approval gate다.

## Approval Status

| field | value |
| --- | --- |
| `work_id` | `HD-VOICE-STT-TTS-AZURE-CREDENTIAL-READY-AND-SMOKE-APPROVAL-001` |
| `depends_on` | `HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-001` |
| `next_work_id` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| `provider_candidate_id` | `managed_azure_ai_speech` |
| `azure_credential_ready` | `false` |
| `azure_smoke_execution_ready` | `false` |
| `azure_smoke_execution_approved` | `false` |
| `approval_decision` | `blocked_missing_azure_credentials` |
| `managed_provider_api_call_count` | `0` |
| `external_audio_transmission_count` | `0` |
| `live_stt_call_count` | `0` |
| `live_tts_call_count` | `0` |
| `live_solar_call_count` | `0` |

## Required Credentials

- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`

## Source Recheck

| source_check_type | required | completed |
| --- | --- | --- |
| `region_resource_binding` | true | false |
| `pricing_billing_unit` | true | false |
| `korean_language_support` | true | false |
| `stt_data_privacy_security` | true | false |
| `tts_data_privacy_security` | true | false |

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

## Data Mart Grain

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_azure_credential_ready_approval` | `approval_id + provider_candidate_id` | public aggregate |
| `fact_voice_azure_credential_ready_source_recheck` | `approval_id + source_check_type` | public aggregate |
| `fact_voice_azure_credential_ready_metric_plan` | `approval_id + provider_candidate_id + metric_name` | public aggregate |
| `fact_voice_azure_smoke_private_stt_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_private_tts_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_public_summary` | `run_id + provider_candidate_id + metric_name` | public aggregate |

## Stop Conditions

- `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` 중 하나라도 missing인 경우

- source, region, retention, cost 재확인이 완료되지 않은 경우

- 사용자 별도 external call 승인이 없는 경우

- raw audio, raw transcript, provider payload가 public artifact에 남을 가능성이 있는 경우

- 비용 cap 또는 quota 상태가 불명확한 경우

## Claim Boundary

허용 claim:

- Azure credential ready와 smoke approval gate를 구현했다.

- 현재 Azure API call과 external audio transmission은 0회다.

- credential 값과 raw audio/transcript/payload는 public artifact에 기록하지 않았다.

- 실제 Azure smoke는 credential, source, region, retention, cost, 사용자 external call 승인이 모두 충족될 때만 가능하다.

금지 claim:

- Azure STT/TTS 품질 검증 완료
- Azure managed provider smoke 실행 완료
- Azure provider 최종 선택 완료
- production voice service 준비 완료
- 외부 audio 전송 검증 완료
