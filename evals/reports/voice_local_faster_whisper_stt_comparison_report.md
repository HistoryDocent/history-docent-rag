# Voice Local Faster Whisper STT Comparison Report

## 결론

`HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001`는 `openai-whisper small CUDA`와 `faster-whisper small CUDA`를 같은 fixture로 비교한 local-only STT 리포트다.

이 리포트는 STT provider 최종 선택이나 production 품질 검증이 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-faster-whisper-stt-comparison-report/v1` |
| comparison_id | `voice-faster-whisper-stt-cmp-s5-f2033f70` |
| work_id | `HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001` |
| depends_on | `HD-VOICE-LOCAL-FREE-STT-TTS-BENCH-V2-001` |
| generated_at_utc | `2026-05-20T11:22:54+00:00` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| baseline_report_path | `evals/reports/voice_stt_tts_local_model_ablation_report.md` |
| private_audio_path_alias | `<private artifact: local_smoke_audio>` |
| result_path | `<private artifact: voice_local_faster_whisper_stt_comparison_rows.jsonl>` |
| source_fingerprint | `cd551b5437ced6d0` |
| comparison_decision | `completed_faster_whisper_comparison` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| baseline_provider_count | 1 |
| faster_whisper_provider_count | 1 |
| baseline_execution_count | 5 |
| faster_whisper_execution_count | 5 |
| paired_script_count | 5 |
| faster_whisper_runtime_available_count | 1 |
| package_install_attempted_count | 1 |
| model_download_attempted_count | 1 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| resolved_device | `cuda` |
| compute_type | `float16` |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| baseline_cer_avg | 0.053333 |
| faster_whisper_cer_avg | 0.026667 |
| cer_delta_baseline_minus_faster | 0.026666 |
| place_accuracy_delta_faster_minus_baseline | 0.200000 |
| latency_p95_delta_faster_minus_baseline_ms | -32.924440 |
| recommended_stt_candidate_id | `local_faster_whisper_small_cuda` |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Provider Summary

| provider_candidate_id | executed | load_ms | wer_avg | cer_avg | place_acc_avg | latency_p95_ms | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| local_openai_whisper_small_cuda_current | 5 | 0.000000 | 0.080000 | 0.053333 | 0.800000 | 360.612560 | `kept_as_comparison_candidate` |
| local_faster_whisper_small_cuda | 5 | 2006.830700 | 0.040000 | 0.026667 | 1.000000 | 327.688120 | `recommended_current` |

## Result Row Summary

| provider_candidate_id | script_id | status | latency_ms | wer | cer | place_acc | error_code |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| local_openai_whisper_small_cuda_current | voice-script-place-fact-001 | `baseline_report_row` | 348.013400 | 0.400000 | 0.266667 | 0.000000 | `` |
| local_openai_whisper_small_cuda_current | voice-script-place-fact-002 | `baseline_report_row` | 275.962600 | 0.000000 | 0.000000 | 1.000000 | `` |
| local_openai_whisper_small_cuda_current | voice-script-place-fact-003 | `baseline_report_row` | 362.916000 | 0.000000 | 0.000000 | 1.000000 | `` |
| local_openai_whisper_small_cuda_current | voice-script-place-fact-004 | `baseline_report_row` | 298.581900 | 0.000000 | 0.000000 | 1.000000 | `` |
| local_openai_whisper_small_cuda_current | voice-script-place-fact-005 | `baseline_report_row` | 351.398800 | 0.000000 | 0.000000 | 1.000000 | `` |
| local_faster_whisper_small_cuda | voice-script-place-fact-001 | `executed` | 345.163700 | 0.200000 | 0.133333 | 1.000000 | `` |
| local_faster_whisper_small_cuda | voice-script-place-fact-002 | `executed` | 193.004400 | 0.000000 | 0.000000 | 1.000000 | `` |
| local_faster_whisper_small_cuda | voice-script-place-fact-003 | `executed` | 257.785800 | 0.000000 | 0.000000 | 1.000000 | `` |
| local_faster_whisper_small_cuda | voice-script-place-fact-004 | `executed` | 233.275600 | 0.000000 | 0.000000 | 1.000000 | `` |
| local_faster_whisper_small_cuda | voice-script-place-fact-005 | `executed` | 225.953700 | 0.000000 | 0.000000 | 1.000000 | `` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 10 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
faster_whisper_comparison_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 무료 로컬 STT 후보 2개를 같은 5개 private wav fixture로 비교했다. |
| baseline | openai-whisper small CUDA metric은 기존 local model ablation report를 기준으로 삼았다. |
| candidate | faster-whisper small은 CTranslate2 기반 로컬 후보로 실행 가능성을 검증했다. |
| cuda | CUDA 가능 시 사용하며 resolved_device=cuda로 기록했다. |
| privacy | raw audio와 raw transcript는 public artifact에 저장하지 않았다. |
| cost | cloud STT/TTS provider 호출과 외부 음성 전송은 모두 0이다. |
| data_mart | candidate/script metric row와 provider summary grain을 분리했다. |
| portfolio | 로컬 GPU STT 후보를 정량 비교해 채택/보류 근거를 남기는 evidence로 사용한다. |
| external_audit | faster-whisper를 바로 최종 provider로 주장하지 않고 baseline 비교로 제한한 판단은 타당하다. |
| decision | completed_faster_whisper_comparison |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
