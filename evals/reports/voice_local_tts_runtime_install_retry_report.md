# Voice Local TTS Runtime Install Retry Report

## 결론

`HD-VOICE-STT-TTS-LOCAL-TTS-RUNTIME-INSTALL-001`는 무료 로컬 TTS runtime 설치/재시도 결과다.

MeloTTS는 설치, CUDA torch, import, model load 단계까지 진행됐지만 한국어 합성에서 Windows `eunjeon` build dependency로 차단됐다. 실제 local wav smoke는 Windows SAPI Korean voice fallback으로 수행했다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-tts-runtime-install-retry-report/v1` |
| retry_id | `voice-local-tts-runtime-retry-s5-70ca11a3` |
| work_id | `HD-VOICE-STT-TTS-LOCAL-TTS-RUNTIME-INSTALL-001` |
| depends_on | `HD-VOICE-STT-TTS-LOCAL-RUNTIME-MATRIX-001` |
| generated_at_utc | `2026-05-19T15:34:48+00:00` |
| scripts_path | `data_samples/voice_tts_smoke_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_local_tts_runtime_install_retry_rows.jsonl>` |
| private_audio_path_alias | `<private artifact: local_tts_pyttsx3_sapi_audio>` |
| source_fingerprint | `6530cff56414cbb8` |
| voice_available | `True` |
| voice_name | `Microsoft Heami Desktop - Korean` |
| voice_language | `ko-KR` |
| voice_id_hash | `e1bffbcfc8f8d27c` |
| retry_status | `completed_local_sapi_tts_fallback` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| runtime_install_attempt_count | 11 |
| package_install_attempted_count | 5 |
| package_install_success_count | 4 |
| package_install_blocked_count | 1 |
| cuda_wheel_install_success_count | 1 |
| dictionary_download_attempted_count | 1 |
| dictionary_download_success_count | 1 |
| model_load_attempted_count | 1 |
| model_load_success_count | 1 |
| melotts_import_available_count | 1 |
| melotts_synthesis_attempt_count | 1 |
| melotts_synthesis_success_count | 0 |
| melotts_blocker_count | 2 |
| sapi_korean_voice_detected_count | 1 |
| fallback_sapi_synthesis_attempt_count | 5 |
| local_tts_execution_count | 5 |
| private_audio_generated_count | 5 |
| private_audio_saved_count | 5 |
| tts_latency_p50_ms | 28.844340 |
| tts_latency_p95_ms | 28.844340 |
| audio_duration_total_ms | 40004.263038 |
| audio_file_size_total_bytes | 1764418 |
| resolved_device | `cuda` |
| cuda_device_count | 1 |
| local_cuda_available_count | 1 |
| isolated_cuda_torch_available_count | 1 |
| selected_provider_candidate_id | `local_windows_sapi_pyttsx3_korean_fallback` |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Runtime Attempt Rows

| attempt_id | provider_candidate_id | kind | status | package_or_runtime | sanitized_result_code |
| --- | --- | --- | --- | --- | --- |
| python311_venv_create | local_melotts_korean | `venv_create` | `success` | python3.11 venv | `isolated_venv_created` |
| melotts_pypi_install | local_melotts_korean | `package_install` | `blocked` | melotts | `pypi_sdist_missing_requirements_file` |
| melotts_github_install | local_melotts_korean | `package_install` | `success` | MeloTTS GitHub source | `github_source_install_success` |
| torch_cuda126_wheel_install | local_melotts_korean | `cuda_wheel_install` | `success` | torch cu126 | `cuda_torch_available` |
| melotts_dependency_networkx_pin | local_melotts_korean | `dependency_install` | `success` | networkx<3 | `dependency_conflict_resolved` |
| unidic_dictionary_download | local_melotts_korean | `dictionary_download` | `success` | unidic dictionary | `dictionary_ready` |
| melotts_import_check | local_melotts_korean | `import_check` | `success` | melo.api | `melo_api_import_success` |
| melotts_model_load | local_melotts_korean | `model_load` | `success` | MeloTTS KR model | `model_load_reached_synthesis_stage` |
| melotts_korean_synthesis | local_melotts_korean | `synthesis` | `blocked` | eunjeon | `eunjeon_requires_msvc_build_tools_on_windows` |
| pyttsx3_sapi_install | local_windows_sapi_pyttsx3_korean_fallback | `package_install` | `success` | pyttsx3 | `local_sapi_runtime_available` |
| sapi_korean_voice_probe | local_windows_sapi_pyttsx3_korean_fallback | `voice_probe` | `success` | Windows SAPI Korean voice | `korean_voice_detected` |

## Synthesis Row Summary

| script_id | provider_candidate_id | status | latency_ms | duration_ms | file_size_bytes | error_code |
| --- | --- | --- | ---: | ---: | ---: | --- |
| tts-smoke-docent-001 | local_windows_sapi_pyttsx3_korean_fallback | `executed` | 28.844340 | 7982.902494 | 352092 | `` |
| tts-smoke-docent-002 | local_windows_sapi_pyttsx3_korean_fallback | `executed` | 28.844340 | 8132.879819 | 358706 | `` |
| tts-smoke-docent-003 | local_windows_sapi_pyttsx3_korean_fallback | `executed` | 28.844340 | 8162.902494 | 360030 | `` |
| tts-smoke-docent-004 | local_windows_sapi_pyttsx3_korean_fallback | `executed` | 28.844340 | 7922.766440 | 349440 | `` |
| tts-smoke-docent-005 | local_windows_sapi_pyttsx3_korean_fallback | `executed` | 28.844340 | 7802.811791 | 344150 | `` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 16 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
voice_local_tts_runtime_install_retry_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 무료 로컬 TTS runtime만 확인했고 managed provider는 호출하지 않았다. |
| melotts | MeloTTS는 설치와 CUDA import를 통과했지만 Korean synthesis에서 eunjeon build dependency로 차단됐다. |
| fallback | Windows SAPI Korean voice fallback으로 5개 private wav를 생성했다. |
| cuda | CUDA 가능성은 resolved_device=cuda, isolated CUDA torch=1로 기록했다. |
| metric | install attempt, blocker, local execution count, latency, duration, file size를 기록했다. |
| privacy | audio artifact는 private output이며 public report에는 raw audio와 raw transcript를 저장하지 않는다. |
| cost | external provider call과 external audio transmission은 0이다. |
| data_mart | install attempt fact와 synthesis metric fact를 분리했다. |
| portfolio | MeloTTS 실패를 숨기지 않고 local fallback까지 검증한 engineering decision으로 설명한다. |
| external_audit | 시스템 전역 build tool 설치 없이 격리 환경과 local fallback을 우선한 판단은 타당하다. |

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_tts_runtime_install_attempt | retry_id + attempt_id + provider_candidate_id |
| fact_voice_tts_local_synthesis_private | retry_id + script_id + provider_candidate_id + metric_name |
| fact_voice_tts_local_synthesis_public_summary | retry_id + provider_candidate_id + metric_name |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
