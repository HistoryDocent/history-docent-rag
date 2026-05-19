# Voice STT/TTS Provider Benchmark Plan

## 결론

`HD-VOICE-STT-TTS-PROVIDER-BENCH-PLAN-001`은 provider benchmark 실행 전 계획 gate다. 이후 `HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001`에서 무료 로컬 STT/TTS 우선 전략으로 변경했으며, 이 문서의 external managed 후보는 optional paid comparison으로만 유지한다.

이번 단계에서 provider를 확정하지 않는다. STT/TTS 실제 호출, Solar Pro 3 호출, raw audio 저장, raw transcript 공개 artifact 생성도 하지 않는다. 목표는 다음 실행 단계에서 비용과 개인정보 리스크를 통제하면서 비교할 후보, 평가 지표, 중단 조건을 고정하는 것이다.

## 범위

포함:

- browser native Web Speech 후보 검토
- local CUDA STT 후보 검토
- Google Cloud, Azure AI Speech, AWS Transcribe/Polly 외부 API 후보 검토. 단, 기본 구현 경로가 아니라 optional paid comparison 후보로 제한
- 공식 문서, 가격 문서, 데이터 처리 문서 링크 고정
- STT/TTS benchmark metric과 public-safe report grain 고정
- live call budget과 중단 조건 고정

제외:

- STT/TTS provider 실제 호출
- provider 최종 선택
- production voice service 구현
- raw audio, raw transcript, private eval payload 공개
- Solar Pro 3 generation 품질 재평가

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| 제품 | 서울/한양 관광 도슨트는 짧은 음성 질문과 짧은 spoken answer가 중요하다. browser native는 demo 접근성이 좋지만 지원 편차가 크다. |
| 음성 엔지니어링 | STT는 local CUDA 후보를 반드시 포함한다. 이후 전략 변경으로 TTS도 `MeloTTS Korean` local smoke를 먼저 검증하고, browser/managed TTS는 비교 후보로 둔다. |
| RAG 아키텍처 | 음성 provider 비교는 retrieval 성능 개선 주장이 아니다. `/api/v1/chat` contract와 `spoken_answer` 품질 보존 여부만 연결한다. |
| Evaluation | STT/TTS는 WER/CER만으로 부족하다. place name accuracy, round-trip latency, cost, privacy metric을 같이 봐야 한다. |
| Data warehouse | grain은 `work_id + provider_candidate_id + modality + metric_family + claim_boundary`로 둔다. raw audio/transcript는 금지 필드다. |
| 보안 | 외부 API 후보는 audio/transcript 외부 전송을 전제로 한다. 명시 승인, call cap, artifact sanitization 없이는 실행하지 않는다. |
| 포트폴리오 | "무조건 최신 API 사용"보다 "개인정보/비용/latency/한국어 장소명 정확도 기준으로 provider를 선별했다"가 더 강한 메시지다. |
| 외부 감사 | 계획 gate로는 적절하다. 다만 실제 benchmark 전에는 각 provider의 최신 가격, region, retention option을 실행일 기준으로 다시 확인해야 한다. |

## Provider Candidate Groups

| provider_candidate_id | modality | 후보 | 장점 | 주요 리스크 | 이번 결정 |
| --- | --- | --- | --- | --- | --- |
| `browser_native_web_speech` | STT/TTS | Web Speech API | backend secret 불필요, local demo 접근성 높음, browser TTS 사용 가능 | browser 지원 편차, STT 처리 위치와 품질 편차, 모바일 제약 | benchmark 후보 유지 |
| `local_cuda_whisper` | STT | OpenAI Whisper, faster-whisper | audio 외부 전송 없음, RTX 4080 SUPER CUDA 활용 가능, 비용 예측 쉬움 | model download, GPU dependency, realtime latency 검증 필요, TTS 별도 필요 | STT 후보 유지 |
| `external_google_cloud` | STT/TTS | Google Cloud Speech-to-Text, Text-to-Speech | managed STT/TTS, 한국어 지원 확인 가능, pricing/data logging 문서 명확 | billing, quota, audio/transcript 외부 전송 | optional paid comparison |
| `external_azure_speech` | STT/TTS | Azure AI Speech | speech-to-text/text-to-speech 통합, data privacy 문서 확인 가능 | region/price 변동, 외부 전송, Azure resource 설정 필요 | optional paid comparison |
| `external_aws_transcribe_polly` | STT/TTS | Amazon Transcribe + Amazon Polly | STT/TTS managed 조합, pricing/data protection 문서 확인 가능 | STT/TTS 서비스가 분리됨, 한국어 품질 별도 검증 필요, 비용/region 관리 필요 | optional paid comparison |

## 공식 문서 확인

확인일: 2026-05-19

