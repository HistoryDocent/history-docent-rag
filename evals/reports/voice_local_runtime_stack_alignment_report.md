# Voice Local Runtime Stack Alignment Report

## 결론

`HD-VOICE-LOCAL-RUNTIME-STACK-ALIGN-001`는 stack lock의 무료 로컬 음성 결정을 실제 runtime/API contract에 반영했는지 검증한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-runtime-stack-alignment-report/v1` |
| alignment_id | `voice-runtime-stack-align-4a90bd10` |
| work_id | `HD-VOICE-LOCAL-RUNTIME-STACK-ALIGN-001` |
| depends_on | `HD-VOICE-LOCAL-FREE-STACK-LOCK-001` |
| generated_at_utc | `2026-05-21T13:00:03+00:00` |
| result_path | `<private artifact: voice_local_runtime_stack_alignment_rows.jsonl>` |
| source_fingerprint | `4a90bd10f5088cd6` |

## 정량 리포트

| metric | value |
| --- | ---: |
| expected_primary_stt_provider_id | `local_faster_whisper_small_cuda` |
| actual_runtime_stt_provider_id | `local_faster_whisper_small_cuda` |
| stt_model_id | `small` |
| stt_runtime_family | `faster-whisper via CTranslate2` |
| runtime_default_transcriber | `FasterWhisperSmallTranscriber` |
| provider_id_mismatch_count | 0 |
| primary_local_stt_candidate_count | 1 |
| primary_local_tts_candidate_count | 0 |
| tts_provider_candidate_id | `local_windows_sapi_pyttsx3_korean_fallback` |
| tts_provider_role | `fallback` |
| tts_provider_status | `fallback_not_quality_candidate` |
| tts_fallback_candidate_count | 1 |
| tts_final_provider_count | 0 |
| runtime_default_faster_whisper_transcriber_count | 1 |
| api_provider_status_field_count | 5 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| alignment_decision | `aligned_local_stt_tts_blocked` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 3 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
voice_local_runtime_stack_alignment_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| backend | runtime 기본 STT provider id와 transcriber 구현이 stack lock 결정과 일치한다. |
| voice_ml | faster-whisper small CUDA는 demo evidence 후보이며 신규 전사 실행은 하지 않았다. |
| product | TTS는 fallback_not_quality_candidate로 노출해 final provider 오해를 줄였다. |
| security | 외부 provider call과 외부 음성 전송은 0이며 public artifact에는 raw audio/transcript가 없다. |
| evaluation | provider id, API field, public safety를 deterministic gate로 고정했다. |
| data_mart | alignment fact grain은 alignment_id + provider_candidate_id + metric_name이다. |
| external_audit | 무료 로컬 TTS final provider claim을 만들지 않은 점이 현재 evidence와 맞다. |
| decision | aligned_local_stt_tts_blocked |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
