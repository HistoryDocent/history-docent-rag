# Voice STT/TTS Azure Smoke Execution Approval

## 결론

`HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-APPROVAL-001`은 Azure managed STT/TTS smoke를 실행하지 않는다.

이번 gate의 목적은 Azure credential preflight 이후 실제 외부 audio 전송과 비용 발생이 있는 smoke를 실행하기 전, 승인 조건과 중단 조건을 고정하는 것이다.

현재 기준 `azure_credential_ready=false`이므로 Azure smoke 실행은 승인하지 않는다.

## Scope

포함:

- Azure AI Speech 1개 provider만 대상으로 하는 selected smoke 승인 기준
- 3개 script, STT 3회, TTS 3회 call cap
- source, region, retention, cost 재확인 조건
- raw audio, raw transcript, provider payload 공개 금지
- public aggregate와 private payload grain 분리

제외:

- Azure API 호출
- 외부 audio 전송
- STT/TTS 품질 검증 완료 주장
- Azure provider 최종 선택
- production 음성 서비스 검증

## Approval Status

| field | value |
| --- | --- |
| `work_id` | `HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-APPROVAL-001` |
| `depends_on` | `HD-VOICE-STT-TTS-AZURE-CREDENTIAL-PREFLIGHT-001` |
| `next_work_id` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| `provider_candidate_id` | `managed_azure_ai_speech` |
| `azure_credential_ready` | `false` |
| `azure_smoke_execution_approved` | `false` |
| `approval_decision` | `blocked_missing_azure_credentials` |
| `managed_provider_api_call_count` | `0` |
| `external_audio_transmission_count` | `0` |
| `live_stt_call_count` | `0` |
| `live_tts_call_count` | `0` |
| `live_solar_call_count` | `0` |

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| Product | 실제 smoke는 portfolio value가 있지만 credential과 source 재확인 전에는 실행하지 않는다. |
| Voice engineering | Azure STT/TTS를 같은 3개 script로 실행해 local CUDA `small`과 비교할 수 있게 한다. |
| RAG | 이번 gate는 RAG 답변 품질이 아니라 음성 provider 입력 품질 실험의 실행 조건이다. |
| Evaluation | WER, CER, place name accuracy, latency, cost를 같은 run grain으로 기록한다. |
| Security | credential 값, raw audio, raw transcript, provider payload는 public artifact에 남기지 않는다. |
| Data warehouse | public summary와 private payload fact를 분리한다. |
| Portfolio | 실제 호출보다 실행 통제와 실패 조건을 먼저 둔 점을 강조한다. |
| External audit | credential이 missing인 상태에서 execution approval을 false로 유지한 것은 타당하다. |

## Execution Preconditions

| precondition | required_value | current_value |
| --- | --- | --- |
| `azure_credential_ready` | true | false |
| `source_recheck_completed_for_execution_count` | 5 | 0 |
| `region_confirmation_completed` | true | false |
| `retention_confirmation_completed` | true | false |
| `cost_confirmation_completed` | true | false |
| `user_execution_approval_recorded` | true | false |
| `raw_audio_public_artifact_count` | 0 | 0 |
| `raw_transcript_public_artifact_count` | 0 | 0 |
| `raw_payload_public_artifact_count` | 0 | 0 |

## Quantitative Approval Criteria

| metric | required_value | current_value |
| --- | ---: | ---: |
| `provider_candidate_count` | 1 | 1 |
| `planned_script_count` | 3 | 3 |
| `planned_stt_call_count` | 3 | 3 |
| `planned_tts_call_count` | 3 | 3 |
| `call_cap_enforced` | true | true |
| `azure_credential_ready` | true | false |
| `azure_smoke_execution_approved` | false | false |
| `managed_provider_api_call_count` | 0 | 0 |
| `external_audio_transmission_count` | 0 | 0 |
| `live_stt_call_count` | 0 | 0 |
| `live_tts_call_count` | 0 | 0 |
| `live_solar_call_count` | 0 | 0 |
| `credential_value_public_exposure_count` | 0 | 0 |
| `source_recheck_required_before_execution_count` | 5 | 5 |
| `source_recheck_completed_for_execution_count` | 5 | 0 |
| `region_recheck_required_count` | 1 | 1 |
| `retention_recheck_required_count` | 1 | 1 |
| `cost_confirmation_required_count` | 1 | 1 |

## Metric Plan

STT:

- `wer`
- `cer`
- `place_name_accuracy`
- `stt_latency_p50_ms`
- `stt_latency_p95_ms`
- `stt_error_rate`

TTS:

- `tts_character_count`
- `tts_latency_p50_ms`
- `tts_latency_p95_ms`
- `tts_error_rate`
- `spoken_answer_length_violation_rate`

Security and cost:

- `managed_provider_api_call_count`
- `external_audio_transmission_count`
- `estimated_stt_cost`
- `estimated_tts_cost`
- `credential_value_public_exposure_count`
- `raw_payload_public_artifact_count`

## Data Mart Grain

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_azure_smoke_execution_approval` | `approval_id + provider_candidate_id` | public aggregate |
| `fact_voice_azure_smoke_source_recheck` | `approval_id + source_check_type` | public aggregate |
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
- 사용자 별도 실행 승인이 없는 경우
- 예상 STT/TTS call cap을 초과하는 경우
- raw audio, raw transcript, provider payload가 public artifact에 남을 가능성이 있는 경우
- Azure SDK 또는 API error가 반복되어 3개 script 비교가 불공정해지는 경우
- 비용 cap 또는 quota 상태가 불명확한 경우

## 다음 작업 지시서

| field | value |
| --- | --- |
| `id` | `HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-001` |
| `depends_on` | `HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-APPROVAL-001` |
| `scope` | Azure credential ready, source recheck, user approval이 모두 충족될 때 3개 script smoke를 실행하고 public-safe summary만 남긴다. |
| `acceptance_tests` | STT/TTS call cap 준수, raw artifact public 0, WER/CER/place/latency/cost summary 생성, secret exposure 0 |
| `risk_level` | Medium |
| `rollback_plan` | private run artifact 폐기, public summary는 failed smoke report로만 보존 |

## Claim Boundary

허용 claim:

- Azure smoke 실행 승인 기준을 문서화했다.
- 현재 Azure credential이 준비되지 않아 실행 승인은 false다.
- Azure API call과 external audio transmission은 0회다.
- 실제 Azure smoke는 credential 준비, source 재확인, 사용자 별도 승인 뒤에만 가능하다.

금지 claim:

- Azure STT/TTS 품질 검증 완료
- Azure managed provider smoke 실행 완료
- Azure provider 최종 선택 완료
- production voice service 준비 완료
- 외부 audio 전송 검증 완료
