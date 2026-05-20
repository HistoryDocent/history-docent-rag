# Voice Local Piper TTS Smoke

## 결론

`HD-VOICE-LOCAL-PIPER-TTS-SMOKE-001`는 무료 로컬 TTS 후보인 Piper를 한국어 도슨트 TTS 후보로 검증한다.

현재 결과는 `piper-tts` runtime은 설치됐지만 공식 voice manifest에서 Korean voice를 찾지 못해 한국어 합성을 진행하지 않는다는 것이다. 따라서 Piper는 현재 Korean TTS 기본 provider가 아니다.

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| piper_runtime_available_count | 1 |
| piper_distribution_installed_count | 1 |
| package_install_attempted_count | 1 |
| voice_manifest_checked_count | 1 |
| manifest_voice_count | 161 |
| manifest_language_count | 49 |
| korean_voice_available_count | 0 |
| model_download_attempted_count | 0 |
| tts_execution_requested_count | 0 |
| local_tts_execution_count | 0 |
| private_audio_generated_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_tts_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| resolved_device | `cuda` |
| local_cuda_available_count | 1 |
| selected_voice_id | `` |
| piper_tts_decision | `blocked_missing_korean_voice` |

## Source Boundary

| source | decision |
| --- | --- |
| `piper_source` | `piper-tts` current package source로 기록 |
| `piper_voice_manifest` | voice manifest 확인 source로 기록 |
| license_policy | piper-tts current package is GPL-3.0-or-later. Voice models require per-voice MODEL_CARD/license review. |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_piper_tts_smoke_public` | `smoke_id + script_id + metric_name` | public-safe |
| `fact_voice_local_piper_tts_artifact_private` | `smoke_id + script_id + audio_artifact_id` | private only |

## Claim Boundary

허용 claim:

- Piper runtime 설치 여부와 공식 voice manifest의 Korean voice 부재를 검증했다.
- external provider call과 external audio transmission은 0이다.
- raw audio와 raw transcript는 public artifact에 저장하지 않았다.

금지 claim:

- Piper가 Korean TTS provider로 채택됐다는 주장
- Piper 한국어 합성 품질 검증 완료
- 무료 로컬 음성 관광 앱 완성
- 실제 관광객 음성 품질 검증 완료
