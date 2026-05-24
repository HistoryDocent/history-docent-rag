# Voice Local TTS Human Score Manual Scoring Runbook

## 결론

`HD-VOICE-LOCAL-TTS-HUMAN-SCORE-MANUAL-SCORING-RUNBOOK-001`는 무료 로컬 TTS 사람 청취 평가를 실제로 실행하기 위한 절차와 gate를 고정한다.

현재 runbook decision은 `completed_scores_ready_for_decision`이다. completed score는 `30`건이다. 사람 청취 점수 입력이 완료되어 provider decision gate로 넘길 수 있다.

## 실행 절차

1. private manual score sheet를 연다.
2. 5개 audio sample을 순서대로 재생한다.
3. 각 sample마다 6개 rubric을 1-5점으로 채점한다.
4. reviewer id와 reviewed timestamp를 입력한다.
5. JSONL을 생성해 private score input 위치에 저장한다.
6. score decision runner를 실행해 30개 row 완료 여부를 검증한다.
7. public report에는 aggregate와 decision만 반영한다.

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| rubric_criterion_count | 6 |
| expected_private_score_row_count | 30 |
| private_audio_expected_count | 5 |
| private_audio_available_count | 5 |
| private_audio_missing_count | 0 |
| private_manual_score_sheet_available_count | 1 |
| private_manual_score_draft_available_count | 1 |
| private_score_input_available_count | 1 |
| private_score_input_row_count | 30 |
| valid_private_score_row_count | 30 |
| invalid_private_score_row_count | 0 |
| completed_score_row_count | 30 |
| pending_score_row_count | 0 |
| completed_script_count | 5 |
| completed_script_rate | 1.000000 |
| reviewer_count | 1 |
| aggregate_public_row_count | 6 |
| runbook_step_count | 7 |
| user_action_required_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| human_score_public_detail_row_count | 0 |
| runbook_decision | `completed_scores_ready_for_decision` |

## Rubric

| criterion_id | label | score range |
| --- | --- | --- |
| pronunciation_clarity | 발음 명료도 | 1-5 |
| korean_naturalness | 한국어 자연스러움 | 1-5 |
| docent_tone | 역사 도슨트 톤 | 1-5 |
| speaking_rate | 말 속도 | 1-5 |
| artifact_noise | 잡음/끊김 | 1-5 |
| tourist_fit | 관광 안내 적합성 | 1-5 |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_manual_score_private` | `runbook_id + script_id + reviewer_id + criterion_id` | private |
| `fact_voice_local_tts_manual_score_aggregate_public` | `runbook_id + provider_candidate_id + criterion_id` | public-safe |
| `fact_voice_local_tts_manual_score_runbook_public` | `runbook_id + provider_candidate_id + runbook_decision` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 수동 청취 평가 실행 절차와 gate를 고정했다. |
| allowed | score 미입력 상태에서는 사람 action required로 남긴다. |
| allowed | score 완료 시 completed_scores_ready_for_decision을 기록한다. |
| allowed | public에는 aggregate와 runbook decision만 공개한다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
