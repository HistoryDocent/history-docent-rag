# Voice Local whisper.cpp Deployment Retry Report

## 결론

`HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-RETRY-001`은 PASS다.

현재 환경을 재점검한 결과 `whisper.cpp` runtime과 model file은 여전히 준비되지 않았다. 따라서 `whisper.cpp` 실행은 0건이며, 기본 STT 후보는 `local_faster_whisper_small_cuda`로 유지한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-whispercpp-deployment-retry-report/v1` |
| work_id | `HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-RETRY-001` |
| depends_on | `HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-SMOKE-001` |
| generated_at_utc | `2026-05-25T14:28:27Z` |
| runtime_alias | `not_found` |
| model_path_alias | `not_found` |
| resolved_device | `cuda` |
| deployment_decision | `still_blocked_missing_whispercpp_runtime` |

## 정량 결과

| metric | value |
| --- | ---: |
| retry_document_count | 1 |
| retry_report_count | 1 |
| regression_test_file_count | 1 |
| prior_smoke_dependency_pass_count | 1 |
| path_runtime_command_probe_count | 2 |
| local_runtime_candidate_path_count | 4 |
| whisper_cpp_runtime_available_count | 0 |
| whisper_cpp_model_file_available_count | 0 |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| local_stt_execution_requested_count | 5 |
| local_stt_execution_count | 0 |
| blocked_missing_runtime_count | 5 |
| blocked_missing_model_count | 0 |
| package_install_attempted_count | 0 |
| model_download_attempted_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| push_command_execution_count | 0 |
| wer_avg | null |
| cer_avg | null |
| place_name_accuracy_avg | null |
| stt_latency_p95_ms | 0.000000 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_env_assignment_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| production_voice_app_claim_count | 0 |
| recommended_stt_candidate_id | `local_faster_whisper_small_cuda` |
| next_gate_install_approval_count | 1 |

## 정성 평가

| criterion | result | note |
| --- | --- | --- |
| Dependency | PASS | 기존 whisper.cpp deployment smoke의 blocker를 재점검했다. |
| Runtime | PASS | PATH와 repo-local 후보 경로에서 runtime이 발견되지 않았다. |
| Model | PASS | 후보 `ggml` model file이 발견되지 않았다. |
| CUDA | PASS | GPU preflight는 가능 상태지만 runtime 부재라 CUDA 실행 성공으로 주장하지 않는다. |
| Privacy | PASS | raw audio, raw transcript, private path, secret을 public artifact에 기록하지 않았다. |
| Cost | PASS | 설치, model 다운로드, 외부 STT/TTS provider 호출을 수행하지 않았다. |
| Decision | PASS | `whisper.cpp`를 성급히 채택하지 않고 blocker를 유지했다. |
| External audit | PASS | 실제 환경 변경 없이 재점검 evidence만 추가한 판단은 타당하다. |

## 금지:

- `whisper.cpp` CUDA 실행 성공
- `whisper.cpp` production STT provider 확정
- `whisper.cpp`가 faster-whisper보다 우수함
- STT/TTS production 품질 검증 완료
- 실제 관광객 음성 품질 검증 완료
- 음성 관광 앱 완성
- GitHub push 완료

## Data Mart

`fact_voice_local_whispercpp_deployment_retry` grain은 `retry_id + probe_id + candidate_id + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `retry_id` | `HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-RETRY-001` |
| `probe_id` | runtime_command, runtime_local_path, model_file, cuda_preflight, external_call |
| `candidate_id` | `local_whispercpp_small_cuda` |
| `claim_boundary` | `deployment-retry-blocker-only` |
| `status` | PASS, BLOCKED, WAIT |

금지 필드:

- raw query
- raw answer
- raw evidence
- raw audio
- transcript
- prompt
- chunk text
- private path
- secret

## 다음 Gate

`HD-VOICE-LOCAL-WHISPERCPP-INSTALL-APPROVAL-001`을 권장한다. 설치/build/model 다운로드는 로컬 환경 변경과 대용량 파일 생성을 수반하므로 별도 승인 기준을 먼저 고정한다.

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
