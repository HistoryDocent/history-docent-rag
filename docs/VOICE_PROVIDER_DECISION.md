# Voice Provider Decision

## 결론

`HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001`의 결론은 STT/TTS 기본 전략을 무료 로컬 provider 우선으로 변경하는 것이다.

Azure AI Speech, Google Cloud, AWS Transcribe/Polly 같은 managed provider는 기본 구현 경로가 아니라 optional paid comparison 후보로 둔다. 이유는 비용, 계정 설정, 외부 음성 전송, secret 관리가 발생하기 때문이다. 취업 포트폴리오 기준으로는 local-first 전략이 개인정보, 비용 통제, GPU 활용, 재현 가능한 실험 메시지를 더 잘 만든다.

## 변경 결정

| 항목 | 이전 흐름 | 변경 후 흐름 |
| --- | --- | --- |
| 기본 STT 후보 | local CUDA Whisper 실험 후 managed provider smoke로 진행 | `faster-whisper` local CUDA를 기본 STT 후보로 유지 |
| 기본 TTS 후보 | browser/managed TTS 중심 benchmark 후보 | `MeloTTS Korean` local TTS smoke를 다음 우선순위로 지정 |
| managed provider | Azure first smoke gate | optional paid comparison only |
| 외부 음성 전송 | 별도 승인 후 가능 | 기본값 0, paid comparison에서만 별도 승인 |
| secret 필요성 | Azure credential gate 필요 | local baseline에는 secret 불필요 |
| 포트폴리오 메시지 | managed provider smoke 준비 | 무료 로컬 음성 pipeline을 우선 설계하고 managed는 비용/품질 비교 후보로 격하 |

## Provider 후보 판단

| provider_candidate_id | modality | 비용/실행 | 라이선스/운영 판단 | 결정 |
| --- | --- | --- | --- | --- |
| `local_faster_whisper_cuda` | STT | 로컬 실행, API 비용 없음 | Whisper는 MIT, faster-whisper는 CUDA 실행에 적합 | primary STT |
| `local_melotts_korean` | TTS | 로컬 실행, API 비용 없음 | MeloTTS는 Korean 지원과 MIT license를 명시 | primary TTS smoke 후보 |
| `local_sherpa_onnx` | STT/TTS | 로컬 실행, API 비용 없음 | Apache-2.0, offline STT/TTS toolkit 후보 | secondary local 후보 |
| `local_piper` | TTS | 로컬 실행, API 비용 없음 | 현재 주요 repo는 GPL-3.0이므로 포트폴리오/배포 라이선스 검토 필요 | optional only |
| `managed_azure_ai_speech` | STT/TTS | cloud API, free tier가 있어도 사용량/계정/과금 관리 필요 | 외부 음성 전송과 credential 필요 | optional paid comparison |
| `managed_google_cloud_speech_tts` | STT/TTS | cloud API, 과금/credential 필요 | 외부 음성 전송과 data policy 재확인 필요 | optional paid comparison |
| `managed_aws_transcribe_polly` | STT/TTS | cloud API, 과금/credential 필요 | STT/TTS 서비스 분리, region/cost 재확인 필요 | optional paid comparison |

## 근거 Source

확인일: 2026-05-19

