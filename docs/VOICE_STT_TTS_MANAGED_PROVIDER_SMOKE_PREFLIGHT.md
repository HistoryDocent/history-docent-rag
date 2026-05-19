# Voice STT/TTS Managed Provider Smoke Preflight

`HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-PREFLIGHT-001`는 managed provider smoke 실행 직전의 credential, source, region, retention, cost preflight를 수행한다.

결론: 이 단계는 외부 provider API를 호출하지 않으며 credential 값도 기록하지 않는다.

## Scope

| field | value |
| --- | --- |
| work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-PREFLIGHT-001` |
| depends_on | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-EXECUTION-HARNESS-001` |
| next_work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| executable_provider_candidate_count | 0 |
| recommended_first_provider_count | 0 |
| preflight_decision | `preflight_complete_missing_credentials` |

## Provider Preflight

credential 값은 읽거나 출력하지 않고 환경 변수 존재 여부만 집계한다.

| provider_candidate_id | modality | credential count | present | missing | source recheck | status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `managed_google_cloud_speech_to_text` | stt | 2 | 0 | 2 | 3 | `blocked_missing_credentials` |
| `managed_azure_ai_speech` | stt_tts | 2 | 0 | 2 | 2 | `blocked_missing_credentials` |
| `managed_aws_transcribe_polly` | stt_tts | 3 | 0 | 3 | 4 | `blocked_missing_credentials` |

## Recommended First Smoke Target

| provider_candidate_id | planned scripts | planned STT | planned TTS | reason |
| --- | ---: | ---: | ---: | --- |
| none | 0 | 0 | 0 | credential 준비 후 재실행 필요 |

## Quantitative Gate

| metric | value |
| --- | ---: |
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

## Data Mart

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_managed_smoke_preflight_provider` | `preflight_id + provider_candidate_id` | public aggregate |
| `fact_voice_managed_smoke_preflight_recommendation` | `preflight_id + selection_rank` | public aggregate |
| `fact_voice_managed_smoke_private_payload` | `run_id + provider_candidate_id + script_id` | private only |

## Claim Boundary

허용 claim:

- managed provider smoke 실행 전 preflight를 구현했다.

- managed provider API call과 external audio transmission은 0회다.

- credential 값은 public artifact에 기록하지 않았다.

- 실제 smoke 실행은 source, region, retention, cost 재확인과 별도 승인 뒤에만 가능하다.

금지 claim:

- provider 최종 선택 완료

- managed provider STT/TTS 품질 검증 완료

- 외부 provider benchmark 완료

- production voice service 준비 완료

- managed provider 비용/정책 최신 확인 완료
