# Voice Provider Decision

## 결론

`HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001`의 결론은 STT/TTS 기본 전략을 무료 로컬 provider 우선으로 변경하는 것이다.

Azure AI Speech, Google Cloud, AWS Transcribe/Polly 같은 managed provider는 기본 구현 경로가 아니라 optional paid comparison 후보로 둔다. 이유는 비용, 계정 설정, 외부 음성 전송, secret 관리가 발생하기 때문이다. 취업 포트폴리오 기준으로는 local-first 전략이 개인정보, 비용 통제, GPU 활용, 재현 가능한 실험 메시지를 더 잘 만든다.

## 변경 결정

| 항목 | 이전 흐름 | 변경 후 흐름 |
| --- | --- | --- |
| 기본 STT 후보 | local CUDA Whisper 실험 후 managed provider smoke로 진행 | `faster-whisper` local CUDA를 기본 STT 후보로 유지 |
| 기본 TTS 후보 | browser/managed TTS 중심 benchmark 후보 | 현재 실행 baseline은 Windows SAPI fallback, Piper는 Korean voice 부재로 차단, 다음은 무료 로컬 한국어 TTS 대안 검토 |
| managed provider | Azure first smoke gate | optional paid comparison only |
| 외부 음성 전송 | 별도 승인 후 가능 | 기본값 0, paid comparison에서만 별도 승인 |
| secret 필요성 | Azure credential gate 필요 | local baseline에는 secret 불필요 |
| 포트폴리오 메시지 | managed provider smoke 준비 | 무료 로컬 음성 pipeline을 우선 설계하고 managed는 비용/품질 비교 후보로 격하 |

## Provider 후보 판단

| provider_candidate_id | modality | 비용/실행 | 라이선스/운영 판단 | 결정 |
| --- | --- | --- | --- | --- |
| `local_faster_whisper_cuda` | STT | 로컬 실행, API 비용 없음 | Whisper는 MIT, faster-whisper는 CUDA 실행에 적합 | primary STT |
| `local_windows_sapi_pyttsx3_korean_fallback` | TTS | 로컬 실행, API 비용 없음 | 현재 Windows 환경에서 실행된 fallback이며 품질 후보는 아님 | current fallback |
| `local_piper` | TTS | 로컬 실행, API 비용 없음 | runtime은 설치됐지만 공식 voice manifest에 Korean voice가 없어 현재 한국어 후보로 부적합 | blocked missing Korean voice |
| `local_melotts_korean` | TTS | 로컬 실행, API 비용 없음 | MeloTTS는 Korean 지원과 MIT license를 명시하지만 현재 Windows `eunjeon` blocker가 있음 | blocked optional |
| `local_sherpa_onnx_supertonic3_ko` | TTS | 로컬 실행, API 비용 없음 | sherpa-onnx Supertonic 3 Korean smoke에서 5개 public-safe script private wav 합성 완료. 음질 우수와 최종 provider 확정은 별도 review 전 금지 | completed local smoke candidate |
| `managed_azure_ai_speech` | STT/TTS | cloud API, free tier가 있어도 사용량/계정/과금 관리 필요 | 외부 음성 전송과 credential 필요 | optional paid comparison |
| `managed_google_cloud_speech_tts` | STT/TTS | cloud API, 과금/credential 필요 | 외부 음성 전송과 data policy 재확인 필요 | optional paid comparison |
| `managed_aws_transcribe_polly` | STT/TTS | cloud API, 과금/credential 필요 | STT/TTS 서비스 분리, region/cost 재확인 필요 | optional paid comparison |

## 근거 Source

확인일: 2026-05-20

| source_id | 확인 내용 | URL |
| --- | --- | --- |
| `openai_whisper` | Whisper는 multilingual speech recognition 모델이며 MIT license로 공개되어 있음 | https://github.com/openai/whisper |
| `faster_whisper` | CTranslate2 기반 Whisper 구현, CUDA 사용 예시와 GPU benchmark 제공 | https://github.com/SYSTRAN/faster-whisper |
| `melotts` | Korean 포함 multilingual TTS, MIT license, CPU real-time inference 언급 | https://github.com/myshell-ai/MeloTTS |
| `sherpa_onnx` | offline STT/TTS/VAD 등을 지원하는 Apache-2.0 toolkit | https://github.com/k2-fsa/sherpa-onnx |
| `piper1_gpl` | fast local neural TTS, 현재 주요 repo는 GPL-3.0 | https://github.com/OHF-Voice/piper1-gpl |
| `piper_voices_manifest` | 공식 voice manifest 기준 161개 voice, 49개 language 중 Korean voice 0개 확인 | https://huggingface.co/rhasspy/piper-voices |
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

추가 실행 결과: `HD-VOICE-STT-TTS-LOCAL-RUNTIME-MATRIX-001`에서 무료 로컬 후보 5개를 preflight했다. 당시 import 가능한 후보는 기존 `openai-whisper` fallback 1개뿐이며, `faster-whisper`, `MeloTTS`, `sherpa-onnx`, `piper` 계열은 미설치였다. 설치, 모델 다운로드, STT/TTS 실행, 외부 provider 호출은 모두 0으로 유지했다.

추가 실행 결과: `HD-VOICE-STT-TTS-LOCAL-TTS-RUNTIME-INSTALL-001`에서 MeloTTS를 격리 Python 3.11 환경에 설치하고 CUDA torch, import, model load까지 확인했다. Korean synthesis는 Windows `eunjeon` build dependency로 차단됐고, 무료 로컬 fallback으로 Windows SAPI Korean voice를 사용해 private wav 5개를 생성했다. 외부 provider 호출과 외부 음성 전송은 0으로 유지했다.

