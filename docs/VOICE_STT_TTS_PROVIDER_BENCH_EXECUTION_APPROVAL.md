# Voice STT/TTS Provider Benchmark Execution Approval

## 결론

`HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001`은 실제 STT/TTS provider benchmark를 실행하지 않는다.

이번 gate의 목적은 다음 live smoke 실행 전에 provider별 call cap, 비용 재확인, region/privacy boundary, raw audio/transcript 보관 정책, 평가 metric, data mart grain을 고정하는 것이다.

이 문서는 `docs/VOICE_STT_TTS_PROVIDER_BENCH_READINESS.md`와 `evals/reports/voice_stt_tts_provider_bench_readiness_report.md`의 후속 승인 기준이다.

## Scope

포함:

- provider 후보 5개에 대한 smoke 실행 승인 조건
- low-risk 후보와 external provider 후보의 call cap 분리
- STT, TTS, end-to-end voice metric 정의
- 비용, region, privacy, retention/logging 재확인 필드 고정
- private fact와 public summary를 분리한 data mart grain 정의
- public repo에 raw audio, raw transcript, raw provider payload를 남기지 않는 규칙

제외:

- 실제 provider API 호출
- STT/TTS 품질 검증 완료 주장
- provider 최종 선택
- production 음성 관광 앱 완성 주장
- raw audio 또는 raw transcript 공개

## Approval Status

| field | value |
| --- | --- |
| `work_id` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001` |
| `depends_on` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001` |
| `approval_decision` | `ready_for_user_smoke_execution_approval` |
| `provider_benchmark_execution_approved` | `false` |
| `provider_benchmark_execution_count` | `0` |
| `live_stt_call_count` | `0` |
| `live_tts_call_count` | `0` |
| `live_solar_call_count` | `0` |
| `private_audio_saved_count` | `0` |
| `raw_transcript_public_artifact_count` | `0` |
| `client_secret_exposure_count` | `0` |
| `cuda_required_for_future_local_stt` | `true` |
| `readiness_cuda_resolved_device` | `cuda` |
| `readiness_report` | `evals/reports/voice_stt_tts_provider_bench_readiness_report.md` |

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| Product | 바로 full benchmark로 가지 말고 tiered smoke로 시작한다. |
| Voice engineering | browser/local CUDA 후보와 managed cloud 후보를 분리해 call cap을 다르게 둔다. |
| RAG | STT 결과가 `/api/v1/chat` contract와 citation answer contract를 훼손하는지 별도 측정한다. |
| Evaluation | WER/CER만 보지 말고 place name accuracy, latency, cost, fallback rate를 같이 본다. |
| Security | 외부 provider 전송 전 region, retention, logging, credential boundary를 재확인한다. |
| Data warehouse | private row-level fact와 public aggregate summary를 분리한다. |
| Portfolio | "provider를 골랐다"가 아니라 "provider 선택 실험을 안전하게 설계했다"로 표현한다. |
| External audit | live call 전 approval gate를 둔 것은 타당하다. 단, smoke 실행은 별도 승인 없이는 금지한다. |

## Provider Execution Tiers

| tier_id | 목적 | 실행 범위 | 승인 상태 |
| --- | --- | --- | --- |
| `tier_0_contract_only` | 기존 readiness와 contract 확인 | live call 0 | completed |
| `tier_1_local_browser_smoke` | low-risk 후보의 기본 동작 확인 | provider당 최대 5 scripts | pending user approval |
| `tier_2_managed_provider_smoke` | 외부 provider 전송 후보 최소 비교 | provider당 최대 3 scripts | pending source recheck and user approval |
| `tier_3_full_private_benchmark` | 30개 script 전체 비교 | smoke pass 후 별도 승인 | blocked |

## Provider Candidate Execution Boundary

| provider_candidate_id | tier | planned_max_stt_calls | planned_max_tts_calls | external_audio_transmission | required_recheck |
| --- | --- | ---: | ---: | --- | --- |
| `browser_native_web_speech` | `tier_1_local_browser_smoke` | 5 | 5 | false | browser support and consent |
| `local_cuda_whisper` | `tier_1_local_browser_smoke` | 5 | 0 | false | model license, disk, CUDA |
| `external_google_cloud` | `tier_2_managed_provider_smoke` | 3 | 3 | true | pricing, privacy, region, retention |
| `external_azure_speech` | `tier_2_managed_provider_smoke` | 3 | 3 | true | pricing, privacy, region, retention |
| `external_aws_transcribe_polly` | `tier_2_managed_provider_smoke` | 3 | 3 | true | pricing, privacy, region, retention |

## Quantitative Approval Criteria

