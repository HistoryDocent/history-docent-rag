# Voice STT/TTS Provider Benchmark Readiness Report

## 목적

`HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001`는 provider 비교 실행 전 조건만 검증한다.

이번 리포트는 quality benchmark 결과가 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-stt-tts-provider-bench-readiness-report/v1` |
| readiness_id | `voice-provider-readiness-p5-s30-ad55a680` |
| work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001` |
| depends_on | `HD-VOICE-STT-TTS-PROVIDER-BENCH-PLAN-001` |
| generated_at_utc | `2026-05-19T11:51:40+00:00` |
| config_path | `configs/voice_provider_candidates.yaml` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_stt_tts_provider_bench_readiness_rows.jsonl>` |
| source_fingerprint | `3de6c52981ee2742` |
| readiness_status | `PASS` |

## 정량 리포트

| metric | value |
| --- | ---: |
| provider_candidate_group_count | 5 |
| required_provider_candidate_group_count | 5 |
| official_source_checked_count | 14 |
| pricing_source_link_count | 5 |
| privacy_source_link_count | 4 |
| benchmark_script_count | 30 |
| benchmark_query_type_count | 6 |
| script_per_query_type_min_count | 5 |
| planned_public_safe_script_min_count | 30 |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| provider_finalized_count | 0 |
| provider_benchmark_execution_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| private_audio_saved_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| pricing_recheck_required_count | 5 |
| privacy_recheck_required_count | 5 |
| region_recheck_required_count | 5 |
| pricing_claim_without_source_count | 0 |
| privacy_policy_unknown_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| readiness_decision | `ready_for_provider_benchmark_execution_approval` |

## CUDA Runtime Preflight

| field | value |
| --- | --- |
| resolved_device | `cuda` |
| local_cuda_available | true |
| torch_cuda_available | true |
| cuda_device_count | 1 |
| cuda_device_name | `NVIDIA GeForce RTX 4080 SUPER` |
| cuda_runtime_probe_error_count | 0 |

## Provider Candidate Summary

| provider_candidate_id | modality | server_credential | external_audio | model_download | max_stt | max_tts | live_stt | live_tts |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| browser_native_web_speech | stt_tts | false | browser_dependent | false | 10 | 10 | 0 | 0 |
| local_cuda_whisper | stt | false | none | true | 30 | 0 | 0 | 0 |
| external_google_cloud | stt_tts | true | managed_provider | false | 20 | 20 | 0 | 0 |
| external_azure_speech | stt_tts | true | managed_provider | false | 20 | 20 | 0 | 0 |
| external_aws_transcribe_polly | stt_tts | true | managed_provider | false | 20 | 20 | 0 | 0 |

## Query Type Script Summary

| query_type | script_count | public_allowed | audio_required | raw_audio_saved |
| --- | ---: | ---: | ---: | ---: |
| place_fact | 5 | 5 | 0 | 0 |
| place_story | 5 | 5 | 0 | 0 |
| relationship | 5 | 5 | 0 | 0 |
| route_context | 5 | 5 | 0 | 0 |
| voice_followup | 5 | 5 | 0 | 0 |
| no_answer | 5 | 5 | 0 | 0 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 12 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
readiness_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | 실제 provider 호출 전 public-safe fixture와 config만 검증했다. |
| quality_boundary | STT/TTS 품질 비교와 provider 최종 선택은 아직 수행하지 않았다. |
| cost_boundary | 가격 숫자는 고정하지 않고 실행일 source recheck를 필수로 둔다. |
| privacy_boundary | 외부 provider는 audio 전송 후보라 별도 승인 없이는 실행하지 않는다. |
| cuda_boundary | local STT 후보는 CUDA 사용 가능 시 사용하며 현재 device는 cuda다. |
| security_boundary | public artifact에는 raw audio, transcript, secret을 저장하지 않는다. |
| portfolio_boundary | 음성 기능 완성이 아니라 provider 비교 준비 gate로만 설명한다. |
| external_audit | 실행 전 call cap과 공개 경계를 고정한 판단은 타당하다. |

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_stt_tts_provider_bench_readiness | work_id + provider_candidate_id + query_type + metric_name |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
