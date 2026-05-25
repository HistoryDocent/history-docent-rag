# Voice Local whisper.cpp Install Readiness

## 결론

`HD-VOICE-LOCAL-WHISPERCPP-INSTALL-READINESS-001`은 PASS다.

단, PASS 의미는 설치 가능 확정이 아니다. 현재 환경을 읽기 전용으로 점검한 결과 GPU는 확인됐지만 source build에 필요한 toolchain 일부가 PATH에서 발견되지 않았다. 따라서 `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-EXECUTION-001`은 바로 실행하지 않고, 다음 단계에서 source build와 prebuilt binary 중 어떤 전략을 쓸지 결정해야 한다.

## 작업 단위

| field | value |
| --- | --- |
| `id` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-READINESS-001` |
| `depends_on` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-APPROVAL-001` |
| `scope` | `whisper.cpp` 설치 실행 전 로컬 toolchain, GPU, runtime/model 상태를 읽기 전용으로 점검 |
| `acceptance_tests` | command probe, GPU probe, runtime/model probe, no install/download/build, no external provider call, public-safe report |
| `risk_level` | Low |
| `rollback_plan` | 문서와 테스트 추가분 revert. 로컬 환경 변경은 수행하지 않았으므로 runtime rollback 없음 |

## Read-only 점검 결과

| item | result |
| --- | --- |
| `git` | available |
| `curl` | available |
| `nvidia-smi` | available |
| GPU | `NVIDIA GeForce RTX 4080 SUPER` |
| `cmake` | not found |
| `ninja` | not found |
| MSVC `cl` | not found |
| CUDA `nvcc` | not found |
| local `whisper-cli` 후보 | not found |
| local `ggml` model 후보 | not found |

## 판단

현재 환경은 CUDA GPU 자체는 있으나 source build 준비 상태는 아니다. 특히 `cmake`, MSVC compiler, CUDA compiler가 PATH에서 확인되지 않았으므로 바로 CUDA build를 시도하면 실패 가능성이 높다.

따라서 다음 선택지는 둘 중 하나다.

- source build 전략: Visual Studio Build Tools, CMake, CUDA toolkit 확인 후 build한다.
- prebuilt binary 전략: 공식 release 또는 검증 가능한 binary provenance를 확인하고 model만 별도 확보한다.

## 정량 Gate

| metric | value |
| --- | ---: |
| install_readiness_document_count | 1 |
| install_readiness_report_count | 1 |
| regression_test_file_count | 1 |
| prior_install_approval_dependency_pass_count | 1 |
| toolchain_probe_command_count | 7 |
| available_tool_command_count | 3 |
| missing_build_tool_command_count | 4 |
| gpu_probe_available_count | 1 |
| cuda_gpu_detected_count | 1 |
| cuda_compiler_available_count | 0 |
| msvc_compiler_available_count | 0 |
| cmake_available_count | 0 |
| ninja_available_count | 0 |
| whisper_cpp_runtime_available_count | 0 |
| whisper_cpp_model_file_available_count | 0 |
| runtime_build_attempted_count | 0 |
| model_download_attempted_count | 0 |
| local_stt_execution_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| push_command_execution_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| readiness_decision | `blocked_source_build_toolchain_missing` |
| next_gate_strategy_decision_count | 1 |

## 말해도 되는 문장

- `whisper.cpp` 설치 실행 전 toolchain readiness를 읽기 전용으로 점검했다.
- GPU는 확인됐지만 source build toolchain 일부가 PATH에서 확인되지 않았다.
- 설치, build, model 다운로드, STT 실행, 외부 provider 호출은 수행하지 않았다.

## 말하면 안 되는 문장

- `whisper.cpp` 설치 완료
- `whisper.cpp` CUDA build 완료
- `ggml` model 다운로드 완료
- `whisper.cpp` STT 실행 성공
- `whisper.cpp` production STT provider 확정
- STT/TTS production 품질 검증 완료
- 실제 관광객 음성 품질 검증 완료
- 음성 관광 앱 완성
- GitHub push 완료

## 다음 작업 지시서

| field | value |
| --- | --- |
| `id` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-STRATEGY-001` |
| `depends_on` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-READINESS-001` |
| `scope` | source build, prebuilt binary, skip/keep faster-whisper 중 하나를 선택하는 install strategy decision을 작성한다. |
| `acceptance_tests` | strategy option count 3, selected strategy 1, source/provenance check required, install execution count 0, model download count 0 |
| `risk_level` | Low |
| `rollback_plan` | 문서 decision만 revert. 실제 설치나 다운로드는 별도 명시 승인 전까지 수행하지 않는다. |

## 외부 감사 의견

이 readiness gate는 타당하다. 일반적인 다음 작업 진행 요청만으로 build/download를 실행하지 않았고, 현재 source build blocker를 숨기지 않고 기록했다.