| metric | required_value | current_value |
| --- | ---: | ---: |
| `provider_candidate_group_count` | 5 | 5 |
| `public_safe_script_fixture_count` | 30 | 30 |
| `planned_smoke_script_count_per_low_risk_provider` | 5 | 5 |
| `planned_smoke_script_count_per_external_provider` | 3 | 3 |
| `planned_full_benchmark_script_count` | 30 | 30 |
| `pricing_recheck_required_count` | 5 | 5 |
| `privacy_recheck_required_count` | 5 | 5 |
| `region_recheck_required_count` | 5 | 5 |
| `provider_benchmark_execution_approved` | false | false |
| `provider_benchmark_execution_count` | 0 | 0 |
| `live_stt_call_count` | 0 | 0 |
| `live_tts_call_count` | 0 | 0 |
| `live_solar_call_count` | 0 | 0 |
| `public_private_path_leakage_count` | 0 | 0 |
| `public_secret_like_leakage_count` | 0 | 0 |
| `public_raw_payload_leakage_count` | 0 | 0 |

## Metric Plan

STT metric:

- `wer`
- `cer`
- `place_name_accuracy`
- `transcript_confirmation_required_rate`
- `stt_latency_p50_ms`
- `stt_latency_p95_ms`
- `stt_error_rate`

TTS metric:

- `playback_success_rate`
- `tts_latency_p50_ms`
- `tts_latency_p95_ms`
- `spoken_answer_length_violation_rate`
- `tts_error_rate`

End-to-end metric:

- `voice_round_trip_latency_p95_ms`
- `fallback_to_text_rate`
- `rag_answer_contract_preserved_rate`
- `citation_display_preserved_rate`
- `no_answer_voice_hallucination_count`

Cost and privacy metric:

- `estimated_stt_cost`
- `estimated_tts_cost`
- `external_audio_transmission_count`
- `raw_transcript_public_artifact_count`
- `credential_client_exposure_count`

## Data Mart Grain

| table | grain | public_allowed |
| --- | --- | --- |
| `fact_voice_provider_benchmark_run` | `run_id + provider_candidate_id + tier_id + modality` | aggregate only |
| `fact_voice_stt_eval_private` | `run_id + script_id + provider_candidate_id + metric_name` | false |
| `fact_voice_tts_eval_private` | `run_id + script_id + provider_candidate_id + metric_name` | false |
| `fact_voice_e2e_eval_private` | `run_id + script_id + provider_candidate_id + metric_name` | false |
| `fact_voice_provider_public_summary` | `run_id + provider_candidate_id + tier_id + metric_name` | true |

Conformed dimensions:

- `dim_voice_provider_candidate`
- `dim_voice_query_type`
- `dim_voice_runtime`
- `dim_source_recheck`
- `dim_voice_execution_tier`

금지 필드:

- raw audio
- raw transcript
- raw provider payload
- credential value
- private absolute path
- full user utterance with personal information

## Stop Conditions

- pricing, privacy, region, retention/logging source가 재확인되지 않은 경우
- browser client에 server credential이 노출될 가능성이 있는 경우
- raw audio 또는 raw transcript가 public artifact로 남는 경우
- 예상 비용 cap을 초과할 가능성이 있는 경우
- local CUDA 후보 실행 시 CUDA device가 잡히지 않는 경우
- smoke에서 `place_name_accuracy`가 낮아 transcript confirmation 없이는 RAG 질문으로 넘기기 어려운 경우
- provider quota, region, error rate가 불안정해 비교가 불공정한 경우

## 다음 작업 지시서

| field | value |
| --- | --- |
| `id` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-EXECUTION-001` |
| `depends_on` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001` |
| `scope` | low-risk 후보와 external provider smoke를 분리 실행하고 STT/TTS/E2E metric을 private fact로 기록 |
| `acceptance_tests` | live call cap 준수, public leakage 0, WER/CER/place_name_accuracy/latency/cost summary 생성 |
| `risk_level` | Medium |
| `rollback_plan` | smoke result artifact와 private run metadata 삭제 또는 폐기, public summary는 실패 리포트로만 보존 |

## Claim Boundary

허용 claim:

- provider benchmark 실행 전 승인 기준을 문서화했다.
- provider 후보 5개, public-safe script 30개, CUDA readiness 결과를 기준으로 smoke 실행 경계를 고정했다.
- 실제 provider 호출은 아직 수행하지 않았다.

금지 claim:

- provider 최종 선택 완료
- STT/TTS 품질 검증 완료
- 음성 관광 앱 완성
- production 음성 서비스 검증 완료
- external provider benchmark 성능 개선 입증