| source_id | provider | 확인 목적 | URL |
| --- | --- | --- | --- |
| `web_speech_spec` | Web Speech API | browser STT/TTS 표준 경계 | https://webaudio.github.io/web-speech-api/ |
| `mdn_web_speech` | Web Speech API | browser API, SpeechRecognition/SpeechSynthesis 개요 | https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API |
| `openai_whisper_readme` | local CUDA STT | Whisper 모델과 transcription 사용 경계 | https://github.com/openai/whisper/blob/main/README.md |
| `faster_whisper_readme` | local CUDA STT | CTranslate2 기반 CUDA 실행, GPU dependency, benchmark 주의 | https://github.com/SYSTRAN/faster-whisper |
| `google_stt_pricing` | Google Cloud STT | audio length/channel/model 기반 과금 확인 | https://cloud.google.com/speech-to-text/pricing |
| `google_stt_data_logging` | Google Cloud STT | 기본 data logging/opt-in 경계 확인 | https://cloud.google.com/speech-to-text/docs/data-logging |
| `google_tts_pricing` | Google Cloud TTS | character/audio-token 기반 과금 확인 | https://cloud.google.com/text-to-speech/pricing |
| `azure_speech_pricing` | Azure AI Speech | STT hour, TTS character 기반 과금 확인 | https://azure.microsoft.com/en-us/pricing/details/speech/ |
| `azure_stt_privacy` | Azure AI Speech | speech-to-text data/privacy/security 경계 확인 | https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/speech-service/speech-to-text/data-privacy-security |
| `azure_tts_overview` | Azure AI Speech | text-to-speech 기능과 billing 단위 확인 | https://learn.microsoft.com/en-us/azure/ai-services/Speech-Service/text-to-speech |
| `aws_transcribe_pricing` | AWS Transcribe | STT duration billing 확인 | https://aws.amazon.com/transcribe/pricing/ |
| `aws_transcribe_data` | AWS Transcribe | shared responsibility와 data protection 경계 확인 | https://docs.aws.amazon.com/transcribe/latest/dg/data-protection.html |
| `aws_polly_pricing` | AWS Polly | TTS character billing 확인 | https://aws.amazon.com/polly/pricing/ |
| `aws_polly_data` | AWS Polly | shared responsibility와 sensitive field 입력 금지 확인 | https://docs.aws.amazon.com/polly/latest/dg/data-protection.html |

가격 숫자는 문서에 고정하지 않는다. provider benchmark 실행일의 공식 pricing page와 region을 다시 확인하고 report에는 확인일, region, pricing source URL만 남긴다.

## Local CUDA Readiness

현재 로컬 확인 결과:

| field | value |
| --- | --- |
| `local_cuda_available` | true |
| `cuda_device_count` | 1 |
| `cuda_device_name` | NVIDIA GeForce RTX 4080 SUPER |
| `driver_version` | 560.94 |
| `gpu_memory_total_mib` | 16376 |
| `torch_cuda_available` | true |

이 결과는 local STT 후보를 benchmark 계획에 포함할 근거다. faster-whisper 실행 가능성, cuBLAS/cuDNN runtime, model download, realtime latency는 아직 검증하지 않았다.

## Benchmark Dataset Plan

public repo에는 raw audio를 올리지 않는다. 다음 단계에서는 public-safe synthetic script만 사용하고, audio artifact가 필요하면 private local storage에서 생성한다.

| query_type | 목적 | public-safe script 예 |
| --- | --- | --- |
| `place_fact` | 장소명 인식과 짧은 사실 질문 | "경복궁은 왜 조선의 중심 궁궐이었어?" |
| `place_story` | 구어체 역사 설명 요청 | "광화문 근처에서 들을 만한 한양 이야기를 짧게 해줘." |
| `relationship` | 장소-인물-사건 연결 | "정도전이 한양 설계와 어떤 관련이 있어?" |
| `route_context` | 이동 중 맥락 질문 | "북촌에서 한양도성 쪽으로 걸어가면 어떤 이야기를 연결하면 좋아?" |
| `voice_followup` | 지시어/후속 질문 | "방금 말한 그 궁궐을 한 문장으로 다시 설명해줘." |
| `no_answer` | 모르는 질문 환각 방지 | "이 책에 없는 현대 카페 추천을 해줘." |

Benchmark set은 최소 30개 script로 시작한다. 외부 provider live call은 별도 승인 전까지 실행하지 않는다.

## Metrics

### STT Metrics

- `wer`
- `cer`
- `place_name_accuracy`
- `transcript_confirmation_required_rate`
- `stt_latency_p50_ms`
- `stt_latency_p95_ms`
- `stt_timeout_rate`
- `stt_error_rate`
- `estimated_stt_cost`

### TTS Metrics

- `playback_success_rate`
- `tts_latency_p50_ms`
- `tts_latency_p95_ms`
- `spoken_answer_length_violation_rate`
- `text_to_audio_mismatch_review_rate`
- `tts_error_rate`
- `estimated_tts_cost`

