# Voice STT/TTS Provider Benchmark Readiness

## 결론

`HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001`는 provider benchmark 실행 전 readiness gate다.

| boundary | value |
| --- | --- |
| STT/TTS provider live call | disabled |
| Solar Pro 3 live call | disabled |
| raw audio public artifact | forbidden |
| raw transcript public artifact | forbidden |
| provider final decision | forbidden |

## 정량 요약

| metric | value |
| --- | ---: |
| provider_candidate_group_count | 5 |
| official_source_checked_count | 14 |
| pricing_source_link_count | 5 |
| privacy_source_link_count | 4 |
| benchmark_script_count | 30 |
| benchmark_query_type_count | 6 |
| script_per_query_type_min_count | 5 |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| provider_benchmark_execution_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| readiness_decision | `ready_for_provider_benchmark_execution_approval` |

## CUDA Preflight

| field | value |
| --- | --- |
| resolved_device | `cuda` |
| local_cuda_available | true |
| torch_cuda_available | true |
| cuda_device_count | 1 |
| cuda_device_name | `NVIDIA GeForce RTX 4080 SUPER` |

## Provider Candidate Boundary

| provider_candidate_id | modality | planned_stt | planned_tts | live_stt | live_tts |
| --- | --- | ---: | ---: | ---: | ---: |
| browser_native_web_speech | stt_tts | 10 | 10 | 0 | 0 |
| local_cuda_whisper | stt | 30 | 0 | 0 | 0 |
| external_google_cloud | stt_tts | 20 | 20 | 0 | 0 |
| external_azure_speech | stt_tts | 20 | 20 | 0 | 0 |
| external_aws_transcribe_polly | stt_tts | 20 | 20 | 0 | 0 |

## Benchmark Script Fixture

| query_type | script_count | public_allowed | audio_required | raw_audio_saved |
| --- | ---: | ---: | ---: | ---: |
| place_fact | 5 | 5 | 0 | 0 |
| place_story | 5 | 5 | 0 | 0 |
| relationship | 5 | 5 | 0 | 0 |
| route_context | 5 | 5 | 0 | 0 |
| voice_followup | 5 | 5 | 0 | 0 |
| no_answer | 5 | 5 | 0 | 0 |

## 다음 작업

| priority | work_id | 작업 | 승인 필요 |
| ---: | --- | --- | --- |
| 1 | `HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001` | provider별 live benchmark 실행 승인 | 예 |

## Claim Boundary

| claim | allowed |
| --- | --- |
| provider benchmark readiness gate 통과 | yes |
| live STT/TTS call은 0회 | yes |
| CUDA 사용 가능 여부를 기록 | yes |
| provider 최종 선택 완료 | no |
| STT/TTS 품질 검증 완료 | no |
| 음성 관광 앱 완성 | no |
