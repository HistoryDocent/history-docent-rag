# Voice Local TTS Automated Proxy Eval Report

## 결론

`HD-VOICE-LOCAL-TTS-AUTOMATED-PROXY-EVAL-001`는 사람 청취 점수 없이 가능한 자동 대체 평가를 수행한다.

현재 proxy decision은 `automated_proxy_failed_quality_threshold`이다. 이 결과는 human listening score가 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-tts-automated-proxy-eval-report/v1` |
| proxy_eval_id | `voice-local-tts-proxy-s5-4b722fc9` |
| work_id | `HD-VOICE-LOCAL-TTS-AUTOMATED-PROXY-EVAL-001` |
| depends_on_quality_review | `HD-VOICE-LOCAL-TTS-QUALITY-LISTENING-REVIEW-001` |
| depends_on_stt_comparison | `HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001` |
| depends_on_tts_smoke | `HD-VOICE-LOCAL-SHERPA-ONNX-SUPERTONIC3-KO-SMOKE-001` |
| generated_at_utc | `2026-05-21T12:25:01+00:00` |
| scripts_path | `data_samples/voice_tts_smoke_scripts.sample.jsonl` |
| audio_path_alias | `<private artifact: sherpa_onnx_supertonic3_ko_audio>` |
| result_path | `<private artifact: voice_local_tts_automated_proxy_eval_rows.jsonl>` |
| tts_provider_candidate_id | `local_sherpa_onnx_supertonic3_ko` |
| stt_provider_candidate_id | `local_faster_whisper_small_cuda` |
| source_fingerprint | `950c1eb231916025` |
| proxy_decision_status | `automated_proxy_failed_quality_threshold` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | 5 |
| audio_file_available_count | 5 |
| automated_audio_sanity_pass_count | 5 |
| local_stt_runtime_available_count | 1 |
| local_stt_execution_requested_count | 5 |
| local_stt_execution_count | 5 |
| local_cuda_stt_call_count | 5 |
| local_stt_model_load_attempt_count | 1 |
| local_stt_model_load_error_count | 0 |
| proxy_metric_row_count | 5 |
| proxy_metric_pass_count | 4 |
| proxy_metric_fail_count | 1 |
| stt_latency_p50_ms | 426.940800 |
| stt_latency_p95_ms | 850.502480 |
| cer_avg | 0.032306 |
| char_f1_avg | 0.967694 |
| sequence_similarity_avg | 0.967694 |
| place_name_accuracy_avg | 0.800000 |
| quality_threshold_cer_max | 0.150000 |
| quality_threshold_char_f1_min | 0.850000 |
| quality_threshold_sequence_similarity_min | 0.850000 |
| quality_threshold_place_accuracy_min | 0.800000 |
| quality_threshold_pass_count | 4 |
| human_listening_completed_count | 0 |
| human_score_public_detail_row_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_script_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| resolved_device | `cuda` |
| compute_type | `float16` |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| proxy_decision | `automated_proxy_failed_quality_threshold` |

## Proxy Rows

| script_id | status | audio_pass | latency_ms | cer | char_f1 | seq_sim | place_acc | threshold_pass | error_code |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| tts-smoke-docent-001 | `executed` | `True` | 952.934300 | 0.055556 | 0.944444 | 0.944444 | 0.000000 | `False` | `` |
| tts-smoke-docent-002 | `executed` | `True` | 440.775200 | 0.078947 | 0.921053 | 0.921053 | 1.000000 | `True` | `` |
| tts-smoke-docent-003 | `executed` | `True` | 426.940800 | 0.027027 | 0.972973 | 0.972973 | 1.000000 | `True` | `` |
| tts-smoke-docent-004 | `executed` | `True` | 416.703000 | 0.000000 | 1.000000 | 1.000000 | 1.000000 | `True` | `` |
| tts-smoke-docent-005 | `executed` | `True` | 421.150600 | 0.000000 | 1.000000 | 1.000000 | 1.000000 | `True` | `` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 5 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
tts_automated_proxy_eval_failures=[]
tts_automated_proxy_eval_blockers=['proxy_quality_threshold_failed', 'human_listening_scores_still_required']
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 사람 채점 대신 쓸 수 없는 자동 proxy를 별도 evidence로 분리했다. |
| voice_ml | TTS wav를 local STT로 round-trip해 발음/전달력의 기계적 신호만 측정했다. |
| evaluation | CER, 문자 F1, sequence similarity, 장소명 복원률을 script 단위로 기록했다. |
| human_review | human listening completed count는 0으로 유지해 최종 품질 판단을 차단했다. |
| privacy | raw audio, raw transcript, raw script text, private path는 public artifact에 저장하지 않았다. |
| cost | 외부 STT/TTS provider 호출과 외부 음성 전송은 0이다. |
| cuda | CUDA 가능 시 사용하며 resolved_device=cuda로 기록했다. |
| data_mart | public proxy metric grain과 private transcript/human score grain을 분리했다. |
| portfolio | 사람 평가 전 자동 대체 지표로 risk를 낮춘 과정으로 설명할 수 있다. |
| external_audit | 자동 proxy를 human score로 둔갑시키지 않고 별도 gate로 둔 판단은 타당하다. |
| decision | automated_proxy_failed_quality_threshold |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
