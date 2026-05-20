# Voice Local E2E Eval Report

## 결론

`HD-VOICE-LOCAL-E2E-EVAL-001`는 무료 로컬 STT/TTS 우선 전략을 30개 public-safe script 기준 local E2E regression으로 확장했다.

이 리포트는 실제 관광객 음성 품질 최종 검증이 아니다. raw audio와 raw transcript는 public artifact에 저장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-e2e-eval-report/v1` |
| e2e_id | `voice-local-e2e-s30-7a5d78b7` |
| work_id | `HD-VOICE-LOCAL-E2E-EVAL-001` |
| depends_on | `HD-VOICE-STT-TTS-LOCAL-ADAPTER-INTEGRATION-001` |
| generated_at_utc | `2026-05-20T10:26:35+00:00` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_local_e2e_eval_rows.jsonl>` |
| private_input_audio_path_alias | `<private artifact: local_e2e_input_audio>` |
| private_output_audio_path_alias | `<private artifact: local_e2e_output_audio>` |
| source_fingerprint | `6390b5b5335e761e` |
| e2e_decision | `completed_local_voice_e2e_regression` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | 30 |
| public_safe_script_count | 30 |
| query_type_count | 6 |
| script_per_query_type_min_count | 5 |
| local_voice_adapter_module_count | 1 |
| local_stt_provider_candidate_count | 1 |
| local_tts_provider_candidate_count | 1 |
| local_stt_runtime_available_count | 1 |
| input_tts_generation_requested_count | 30 |
| input_tts_generation_count | 30 |
| local_stt_execution_requested_count | 30 |
| local_stt_execution_count | 30 |
| local_cuda_whisper_call_count | 30 |
| chat_contract_execution_count | 30 |
| answer_with_citation_script_count | 25 |
| abstain_script_count | 5 |
| citation_response_count | 25 |
| expected_behavior_pass_count | 30 |
| output_tts_generation_requested_count | 30 |
| output_tts_generation_count | 30 |
| private_input_audio_generated_count | 30 |
| private_output_audio_generated_count | 30 |
| stt_wer_avg | 0.066045 |
| stt_cer_avg | 0.028262 |
| stt_place_name_accuracy_avg | 0.740000 |
| input_tts_latency_p95_ms | 93.819120 |
| stt_latency_p95_ms | 268.553150 |
| chat_latency_p95_ms | 0.518885 |
| output_tts_latency_p95_ms | 98.918350 |
| voice_round_trip_latency_p95_ms | 444.628360 |
| input_audio_duration_total_ms | 123628.163265 |
| output_audio_duration_total_ms | 261585.941055 |
| input_audio_file_size_total_bytes | 5453382 |
| output_audio_file_size_total_bytes | 11537320 |
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

## Query Type Breakdown

| query_type | scripts | stt | chat | output_tts | expected_pass | wer_avg | cer_avg | place_acc_avg | round_trip_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_answer | 5 | 5 | 5 | 5 | 5 | 0.095238 | 0.014286 | null | 422.196780 |
| place_fact | 5 | 5 | 5 | 5 | 5 | 0.080000 | 0.026667 | 0.800000 | 786.020340 |
| place_story | 5 | 5 | 5 | 5 | 5 | 0.028571 | 0.010526 | 1.000000 | 429.299700 |
| relationship | 5 | 5 | 5 | 5 | 5 | 0.145238 | 0.076822 | 0.800000 | 403.287120 |
| route_context | 5 | 5 | 5 | 5 | 5 | 0.022222 | 0.019048 | 0.900000 | 443.737440 |
| voice_followup | 5 | 5 | 5 | 5 | 5 | 0.025000 | 0.022222 | 0.200000 | 440.459680 |

## Script Row Summary

