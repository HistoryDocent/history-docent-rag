# Voice STT/TTS Provider Benchmark Local Smoke Report

## 결론

`HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-LOCAL-001`는 local CUDA Whisper 후보를 external provider 호출 없이 smoke로 검증한다.

이 리포트는 STT/TTS 품질 최종 검증이 아니다. raw audio와 raw transcript는 public artifact에 저장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-stt-tts-local-smoke-report/v1` |
| smoke_id | `voice-local-smoke-tiny-s5-1405fa80` |
| work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-LOCAL-001` |
| depends_on | `HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001` |
| generated_at_utc | `2026-05-19T12:13:59+00:00` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_stt_tts_provider_bench_smoke_local_rows.jsonl>` |
| private_audio_path_alias | `<private artifact: local_smoke_audio>` |
| provider_candidate_id | `local_cuda_whisper` |
| model_id | `tiny` |
| source_fingerprint | `80a800d3883d716b` |
| smoke_status | `completed_local_smoke` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| public_safe_script_fixture_count | 5 |
| local_provider_candidate_count | 1 |
| local_whisper_runtime_available_count | 1 |
| local_tts_generation_requested_count | 5 |
| private_audio_generated_count | 5 |
| audio_fixture_available_count | 5 |
| local_stt_execution_requested_count | 5 |
| local_stt_execution_count | 5 |
| local_cuda_whisper_call_count | 5 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| private_audio_saved_count | 5 |
| raw_transcript_public_artifact_count | 0 |
| raw_audio_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| wer_avg | 0.553333 |
| cer_avg | 0.164183 |
| place_name_accuracy_avg | 0.600000 |
| stt_latency_p50_ms | 83.296100 |
| stt_latency_p95_ms | 651.099660 |
| resolved_device | `cuda` |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Result Row Summary

| script_id | query_type | status | latency_ms | wer | cer | place_name_accuracy | place_count | error_code |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| voice-script-place-fact-001 | place_fact | `executed` | 790.253800 | 1.000000 | 0.466667 | 0.000000 | 1 | `` |
| voice-script-place-fact-002 | place_fact | `executed` | 80.102700 | 0.600000 | 0.066667 | 1.000000 | 1 | `` |
| voice-script-place-fact-003 | place_fact | `executed` | 83.296100 | 0.666667 | 0.176471 | 0.000000 | 2 | `` |
| voice-script-place-fact-004 | place_fact | `executed` | 71.953300 | 0.500000 | 0.111111 | 1.000000 | 1 | `` |
| voice-script-place-fact-005 | place_fact | `executed` | 94.483100 | 0.000000 | 0.000000 | 1.000000 | 1 | `` |

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
local_smoke_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | external provider 호출 없이 local_cuda_whisper 후보만 smoke 대상으로 제한했다. |
| cuda | CUDA 가능 시 사용하며 resolved_device=cuda로 기록했다. |
| metric | WER, CER, place_name_accuracy, latency를 public-safe aggregate로 기록한다. |
| privacy | raw audio는 private artifact이며 public report에는 raw transcript를 저장하지 않는다. |
| cost | managed cloud STT/TTS 호출이 없어 external provider 비용은 발생하지 않는다. |
| data_mart | private script-level fact와 public provider/model summary grain을 분리했다. |
| portfolio | provider 최종 선택이 아니라 local smoke 실행 결과로만 설명한다. |
| external_audit | low-risk local 후보부터 검증하는 순서는 타당하다. |

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_stt_local_smoke_private | smoke_id + script_id + provider_candidate_id + model_id + metric_name |
| fact_voice_stt_local_smoke_public_summary | smoke_id + provider_candidate_id + model_id + metric_name |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
