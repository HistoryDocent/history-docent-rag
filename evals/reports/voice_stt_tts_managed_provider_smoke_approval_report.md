# Voice STT/TTS Managed Provider Smoke Approval Report

`HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-APPROVAL-001`은 PASS다.

이번 report는 managed provider smoke를 실행한 결과가 아니라 실행 전 승인 기준을 검증한 public-safe report다. 외부 STT/TTS provider API 호출, 외부 audio 전송, Solar Pro 3 호출은 모두 0회다.

## Summary

| metric | value |
| --- | --- |
| source_document | `docs/VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_APPROVAL.md` |
| work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-APPROVAL-001` |
| depends_on | `HD-VOICE-STT-TTS-LOCAL-MODEL-ABLATION-001` |
| next_gate | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
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
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_payload_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Quantitative Evaluation

| gate | expected | actual | result |
| --- | ---: | ---: | --- |
| planned provider count | >=3 | 3 | PASS |
| provider별 STT call cap | <=3 | 3 | PASS |
| provider별 TTS call cap | <=3 | 3 | PASS |
| official source count | >=7 | 9 | PASS |
| managed provider API call | 0 | 0 | PASS |
| external audio transmission | 0 | 0 | PASS |
| public raw audio artifact | 0 | 0 | PASS |
| public raw transcript artifact | 0 | 0 | PASS |
| public raw payload artifact | 0 | 0 | PASS |
| secret exposure | 0 | 0 | PASS |

## Qualitative Evaluation

| item | result | note |
| --- | --- | --- |
| provider candidate boundary | PASS | Google STT, Azure AI Speech, AWS Transcribe/Polly를 비교 후보로만 둔다. |
| local baseline boundary | PASS | `local_cuda_whisper_small`은 local 후보이며 managed provider 선택 결론이 아니다. |
| privacy boundary | PASS | 외부 audio 전송은 다음 gate에서 별도 승인 전까지 금지한다. |
| cost boundary | PASS | 단가는 고정하지 않고 공식 source recheck만 요구한다. |
| claim boundary | PASS | provider 최종 선택, 품질 검증 완료, production 준비 완료 claim을 금지한다. |

## External Audit

| audit_item | result |
| --- | --- |
| external provider call 없이 approval-only gate로 유지 | PASS |
| 비용 발생 가능 작업 분리 | PASS |
| raw audio/transcript/payload public artifact 금지 | PASS |
| credential 값 미기록 | PASS |
| 다음 execution gate 별도 승인 필요 | PASS |

## Residual Risk

- managed provider의 실제 STT/TTS 품질은 아직 검증하지 않았다.
- 실제 smoke는 audio가 외부 provider로 전송될 수 있으므로 비용, region, retention, credential scope를 다시 확인해야 한다.
- public report에는 aggregate metric만 남겨야 하며 raw transcript와 raw payload는 private artifact로도 최소 보관한다.
