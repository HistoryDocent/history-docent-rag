# Voice Local Runtime Contract

## 결론

`HD-VOICE-LOCAL-RUNTIME-CONTRACT-001`는 무료 로컬 STT/TTS 우선 전략을 데모 가능한 local-only runtime contract로 연결한 결과다.

이 gate는 실제 관광객 음성 품질 최종 검증이나 production 음성 앱 완성 claim이 아니다.

## Scope

| type | item |
| --- | --- |
| include | local private wav input validation |
| include | local voice runtime service |
| include | 기본 비활성화된 `POST /api/v1/voice/local-runtime` route |
| include | `/api/v1/chat` contract bridge |
| include | optional local TTS private artifact |
| exclude | public raw audio artifact |
| exclude | public raw transcript artifact |
| exclude | managed STT/TTS provider call |
| exclude | Solar Pro 3 call |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| local_voice_runtime_contract_count | 1 |
| api_route_contract_count | 1 |
| accepted_audio_input_count | 5 |
| validation_reject_case_count | 3 |
| validation_reject_pass_count | 3 |
| local_stt_execution_count | 0 |
| local_tts_execution_count | 5 |
| chat_contract_execution_count | 5 |
| citation_response_count | 5 |
| private_input_audio_generated_count | 5 |
| private_output_audio_generated_count | 5 |
| chat_latency_p95_ms | 0.906920 |
| output_tts_latency_p95_ms | 98.622380 |
| runtime_latency_p95_ms | 189.701640 |
| resolved_device | `cuda` |
| cuda_device_count | 1 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| runtime_decision | `completed_local_voice_runtime_contract` |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_runtime_contract` | `runtime_contract_id + script_id + stage + metric_name` | public-safe summary |
| `fact_voice_local_runtime_audio_private` | `runtime_contract_id + request_id + audio_role + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | local-only voice runtime contract와 disabled-by-default API route를 구현했다. |
| allowed | external provider call과 external audio transmission은 0이다. |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | STT/TTS provider 최종 확정 |
