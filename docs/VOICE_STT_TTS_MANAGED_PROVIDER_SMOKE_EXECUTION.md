# Voice STT/TTS Managed Provider Smoke Execution

## 결론

`HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001`는 selected managed provider smoke execution work order를 만든다.

현재 `execution_decision=blocked_missing_azure_credentials`이며, managed provider API call과 external audio transmission은 0회다.

이번 산출물은 실제 Azure STT/TTS 품질 검증이 아니라, credential/source/region/retention/cost/user approval/actual-call phrase가 모두 충족될 때만 실행 가능한지 판정하는 execution gate다.

## Execution Status

| field | value |
| --- | --- |
| `work_id` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| `depends_on` | `HD-VOICE-STT-TTS-AZURE-CREDENTIAL-READY-AND-SMOKE-APPROVAL-001` |
| `next_work_id` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-LIVE-001` |
| `provider_candidate_id` | `managed_azure_ai_speech` |
| `azure_credential_ready` | `false` |
| `managed_provider_execution_ready` | `false` |
| `managed_provider_execution_approved` | `false` |
| `execution_decision` | `blocked_missing_azure_credentials` |
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

## Script Plan

| provider | script_id | query_type | planned_stt | planned_tts | actual_stt | actual_tts | status |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `managed_azure_ai_speech` | `voice-script-place-fact-001` | `place_fact` | 1 | 1 | 0 | 0 | `blocked_not_executed` |
| `managed_azure_ai_speech` | `voice-script-place-fact-002` | `place_fact` | 1 | 1 | 0 | 0 | `blocked_not_executed` |
| `managed_azure_ai_speech` | `voice-script-place-fact-003` | `place_fact` | 1 | 1 | 0 | 0 | `blocked_not_executed` |

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
| `fact_voice_managed_smoke_execution` | `execution_id + provider_candidate_id` | public aggregate |
| `fact_voice_managed_smoke_script_plan` | `execution_id + provider_candidate_id + script_id` | public aggregate |
| `fact_voice_managed_smoke_metric_plan` | `execution_id + provider_candidate_id + metric_name` | public aggregate |
| `fact_voice_managed_smoke_private_stt_eval` | `execution_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_managed_smoke_private_tts_eval` | `execution_id + provider_candidate_id + script_id + metric_name` | private only |

## Stop Conditions

- Azure credential이 missing인 경우

- source, region, retention, cost 재확인이 완료되지 않은 경우

- 사용자 external call 승인이 없는 경우

- actual-call 승인 문구가 없는 경우

- raw audio, raw transcript, provider payload가 public artifact에 남을 가능성이 있는 경우

## Claim Boundary

허용 claim:

- managed provider smoke execution gate를 구현했다.

- 현재 managed provider API call과 external audio transmission은 0회다.

- credential 값과 raw audio/transcript/payload는 public artifact에 기록하지 않았다.

- 실제 Azure smoke는 credential, source, region, retention, cost, 사용자 external call 승인, actual-call 승인 문구가 모두 충족될 때만 가능하다.

금지 claim:

- Azure STT/TTS 품질 검증 완료
- Azure managed provider smoke 실행 완료
- managed provider benchmark 성능 개선 입증
- production voice service 준비 완료
- 외부 audio 전송 검증 완료
