# Voice Local whisper.cpp Install Approval

## 결론

`HD-VOICE-LOCAL-WHISPERCPP-INSTALL-APPROVAL-001`은 통과다.

이 문서는 `whisper.cpp` runtime build와 `ggml` model 다운로드를 실제로 실행하기 전 승인 기준을 고정한다. 현재 gate에서는 설치, build, model 다운로드, STT 실행, 외부 provider 호출, `git push`를 모두 실행하지 않았다.

## 작업 단위

| field | value |
| --- | --- |
| `id` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-APPROVAL-001` |
| `depends_on` | `HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-RETRY-001` |
| `scope` | `whisper.cpp` 설치/build/model 다운로드 승인 기준 고정 |
| `acceptance_tests` | source URL, model source, CUDA build option, 예상 artifact, rollback plan, public repo 추적 금지, 실행 전 명시 승인 |
| `risk_level` | Medium |
| `rollback_plan` | 생성된 runtime/model/build artifact를 별도 승인 후 삭제한다. public repo에는 binary, model, raw audio를 추적하지 않는다. |

## 승인 기준

실제 실행은 다음 문구 또는 동등한 명시 승인 이후에만 진행한다.

- `whisper.cpp 설치 실행 승인`
- `whisper.cpp 빌드와 모델 다운로드 진행해`
- `ggml 모델 다운로드까지 승인`

불충분한 문구:

- `다음 작업 진행해`
- `좋아 진행해`
- `문서 작업 계속해`

## 실행 전 확인해야 할 source

| item | source |
| --- | --- |
| runtime source | `https://github.com/ggml-org/whisper.cpp` |
| model guidance | `https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md` |

실행 직전에는 source URL, release/tag 또는 commit, Windows CUDA build option, model file provenance를 다시 확인한다.

## 계획된 실행 범위

포함:

- `whisper.cpp` runtime source 확인
- Windows CUDA build 가능성 확인
- `whisper-cli` 또는 동등 CLI 생성
- `ggml-small.bin` 우선 model 확보
- private wav fixture 5개로 local STT smoke 재실행
- WER, CER, place name accuracy, latency 기록

제외:

- public repo에 binary/model 추적
- raw audio 또는 raw transcript 공개
- Azure/Google/AWS STT/TTS 호출
- Solar Pro 3 호출
- 실제 `git push`

## 정량 Gate

| metric | value |
| --- | ---: |
| install_approval_document_count | 1 |
| install_approval_report_count | 1 |
| regression_test_file_count | 1 |
| prior_retry_dependency_pass_count | 1 |
| official_source_url_count | 2 |
| source_recheck_required_count | 1 |
| explicit_install_approval_count | 0 |
| runtime_build_attempted_count | 0 |
| model_download_attempted_count | 0 |
| local_stt_execution_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| binary_model_public_tracking_allowed_count | 0 |
| push_command_execution_count | 0 |
| next_gate_install_execution_count | 1 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| production_voice_app_claim_count | 0 |

## Data Mart Grain

`fact_voice_local_whispercpp_install_approval`의 grain은 `approval_id + approval_check_id + artifact_class + claim_boundary`다.

금지 필드:

- private path
- raw audio
- raw transcript
- model binary content
- build log 원문
- secret

## 말해도 되는 문장

- `whisper.cpp` 설치/build/model 다운로드 전 승인 기준을 고정했다.
- 현재 gate에서는 설치, build, model 다운로드, STT 실행을 하지 않았다.
- 실행 전 source/provenance, artifact, rollback 기준을 다시 확인해야 한다.

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
| `id` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-EXECUTION-001` |
| `depends_on` | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-APPROVAL-001` |
| `scope` | 명시 승인 후 `whisper.cpp` runtime build, `ggml-small.bin` model 확보, 5개 private wav STT smoke 실행 |
| `acceptance_tests` | explicit install approval, runtime available 1, model file available 1, local STT execution 5, external provider call 0, public binary/model tracking 0 |
| `risk_level` | Medium |
| `rollback_plan` | build/model artifact를 별도 승인 후 삭제하고 문서는 blocker 또는 success evidence로 갱신한다. |

## 외부 감사 의견

이 approval gate는 타당하다. `whisper.cpp` build와 model 다운로드는 로컬 환경 변경과 대용량 artifact 생성을 동반할 수 있으므로, 일반적인 다음 작업 진행 요청만으로 실행하면 안 된다.
