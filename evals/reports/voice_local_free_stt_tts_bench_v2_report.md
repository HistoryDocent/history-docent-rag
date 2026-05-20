# Voice Local Free STT/TTS Bench v2 Report

## 결론

`HD-VOICE-LOCAL-FREE-STT-TTS-BENCH-V2-001`는 무료 로컬 STT/TTS 우선 전략의 current baseline과 next target을 분리한 평가 리포트다.

이 리포트는 새 외부 호출, 패키지 설치, 모델 다운로드 없이 기존 실행 evidence와 runtime preflight를 집계한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-free-stt-tts-bench-v2-report/v1` |
| bench_id | `voice-local-free-bench-v2-c6-52e8c214` |
| work_id | `HD-VOICE-LOCAL-FREE-STT-TTS-BENCH-V2-001` |
| depends_on | `HD-VOICE-LOCAL-RUNTIME-CONTRACT-001` |
| generated_at_utc | `2026-05-20T11:06:40+00:00` |
| result_path | `<private artifact: voice_local_free_stt_tts_bench_v2_rows.jsonl>` |
| local_model_ablation_report_path | `evals/reports/voice_stt_tts_local_model_ablation_report.md` |
| local_e2e_report_path | `evals/reports/voice_local_e2e_eval_report.md` |
| local_tts_install_report_path | `evals/reports/voice_local_tts_runtime_install_retry_report.md` |
| source_checked_at | `2026-05-20` |
| source_fingerprint | `ec867235814ee636` |
| resolved_device | `cuda` |
| cuda_device_name | `NVIDIA GeForce RTX 4080 SUPER` |
| bench_status | `PASS` |

## 정량 리포트

| metric | value |
| --- | ---: |
| candidate_count | 6 |
| stt_candidate_count | 3 |
| tts_candidate_count | 3 |
| current_stt_benchmarked_count | 1 |
| current_tts_benchmarked_count | 1 |
| target_next_candidate_count | 2 |
| missing_runtime_candidate_count | 2 |
| license_review_candidate_count | 1 |
| blocked_dependency_candidate_count | 1 |
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
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| recommended_current_stt_candidate_id | `local_openai_whisper_small_cuda_current` |
| recommended_current_tts_candidate_id | `local_windows_sapi_pyttsx3_korean_fallback` |
| next_stt_candidate_id | `local_faster_whisper_cuda_target` |
| next_tts_candidate_id | `local_piper_tts_target` |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| bench_decision | `local_first_current_baseline_ready_next_targets_pending` |

## Candidate Rows

| provider_candidate_id | modality | role | family | import | cli | runtime_status | exec | wer | cer | place_acc | latency_p95_ms | synth_success | next_action |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| local_openai_whisper_small_cuda_current | stt | current_stt_baseline | openai-whisper | true | false | `benchmarked_current` | 5 | 0.080000 | 0.053333 | 0.800000 | 360.612560 | 0 | 현재 무료 로컬 STT baseline으로 유지하고 faster-whisper와 같은 조건에서 재비교한다. |
| local_faster_whisper_cuda_target | stt | target_stt_next | faster-whisper | false | false | `runtime_missing` | 0 | null | null | null | null | 0 | 별도 승인 후 설치/모델 cache를 고정하고 small 또는 distil-large-v3를 실행 비교한다. |
| local_whisper_cpp_cuda_deploy_candidate | stt | deployment_stt_candidate | whisper.cpp | false | false | `runtime_missing` | 0 | null | null | null | null | 0 | Python API baseline 이후 Windows 배포성 후보로 CLI smoke를 검토한다. |
| local_windows_sapi_pyttsx3_korean_fallback | tts | current_tts_fallback | Windows SAPI via pyttsx3 | true | false | `benchmarked_current` | 30 | null | null | null | 98.918350 | 30 | 무료 로컬 TTS target이 준비될 때까지 fallback으로만 유지한다. |
| local_piper_tts_target | tts | target_tts_next | Piper | false | false | `license_review_required` | 0 | null | null | null | null | 0 | 한국어 voice availability와 license를 확인한 뒤 private wav smoke를 실행한다. |
| local_melotts_korean_blocked | tts | blocked_tts_candidate | MeloTTS | false | false | `blocked_dependency` | 0 | null | null | null | null | 0 | optional Windows dependency fix로 분리하고 기본 TTS target에서 제외한다. |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 6 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
free_local_voice_bench_v2_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 무료 로컬 STT/TTS 후보를 current baseline과 next target으로 분리했다. |
| stt | 현재 실행 evidence는 openai-whisper small CUDA이며 faster-whisper는 다음 target이다. |
| tts | 현재 실행 evidence는 Windows SAPI fallback이며 Piper는 license/voice 확인 후 다음 target이다. |
| cuda | CUDA preflight 결과 resolved_device=cuda다. |
| security | raw audio, raw transcript, secret, private path를 public artifact에 저장하지 않았다. |
| cost | cloud STT/TTS provider 호출과 외부 음성 전송은 모두 0이다. |
| data_mart | candidate grain은 bench_id + provider_candidate_id + metric_name으로 고정했다. |
| portfolio | GPU local-first 전략과 후보 기각/보류 근거를 설명하는 evidence로 사용한다. |
| external_audit | 현재 baseline과 다음 target을 혼동하지 않도록 claim boundary를 분리한 판단은 타당하다. |
| decision | local_first_current_baseline_ready_next_targets_pending |

## Source Boundary

| provider_candidate_id | source_id |
| --- | --- |
| local_openai_whisper_small_cuda_current | openai-whisper-small-cuda-current |
| local_faster_whisper_cuda_target | faster-whisper-cuda-target |
| local_whisper_cpp_cuda_deploy_candidate | whisper-cpp-cuda-deploy-candidate |
| local_windows_sapi_pyttsx3_korean_fallback | windows-sapi-pyttsx3-korean-fallback |
| local_piper_tts_target | piper-tts-target |
| local_melotts_korean_blocked | melotts-korean-blocked |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
