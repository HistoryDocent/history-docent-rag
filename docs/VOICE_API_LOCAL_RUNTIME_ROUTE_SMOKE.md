# Voice API Local Runtime Route Smoke

## 결론

`HD-VOICE-API-LOCAL-RUNTIME-ROUTE-SMOKE-001`는 `/api/v1/voice/local-runtime` route를 local-only contract smoke로 검증한 gate다.

결과는 `completed_local_voice_api_route_smoke`이다.

## Scope

| type | item |
| --- | --- |
| include | default disabled route check |
| include | explicit `HISTORY_DOCENT_ENABLE_LOCAL_VOICE_DEMO` flag contract response |
| include | relative private wav input validation |
| include | path traversal and public audio path rejection |
| exclude | live microphone capture |
| exclude | speaker playback |
| exclude | local STT execution |
| exclude | local TTS execution |
| exclude | managed STT/TTS provider call |
| exclude | Solar Pro 3 call |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 1 |
| api_route_smoke_count | 1 |
| endpoint_count | 1 |
| total_route_request_count | 4 |
| default_disabled_request_count | 1 |
| default_disabled_pass_count | 1 |
| default_disabled_status_code | 403 |
| explicit_flag_request_count | 1 |
| explicit_flag_contract_pass_count | 1 |
| explicit_flag_status_code | 200 |
| validation_request_count | 2 |
| validation_reject_pass_count | 2 |
| path_traversal_status_code | 422 |
| public_audio_status_code | 400 |
| private_input_audio_generated_count | 1 |
| accepted_audio_input_count | 1 |
| chat_contract_execution_count | 1 |
| stt_execution_requested_count | 0 |
| local_stt_execution_count | 0 |
| tts_execution_requested_count | 0 |
| local_tts_execution_count | 0 |
| tts_final_provider_count | 0 |
| response_answer_public_row_count | 0 |
| response_spoken_answer_public_row_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_api_local_runtime_route_smoke_public` | `route_smoke_id + scenario_id + endpoint + metric_name` | public-safe |
| `fact_voice_api_local_runtime_request_private` | `route_smoke_id + request_id + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | local runtime route is disabled by default. |
| allowed | explicit local demo flag returns contract-only response. |
| allowed | public artifact stores hashes, status codes, and metrics only. |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | STT/TTS provider 최종 확정 |
| forbidden | microphone capture 구현 완료 |
| forbidden | speaker playback 구현 완료 |
