# Voice Local Free Stack Lock

## 결론

`HD-VOICE-LOCAL-FREE-STACK-LOCK-001`의 결론은 무료 로컬 STT/TTS 우선 전략을 제품 계약으로 고정하되, TTS 최종 provider는 아직 채택하지 않는 것이다.

STT는 `local_faster_whisper_small_cuda`를 현재 demo evidence 기준 primary 후보로 둔다. TTS는 `sherpa-onnx Supertonic 3 Korean` smoke와 자동 proxy가 있지만 threshold 4/5이고 사람 청취 점수는 0건이므로 최종 provider가 아니다.

## Scope

| include/exclude | 내용 |
| --- | --- |
| include | local-first voice stack decision contract |
| include | primary STT, experimental TTS, fallback TTS, blocked TTS, optional paid provider 역할 분리 |
| include | public-safe 정량/정성 평가 리포트 |
| exclude | 신규 음성 합성/전사 실행 |
| exclude | TTS 최종 채택 |
| exclude | managed STT/TTS provider 호출 |

## Provider Lock

| provider_candidate_id | modality | role | status | default_enabled | secret_required |
| --- | --- | --- | --- | --- | --- |
| `local_faster_whisper_small_cuda` | stt | primary | locked_for_demo | true | false |
| `local_sherpa_onnx_supertonic3_ko` | tts | experimental | blocked_missing_human_scores | false | false |
| `local_windows_sapi_pyttsx3_korean_fallback` | tts | fallback | fallback_not_quality_candidate | false | false |
| `local_melotts_korean` | tts | blocked | blocked_runtime_or_voice | false | false |
| `local_piper` | tts | blocked | blocked_runtime_or_voice | false | false |
| `managed_azure_ai_speech` | stt_tts | optional_paid_comparison | optional_paid_only | false | true |
| `managed_google_cloud_speech_tts` | stt_tts | optional_paid_comparison | optional_paid_only | false | true |
| `managed_aws_transcribe_polly` | stt_tts | optional_paid_comparison | optional_paid_only | false | true |

## Quantitative Gate

| metric | value |
| --- | ---: |
| provider_candidate_count | 8 |
| primary_local_stt_candidate_count | 1 |
| primary_local_tts_candidate_count | 0 |
| experimental_local_tts_candidate_count | 1 |
| fallback_local_tts_candidate_count | 1 |
| blocked_local_tts_candidate_count | 2 |
| optional_paid_provider_candidate_count | 3 |
| managed_provider_default_count | 0 |
| default_external_audio_transmission_count | 0 |
| secret_required_for_default_voice_count | 0 |
| local_stt_locked_count | 1 |
| local_tts_final_provider_claim_count | 0 |
| tts_automated_proxy_execution_count | 5 |
| tts_automated_proxy_pass_count | 4 |
| tts_automated_proxy_fail_count | 1 |
| tts_human_listening_completed_count | 0 |
| human_score_required_for_tts_adoption_count | 1 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_script_public_artifact_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| stack_decision | `locked_local_stt_tts_blocked` |

## Qualitative Assessment

| 담당 관점 | 판단 |
| --- | --- |
| 제품 | 무료 로컬 음성을 기본 방향으로 유지하되 TTS 최종 채택은 차단한다. |
| 음성 ML | STT는 faster-whisper small CUDA 후보를 유지하고, TTS는 사람 청취 점수 전까지 experimental이다. |
| 백엔드 | voice API 기본 contract는 text-first를 유지하고 provider status를 명시한다. |
| 보안 | 기본 경로에서 secret과 외부 음성 전송은 필요하지 않다. |
| Evaluation | proxy pass 4/5와 human score 0건을 분리 기록한다. |
| Data warehouse | fact grain은 stack_lock_id + provider_candidate_id + role + metric_name으로 둔다. |
| 외부 감사 | TTS를 채택하지 않고 STT만 lock한 판단은 현재 evidence와 일치한다. |

## Claim Boundary

허용 claim:

- 무료 로컬 음성 전략을 기본 방향으로 고정했다.
- STT는 `faster-whisper small CUDA`를 현재 demo evidence 기준 primary 후보로 둔다.
- TTS는 아직 final provider가 없다.
- `sherpa-onnx Supertonic 3 Korean`은 experimental TTS 후보이며 사람 청취 점수가 필요하다.
- managed provider는 optional paid comparison으로만 유지한다.

금지 claim:

- 무료 로컬 TTS 최종 provider 확정
- Supertonic 3 음성 품질 우수 검증 완료
- 자동 proxy가 사람 평가를 대체한다
- 실제 관광객 음성 품질 검증 완료
- production 음성 관광 앱 완성
- external provider 없이 모든 음성 기능 production-ready

## Next Gate

다음 구현 gate는 둘 중 하나만 선택한다.

1. 사람 청취 점수 30행을 실제로 입력한 뒤 TTS provider decision을 재실행한다.
2. TTS 채택 없이 `faster-whisper` STT만 local demo path에 제한적으로 연결한다.

현 상태에서는 TTS playback을 포트폴리오 필수 기능으로 주장하지 않는다.