| source_id | 확인 내용 | URL |
| --- | --- | --- |
| `openai_whisper` | Whisper는 multilingual speech recognition 모델이며 MIT license로 공개되어 있음 | https://github.com/openai/whisper |
| `faster_whisper` | CTranslate2 기반 Whisper 구현, CUDA 사용 예시와 GPU benchmark 제공 | https://github.com/SYSTRAN/faster-whisper |
| `melotts` | Korean 포함 multilingual TTS, MIT license, CPU real-time inference 언급 | https://github.com/myshell-ai/MeloTTS |
| `sherpa_onnx` | offline STT/TTS/VAD 등을 지원하는 Apache-2.0 toolkit | https://github.com/k2-fsa/sherpa-onnx |
| `piper1_gpl` | fast local neural TTS, 현재 주요 repo는 GPL-3.0 | https://github.com/OHF-Voice/piper1-gpl |
| `azure_speech_pricing` | Azure Speech는 pricing/free tier가 존재하지만 cloud billing 관리가 필요 | https://azure.microsoft.com/en-us/pricing/details/speech/ |

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| 제품 | 서울 관광 도슨트 demo는 비용 없이 반복 실행되는 local voice가 더 적합하다. |
| 음성 ML | STT는 이미 local CUDA Whisper 계열 실험이 있으므로 이어간다. TTS는 Korean 지원과 license가 명확한 MeloTTS를 먼저 검증한다. |
| 아키텍처 | `/api/v1/chat`는 text-first로 유지한다. voice adapter는 STT transcript와 TTS playback을 감싸는 외부 계층이다. |
| 보안 | 기본 전략은 external audio transmission 0이다. managed provider는 별도 승인과 public-safe artifact gate가 있을 때만 실행한다. |
| Evaluation | STT/TTS provider 선택은 RAG 성능 개선 주장이 아니다. WER/CER, place name accuracy, TTS playback, latency, privacy metric을 분리한다. |
| Data warehouse | fact grain은 `work_id + provider_candidate_id + modality + metric_family + claim_boundary`로 유지하되 local/managed 구분 dimension을 추가한다. |
| 외부 감사 | Azure gate를 삭제하지 않고 optional paid comparison으로 남기는 판단은 타당하다. 다만 README의 다음 단계가 managed live smoke로 보이면 안 된다. |

## 평가 Gate

이번 decision gate는 실제 모델 실행이 아니다.

| metric | value | 설명 |
| --- | ---: | --- |
| `local_first_strategy_document_count` | 1 | 이 문서 |
| `local_first_strategy_report_count` | 1 | public-safe 평가 리포트 |
| `default_external_audio_transmission_count` | 0 | 기본 strategy에서는 외부 음성 전송 금지 |
| `managed_provider_default_count` | 0 | managed provider를 기본 provider로 채택하지 않음 |
| `paid_provider_optional_count` | 3 | Azure, Google, AWS는 optional paid comparison 후보 |
| `primary_local_stt_candidate_count` | 1 | `local_faster_whisper_cuda` |
| `primary_local_tts_candidate_count` | 1 | `local_melotts_korean` |
| `secret_required_for_default_voice_count` | 0 | local-first baseline은 credential 없이 실행 가능해야 함 |
| `raw_audio_public_artifact_count` | 0 | public repo 금지 |
| `raw_transcript_public_artifact_count` | 0 | public repo 금지 |

## 다음 작업 지시서

| field | value |
| --- | --- |
| `id` | `HD-VOICE-STT-TTS-LOCAL-TTS-SMOKE-001` |
| `depends_on` | `HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001` |
| `scope` | `MeloTTS Korean` local TTS smoke 실행 조건, 설치 gate, public-safe script subset, private audio output boundary를 구현한다. |
| `acceptance_tests` | local TTS candidate 1개 이상, public-safe script 5개, external provider call 0, external audio transmission 0, raw audio/transcript public artifact 0, TTS latency/playback metric 기록 |
| `risk_level` | Medium |
| `rollback_plan` | local TTS smoke 관련 runner, docs, report, tests만 revert한다. |

후속 실행 결과: `HD-VOICE-STT-TTS-LOCAL-TTS-SMOKE-001`에서 runner와 public-safe report를 추가했고, 현재 환경은 CUDA를 감지했지만 MeloTTS runtime 미설치로 실제 합성은 차단됐다. 이 결과는 TTS 품질 검증 완료가 아니라 runtime gate 결과다.

## 금지 Claim

- 무료 로컬 TTS 품질 검증 완료
- MeloTTS가 최종 provider로 확정
- Azure보다 local TTS가 품질 우수
- production 음성 관광 앱 완성
- browser/mobile 전체에서 voice UX 검증 완료
- 외부 API 없이 모든 기능 production-ready

## 외부 감사 결론

PASS.

기존 Azure gate는 실행을 차단한 증거로 유지하고, 기본 전략은 무료 로컬 STT/TTS로 바꾸는 것이 타당하다. local TTS smoke runner는 추가됐지만 현재 runtime missing 상태이므로 다음 단계는 managed provider가 아니라 local MeloTTS runtime 설치와 재실행이다.
