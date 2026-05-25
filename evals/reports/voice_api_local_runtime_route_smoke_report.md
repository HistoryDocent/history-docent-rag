# Voice API Local Runtime Route Smoke Report

## 결론

`HD-VOICE-API-LOCAL-RUNTIME-ROUTE-SMOKE-001`는 `completed_local_voice_api_route_smoke`이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-api-local-runtime-route-smoke-report/v1` |
| route_smoke_id | `voice-api-route-smoke-r4-e0c1d61f` |
| work_id | `HD-VOICE-API-LOCAL-RUNTIME-ROUTE-SMOKE-001` |
| depends_on | `HD-VOICE-DEMO-PLAYBACK-SMOKE-001` |
| generated_at_utc | `2026-05-25T11:29:26+00:00` |
| endpoint | `/api/v1/voice/local-runtime` |
| env_flag_name | `HISTORY_DOCENT_ENABLE_LOCAL_VOICE_DEMO` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| private_input_audio_path_alias | `<private artifact: local_api_route_smoke>` |
| result_path | `<private artifact: voice_api_local_runtime_route_smoke_rows.jsonl>` |
| source_fingerprint | `cbfb32372effac59` |
| route_smoke_decision | `completed_local_voice_api_route_smoke` |

## 정량 리포트

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
| citation_response_count | 1 |
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
| client_secret_exposure_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Scenario Summary

| scenario_id | env_flag | expected | observed | passed | status | detail_code | stt | tts | external_calls |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- | ---: |
| default_disabled | unset | 403 | 403 | true | default_disabled | local_voice_runtime_disabled |  |  | 0 |
| explicit_flag_contract_response | enabled | 200 | 200 | true | enabled_contract_response |  | skipped_by_flag | skipped_by_flag | 0 |
| reject_path_traversal | enabled | 422 | 422 | true | validation_rejected | validation_error |  |  | 0 |
| reject_public_audio_path | enabled | 400 | 400 | true | validation_rejected | public_audio_path_not_allowed |  |  | 0 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 4 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
voice_api_local_runtime_route_smoke_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | local voice runtime route의 API 경계만 검증했다. |
| security | 기본 disabled 상태와 explicit local flag를 분리했다. |
| validation | path traversal과 public audio path 입력을 거부했다. |
| privacy | public row에는 response answer와 spoken answer를 저장하지 않았다. |
| cost | external provider call과 external audio transmission은 0이다. |
| data_mart | public route scenario fact와 private request/audio fact를 분리했다. |
| portfolio | 음성 서비스 완성이 아니라 disabled-by-default API route smoke로 설명한다. |
| external_audit | 실제 음성 UX 전 API 경계부터 고정한 순서는 타당하다. |
| decision | completed_local_voice_api_route_smoke |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