추가 실행 결과: `HD-VOICE-STT-TTS-LOCAL-ADAPTER-INTEGRATION-001`에서 local Whisper STT 후보, `/api/v1/chat` contract, Windows SAPI TTS fallback을 5개 script로 연결했다. local STT 실행 5건, chat contract 실행 5건, local TTS 실행 5건이며 외부 provider 호출과 외부 음성 전송은 0으로 유지했다.

추가 실행 결과: `HD-VOICE-LOCAL-E2E-EVAL-001`에서 30개 public-safe script 기준 local voice E2E regression을 실행했다. input TTS 생성 30건, CUDA Whisper STT 실행 30건, chat contract 실행 30건, output TTS 생성 30건이며 외부 provider 호출과 외부 음성 전송은 0으로 유지했다.

추가 실행 결과: `HD-VOICE-LOCAL-RUNTIME-CONTRACT-001`에서 local-only voice runtime contract와 기본 비활성화 API route를 구현했다. private wav 입력 검증 5건, validation reject 3건, chat contract 실행 5건, local TTS 실행 5건이며 외부 provider 호출과 외부 음성 전송은 0으로 유지했다.

추가 실행 결과: `HD-VOICE-LOCAL-FREE-STT-TTS-BENCH-V2-001`에서 무료 로컬 STT/TTS current baseline과 next target을 분리했다. 현재 실행 근거는 `openai-whisper small CUDA` STT와 Windows SAPI fallback TTS이고, 다음 target은 `faster-whisper`와 `Piper`다. 새 패키지 설치, 모델 다운로드, 외부 provider 호출, 외부 음성 전송은 모두 0으로 유지했다.

추가 실행 결과: `HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001`에서 `openai-whisper small CUDA` baseline과 `faster-whisper small CUDA`를 같은 5개 private wav fixture로 비교했다. `faster-whisper` 실행 5건, paired script 5건, external provider 호출 0건, 외부 음성 전송 0건이며 현재 evidence 기준 STT 후보는 `local_faster_whisper_small_cuda`로 기록한다. 단, 이는 production 최종 provider 확정이나 실제 관광객 음성 품질 검증이 아니다.

추가 실행 결과: `HD-VOICE-LOCAL-PIPER-TTS-SMOKE-001`에서 `piper-tts` runtime 설치와 공식 voice manifest를 확인했다. manifest 기준 161개 voice, 49개 language 중 Korean voice는 0개라서 local TTS 실행은 0건으로 차단했고, external provider 호출과 외부 음성 전송은 0으로 유지했다. 따라서 Piper는 현재 Korean TTS 기본 provider가 아니다.

추가 실행 결과: `HD-VOICE-LOCAL-KOREAN-TTS-ALTERNATIVE-REVIEW-001`에서 무료 로컬 한국어 TTS 후보 7개를 검토했다. 다음 smoke 후보는 `local_sherpa_onnx_supertonic3_ko`이며, 이 gate에서는 설치, 모델 다운로드, local TTS 실행, external provider 호출, 외부 음성 전송을 모두 0으로 유지했다. 따라서 아직 한국어 TTS 품질 검증 완료나 최종 provider 확정으로 표현하지 않는다.

추가 실행 결과: `HD-VOICE-LOCAL-SHERPA-ONNX-SUPERTONIC3-KO-SMOKE-001`에서 `sherpa-onnx` runtime 설치와 Supertonic 3 Korean private model을 기준으로 5개 public-safe script를 private wav로 합성했다. local TTS 실행 5건, model file available 7건, external provider 호출 0건, 외부 음성 전송 0건으로 기록했다. 단, sherpa-onnx Supertonic 3 Korean은 아직 음질 우수 검증이나 최종 TTS provider 확정이 아니다.

## 금지 Claim

- 무료 로컬 TTS 품질 검증 완료
- MeloTTS 또는 Piper가 최종 provider로 확정
- Piper 한국어 합성 품질 검증 완료
- Supertonic 3 또는 sherpa-onnx 한국어 TTS 품질 검증 완료
- Supertonic 3 음성 품질 우수 검증 완료
- 무료 로컬 TTS 최종 provider 확정
- Azure보다 local TTS가 품질 우수
- production 음성 관광 앱 완성
- browser/mobile 전체에서 voice UX 검증 완료
- 외부 API 없이 모든 기능 production-ready

## 외부 감사 결론

PASS.

기존 Azure gate는 실행을 차단한 증거로 유지하고, 기본 전략은 무료 로컬 STT/TTS로 바꾸는 것이 타당하다. local runtime install retry 기준 MeloTTS는 아직 Korean synthesis blocker가 있으므로 최종 provider로 확정하지 않는다. Windows SAPI Korean fallback은 30개 local voice E2E regression과 local-only runtime contract까지 연결됐지만 production voice app 완성이나 최종 STT/TTS 품질 검증으로 표현하지 않는다. Bench v2 기준으로는 `faster-whisper`와 `Piper`를 다음 실행 target으로 분리했고, faster-whisper STT 비교 기준으로는 현재 evidence 후보를 `local_faster_whisper_small_cuda`로 올린다. Piper smoke 기준으로는 runtime은 가능하지만 Korean voice 0개이므로 한국어 TTS 기본 provider에서 제외한다. Korean TTS alternative review 이후 `local_sherpa_onnx_supertonic3_ko`는 실제 private wav smoke까지 통과했지만, 품질 청취 평가 전에는 최종 provider나 실제 관광객 품질 검증으로 표현하지 않는다. STT/TTS 최종 provider 확정과 실제 관광객 음성 품질 검증 claim은 계속 금지한다.
