# Voice Local TTS Human Score Decision

## 결론

`HD-VOICE-LOCAL-TTS-HUMAN-SCORE-DECISION-001`는 무료 로컬 TTS 후보를 사람 청취 점수로 채택, 보류, 탈락, 차단 중 하나로 판정하는 gate다.

현재 decision은 `blocked_missing_human_scores`이다. completed score가 `0`건이므로 30건이 모두 채워지기 전에는 최종 provider 확정으로 보지 않는다.

## Scope

| type | item |
| --- | --- |
| include | private human score completion validation |
| include | provider candidate decision threshold |
| include | public criterion aggregate report |
| exclude | raw audio public 저장 |
| exclude | raw script text public 저장 |
| exclude | individual reviewer score public 공개 |
| exclude | production TTS 품질 보증 |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| rubric_criterion_count | 6 |
| expected_private_score_row_count | 30 |
| private_audio_expected_count | 5 |
| private_audio_available_count | 5 |
| private_audio_missing_count | 0 |
| private_score_input_available_count | 0 |
| private_score_input_row_count | 0 |
| valid_private_score_row_count | 0 |
| invalid_private_score_row_count | 0 |
| completed_score_row_count | 0 |
| pending_score_row_count | 30 |
| completed_script_count | 0 |
| completed_script_rate | 0.000000 |
| reviewer_count | 0 |
| aggregate_public_row_count | 6 |
| provider_decision_public_row_count | 1 |
| overall_score_avg |  |
| criterion_below_accept_threshold_count | 0 |
| criterion_below_reject_threshold_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| human_score_public_detail_row_count | 0 |
| provider_decision | `blocked_missing_human_scores` |

## Decision Threshold

| decision | condition |
| --- | --- |
| `candidate_accepted_for_demo_review` | 30개 score 완료, overall 평균 4.0 이상, 모든 criterion 평균 3.5 이상 |
| `candidate_pending_more_review` | 30개 score 완료지만 채택/탈락 threshold 사이 |
| `candidate_rejected_by_human_scores` | overall 평균 3.0 미만 또는 criterion 평균 2.5 미만 존재 |
| `blocked_*` | 점수, audio, validation, public safety gate 미충족 |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_human_score_decision_private` | `score_decision_id + script_id + reviewer_id + criterion_id` | private |
| `fact_voice_local_tts_human_score_decision_aggregate_public` | `score_decision_id + provider_candidate_id + criterion_id` | public-safe |
| `fact_voice_local_tts_provider_decision_public` | `score_decision_id + provider_candidate_id + decision` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 사람 청취 점수 기반 provider decision gate를 구현했다. |
| allowed | score 미입력 상태에서는 provider 채택을 차단한다. |
| allowed | public에는 criterion aggregate와 decision summary만 공개한다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
