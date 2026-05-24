# Voice Local TTS Human Score Manual Scoring Report

## 결론

`HD-VOICE-LOCAL-TTS-HUMAN-SCORE-MANUAL-SCORING-001`는 human listening score를 직접 입력하기 위한 private scoring workspace gate다.

현재 completed score가 `30`건이다. 사람 청취 점수 입력은 완료됐지만 최종 provider 확정과 production 품질 보증은 별도 gate다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-tts-human-score-manual-scoring-report/v1` |
| manual_scoring_id | `voice-local-tts-human-manual-scoring-s5-a49fcf4f` |
| work_id | `HD-VOICE-LOCAL-TTS-HUMAN-SCORE-MANUAL-SCORING-001` |
| depends_on_score_entry_completion | `HD-VOICE-LOCAL-TTS-HUMAN-SCORE-ENTRY-COMPLETION-001` |
| generated_at_utc | `2026-05-24T15:47:13+00:00` |
| scripts_path | `data_samples/voice_tts_smoke_scripts.sample.jsonl` |
| audio_path_alias | `<private artifact: sherpa_onnx_supertonic3_ko_audio>` |
| private_manual_score_sheet_alias | `<private artifact: voice_local_tts_human_score_manual_scoring.html>` |
| private_manual_score_draft_alias | `<private artifact: voice_local_tts_human_scores.manual_scoring.template.jsonl>` |
| private_score_input_alias | `<private artifact: voice_local_tts_human_scores.jsonl>` |
| result_path | `<private artifact: voice_local_tts_human_score_manual_scoring_public_rows.jsonl>` |
| provider_candidate_id | `local_sherpa_onnx_supertonic3_ko` |
| source_fingerprint | `9ee99604a0768342` |
| manual_scoring_status | `human_manual_scores_completed_pending_provider_decision` |

## 정량 리포트

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
| overall_score_avg | 5.000000 |
| overall_score_min | 5 |
| overall_score_max | 5 |
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
| human_score_private_artifact_count | 3 |
| human_score_public_detail_row_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| manual_scoring_decision | `human_manual_scores_completed_pending_provider_decision` |

## Criterion Aggregate

| criterion_id | label | score_count | completed_scripts | reviewers | avg | min | max | p50 | stddev |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pronunciation_clarity | 발음 명료도 | 5 | 5 | 1 | 5.000000 | 5 | 5 | 5.000000 | 0.000000 |
| korean_naturalness | 한국어 자연스러움 | 5 | 5 | 1 | 5.000000 | 5 | 5 | 5.000000 | 0.000000 |
| docent_tone | 역사 도슨트 톤 | 5 | 5 | 1 | 5.000000 | 5 | 5 | 5.000000 | 0.000000 |
| speaking_rate | 말 속도 | 5 | 5 | 1 | 5.000000 | 5 | 5 | 5.000000 | 0.000000 |
| artifact_noise | 잡음/끊김 | 5 | 5 | 1 | 5.000000 | 5 | 5 | 5.000000 | 0.000000 |
| tourist_fit | 관광 안내 적합성 | 5 | 5 | 1 | 5.000000 | 5 | 5 | 5.000000 | 0.000000 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 6 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
tts_human_manual_scoring_failures=[]
tts_human_manual_scoring_blockers=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 사람 청취 점수를 실제 입력할 수 있는 private scoring workspace를 생성했다. |
| score_status | 실제 점수 입력 전이므로 TTS 품질 검증 완료로 표현하지 않는다. |
| privacy | 개별 reviewer score, raw audio, raw script text, private path를 public에 내보내지 않는다. |
| cost | 외부 STT/TTS provider 호출과 외부 음성 전송은 0이다. |
| data_mart | private score detail과 public criterion aggregate grain을 분리했다. |
| portfolio | 무료 로컬 TTS 후보의 human scoring 실행 가능성 evidence로 사용한다. |
| external_audit | 사람이 듣지 않은 점수를 임의 생성하지 않은 판단은 타당하다. |
| decision | human_manual_scores_completed_pending_provider_decision |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
