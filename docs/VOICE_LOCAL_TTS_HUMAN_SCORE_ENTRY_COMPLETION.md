# Voice Local TTS Human Score Entry Completion

## 결론

`HD-VOICE-LOCAL-TTS-HUMAN-SCORE-ENTRY-COMPLETION-001`는 무료 로컬 TTS 사람 청취 점수 입력 완료 여부를 검증한다.

현재 completed score는 `0`건이다. 30건이 모두 채워지기 전에는 품질 검증 완료로 보지 않는다.

## Scope

| type | item |
| --- | --- |
| include | private score input validation |
| include | completion decision gate |
| include | public criterion aggregate report |
| exclude | raw audio public 저장 |
| exclude | raw script text public 저장 |
| exclude | individual reviewer score public 공개 |
| exclude | 최종 TTS provider 확정 |

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
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_script_public_artifact_count | 0 |
| score_completion_decision | `blocked_missing_human_scores` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_human_score_completion_private` | `score_completion_id + script_id + reviewer_id + criterion_id` | private |
| `fact_voice_local_tts_human_score_completion_aggregate_public` | `score_completion_id + provider_candidate_id + criterion_id` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 사람 청취 점수 입력 완료 여부를 검증했다. |
| allowed | public에는 criterion aggregate만 공개한다. |
| allowed | 점수 미완료 상태는 blocker로 기록한다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
