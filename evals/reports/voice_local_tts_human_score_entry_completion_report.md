# Voice Local TTS Human Score Entry Completion Report

## 결론

`HD-VOICE-LOCAL-TTS-HUMAN-SCORE-ENTRY-COMPLETION-001`는 human listening score 입력 완료 여부를 검증하는 gate다.

현재 completed score가 `0`건이므로 실제 음질 검증 완료를 주장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-tts-human-score-entry-completion-report/v1` |
| score_completion_id | `voice-local-tts-human-score-completion-s5-ecd9f2dd` |
| work_id | `HD-VOICE-LOCAL-TTS-HUMAN-SCORE-ENTRY-COMPLETION-001` |
| depends_on_score_entry | `HD-VOICE-LOCAL-TTS-HUMAN-SCORE-ENTRY-001` |
| generated_at_utc | `2026-05-21T06:44:05+00:00` |
| scripts_path | `data_samples/voice_tts_smoke_scripts.sample.jsonl` |
| audio_path_alias | `<private artifact: sherpa_onnx_supertonic3_ko_audio>` |
| private_score_input_alias | `<private artifact: voice_local_tts_human_scores.jsonl>` |
| result_path | `<private artifact: voice_local_tts_human_score_entry_completion_public_rows.jsonl>` |
| provider_candidate_id | `local_sherpa_onnx_supertonic3_ko` |
| source_fingerprint | `f20b4169c85fff33` |
| score_completion_status | `blocked_missing_human_scores` |

## 정량 리포트

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
| score_completion_decision | `blocked_missing_human_scores` |

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
| result_row_count | 6 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
tts_human_score_completion_failures=[]
tts_human_score_completion_blockers=['missing_human_score_input', 'incomplete_human_score_rows']
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 사람 청취 점수 입력 완료 여부와 public aggregate 반영 가능성을 검증했다. |
| score_status | 30개 점수가 모두 입력되기 전에는 TTS 품질 검증 완료로 표현하지 않는다. |
| privacy | 개별 reviewer score, raw audio, raw script text, private path를 public에 내보내지 않는다. |
| cost | 외부 STT/TTS provider 호출과 외부 음성 전송은 0이다. |
| data_mart | private score detail과 public criterion aggregate grain을 분리했다. |
| portfolio | 무료 로컬 TTS 후보의 human evaluation completion gate evidence로 사용한다. |
| external_audit | human score 미완료 상태를 blocker로 남긴 판단은 타당하다. |
| decision | blocked_missing_human_scores |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
