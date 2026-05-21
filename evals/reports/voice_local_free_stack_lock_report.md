# Voice Local Free Stack Lock Report

## 목적

무료 로컬 STT/TTS 우선 전략을 실제 제품 계약으로 고정한다.

이 리포트는 신규 음성 실행 결과가 아니라, 이미 생성된 STT/TTS evidence를 기반으로 default provider 역할과 금지 claim을 고정하는 decision gate다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-free-stack-lock-report/v1` |
| stack_lock_id | `voice-local-free-stack-1b5b8906` |
| generated_at_utc | `2026-05-21T12:48:05.817400+00:00` |
| work_id | `HD-VOICE-LOCAL-FREE-STACK-LOCK-001` |
| depends_on_proxy_eval | `HD-VOICE-LOCAL-TTS-AUTOMATED-PROXY-EVAL-001` |
| depends_on_stt_comparison | `HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001` |
| depends_on_tts_human_decision | `HD-VOICE-LOCAL-TTS-HUMAN-SCORE-DECISION-001` |
| result_path | `<private artifact: voice_local_free_stack_lock_rows.jsonl>` |
| source_fingerprint | `0f7d6dfa16866e1ce8e06b7718a441a1d4282c16197e5963428ec46c1a95c5c1` |

## Provider Rows

| provider_candidate_id | modality | role | status | default_enabled | secret_required | external_audio_default |
| --- | --- | --- | --- | --- | --- | --- |
| `local_faster_whisper_small_cuda` | stt | primary | locked_for_demo | true | false | false |
| `local_sherpa_onnx_supertonic3_ko` | tts | experimental | blocked_missing_human_scores | false | false | false |
| `local_windows_sapi_pyttsx3_korean_fallback` | tts | fallback | fallback_not_quality_candidate | false | false | false |
| `local_melotts_korean` | tts | blocked | blocked_runtime_or_voice | false | false | false |
| `local_piper` | tts | blocked | blocked_runtime_or_voice | false | false | false |
| `managed_azure_ai_speech` | stt_tts | optional_paid_comparison | optional_paid_only | false | true | false |
| `managed_google_cloud_speech_tts` | stt_tts | optional_paid_comparison | optional_paid_only | false | true | false |
| `managed_aws_transcribe_polly` | stt_tts | optional_paid_comparison | optional_paid_only | false | true | false |

## Quantitative Report

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

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 9 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Result

voice_local_free_stack_lock_failures=[]

voice_local_free_stack_lock_blockers=['missing_human_tts_scores', 'tts_proxy_threshold_not_fully_passed']

External audit | PASS

## 해석

STT는 `local_faster_whisper_small_cuda`를 현재 local demo evidence 기준 primary 후보로 잠근다.

TTS는 final provider가 아니다. `local_sherpa_onnx_supertonic3_ko`는 experimental 상태이고, 자동 proxy 4/5 결과와 human score 0건 때문에 채택을 차단한다.

managed provider는 기본값이 아니며, 별도 승인형 optional paid comparison으로만 남긴다.