### End-to-End Voice Metrics

- `voice_round_trip_latency_p95_ms`
- `provider_call_count`
- `estimated_total_cost`
- `fallback_to_text_rate`
- `voice_ui_recovery_success_rate`

### Privacy and Safety Metrics

- `external_audio_transmission_count`
- `private_audio_saved_count`
- `raw_transcript_public_artifact_count`
- `client_secret_exposure_count`
- `public_private_path_leakage_count`
- `public_secret_like_leakage_count`
- `public_raw_payload_leakage_count`

## Planned Call Budget

이번 plan gate:

| metric | value |
| --- | ---: |
| `live_stt_call_count` | 0 |
| `live_tts_call_count` | 0 |
| `live_solar_call_count` | 0 |
| `provider_benchmark_execution_count` | 0 |

다음 benchmark readiness gate의 계획 상한:

| provider group | planned max STT calls | planned max TTS calls | 비고 |
| --- | ---: | ---: | --- |
| `browser_native_web_speech` | 10 | 10 | browser support가 확인될 때만 수동/자동 fixture 실행 |
| `local_cuda_whisper` | 30 | 0 | TTS 후보가 아니며 GPU runtime 확인 후 실행 |
| `external_google_cloud` | 20 | 20 | 별도 승인과 billing cap 필요 |
| `external_azure_speech` | 20 | 20 | 별도 승인과 resource/region 확인 필요 |
| `external_aws_transcribe_polly` | 20 | 20 | STT/TTS 서비스별 credential과 cost cap 필요 |

외부 provider는 실행 전 사용자 승인, region, 예상 비용, privacy boundary, artifact sanitization path를 다시 확인한다.

## Stop Conditions

다음 조건 중 하나라도 발생하면 provider benchmark를 중단한다.

- 공식 가격 문서나 region별 과금 기준을 확인하지 못함
- audio/transcript retention 또는 logging 경계가 불명확함
- secret을 browser bundle에 넣어야만 동작함
- public artifact에 raw audio, raw transcript, private path, raw prompt가 남음
- `stt_latency_p95_ms` 또는 `tts_latency_p95_ms`가 demo SLO 후보를 크게 초과함
- 한국어 장소명 accuracy가 낮아 관광 도슨트 UX를 해침
- provider quota, billing, rate limit이 작은 benchmark에도 불안정함
- local CUDA runtime dependency가 재현 불가능함

## Data Mart Grain

`fact_voice_stt_tts_provider_bench_plan`의 grain은 `work_id + provider_candidate_id + modality + metric_family + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-PLAN-001` |
| `provider_candidate_id` | provider group id |
| `modality` | `stt`, `tts`, `stt_tts`, `e2e` |
| `metric_family` | quality, latency, cost, privacy, reliability |
| `source_checked_at` | 공식 문서 확인일 |
| `claim_boundary` | plan-only, readiness-only, live-benchmark-only |
| `decision` | keep_candidate, reject_candidate, needs_readiness |
| `evidence_artifact` | public-safe report path |

금지 필드:

- raw audio
- raw transcript
- raw answer
- raw evidence
- raw prompt
- raw chunk text
- private file path
- secret

## 금지 Claim

- production 성능 검증 완료
- locked test에서 최종 성능 개선 입증
- GraphRAG로 성능 개선
- RAPTOR로 성능 개선
- HyDE로 최종 검색 성능 개선
- Solar Pro 3 답변 품질 최종 개선
- 음성 관광 앱 완성
- STT/TTS 품질 검증 완료
- provider 최종 선택 완료
- Web Speech API가 모든 browser에서 안정 동작
- local CUDA Whisper가 realtime STT 요구사항 충족
- Google Cloud, Azure, AWS 중 특정 provider가 최적
- 전체 도서 데이터 공개

## 다음 작업 지시서

| field | value |
| --- | --- |
| `id` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001` |
| `depends_on` | `HD-VOICE-STT-TTS-PROVIDER-BENCH-PLAN-001` |
| `scope` | public-safe voice benchmark fixture script, provider config skeleton, no-live-call readiness runner 작성 |
| `acceptance_tests` | fixture script 30개, provider candidate config 5개, live call 0, CUDA runtime preflight, pricing/privacy source recheck field, public leakage 0 |
| `risk_level` | Medium |
| `rollback_plan` | 새 readiness 문서, config skeleton, tests revert |

## 외부 감사 결론

PASS.

이번 단계는 provider 선택을 미루고, 실행 전 비교 조건을 고정했다. 포트폴리오 관점에서도 "음성 기능을 붙였다"가 아니라 "음성 provider를 비용, 개인정보, latency, 한국어 장소명 정확도 기준으로 비교할 수 있게 설계했다"는 메시지가 타당하다.
