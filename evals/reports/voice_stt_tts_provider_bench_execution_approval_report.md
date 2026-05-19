# Voice STT/TTS Provider Benchmark Execution Approval Report

## 결론

`HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001`은 PASS다.

단, 이 PASS는 실제 provider benchmark 실행 성공이 아니다. 실제 STT/TTS call은 0이며, 다음 smoke execution을 별도 사용자 승인 대상으로 분리했다.

## Metadata

| field | value |
| --- | --- |
| `report_version` | `voice-stt-tts-provider-bench-execution-approval-report/v1` |
| `source_document` | `docs/VOICE_STT_TTS_PROVIDER_BENCH_EXECUTION_APPROVAL.md` |
| `readiness_report` | `evals/reports/voice_stt_tts_provider_bench_readiness_report.md` |
| `work_id` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001` |
| `depends_on` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001` |
| `next_gate` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-EXECUTION-001` |

## Quantitative Report

| metric | value |
| --- | ---: |
| voice_stt_tts_provider_bench_execution_approval_document_count | 1 |
| voice_stt_tts_provider_bench_execution_approval_report_count | 1 |
| provider_candidate_group_count | 5 |
| public_safe_script_fixture_count | 30 |
| planned_smoke_script_count_per_low_risk_provider | 5 |
| planned_smoke_script_count_per_external_provider | 3 |
| planned_full_benchmark_script_count | 30 |
| pricing_recheck_required_count | 5 |
| privacy_recheck_required_count | 5 |
| region_recheck_required_count | 5 |
| provider_benchmark_execution_approved | false |
| provider_benchmark_execution_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| private_audio_saved_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| external_audio_transmission_count | 0 |
| source_recheck_incomplete_provider_count | 5 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Provider Boundary

| provider_candidate_id | tier | planned_max_stt_calls | planned_max_tts_calls | execution_status |
| --- | --- | ---: | ---: | --- |
| browser_native_web_speech | tier_1_local_browser_smoke | 5 | 5 | pending_user_approval |
| local_cuda_whisper | tier_1_local_browser_smoke | 5 | 0 | pending_user_approval |
| external_google_cloud | tier_2_managed_provider_smoke | 3 | 3 | blocked_until_source_recheck |
| external_azure_speech | tier_2_managed_provider_smoke | 3 | 3 | blocked_until_source_recheck |
| external_aws_transcribe_polly | tier_2_managed_provider_smoke | 3 | 3 | blocked_until_source_recheck |

## Metric Approval Matrix

| metric_family | required_metrics | status |
| --- | --- | --- |
| STT | `wer`, `cer`, `place_name_accuracy`, `stt_latency_p95_ms`, `stt_error_rate` | defined |
| TTS | `playback_success_rate`, `tts_latency_p95_ms`, `spoken_answer_length_violation_rate`, `tts_error_rate` | defined |
| E2E | `voice_round_trip_latency_p95_ms`, `fallback_to_text_rate`, `rag_answer_contract_preserved_rate` | defined |
| Cost | `estimated_stt_cost`, `estimated_tts_cost` | defined |
| Privacy | `external_audio_transmission_count`, `raw_transcript_public_artifact_count` | defined |

## Data Mart Boundary

| table | grain | exposure |
| --- | --- | --- |
| fact_voice_provider_benchmark_run | run_id + provider_candidate_id + tier_id + modality | aggregate only |
| fact_voice_stt_eval_private | run_id + script_id + provider_candidate_id + metric_name | private |
| fact_voice_tts_eval_private | run_id + script_id + provider_candidate_id + metric_name | private |
| fact_voice_e2e_eval_private | run_id + script_id + provider_candidate_id + metric_name | private |
| fact_voice_provider_public_summary | run_id + provider_candidate_id + tier_id + metric_name | public-safe |

## Qualitative Report

| 담당 관점 | 결과 |
| --- | --- |
| Product | PASS. full benchmark보다 smoke를 먼저 실행하도록 범위를 좁혔다. |
| Voice engineering | PASS. local/browser 후보와 external 후보의 call cap을 분리했다. |
| RAG | PASS. STT가 RAG answer contract를 훼손하는지 별도 metric으로 본다. |
| Evaluation | PASS. WER/CER/place-name/latency/cost/privacy를 한 번에 기록한다. |
| Security | PASS. 외부 provider 전송 전 recheck와 public artifact 금지를 고정했다. |
| Data warehouse | PASS. private fact와 public summary grain을 분리했다. |
| Portfolio | PASS. provider 선택 완료가 아니라 선택 실험 설계로만 표현한다. |
| External audit | PASS. live call 전 승인 기준은 적절하며, smoke 실행은 별도 승인이 필요하다. |

## Public Safety Gate

| gate | result |
| --- | --- |
| private path leakage | PASS |
| secret-like leakage | PASS |
| env assignment leakage | PASS |
| raw audio public artifact | PASS |
| raw transcript public artifact | PASS |
| raw provider payload public artifact | PASS |

## Claim Boundary

허용:

- provider benchmark 실행 승인 기준을 고정했다.
- STT/TTS provider 후보 비교를 위한 metric과 data mart grain을 정의했다.
- 실제 live call은 수행하지 않았다.

금지:

- provider 최종 선택 완료
- STT/TTS 품질 검증 완료
- 음성 관광 앱 완성
- external provider benchmark 성능 개선 입증
