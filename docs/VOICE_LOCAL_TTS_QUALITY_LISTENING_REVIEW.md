# Voice Local TTS Quality Listening Review

## 결론

`HD-VOICE-LOCAL-TTS-QUALITY-LISTENING-REVIEW-001`는 무료 로컬 TTS 음성의 청취 평가 기준과 자동 sanity metric을 고정한다.

이번 gate는 사람 청취 평가 완료가 아니다. 사람이 채점할 rubric과 자동 음성 metric만 만든다.

## Scope

| type | item |
| --- | --- |
| include | `sherpa-onnx + Supertonic 3 Korean` private wav 5개 자동 metric |
| include | duration, file size, silence, clipping, sample rate gate |
| include | 사람 청취 평가 rubric template |
| exclude | raw audio public 저장 |
| exclude | raw script text public 저장 |
| exclude | 외부 STT/TTS provider 호출 |
| exclude | 최종 TTS provider 확정 |
| exclude | 음질 우수 검증 완료 claim |

## 정량 요약

| metric | value |
| --- | ---: |
| expected_audio_count | 5 |
| selected_audio_count | 5 |
| audio_file_available_count | 5 |
| audio_metric_row_count | 5 |
| automated_metric_pass_count | 5 |
| automated_metric_fail_count | 0 |
| duration_gate_pass_count | 5 |
| clipping_gate_pass_count | 5 |
| silence_gate_pass_count | 5 |
| sample_rate_gate_pass_count | 5 |
| human_listening_rubric_criterion_count | 6 |
| human_listening_required_count | 5 |
| human_listening_completed_count | 0 |
| human_listening_score_public_artifact_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| review_decision | `automated_audio_sanity_passed_pending_human_review` |

## Human Listening Rubric Template

| criterion_id | label | range | low_anchor | high_anchor |
| --- | --- | --- | --- | --- |
| pronunciation_clarity | 발음 명료도 | 1-5 | 고유명사와 문장 핵심어가 잘 들리지 않는다. | 고유명사와 문장 핵심어가 또렷하게 들린다. |
| korean_naturalness | 한국어 자연스러움 | 1-5 | 억양이나 띄어읽기가 한국어 안내로 부자연스럽다. | 한국어 문장 흐름과 억양이 자연스럽다. |
| docent_tone | 역사 도슨트 톤 | 1-5 | 관광 안내보다 기계 낭독에 가깝다. | 관광 도슨트 안내 톤으로 수용 가능하다. |
| speaking_rate | 말 속도 | 1-5 | 너무 빠르거나 느려서 관광 중 듣기 어렵다. | 이동 중 짧은 안내로 듣기 적절하다. |
| artifact_noise | 잡음/끊김 | 1-5 | 끊김, 왜곡, 잡음이 안내 이해를 방해한다. | 끊김과 잡음이 거의 느껴지지 않는다. |
| tourist_fit | 관광 안내 적합성 | 1-5 | 현장 관광객에게 들려주기 어렵다. | 짧은 현장 안내 음성 후보로 검토 가능하다. |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_audio_metric_public` | `review_id + script_id + metric_name` | public-safe |
| `fact_voice_local_tts_human_score_private` | `review_id + script_id + reviewer_id + criterion_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | local TTS 음성 자동 sanity metric을 기록했다. |
| allowed | 사람 청취 평가 rubric template을 만들었다. |
| allowed | 외부 provider 호출 없이 평가 준비를 완료했다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
