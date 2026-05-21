# Voice Local whisper.cpp Deployment Smoke

## 결론

`HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-SMOKE-001`는 `whisper.cpp` local STT 배포 가능성을 확인하는 public-safe smoke gate다.

현재 기본 STT 후보는 `local_faster_whisper_small_cuda`로 유지한다. `whisper.cpp`는 더 가벼운 C/C++ 배포 후보로만 비교하며, runtime과 model이 준비되지 않으면 blocker evidence로 기록한다.

## Scope

포함:

- `whisper-cli` 실행 파일 탐지
- `ggml` model file 탐지
- CUDA 사용 가능 시 `resolved_device=cuda`로 기록
- private wav fixture 기반 STT smoke
- WER, CER, place name accuracy, latency metric 기록
- raw audio, raw transcript, private path public 기록 금지

제외:

- `whisper.cpp` 자동 설치 또는 빌드
- model 자동 다운로드
- 외부 STT/TTS provider 호출
- STT provider 최종 확정

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| whisper_cpp_runtime_available_count | 0 |
| whisper_cpp_model_file_available_count | 0 |
| local_stt_execution_requested_count | 5 |
| local_stt_execution_count | 0 |
| wer_avg | null |
| cer_avg | null |
| place_name_accuracy_avg | null |
| stt_latency_p95_ms | 0.000000 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| resolved_device | `cuda` |
| local_cuda_available_count | 1 |
| runtime_cuda_capability | `not_verified_missing_runtime` |
| recommended_stt_candidate_id | `local_faster_whisper_small_cuda` |
| deployment_decision | `blocked_missing_whispercpp_runtime` |

## Claim Boundary

허용 claim:

- `whisper.cpp` local STT 배포 가능성 smoke gate를 추가했다.
- external provider call과 external audio transmission은 0이다.
- raw audio와 raw transcript는 public artifact에 저장하지 않았다.
- runtime 또는 model 부재 시 이를 blocker로 기록했다.

금지 claim:

- `whisper.cpp`가 production 최종 STT provider라는 주장
- `whisper.cpp` CUDA 실행이 실제로 성공했다는 주장, 성공 row가 없을 때
- STT/TTS 품질 최종 검증 완료
- 실제 관광객 음성 품질 검증 완료
- 음성 관광 앱 완성
