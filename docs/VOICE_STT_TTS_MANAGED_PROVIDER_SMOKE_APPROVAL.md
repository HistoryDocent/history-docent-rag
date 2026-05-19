# Voice STT/TTS Managed Provider Smoke Approval

`HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-APPROVAL-001`은 managed STT/TTS provider를 실제 호출하기 전 승인 기준을 고정하는 gate다.

결론: 아직 managed provider API를 호출하지 않는다. 이 단계의 목적은 비용, 개인정보, region, retention, call cap, 공개 산출물 경계를 문서화해서 다음 smoke 실행 여부를 사람이 승인할 수 있게 만드는 것이다.

## Scope

| field | value |
| --- | --- |
| work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-APPROVAL-001` |
| depends_on | `HD-VOICE-STT-TTS-LOCAL-MODEL-ABLATION-001` |
| status | `approval_only_pass` |
| managed_provider_execution_approved | false |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |

## Provider Candidate Boundary

| provider_candidate_id | modality | planned_max_stt_calls | planned_max_tts_calls | later_external_audio_transmission | credential boundary | decision |
| --- | --- | ---: | ---: | --- | --- | --- |
| `managed_google_cloud_speech_to_text` | STT | 3 | 0 | true if executed later | env var name only, value never documented | compare only after approval |
| `managed_azure_ai_speech` | STT/TTS | 3 | 3 | true if executed later | env var name only, value never documented | compare only after approval |
| `managed_aws_transcribe_polly` | STT/TTS | 3 | 3 | true if executed later | env var name only, value never documented | compare only after approval |

`local_cuda_whisper_small`은 이전 ablation에서 local STT 품질 후보로 남긴다. managed provider는 local 후보를 대체하는 결론이 아니라 비교 후보일 뿐이다.

## Official Source Recheck

가격, 데이터 사용, 보관 정책은 변동 가능성이 있으므로 smoke 실행 직전 다시 확인한다. 이 문서에는 특정 단가를 고정하지 않는다.

| provider_candidate_id | source_type | source | recheck_required_before_execution |
| --- | --- | --- | --- |
| `managed_google_cloud_speech_to_text` | pricing | https://cloud.google.com/speech-to-text/pricing | yes |
| `managed_google_cloud_speech_to_text` | privacy_logging | https://docs.cloud.google.com/speech-to-text/docs/v1/data-logging | yes |
| `managed_google_cloud_speech_to_text` | data_usage | https://docs.cloud.google.com/speech-to-text/docs/v1/data-usage-faq | yes |
| `managed_azure_ai_speech` | pricing | https://azure.microsoft.com/en-us/pricing/details/speech/ | yes |
| `managed_azure_ai_speech` | privacy_security | https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/speech-service/speech-to-text/data-privacy-security | yes |
| `managed_aws_transcribe_polly` | transcribe_pricing | https://aws.amazon.com/transcribe/pricing/ | yes |
| `managed_aws_transcribe_polly` | transcribe_data_protection | https://docs.aws.amazon.com/transcribe/latest/dg/data-protection.html | yes |
| `managed_aws_transcribe_polly` | polly_pricing | https://aws.amazon.com/polly/pricing/ | yes |
| `managed_aws_transcribe_polly` | polly_data_protection | https://docs.aws.amazon.com/polly/latest/dg/data-protection.html | yes |

## Approval Metrics

| metric | value |
| --- | ---: |
| planned_provider_count | 3 |
| planned_max_stt_calls_per_provider | 3 |
| planned_max_tts_calls_per_provider | 3 |
| official_source_count | 9 |
| pricing_source_recheck_required_count | 4 |
| privacy_source_recheck_required_count | 5 |
| region_recheck_required_count | 3 |
| retention_recheck_required_count | 3 |
| managed_provider_execution_approved | false |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_payload_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |

## Evaluation Plan

Smoke 실행을 별도 승인하면 같은 public-safe script와 같은 private wav 기준으로 비교한다.

| metric_family | metrics | grain |
| --- | --- | --- |
| STT quality | WER, CER, place_name_accuracy | provider + script_id |
| STT latency | stt_latency_p50_ms, stt_latency_p95_ms | provider + script_id |
| TTS usability | playback_success_rate, tts_latency_p95_ms | provider + voice_profile |
| E2E voice | voice_round_trip_latency_p95_ms, rag_answer_contract_preserved_rate | provider + query_type |
| safety | no_answer_voice_hallucination_count, unsupported_claim_rate | provider + query_type |
| cost/privacy | estimated_cost_field_present, region_policy_rechecked, retention_policy_rechecked | provider + run_id |

## Data Mart

| table | grain | public artifact policy |
| --- | --- | --- |
| `fact_voice_managed_provider_smoke_run` | run_id + provider_candidate_id | aggregate only |
| `fact_voice_managed_stt_eval_private` | run_id + provider_candidate_id + script_id | private only |
| `fact_voice_managed_tts_eval_private` | run_id + provider_candidate_id + voice_profile_id | private only |
| `fact_voice_managed_e2e_eval_private` | run_id + provider_candidate_id + query_type | private only |
| `fact_voice_managed_provider_public_summary` | run_id + provider_candidate_id + metric_family | public aggregate only |

Conformed dimensions:

- `dim_provider_candidate`
- `dim_voice_query_type`
- `dim_official_source_recheck`
- `dim_region_policy`
- `dim_modality`
- `dim_runtime`
- `dim_consent_policy`

## Stop Conditions

- pricing, privacy, region, retention source recheck가 완료되지 않으면 실행하지 않는다.
- credential 값이 문서, 로그, report, test fixture에 노출되면 실행을 중지한다.
- planned call cap이 provider별 STT 3회 또는 TTS 3회를 넘으면 실행하지 않는다.
- raw audio, raw transcript, raw request/response payload가 public artifact에 기록되면 실패다.
- 외부 provider 호출은 별도 승인 없이 수행하지 않는다.

## Claim Boundary

허용 claim:

- managed provider smoke 실행 전 승인 기준을 문서화했다.
- 이번 gate에서 managed provider API 호출은 0회다.
- local CUDA Whisper `small`은 이전 local ablation의 품질 후보로 유지한다.

금지 claim:

- provider 최종 선택 완료
- STT/TTS 품질 검증 완료
- 음성 관광 앱 완성
- managed provider benchmark 성능 개선 입증
- production voice service 준비 완료

## Next Work Order

| field | value |
| --- | --- |
| id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| depends_on | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-APPROVAL-001` |
| scope | approved provider별 최대 3개 script smoke 실행 |
| acceptance_tests | provider API call count cap, external audio transmission count 기록, raw artifact public leakage 0, WER/CER/place/latency/cost/privacy metric 기록 |
| risk_level | high |
| rollback_plan | generated private audio/transcript/payload 삭제, external provider credential rotate 검토, public report는 aggregate summary만 유지 |
