# Voice Local whisper.cpp Install Strategy Report

## 결론

`HD-VOICE-LOCAL-WHISPERCPP-INSTALL-STRATEGY-001`은 PASS다.

선택 전략은 `defer_whispercpp_keep_faster_whisper_primary`다. `whisper.cpp` 설치는 지금 실행하지 않고, `faster-whisper small CUDA`를 현재 local STT demo primary 후보로 유지한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-whispercpp-install-strategy-report/v1` |
| work_id | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-STRATEGY-001` |
| depends_on | `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-READINESS-001` |
| generated_at_utc | `2026-05-25T15:30:35Z` |
| selected_strategy | `defer_whispercpp_keep_faster_whisper_primary` |
| runtime_source | `https://github.com/ggml-org/whisper.cpp` |
| model_guidance | `https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md` |

## 정량 결과

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
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| push_command_execution_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_env_assignment_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| production_voice_app_claim_count | 0 |
| next_explicit_install_gate_required_count | 1 |

## 정성 평가

| criterion | result | note |
| --- | --- | --- |
| Dependency | PASS | install readiness 이후 strategy decision으로 이어졌다. |
| Option coverage | PASS | source build, prebuilt binary, keep faster-whisper 3개 선택지를 비교했다. |
| Portfolio risk | PASS | 마감 기준에서는 추가 환경 리스크보다 기존 evidence 유지가 낫다. |
| Runtime/model execution | PASS | runtime build, model download, STT 실행은 모두 0회다. |
| Security | PASS | binary/model을 public repo에 추적하지 않았고 secret/private path를 기록하지 않았다. |
| External audit | PASS | 성공 claim 없이 보류 판단을 남긴 결정은 타당하다. |

## 금지:

- `whisper.cpp` 설치 완료
- `whisper.cpp` CUDA build 완료
- `ggml` model 다운로드 완료
- `whisper.cpp` STT 실행 성공
- `whisper.cpp` production STT provider 확정
- STT/TTS production 품질 검증 완료
- 실제 관광객 음성 품질 검증 완료
- 음성 관광 앱 완성
- GitHub push 완료

## Data Mart

`fact_voice_local_whispercpp_install_strategy` grain은 `strategy_id + option_id + artifact_class + claim_boundary`다.

## 다음 Gate

기본 추천은 `HD-GITHUB-PUSH-EXECUTION-001`이다. 단, 실제 push는 사용자가 `git push 실행 승인`이라고 명시해야 한다.

대안은 `HD-VOICE-LOCAL-WHISPERCPP-INSTALL-EXECUTION-001`이다. 단, 실제 설치는 사용자가 `whisper.cpp 설치 실행 승인`이라고 명시하고 toolchain/provenance 조건을 충족해야 한다.

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
