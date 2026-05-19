# Voice STT/TTS Provider Benchmark Plan Report

## 결론

`HD-VOICE-STT-TTS-PROVIDER-BENCH-PLAN-001`은 통과다.

이번 작업은 STT/TTS provider benchmark 실행이 아니라 실행 전 계획 gate다. 공식 문서, 후보군, call budget, CUDA local 후보, 개인정보/비용/latency metric을 고정했고 실제 provider 호출은 0회로 유지했다.

## 정량 리포트

| metric | value |
| --- | ---: |
| voice_stt_tts_provider_bench_plan_document_count | 1 |
| voice_stt_tts_provider_bench_plan_report_count | 1 |
| provider_candidate_group_count | 5 |
| official_source_checked_count | 14 |
| pricing_source_link_count | 5 |
| privacy_source_link_count | 4 |
| benchmark_query_type_count | 6 |
| planned_public_safe_script_min_count | 30 |
| planned_metric_count | 25 |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| provider_finalized_count | 0 |
| provider_benchmark_execution_count | 0 |
| private_audio_saved_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| pricing_claim_without_source_count | 0 |
| privacy_policy_unknown_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| 제품 적합성 | PASS. 서울/한양 관광 도슨트의 짧은 음성 질문, 짧은 spoken answer, 장소명 정확도를 평가 지표로 분리했다. |
| 비용 통제 | PASS. 가격 숫자를 고정 claim으로 쓰지 않고 실행일 기준 공식 pricing page 재확인을 요구했다. |
| 개인정보 | PASS. 외부 전송, raw audio 저장, raw transcript 공개를 별도 metric과 중단 조건으로 분리했다. |
| CUDA 활용 | PASS. RTX 4080 SUPER와 torch CUDA 사용 가능성을 확인했고 local STT 후보를 포함했다. |
| Provider 선택 | PASS. provider를 확정하지 않고 benchmark 후보로만 유지했다. |
| Claim boundary | PASS. STT/TTS 품질 검증, 음성 앱 완성, provider 최적 선택 주장을 금지했다. |
| 외부 감사 | PASS. plan-only 산출물로는 충분하다. 다음 단계는 no-live-call readiness runner다. |

## 확인한 공식 Source

확인일: 2026-05-19

| provider | source count | pricing source count | privacy/data source count |
| --- | ---: | ---: | ---: |
| Web Speech API | 2 | 0 | 0 |
| local CUDA Whisper | 2 | 0 | 0 |
| Google Cloud STT/TTS | 3 | 2 | 1 |
| Azure AI Speech | 3 | 1 | 1 |
| AWS Transcribe/Polly | 4 | 2 | 2 |

## Data Mart Grain

`fact_voice_stt_tts_provider_bench_plan`

grain: `work_id + provider_candidate_id + modality + metric_family + claim_boundary`

금지 필드:

- raw audio
- raw transcript
- raw answer
- raw evidence
- raw prompt
- raw chunk text
- private file path
- secret

## 다음 Gate

다음 작업 후보는 `HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001`이다.

다음 단계도 live call을 실행하지 않는다. 먼저 public-safe fixture script, provider config skeleton, CUDA runtime preflight, pricing/privacy source recheck field를 만들고 사용자 승인 후에만 실제 benchmark로 넘어간다.

External audit | PASS