| script_id | query_type | expected | input_tts | stt | chat | output_tts | expected_pass | round_trip_ms | citation_count | error_code |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- |
| voice-script-place-fact-001 | place_fact | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 873.455200 | 1 |  |
| voice-script-place-fact-002 | place_fact | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 406.298700 | 1 |  |
| voice-script-place-fact-003 | place_fact | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 420.346900 | 1 |  |
| voice-script-place-fact-004 | place_fact | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 351.732300 | 1 |  |
| voice-script-place-fact-005 | place_fact | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 436.280900 | 1 |  |
| voice-script-place-story-001 | place_story | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 350.487700 | 1 |  |
| voice-script-place-story-002 | place_story | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 433.176400 | 1 |  |
| voice-script-place-story-003 | place_story | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 413.792900 | 1 |  |
| voice-script-place-story-004 | place_story | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 409.815200 | 1 |  |
| voice-script-place-story-005 | place_story | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 373.775600 | 1 |  |
| voice-script-relationship-001 | relationship | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 365.834300 | 1 |  |
| voice-script-relationship-002 | relationship | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 406.987500 | 1 |  |
| voice-script-relationship-003 | relationship | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 385.051400 | 1 |  |
| voice-script-relationship-004 | relationship | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 388.485600 | 1 |  |
| voice-script-relationship-005 | relationship | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 354.507000 | 1 |  |
| voice-script-route-context-001 | route_context | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 398.547200 | 1 |  |
| voice-script-route-context-002 | route_context | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 422.297700 | 1 |  |
| voice-script-route-context-003 | route_context | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 447.055300 | 1 |  |
| voice-script-route-context-004 | route_context | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 426.868400 | 1 |  |
| voice-script-route-context-005 | route_context | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 430.466000 | 1 |  |
| voice-script-followup-001 | voice_followup | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 435.650000 | 1 |  |
| voice-script-followup-002 | voice_followup | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 411.395900 | 1 |  |
| voice-script-followup-003 | voice_followup | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 400.392100 | 1 |  |
| voice-script-followup-004 | voice_followup | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 441.662100 | 1 |  |
| voice-script-followup-005 | voice_followup | answer_with_citation | executed | executed | executed_contract_chat | executed | true | 364.092000 | 1 |  |
| voice-script-no-answer-001 | no_answer | abstain | executed | executed | executed_contract_chat | executed | true | 402.389500 | 0 |  |
| voice-script-no-answer-002 | no_answer | abstain | executed | executed | executed_contract_chat | executed | true | 318.947000 | 0 |  |
| voice-script-no-answer-003 | no_answer | abstain | executed | executed | executed_contract_chat | executed | true | 427.148600 | 0 |  |
| voice-script-no-answer-004 | no_answer | abstain | executed | executed | executed_contract_chat | executed | true | 387.812100 | 0 |  |
| voice-script-no-answer-005 | no_answer | abstain | executed | executed | executed_contract_chat | executed | true | 369.550700 | 0 |  |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 36 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
voice_local_e2e_eval_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 30개 public-safe script로 local voice regression gate만 수행했다. |
| stt | CUDA local Whisper 후보를 사용하고 raw transcript 대신 hash와 오류율 metric만 공개한다. |
| chat | `/api/v1/chat` contract-only 경로로 citation과 abstain 계약을 검증한다. |
| tts | Windows SAPI fallback으로 input/output private wav를 생성한다. |
| privacy | raw audio와 raw transcript는 public artifact에 저장하지 않는다. |
| cost | external provider call, external audio transmission, live Solar call은 모두 0이다. |
| data_mart | script-level public summary fact와 private audio fact grain을 분리한다. |
| portfolio | 음성 앱 완성이 아니라 local-first voice regression gate로 설명한다. |
| external_audit | managed provider보다 local 반복 평가 gate를 먼저 고정한 순서는 타당하다. |
| decision | completed_local_voice_e2e_regression |

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_local_e2e_eval_public_summary | e2e_id + script_id + stage + metric_name |
| fact_voice_local_e2e_audio_private | e2e_id + script_id + audio_role + audio_artifact_id |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
