# Voice Local Runtime Contract Report

## 결론

`HD-VOICE-LOCAL-RUNTIME-CONTRACT-001`는 무료 로컬 STT/TTS 우선 전략을 local-only runtime contract와 기본 비활성화 API route로 연결했다.

raw audio, raw transcript, private path는 public artifact에 저장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-runtime-contract-report/v1` |
| runtime_contract_id | `voice-runtime-contract-s5-308b5ced` |
| work_id | `HD-VOICE-LOCAL-RUNTIME-CONTRACT-001` |
| depends_on | `HD-VOICE-LOCAL-E2E-EVAL-001` |
| generated_at_utc | `2026-05-20T10:44:24+00:00` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_local_runtime_contract_rows.jsonl>` |
| private_input_audio_path_alias | `<private artifact: local_runtime_input_audio>` |
| private_output_audio_path_alias | `<private artifact: local_runtime_output_audio>` |
| source_fingerprint | `7f038f545cdc4911` |
| runtime_decision | `completed_local_voice_runtime_contract` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| local_voice_runtime_contract_count | 1 |
| api_route_contract_count | 1 |
| accepted_audio_input_count | 5 |
| validation_reject_case_count | 3 |
| validation_reject_pass_count | 3 |
| local_stt_execution_requested_count | 0 |
| local_stt_execution_count | 0 |
| local_tts_execution_requested_count | 5 |
| local_tts_execution_count | 5 |
| chat_contract_execution_count | 5 |
| citation_response_count | 5 |
| private_input_audio_generated_count | 5 |
| private_output_audio_generated_count | 5 |
| stt_latency_p95_ms | 0.000000 |
| chat_latency_p95_ms | 0.906920 |
| output_tts_latency_p95_ms | 98.622380 |
| runtime_latency_p95_ms | 189.701640 |
| resolved_device | `cuda` |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
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

## Runtime Row Summary

| script_id | query_type | audio | stt | chat | tts | citation_count | runtime_latency_ms | error_code |
| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |
| voice-script-place-fact-001 | place_fact | accepted_private_wav | skipped_by_flag | executed_contract_chat | executed | 1 | 207.762200 |  |
| voice-script-place-fact-002 | place_fact | accepted_private_wav | skipped_by_flag | executed_contract_chat | executed | 1 | 115.820700 |  |
| voice-script-place-fact-003 | place_fact | accepted_private_wav | skipped_by_flag | executed_contract_chat | executed | 1 | 117.459400 |  |
| voice-script-place-fact-004 | place_fact | accepted_private_wav | skipped_by_flag | executed_contract_chat | executed | 1 | 114.594700 |  |
| voice-script-place-fact-005 | place_fact | accepted_private_wav | skipped_by_flag | executed_contract_chat | executed | 1 | 113.122600 |  |

## Validation Cases

| case_id | expected_code | observed_code | passed |
| --- | --- | --- | --- |
| reject_path_traversal | path_traversal_not_allowed | path_traversal_not_allowed | true |
| reject_public_path | public_audio_path_not_allowed | public_audio_path_not_allowed | true |
| reject_non_wav_extension | unsupported_audio_extension | unsupported_audio_extension | true |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 8 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
voice_local_runtime_contract_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 평가 파이프라인을 local-only runtime contract와 API route 경계로 확장했다. |
| api | endpoint는 기본 비활성화 상태이며 명시 env flag가 있어야 실행된다. |
| audio_boundary | 입력 wav는 relative private artifact만 허용하고 path traversal을 차단한다. |
| chat | `/api/v1/chat` contract bridge를 유지해 기존 RAG 계약을 깨지 않았다. |
| tts | local TTS는 optional 실행이며 raw audio는 private artifact로만 둔다. |
| privacy | public row에는 transcript hash, artifact id, metric만 저장한다. |
| cost | external provider call과 external audio transmission은 모두 0이다. |
| data_mart | runtime summary fact와 private audio fact grain을 분리했다. |
| portfolio | 음성 앱 완성이 아니라 local demo contract로 설명해야 한다. |
| external_audit | 실제 UX 구현 전 local-only 보안 경계를 먼저 고정한 순서는 타당하다. |
| decision | completed_local_voice_runtime_contract |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
