# Voice Local whisper.cpp Deployment Retry

## 결론

`HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-RETRY-001`은 통과다.

다만 통과 의미는 `whisper.cpp` 실행 성공이 아니다. 현재 환경에서 `whisper-cli` runtime과 `ggml` model file이 여전히 없음을 재확인했고, `whisper.cpp` 후보는 계속 blocker 상태로 둔다. 기본 STT 후보는 `local_faster_whisper_small_cuda`로 유지한다.

## 작업 단위

| field | value |
| --- | --- |
| `id` | `HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-RETRY-001` |
| `depends_on` | `HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-SMOKE-001` |
| `scope` | `whisper.cpp` runtime/model/CUDA 상태 재점검과 blocker evidence 갱신 |
| `acceptance_tests` | runtime probe, model probe, CUDA preflight, no install/download, no external provider call, public-safe report |
| `risk_level` | Low |
| `rollback_plan` | 문서와 테스트 추가분 revert. 설치/다운로드/외부 호출은 수행하지 않았으므로 runtime rollback 없음 |

## 재점검 범위

포함:

- PATH 기반 `whisper-cli`, `whisper-cpp` command 탐지
- repo-local 후보 위치의 `whisper-cli.exe` 탐지
- `ggml-small.bin`, `ggml-base.bin`, `ggml-tiny.bin` model file 존재 여부 탐지
- GPU preflight 결과 기록
- 기존 `HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-SMOKE-001` blocker 유지 여부 판단

제외:

- `whisper.cpp` 자동 clone/build/install
- `ggml` model 자동 다운로드
- private wav fixture STT 실행
- 외부 STT/TTS provider 호출
- 실제 `git push`

## 정량 Gate

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
| package_install_attempted_count | 0 |
| model_download_attempted_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| push_command_execution_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| deployment_decision | `still_blocked_missing_whispercpp_runtime` |
| recommended_stt_candidate_id | `local_faster_whisper_small_cuda` |
| next_gate_install_approval_count | 1 |

## 판단

현재 결과는 기존 blocker를 강화한다.

`whisper.cpp`는 배포성 측면에서 의미 있는 후보지만, 지금 상태에서는 runtime과 model file이 없기 때문에 품질 비교, latency 비교, CUDA 실행 성공을 주장할 수 없다. 취업 포트폴리오에서는 이 결과를 “후보를 무리하게 채택하지 않고 환경 blocker를 명시했다”는 운영 evidence로만 사용한다.

## 말해도 되는 문장

- `whisper.cpp` 배포 후보를 재점검했고, 현재 환경에서는 runtime/model 부재로 실행하지 못했다.
- `whisper.cpp` 관련 설치, 다운로드, 외부 provider 호출은 수행하지 않았다.
- 기본 STT demo 후보는 `local_faster_whisper_small_cuda`로 유지한다.

## 말하면 안 되는 문장

- `whisper.cpp` CUDA 실행 성공
- `whisper.cpp` production STT provider 확정
- `whisper.cpp`가 faster-whisper보다 우수함
- STT/TTS production 품질 검증 완료
- 실제 관광객 음성 품질 검증 완료
- 음성 관광 앱 완성
- GitHub push 완료

## 다음 작업 지시서

| field | value |
| --- | --- |
| `id` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-APPROVAL-001` |
| `depends_on` | `HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-RETRY-001` |
| `scope` | `whisper.cpp` runtime build와 `ggml` model 다운로드를 진행할지 승인 기준을 고정한다. |
| `acceptance_tests` | install/build/download 승인 문구, 예상 디스크 사용량, source URL, checksum 또는 release provenance, CUDA build option, rollback plan |
| `risk_level` | Medium |
| `rollback_plan` | 생성된 runtime/model 파일과 임시 build artifact를 별도 승인 후 삭제한다. public repo에는 binary와 model을 추적하지 않는다. |

## 외부 감사 의견

이 gate는 타당하다. 사용자가 “다음 작업 진행”을 반복했지만, `git push`나 model 다운로드/build는 외부 상태 변경 또는 로컬 환경 변경이므로 별도 승인 없이 실행하지 않았다. 현재는 재점검과 public-safe blocker 리포트 갱신까지만 완료한 상태다.
