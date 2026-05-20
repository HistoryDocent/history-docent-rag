# Voice STT/TTS Local Adapter Integration Report

## 결론

`HD-VOICE-STT-TTS-LOCAL-ADAPTER-INTEGRATION-001`는 무료 로컬 STT/TTS 우선 전략을 local adapter smoke로 연결했다.

STT는 local Whisper 후보와 CUDA 가용성을 기록하고, chat은 `/api/v1/chat` contract-only 경로로 실행하며, TTS는 Windows SAPI Korean fallback으로 private wav를 생성한다. 외부 provider 호출은 0이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-stt-tts-local-adapter-integration-report/v1` |
| integration_id | `voice-local-adapter-s5-5d691da5` |
| work_id | `HD-VOICE-STT-TTS-LOCAL-ADAPTER-INTEGRATION-001` |
| depends_on | `HD-VOICE-STT-TTS-LOCAL-TTS-RUNTIME-INSTALL-001` |
| generated_at_utc | `2026-05-20T10:09:20+00:00` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_stt_tts_local_adapter_integration_rows.jsonl>` |
| private_stt_audio_path_alias | `<private artifact: local_smoke_audio>` |
| private_tts_audio_path_alias | `<private artifact: local_adapter_sapi_audio>` |
| source_fingerprint | `e7cf08dbbf7ba9e8` |
| integration_decision | `completed_local_voice_adapter_smoke` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| local_voice_adapter_module_count | 1 |
| local_stt_runtime_available_count | 1 |
| local_stt_execution_count | 5 |
| local_cuda_whisper_call_count | 5 |
| local_tts_execution_count | 5 |
| private_tts_audio_generated_count | 5 |
| chat_contract_execution_count | 5 |
| citation_response_count | 5 |
| stt_wer_avg | 0.080000 |
| stt_cer_avg | 0.053333 |
| stt_place_name_accuracy_avg | 0.800000 |
| stt_latency_p95_ms | 1154.533780 |
| chat_latency_p95_ms | 1.312780 |
| tts_latency_p95_ms | 170.331560 |
| voice_round_trip_latency_p95_ms | 1323.607100 |
| audio_duration_total_ms | 48138.548755 |
| audio_file_size_total_bytes | 2123140 |
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

## Row Summary

| script_id | stt_status | transcript_source | chat_status | tts_status | round_trip_latency_ms | citation_count | error_code |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| voice-script-place-fact-001 | executed | local_whisper | executed_contract_chat | executed | 1530.516400 | 1 |  |
| voice-script-place-fact-002 | executed | local_whisper | executed_contract_chat | executed | 408.476700 | 1 |  |
| voice-script-place-fact-003 | executed | local_whisper | executed_contract_chat | executed | 495.969900 | 1 |  |
| voice-script-place-fact-004 | executed | local_whisper | executed_contract_chat | executed | 412.000700 | 1 |  |
| voice-script-place-fact-005 | executed | local_whisper | executed_contract_chat | executed | 461.798100 | 1 |  |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 5 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
voice_stt_tts_local_adapter_integration_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 무료 로컬 STT/TTS adapter smoke만 수행했고 managed provider는 호출하지 않았다. |
| stt | local Whisper 후보와 CUDA 가용성을 기록하고, 실행 시 transcript hash와 WER/CER만 공개한다. |
| chat | `/api/v1/chat` contract-only 경로로 spoken_answer를 생성해 voice adapter 입력으로 연결했다. |
| tts | Windows SAPI Korean fallback으로 spoken_answer private wav 생성을 수행한다. |
| privacy | raw audio와 raw transcript는 public artifact에 저장하지 않는다. |
| metric | STT, chat, TTS, round-trip latency와 citation count를 분리 기록한다. |
| cost | external provider call, external audio transmission, live Solar call은 모두 0이다. |
| data_mart | adapter smoke fact와 private audio fact grain을 분리했다. |
| portfolio | 음성 앱 완성이 아니라 local voice adapter integration smoke로 설명한다. |
| external_audit | managed provider보다 실행 가능한 local adapter 연결을 먼저 고정한 순서는 타당하다. |
| decision | completed_local_voice_adapter_smoke |

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_local_adapter_smoke | integration_id + script_id + provider_candidate_id + metric_name |
| fact_voice_local_audio_private | integration_id + script_id + audio_artifact_id |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
