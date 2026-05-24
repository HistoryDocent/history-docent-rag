# Voice Local TTS Human Score Collection

## 결론

`HD-VOICE-LOCAL-TTS-HUMAN-SCORE-COLLECTION-001`는 무료 로컬 TTS wav를 사람이 채점할 수 있는 private collection 절차를 만든다.

현재 실제 사람 청취 점수는 `30`건이다. 사람 청취 점수 입력이 완료되어 provider decision gate로 넘길 수 있다. 최종 provider 확정과 production 품질 보증은 별도 gate다.

## Scope

| type | item |
| --- | --- |
| include | private listening manifest |
| include | private listening guide |
| include | private score input target |
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
| private_listening_manifest_created_count | 1 |
| private_listening_manifest_row_count | 5 |
| private_listening_guide_created_count | 1 |
| private_score_template_created_count | 1 |
| private_score_template_row_count | 30 |
| private_score_input_available_count | 1 |
| completed_score_row_count | 30 |
| pending_score_row_count | 0 |
| completed_script_count | 5 |
| reviewer_count | 1 |
| aggregate_public_row_count | 6 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_script_public_artifact_count | 0 |
| score_collection_decision | `human_scores_collected_pending_provider_decision` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `dim_voice_local_tts_listening_item_private` | `score_collection_id + script_id` | private |
| `fact_voice_local_tts_human_score_private` | `score_collection_id + script_id + reviewer_id + criterion_id` | private |
| `fact_voice_local_tts_human_score_aggregate_public` | `score_collection_id + provider_candidate_id + criterion_id` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | private 청취 점수 수집 절차를 만들었다. |
| allowed | public에는 criterion aggregate만 공개한다. |
| allowed | 실제 점수 미입력 상태는 collection-ready로 기록한다. |
| allowed | 점수 완료 시 aggregate를 provider decision gate 입력으로 사용한다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
