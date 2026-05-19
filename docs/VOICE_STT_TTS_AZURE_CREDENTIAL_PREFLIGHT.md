# Voice STT/TTS Azure Credential Preflight

`HD-VOICE-STT-TTS-AZURE-CREDENTIAL-PREFLIGHT-001`는 Azure managed STT/TTS smoke 실행 전 credential 존재 여부와 source 재확인 조건을 자동 점검한다.

결론: 이 단계는 Azure API를 호출하지 않는다. credential 값, raw audio, raw transcript, provider payload도 public artifact에 기록하지 않는다.

## Scope

| field | value |
| --- | --- |
| work_id | `HD-VOICE-STT-TTS-AZURE-CREDENTIAL-PREFLIGHT-001` |
| depends_on | `HD-VOICE-STT-TTS-AZURE-MANAGED-SMOKE-READINESS-001` |
| next_work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| provider_candidate_id | `managed_azure_ai_speech` |
| azure_credential_ready | false |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| preflight_decision | `blocked_missing_azure_credentials` |

## Credential Check

credential 값은 읽더라도 출력하지 않는다. 아래 표는 존재 여부만 기록한다.

| env name | status | value exposure |
| --- | --- | ---: |
| `AZURE_SPEECH_KEY` | `missing` | 0 |
| `AZURE_SPEECH_REGION` | `missing` | 0 |

## Source Recheck

실제 smoke 직전 같은 날짜에 다시 확인한다. 이 preflight는 최신 가격/정책 확인 완료 claim이 아니다.

| source_check_type | source reference | execution gate |
| --- | --- | --- |
| `region_resource_binding` | official Azure source in readiness doc | recheck before execution |
| `pricing_billing_unit` | official Azure source in readiness doc | recheck before execution |
| `korean_language_support` | official Azure source in readiness doc | recheck before execution |
| `stt_data_privacy_security` | official Azure source in readiness doc | recheck before execution |
| `tts_data_privacy_security` | official Azure source in readiness doc | recheck before execution |

## Quantitative Gate

| metric | value |
| --- | ---: |
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

## Data Mart

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_azure_credential_preflight` | `preflight_id + provider_candidate_id` | public aggregate |
| `fact_voice_azure_credential_check` | `preflight_id + env_name` | public aggregate |
| `fact_voice_azure_source_check` | `preflight_id + source_check_type` | public aggregate |
| `fact_voice_managed_smoke_private_payload` | `run_id + provider_candidate_id + script_id` | private only |

## Claim Boundary

허용 claim:

- Azure credential preflight를 구현했다.

- Azure API call과 external audio transmission은 0회다.

- credential 값은 public artifact에 기록하지 않았다.

- 실제 Azure smoke는 credential 준비, source 재확인, 사용자 별도 승인 뒤에만 가능하다.

금지 claim:

- Azure STT/TTS 품질 검증 완료

- Azure managed provider smoke 실행 완료

- Azure 비용/정책 최신 확인 완료

- production voice service 준비 완료

- 외부 audio 전송 검증 완료
