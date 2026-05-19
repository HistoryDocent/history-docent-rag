# Voice Local Runtime Matrix Report

## 결론

`HD-VOICE-STT-TTS-LOCAL-RUNTIME-MATRIX-001`는 무료 로컬 STT/TTS 후보의 runtime preflight 결과다.

이 리포트는 음성 품질 평가가 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-runtime-matrix-report/v1` |
| matrix_id | `voice-local-runtime-matrix-c5-7949b980` |
| work_id | `HD-VOICE-STT-TTS-LOCAL-RUNTIME-MATRIX-001` |
| depends_on | `HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001,HD-VOICE-STT-TTS-LOCAL-TTS-SMOKE-001` |
| generated_at_utc | `2026-05-19T15:06:39+00:00` |
| result_path | `<private artifact: voice_local_runtime_matrix_rows.jsonl>` |
| source_checked_at | `2026-05-20` |
| source_fingerprint | `f1297ee4adcc9b54` |
| resolved_device | `cuda` |
| cuda_device_name | `NVIDIA GeForce RTX 4080 SUPER` |
| matrix_status | `PASS` |

## 정량 리포트

| metric | value |
| --- | ---: |
| runtime_candidate_count | 5 |
| primary_local_stt_candidate_count | 1 |
| existing_local_stt_fallback_count | 1 |
| primary_local_tts_candidate_count | 1 |
| secondary_local_candidate_count | 1 |
| optional_license_review_candidate_count | 1 |
| import_available_candidate_count | 1 |
| missing_runtime_candidate_count | 4 |
| stt_runtime_available_count | 1 |
| tts_runtime_available_count | 0 |
| stt_tts_runtime_available_count | 0 |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| package_install_attempted_count | 0 |
| model_download_attempted_count | 0 |
| model_load_attempted_count | 0 |
| local_stt_execution_count | 0 |
| local_tts_execution_count | 0 |
| private_audio_generated_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| matrix_decision | `ready_for_local_stt_existing_runtime_tts_blocked` |

## Candidate Runtime Rows

| provider_candidate_id | modality | decision | family | import | dist_count | versions | runtime_status | cuda_candidate | next_action |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| local_faster_whisper_cuda | stt | primary_target | faster-whisper | false | 0 | `not_installed` | `runtime_missing` | true | 설치 호환 환경을 분리한 뒤 STT 후보로 재점검한다. |
| local_openai_whisper_cuda_fallback | stt | existing_fallback | openai-whisper | true | 1 | `openai-whisper==20250625` | `runtime_available` | true | 현재 설치된 fallback으로 STT demo는 유지하되 primary 후보는 별도 비교한다. |
| local_melotts_korean | tts | primary_target | MeloTTS | false | 0 | `not_installed` | `runtime_missing` | true | 호환 Python 환경에서 설치를 재시도하고 private wav smoke를 실행한다. |
| local_sherpa_onnx_offline | stt_tts | secondary_target | sherpa-onnx | false | 0 | `not_installed` | `runtime_missing` | false | MeloTTS가 계속 막히면 TTS 대체 후보로 smoke runner를 만든다. |
| local_piper_tts_optional | tts | optional_license_review | Piper | false | 0 | `not_installed` | `runtime_missing_license_review` | false | 배포 라이선스와 한국어 voice availability 확인 전 기본 후보로 채택하지 않는다. |

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
runtime_matrix_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 현재 Python 환경의 import 가능성만 기록했고 설치나 모델 다운로드는 하지 않았다. |
| stt | 기존 openai-whisper runtime은 보이지만 primary faster-whisper runtime은 아직 없다. |
| tts | 현재 TTS runtime 후보는 설치되어 있지 않아 실제 합성 gate는 계속 차단된다. |
| cuda | CUDA preflight 결과 resolved_device=cuda다. |
| security | secret, raw audio, raw transcript, private path를 public artifact에 저장하지 않았다. |
| cost | cloud STT/TTS provider 호출과 외부 음성 전송은 모두 0이다. |
| data_mart | candidate별 runtime fact grain을 matrix_id + provider_candidate_id로 고정했다. |
| portfolio | provider 선택 완료가 아니라 local-first 실행 가능성 점검으로 설명해야 한다. |
| external_audit | managed provider보다 local runtime matrix를 먼저 고정하는 순서는 타당하다. |

## Source Boundary

| provider_candidate_id | source_id |
| --- | --- |
| local_faster_whisper_cuda | faster-whisper-cuda |
| local_openai_whisper_cuda_fallback | openai-whisper-cuda-fallback |
| local_melotts_korean | melotts-korean |
| local_sherpa_onnx_offline | sherpa-onnx-offline |
| local_piper_tts_optional | piper-tts-optional |

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_local_runtime_matrix | matrix_id + provider_candidate_id + metric_name |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
