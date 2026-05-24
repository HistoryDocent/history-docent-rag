# Voice Local TTS Human Score Decision Report

## 결론

`HD-VOICE-LOCAL-TTS-HUMAN-SCORE-DECISION-001`는 무료 로컬 TTS 후보를 사람 청취 점수 기반으로 판정하는 gate다.

현재 decision은 `candidate_accepted_for_demo_review`이다. completed score는 `30`건이다. demo review 후보로는 수락됐지만 최종 provider 확정이나 production 품질 보증으로 보지는 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-tts-human-score-decision-report/v1` |
| score_decision_id | `voice-local-tts-human-score-decision-s5-e4c24fcd` |
| work_id | `HD-VOICE-LOCAL-TTS-HUMAN-SCORE-DECISION-001` |
| depends_on_manual_scoring | `HD-VOICE-LOCAL-TTS-HUMAN-SCORE-MANUAL-SCORING-001` |
| generated_at_utc | `2026-05-24T15:47:13+00:00` |
| scripts_path | `data_samples/voice_tts_smoke_scripts.sample.jsonl` |
| audio_path_alias | `<private artifact: sherpa_onnx_supertonic3_ko_audio>` |
| private_score_input_alias | `<private artifact: voice_local_tts_human_scores.jsonl>` |
| result_path | `<private artifact: voice_local_tts_human_score_decision_public_rows.jsonl>` |
| provider_candidate_id | `local_sherpa_onnx_supertonic3_ko` |
| source_fingerprint | `b21343273440770c` |
| provider_decision_status | `candidate_accepted_for_demo_review` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| rubric_criterion_count | 6 |
| expected_private_score_row_count | 30 |
| private_audio_expected_count | 5 |
| private_audio_available_count | 5 |
| private_audio_missing_count | 0 |
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
| provider_decision_public_row_count | 1 |
| overall_score_avg | 5.000000 |
| overall_score_min | 5 |
| overall_score_max | 5 |
| accept_overall_score_avg_threshold | 4.000000 |
| accept_min_criterion_score_avg_threshold | 3.500000 |
| reject_overall_score_avg_threshold | 3.000000 |
| reject_min_criterion_score_avg_threshold | 2.500000 |
| criterion_below_accept_threshold_count | 0 |
| criterion_below_reject_threshold_count | 0 |
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
| human_score_private_artifact_count | 1 |
| human_score_public_detail_row_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| provider_decision | `candidate_accepted_for_demo_review` |

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
| result_row_count | 7 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
tts_human_score_decision_failures=[]
tts_human_score_decision_blockers=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| product | 무료 로컬 TTS 후보를 포트폴리오 demo 후보로 올릴지 판단하는 gate다. |
| voice_ml | 자동 audio sanity는 이미 통과했지만 사람 청취 점수가 없으면 품질 후보 채택을 차단한다. |
| evaluation | 5개 script x 6개 rubric score를 모두 채운 뒤에만 채택/보류/탈락 threshold를 적용한다. |
| privacy | 개별 reviewer score, raw audio, raw script text, private path는 public artifact에 포함하지 않는다. |
| cost | 외부 STT/TTS provider 호출과 외부 음성 전송은 0이다. |
| data_mart | private score detail, public criterion aggregate, public decision summary grain을 분리했다. |
| portfolio | 점수 미입력 상태를 숨기지 않고 blocker로 기록해 claim boundary를 유지한다. |
| external_audit | 사람 점수를 임의 생성하지 않고 provider 채택을 보류한 판단은 타당하다. |
| decision | candidate_accepted_for_demo_review |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
