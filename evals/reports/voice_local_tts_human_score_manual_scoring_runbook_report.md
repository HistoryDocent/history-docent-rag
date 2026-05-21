# Voice Local TTS Human Score Manual Scoring Runbook Report

## 결론

`HD-VOICE-LOCAL-TTS-HUMAN-SCORE-MANUAL-SCORING-RUNBOOK-001`는 수동 청취 평가 실행 절차와 입력 완료 gate를 public-safe하게 검증한다.

현재 runbook decision은 `ready_for_manual_score_input`이며, completed score는 `0`건이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-tts-human-score-manual-scoring-runbook-report/v1` |
| runbook_id | `voice-local-tts-human-score-manual-runbook-s5-acc0a56b` |
| work_id | `HD-VOICE-LOCAL-TTS-HUMAN-SCORE-MANUAL-SCORING-RUNBOOK-001` |
| depends_on_manual_scoring | `HD-VOICE-LOCAL-TTS-HUMAN-SCORE-MANUAL-SCORING-001` |
| depends_on_decision | `HD-VOICE-LOCAL-TTS-HUMAN-SCORE-DECISION-001` |
| generated_at_utc | `2026-05-21T11:39:44+00:00` |
| scripts_path | `data_samples/voice_tts_smoke_scripts.sample.jsonl` |
| audio_path_alias | `<private artifact: sherpa_onnx_supertonic3_ko_audio>` |
| private_manual_score_sheet_alias | `<private artifact: voice_local_tts_human_score_manual_scoring.html>` |
| private_manual_score_draft_alias | `<private artifact: voice_local_tts_human_scores.manual_scoring.template.jsonl>` |
| private_score_input_alias | `<private artifact: voice_local_tts_human_scores.jsonl>` |
| result_path | `<private artifact: voice_local_tts_human_score_manual_scoring_runbook_public_rows.jsonl>` |
| provider_candidate_id | `local_sherpa_onnx_supertonic3_ko` |
| source_fingerprint | `77883691a12a50ab` |
| runbook_decision_status | `ready_for_manual_score_input` |

## 정량 리포트

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
| runbook_step_count | 7 |
| user_action_required_count | 1 |
| overall_score_avg |  |
| overall_score_min |  |
| overall_score_max |  |
| score_scale_min | 1 |
| score_scale_max | 5 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_script_public_artifact_count | 0 |
| human_score_private_artifact_count | 0 |
| human_score_public_detail_row_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| runbook_decision | `ready_for_manual_score_input` |

## Criterion Aggregate

| criterion_id | label | score_count | completed_scripts | reviewers | avg | min | max | p50 | stddev |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pronunciation_clarity | 발음 명료도 | 0 | 0 | 0 |  |  |  |  |  |
| korean_naturalness | 한국어 자연스러움 | 0 | 0 | 0 |  |  |  |  |  |
| docent_tone | 역사 도슨트 톤 | 0 | 0 | 0 |  |  |  |  |  |
| speaking_rate | 말 속도 | 0 | 0 | 0 |  |  |  |  |  |
| artifact_noise | 잡음/끊김 | 0 | 0 | 0 |  |  |  |  |  |
| tourist_fit | 관광 안내 적합성 | 0 | 0 | 0 |  |  |  |  |  |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 7 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
tts_manual_scoring_runbook_failures=[]
tts_manual_scoring_runbook_blockers=['awaiting_manual_score_input']
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| product | 무료 로컬 TTS 후보의 demo 적합성을 사람이 판단할 수 있게 실행 절차를 고정했다. |
| voice_ml | 음질 채택은 자동 sanity가 아니라 사람 rubric 점수 30개 완료 뒤 판단한다. |
| evaluation | 현재 completed score가 부족하면 blocker가 아니라 user action required로 기록한다. |
| privacy | 개별 score, raw audio, raw script text, private path는 public artifact에 포함하지 않는다. |
| cost | 외부 STT/TTS provider 호출과 외부 음성 전송은 0이다. |
| data_mart | private score detail과 public aggregate/runbook decision grain을 분리했다. |
| portfolio | 사람 평가가 아직 미완료임을 숨기지 않고 다음 행동으로 드러낸다. |
| external_audit | 사람 점수를 임의 생성하지 않고 실행 절차만 고정한 판단은 타당하다. |
| decision | ready_for_manual_score_input |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
