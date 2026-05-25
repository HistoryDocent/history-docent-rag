# Voice Local whisper.cpp Install Strategy

## 결론

`HD-VOICE-LOCAL-WHISPERCPP-INSTALL-STRATEGY-001`은 PASS다.

현재 전략은 `defer_whispercpp_keep_faster_whisper_primary`로 고정한다. 즉, `whisper.cpp` 설치는 지금 실행하지 않고, 이미 local evidence가 있는 `faster-whisper small CUDA`를 STT primary demo 후보로 유지한다.

이 판단은 `whisper.cpp`가 나쁘다는 뜻이 아니다. 현재 로컬 환경에서 source build toolchain이 부족하고, prebuilt binary는 provenance 확인 부담이 있으므로 포트폴리오 마감 기준에서는 설치 실험보다 검증된 baseline 유지가 더 타당하다는 결정이다.

## 작업 단위

| field | value |
| --- | --- |
| `id` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-STRATEGY-001` |
| `depends_on` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-READINESS-001` |
| `scope` | source build, prebuilt binary, skip/keep faster-whisper 3개 전략을 비교하고 하나를 선택 |
| `acceptance_tests` | strategy option count 3, selected strategy 1, provenance recheck required, install execution 0, model download 0 |
| `risk_level` | Low |
| `rollback_plan` | 문서 decision만 revert. 실제 runtime/model 설치나 다운로드는 수행하지 않았으므로 로컬 artifact rollback 없음 |

## 전략 비교

| option | 장점 | 리스크 | 현재 판단 |
| --- | --- | --- | --- |
| `source_build_after_toolchain_ready` | source provenance가 가장 명확하고 CUDA build를 직접 검증할 수 있다. | 현재 `cmake`, `ninja`, MSVC compiler, CUDA compiler가 PATH에서 확인되지 않았다. 설치 준비 시간이 늘어난다. | 보류 |
| `prebuilt_binary_with_provenance_check` | 가장 빠르게 runtime smoke로 넘어갈 수 있다. | binary provenance, checksum, release source, 보안 검토가 필요하다. 출처가 불명확하면 public portfolio에 부적합하다. | 기본 기각 |
| `defer_whispercpp_keep_faster_whisper_primary` | 이미 검증한 `faster-whisper small CUDA` evidence를 유지하고 추가 환경 리스크를 피한다. | `whisper.cpp` 비교 수치는 아직 만들 수 없다. | 채택 |

## 선택 전략

채택 전략:

`defer_whispercpp_keep_faster_whisper_primary`

운영 기준:

- `local_faster_whisper_small_cuda`를 현재 STT primary demo 후보로 유지한다.
- `whisper.cpp`는 optional comparison 후보로 남긴다.
- source build를 하려면 먼저 toolchain을 갖추고, 실행 직전 source URL과 build option을 재확인한다.
- prebuilt binary를 쓰려면 official release, checksum 또는 reproducible source mapping을 확인해야 한다.
- 어떤 경우에도 명시 승인 전에는 runtime build, model download, STT 실행을 하지 않는다.

## 정량 Gate

| metric | value |
| --- | ---: |
| install_strategy_document_count | 1 |
| install_strategy_report_count | 1 |
| regression_test_file_count | 1 |
| prior_readiness_dependency_pass_count | 1 |
| strategy_option_count | 3 |
| selected_strategy_count | 1 |
| selected_keep_faster_whisper_count | 1 |
| selected_source_build_count | 0 |
| selected_prebuilt_binary_count | 0 |
| source_provenance_recheck_required_count | 1 |
| binary_provenance_recheck_required_count | 1 |
| model_provenance_recheck_required_count | 1 |
| toolchain_blocker_retained_count | 1 |
| runtime_build_attempted_count | 0 |
| model_download_attempted_count | 0 |
| local_stt_execution_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| push_command_execution_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| production_voice_app_claim_count | 0 |
| selected_strategy | `defer_whispercpp_keep_faster_whisper_primary` |
| next_explicit_install_gate_required_count | 1 |

## 말해도 되는 문장

- `whisper.cpp` 설치 전략을 비교했고 현재는 설치 보류를 선택했다.
- `faster-whisper small CUDA`를 현재 local STT demo primary 후보로 유지한다.
- `whisper.cpp`는 optional comparison 후보로 남긴다.
- 실제 설치, build, model 다운로드, STT 실행, 외부 provider 호출은 수행하지 않았다.

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
| `id` | `HD-GITHUB-PUSH-EXECUTION-001` |
| `depends_on` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-STRATEGY-001`, `HD-GITHUB-PUSH-EXECUTION-APPROVAL-001` |
| `scope` | 사용자가 `git push 실행 승인`이라고 명시하면 `origin main`에 push하고 push 전후 status를 확인한다. |
| `acceptance_tests` | explicit push approval, pre-push status clean, push execution success, post-push status clean, remote branch updated |
| `risk_level` | Low |
| `rollback_plan` | push 후 문제 발생 시 새 revert commit을 별도 승인 후 만든다. |

대안 작업:

| field | value |
| --- | --- |
| `id` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-EXECUTION-001` |
| `depends_on` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-STRATEGY-001` |
| `scope` | 사용자가 `whisper.cpp 설치 실행 승인`이라고 명시하고 toolchain/provenance 조건을 충족하면 runtime/model 설치와 smoke를 수행한다. |
| `acceptance_tests` | explicit install approval, toolchain/provenance recheck, runtime available 1, model file available 1, local STT execution 5, external provider call 0 |
| `risk_level` | Medium |
| `rollback_plan` | build/model artifact를 별도 승인 후 삭제하고 문서는 blocker 또는 success evidence로 갱신한다. |

## 외부 감사 의견

이 strategy gate는 타당하다. 현재 포트폴리오 제출 목적에서는 검증된 local STT 후보를 유지하는 편이 source build toolchain 보강이나 prebuilt binary 검증보다 리스크가 낮다. 설치를 보류했으므로 성공 claim을 추가하지 않은 점도 적절하다.
