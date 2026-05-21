# Voice Local TTS Automated Proxy Eval

## 결론

`HD-VOICE-LOCAL-TTS-AUTOMATED-PROXY-EVAL-001`는 사람 청취 점수를 대신 만들지 않고, 로컬 STT round-trip 기반 자동 대체 평가를 기록한다.

현재 decision은 `automated_proxy_failed_quality_threshold`이다. 이 gate는 TTS 음질 최종 판단이나 provider 채택이 아니다.

## Scope

| type | item |
| --- | --- |
| include | `sherpa-onnx + Supertonic 3 Korean` private wav 5개 자동 audio sanity 재사용 |
| include | `faster-whisper small` local STT round-trip proxy |
| include | CER, 문자 precision/recall/F1, sequence similarity, 장소명 복원률 |
| exclude | 사람 청취 점수 생성 |
| exclude | raw audio public 저장 |
| exclude | raw transcript public 저장 |
| exclude | raw script text public 저장 |
| exclude | 외부 STT/TTS provider 호출 |
| exclude | 최종 TTS provider 확정 |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| audio_file_available_count | 5 |
| automated_audio_sanity_pass_count | 5 |
| local_stt_runtime_available_count | 1 |
| local_stt_execution_requested_count | 5 |
| local_stt_execution_count | 5 |
| local_cuda_stt_call_count | 5 |
| cer_avg | 0.032306 |
| char_f1_avg | 0.967694 |
| sequence_similarity_avg | 0.967694 |
| place_name_accuracy_avg | 0.800000 |
| quality_threshold_pass_count | 4 |
| human_listening_completed_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_script_public_artifact_count | 0 |
| proxy_decision | `automated_proxy_failed_quality_threshold` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_proxy_metric_public` | `proxy_eval_id + script_id + metric_name` | public-safe |
| `fact_voice_local_tts_proxy_transcript_private` | `proxy_eval_id + script_id + transcript_artifact_id` | private only |
| `fact_voice_local_tts_human_score_private` | `review_id + script_id + reviewer_id + criterion_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 로컬 STT round-trip 자동 대체 평가를 수행했다. |
| allowed | public에는 hash와 aggregate metric만 저장했다. |
| allowed | 사람 청취 점수는 아직 0건으로 유지한다. |
| forbidden | 사람 청취 점수 입력 완료 |
| forbidden | 자동 proxy가 사람 평가를 대체한다 |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
