# Voice Local whisper.cpp Deployment Smoke Report

## 결론

`HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-SMOKE-001`는 `whisper.cpp` local STT 배포 가능성을 점검한 public-safe report다.

이 리포트는 STT provider 최종 선택이나 production 품질 검증이 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-whispercpp-deployment-smoke-report/v1` |
| smoke_id | `voice-local-whispercpp-s5-afb2aebe` |
| work_id | `HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-SMOKE-001` |
| depends_on | `HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001` |
| local_first_depends_on | `HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001` |
| generated_at_utc | `2026-05-21T11:09:45+00:00` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| baseline_report_path | `evals/reports/voice_local_faster_whisper_stt_comparison_report.md` |
| private_audio_path_alias | `<private artifact: local_smoke_audio>` |
| private_transcript_path_alias | `<private artifact: voice_local_whispercpp_transcripts>` |
| result_path | `<private artifact: voice_local_whispercpp_deployment_smoke_rows.jsonl>` |
| runtime_alias | `not_found` |
| model_path_alias | `not_found` |
| source_fingerprint | `b3602424b01662e0` |
| deployment_decision | `blocked_missing_whispercpp_runtime` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| provider_candidate_count | 1 |
| whisper_cpp_runtime_available_count | 0 |
| whisper_cpp_model_file_available_count | 0 |
| local_stt_execution_requested_count | 5 |
| local_stt_execution_count | 0 |
| blocked_missing_runtime_count | 5 |
| blocked_missing_model_count | 0 |
| blocked_missing_audio_count | 0 |
| blocked_runtime_error_count | 0 |
| package_install_attempted_count | 0 |
| model_download_attempted_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| resolved_device | `cuda` |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| cuda_runtime_probe_error_count | 0 |
| runtime_cuda_capability | `not_verified_missing_runtime` |
| wer_avg | null |
| cer_avg | null |
| place_name_accuracy_avg | null |
| stt_latency_p50_ms | 0.000000 |
| stt_latency_p95_ms | 0.000000 |
| baseline_execution_count | 5 |
| baseline_cer_avg | 0.026667 |
| baseline_latency_p95_ms | 327.688120 |
| cer_delta_baseline_minus_whisper_cpp | null |
| latency_p95_delta_whisper_cpp_minus_baseline_ms | null |
| recommended_stt_candidate_id | `local_faster_whisper_small_cuda` |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Result Row Summary

| provider_candidate_id | script_id | status | latency_ms | wer | cer | place_acc | error_code |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| local_whispercpp_small_cuda | voice-script-place-fact-001 | `blocked_missing_runtime` | 0.000000 | null | null | null | `whisper_cpp_cli_not_available` |
| local_whispercpp_small_cuda | voice-script-place-fact-002 | `blocked_missing_runtime` | 0.000000 | null | null | null | `whisper_cpp_cli_not_available` |
| local_whispercpp_small_cuda | voice-script-place-fact-003 | `blocked_missing_runtime` | 0.000000 | null | null | null | `whisper_cpp_cli_not_available` |
| local_whispercpp_small_cuda | voice-script-place-fact-004 | `blocked_missing_runtime` | 0.000000 | null | null | null | `whisper_cpp_cli_not_available` |
| local_whispercpp_small_cuda | voice-script-place-fact-005 | `blocked_missing_runtime` | 0.000000 | null | null | null | `whisper_cpp_cli_not_available` |

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
whispercpp_deployment_smoke_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | whisper.cpp를 무료 로컬 STT 배포 후보로만 점검했다. |
| runtime | 현재 runner는 whisper.cpp를 설치하지 않고 실행 파일과 model file 존재 여부를 기록한다. |
| cuda | CUDA 가능 시 resolved_device=cuda로 기록하되, 성공 row가 없으면 runtime CUDA 성공으로 주장하지 않는다. 현재 not_verified_missing_runtime. |
| baseline | 비교 기준은 기존 local_faster_whisper_small_cuda report이며, 현재 추천 STT 후보는 local_faster_whisper_small_cuda다. |
| privacy | raw audio, raw transcript, private path, secret은 public artifact에 저장하지 않았다. |
| cost | cloud STT/TTS provider 호출과 외부 음성 전송은 모두 0이다. |
| data_mart | fact grain은 smoke_id + provider_candidate_id + script_id로 고정했다. |
| portfolio | 가벼운 C/C++ 로컬 STT 배포 후보를 검증했다는 evidence로만 사용한다. |
| external_audit | runtime/model 부재를 실패로 숨기지 않고 blocker로 기록한 판단은 타당하다. |
| decision | blocked_missing_whispercpp_runtime |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
