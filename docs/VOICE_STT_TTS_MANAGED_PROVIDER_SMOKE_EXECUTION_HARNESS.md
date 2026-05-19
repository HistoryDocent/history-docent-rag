# Voice STT/TTS Managed Provider Smoke Execution Harness

`HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-EXECUTION-HARNESS-001`는 managed provider smoke를 실행하기 위한 harness를 만든다.

결론: 이 단계의 기본값은 dry-run이며 실제 provider API 호출은 0회다.

## Scope

| field | value |
| --- | --- |
| work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-EXECUTION-HARNESS-001` |
| depends_on | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-APPROVAL-001` |
| next_work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| dry_run_default | true |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| harness_decision | `ready_for_separate_managed_smoke_execution_approval` |

## Provider Config Schema

| provider_candidate_id | modality | STT cap | TTS cap | credential env names |
| --- | --- | ---: | ---: | --- |
| `managed_google_cloud_speech_to_text` | stt | 3 | 0 | `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT` |
| `managed_azure_ai_speech` | stt_tts | 3 | 3 | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` |
| `managed_aws_transcribe_polly` | stt_tts | 3 | 3 | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` |

## Credential Preflight

값은 기록하지 않고 존재 여부만 집계한다.

| provider_candidate_id | env var count | present count | value exposure |
| --- | ---: | ---: | ---: |
| `managed_google_cloud_speech_to_text` | 2 | 0 | 0 |
| `managed_azure_ai_speech` | 2 | 0 | 0 |
| `managed_aws_transcribe_polly` | 3 | 0 | 0 |

## Source Recheck

| provider_candidate_id | source_type | source | recheck |
| --- | --- | --- | --- |
| `managed_google_cloud_speech_to_text` | pricing | `official_source_63252f4a77cb5889` | true |
| `managed_google_cloud_speech_to_text` | privacy | `official_source_659beb58adf56ff7` | true |
| `managed_google_cloud_speech_to_text` | data_usage | `official_source_4439a38a1141e5fc` | true |
| `managed_azure_ai_speech` | pricing | `official_source_68e18c2afabf18b8` | true |
| `managed_azure_ai_speech` | privacy | `official_source_841410d61b62030b` | true |
| `managed_aws_transcribe_polly` | pricing | `official_source_d5d87b8ad846bd30` | true |
| `managed_aws_transcribe_polly` | privacy | `official_source_456c0165c7f7d7be` | true |
| `managed_aws_transcribe_polly` | pricing | `official_source_ffeec72e4f4bdb81` | true |
| `managed_aws_transcribe_polly` | privacy | `official_source_516652cd824ef9a8` | true |

## Quantitative Gate

| metric | value |
| --- | ---: |
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
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_payload_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |

## Data Mart

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_managed_smoke_harness_run` | `harness_id + provider_candidate_id` | public aggregate |
| `fact_voice_managed_smoke_private_payload` | `run_id + provider_candidate_id + script_id` | private only |
| `fact_voice_managed_smoke_public_summary` | `harness_id + provider_candidate_id + metric_family` | public aggregate |

## Claim Boundary

허용 claim:

- managed provider smoke execution harness를 dry-run으로 구현했다.
- managed provider API call과 external audio transmission은 0회다.
- provider별 call cap을 코드 레벨에서 강제한다.

금지 claim:

- provider 최종 선택 완료
- STT/TTS 품질 검증 완료
- 음성 관광 앱 완성
- managed provider benchmark 성능 개선 입증
- production voice service 준비 완료
