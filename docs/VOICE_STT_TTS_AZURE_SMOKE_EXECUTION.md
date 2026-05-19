# Voice STT/TTS Azure Smoke Execution

## 결론

`HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-001`는 Azure AI Speech 실제 STT/TTS smoke를 실행하지 않았다.

현재 `execution_decision=blocked_missing_azure_credentials`이며, `managed_provider_api_call_count=0`, `external_audio_transmission_count=0`이다.

이번 작업은 실행 runner와 public-safe 차단 리포트를 추가해, credential/source/cost/privacy/user approval이 부족한 상태에서 외부 audio 전송이 발생하지 않도록 하는 gate다.

## Scope

포함:

- Azure AI Speech 1개 provider selected execution gate
- 3개 script 기준 STT 3회, TTS 3회 call cap
- credential/source/region/retention/cost/user approval 확인
- public aggregate와 private raw payload grain 분리
- 실행 전 차단 상태의 정량/정성 리포트

제외:

- Azure API 실제 호출
- 외부 audio 전송
- raw audio, raw transcript, provider payload 공개
- Azure provider 최종 선택
- production 음성 서비스 검증

## Execution Status

| field | value |
| --- | --- |
| `work_id` | `HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-001` |
| `depends_on` | `HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-APPROVAL-001` |
| `next_work_id` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| `provider_candidate_id` | `managed_azure_ai_speech` |
| `azure_credential_ready` | `false` |
| `azure_smoke_execution_approved` | `false` |
| `execution_decision` | `blocked_missing_azure_credentials` |
| `managed_provider_api_call_count` | `0` |
| `external_audio_transmission_count` | `0` |
| `live_stt_call_count` | `0` |
| `live_tts_call_count` | `0` |
| `live_solar_call_count` | `0` |

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
| `fact_voice_azure_smoke_execution` | `execution_id + provider_candidate_id` | public aggregate |
| `fact_voice_azure_smoke_source_recheck` | `execution_id + source_check_type` | public aggregate |
| `fact_voice_azure_smoke_script_plan` | `execution_id + provider_candidate_id + script_id` | public aggregate |
| `fact_voice_azure_smoke_private_stt_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_private_tts_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_public_summary` | `run_id + provider_candidate_id + metric_name` | public aggregate |

금지 필드:

- credential value
- raw audio
- raw transcript
- raw provider payload
- private absolute path
- full user utterance with personal information

## Stop Conditions

- `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` 중 하나라도 missing인 경우
- source, region, retention, cost 재확인이 완료되지 않은 경우
- 사용자 별도 external call 승인이 없는 경우
- 예상 STT/TTS call cap을 초과하는 경우
- raw audio, raw transcript, provider payload가 public artifact에 남을 가능성이 있는 경우
- 비용 cap 또는 quota 상태가 불명확한 경우

## Claim Boundary

허용 claim:

- Azure smoke execution runner와 차단 리포트를 구현했다.

- 현재 Azure API call과 external audio transmission은 0회다.

- credential 값과 raw audio/transcript/payload는 public artifact에 기록하지 않았다.

- 실제 Azure smoke는 credential, source, region, retention, cost, 사용자 external call 승인이 모두 충족될 때만 가능하다.

금지 claim:

- Azure STT/TTS 품질 검증 완료
- Azure managed provider smoke 실행 완료
- Azure provider 최종 선택 완료
- production voice service 준비 완료
- 외부 audio 전송 검증 완료
