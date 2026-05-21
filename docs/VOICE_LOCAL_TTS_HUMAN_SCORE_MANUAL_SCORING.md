# Voice Local TTS Human Score Manual Scoring

## 결론

`HD-VOICE-LOCAL-TTS-HUMAN-SCORE-MANUAL-SCORING-001`는 무료 로컬 TTS 사람 청취 점수 수동 입력을 위한 private score sheet와 검증 gate를 만든다.

현재 completed score는 `0`건이다. 사람이 실제로 듣고 30건을 채우기 전에는 품질 검증 완료로 보지 않는다.

## Scope

| type | item |
| --- | --- |
| include | private HTML score sheet generation |
| include | private score JSONL draft generation |
| include | manual score input validation |
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
| private_manual_score_sheet_created_count | 1 |
| private_manual_score_draft_created_count | 1 |
| private_manual_score_draft_row_count | 30 |
| private_score_input_available_count | 0 |
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
| manual_scoring_decision | `ready_for_human_manual_scoring` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_human_manual_score_private` | `manual_scoring_id + script_id + reviewer_id + criterion_id` | private |
| `fact_voice_local_tts_human_manual_score_aggregate_public` | `manual_scoring_id + provider_candidate_id + criterion_id` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 사람 청취 점수 수동 입력용 private score sheet를 만들었다. |
| allowed | public에는 criterion aggregate만 공개한다. |
| allowed | 점수 미입력 상태는 manual scoring pending으로 기록한다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
