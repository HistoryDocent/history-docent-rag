# Voice Local Runtime Matrix

## 결론

`HD-VOICE-STT-TTS-LOCAL-RUNTIME-MATRIX-001`는 무료 로컬 STT/TTS 후보의 현재 실행 가능성을 기록한다.

이번 gate는 설치, 모델 다운로드, STT/TTS 실행을 하지 않는다.

## 후보 Matrix

| provider_candidate_id | modality | decision | import | runtime_status | next_action |
| --- | --- | --- | --- | --- | --- |
| local_faster_whisper_cuda | stt | primary_target | false | `runtime_missing` | 설치 호환 환경을 분리한 뒤 STT 후보로 재점검한다. |
| local_openai_whisper_cuda_fallback | stt | existing_fallback | true | `runtime_available` | 현재 설치된 fallback으로 STT demo는 유지하되 primary 후보는 별도 비교한다. |
| local_melotts_korean | tts | primary_target | false | `runtime_missing` | 호환 Python 환경에서 설치를 재시도하고 private wav smoke를 실행한다. |
| local_sherpa_onnx_offline | stt_tts | secondary_target | false | `runtime_missing` | MeloTTS가 계속 막히면 TTS 대체 후보로 smoke runner를 만든다. |
| local_piper_tts_optional | tts | optional_license_review | false | `runtime_missing_license_review` | 배포 라이선스와 한국어 voice availability 확인 전 기본 후보로 채택하지 않는다. |

## 정량 요약

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
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| matrix_decision | `ready_for_local_stt_existing_runtime_tts_blocked` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_runtime_matrix` | `matrix_id + provider_candidate_id + metric_name` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 무료 로컬 음성 후보의 runtime preflight를 수행했다. |
| allowed | 외부 provider 호출과 외부 음성 전송은 0으로 유지했다. |
| allowed | CUDA 사용 가능 여부와 후보별 import 가능 여부를 기록했다. |
| forbidden | 무료 로컬 TTS 품질 검증 완료 |
| forbidden | MeloTTS가 최종 provider로 확정 |
| forbidden | faster-whisper가 현재 환경에서 실행 가능 |
| forbidden | production 음성 관광 앱 완성 |
