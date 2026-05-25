# Voice Demo Stack Decision

## 결론

`HD-VOICE-DEMO-STACK-DECISION-001`의 결론은 무료 로컬 음성 데모 스택을 다음처럼 정리하는 것이다.

- STT demo 후보: `local_faster_whisper_small_cuda`
- TTS demo review 후보: `local_sherpa_onnx_supertonic3_ko`
- TTS production final provider: 아직 확정하지 않음
- managed provider: Azure, Google, AWS는 optional paid comparison only

근거는 `faster-whisper small CUDA`의 local STT 비교 결과와 `sherpa-onnx Supertonic 3 Korean`의 private wav smoke, 자동 proxy 4/5, 사용자 제공 사람 청취 점수 30/30 평균 5.0이다. 단, 이 결과는 1인 청취 기반 demo review 후보 수락이며 실제 관광객 검증, production 품질 보증, 최종 provider 확정이 아니다.

## Decision

| item | decision | 근거 | claim boundary |
| --- | --- | --- | --- |
| STT | `local_faster_whisper_small_cuda`를 demo primary 후보로 유지 | 같은 5개 private wav fixture에서 기존 local Whisper보다 현재 evidence가 좋음 | demo evidence only |
| TTS | `local_sherpa_onnx_supertonic3_ko`를 demo review 후보로 수락 | private wav 5개, 자동 audio sanity 통과, 자동 proxy 4/5, 사람 청취 점수 30/30 평균 5.0 | demo review candidate only |
| TTS final provider | 미확정 | 청취자는 1명이고 실제 관광객 환경 검증이 없음 | no production final claim |
| Managed provider | optional paid comparison only | 비용, credential, 외부 음성 전송, retention 확인 필요 | explicit approval only |

## 정량 요약

| metric | value |
| --- | ---: |
| primary_local_stt_candidate_count | 1 |
| tts_demo_candidate_count | 1 |
| tts_final_provider_count | 0 |
| managed_provider_default_count | 0 |
| optional_paid_provider_candidate_count | 3 |
| local_tts_private_audio_available_count | 5 |
| tts_automated_proxy_pass_count | 4 |
| tts_automated_proxy_total_count | 5 |
| tts_human_score_completed_count | 30 |
| tts_human_score_expected_count | 30 |
| tts_human_score_overall_avg | 5.000000 |
| tts_human_score_reviewer_count | 1 |
| human_score_public_detail_row_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| 제품 | 취업 포트폴리오 demo에서는 비용 없이 반복 실행 가능한 local-first 음성 스택이 적합하다. |
| 음성 ML | `faster-whisper small CUDA`는 현재 STT 후보로 유지한다. TTS는 `sherpa-onnx Supertonic 3 Korean`을 데모 후보로 올리되 최종 provider로 확정하지 않는다. |
| 아키텍처 | `/api/v1/chat`는 text-first RAG 계약을 유지하고, voice adapter가 STT transcript와 TTS playback을 감싼다. |
| 보안 | 기본 경로의 외부 provider 호출과 외부 음성 전송은 0이어야 한다. private wav와 개별 점수는 공개하지 않는다. |
| Evaluation | 1인 청취 점수는 강한 demo evidence지만 production 품질 검증은 아니다. 추후 다중 청취자 또는 실제 관광 소음 환경 평가가 필요하다. |
| Data warehouse | public fact는 `work_id + provider_candidate_id + modality + metric_family + claim_boundary` grain으로 유지하고, private score detail은 public artifact에서 제외한다. |
| 외부 감사 | 이전 `blocked_missing_human_scores`는 당시 기준으로 타당했고, 이번 판단은 사람 점수 입력 이후의 최신 decision layer로 분리한 점이 타당하다. |

## Claim Boundary

허용:

- 무료 로컬 음성 demo stack 후보를 정리했다.
- `local_faster_whisper_small_cuda`를 현재 demo evidence 기준 STT primary 후보로 유지한다.
- `local_sherpa_onnx_supertonic3_ko`를 사람 청취 점수 기반 demo review 후보로 수락했다.
- 외부 STT/TTS provider 호출과 외부 음성 전송은 0으로 유지했다.

금지:

- 무료 로컬 TTS 최종 provider 확정
- Supertonic 3 음성 품질 우수 production 검증 완료
- 실제 관광객 음성 품질 검증 완료
- production 음성 관광 앱 완성
- Azure/Google/AWS보다 local TTS가 품질 우수하다는 주장

## 후속 작업 결과

| field | value |
| --- | --- |
| `id` | `HD-VOICE-DEMO-PLAYBACK-SMOKE-001` |
| `depends_on` | `HD-VOICE-DEMO-STACK-DECISION-001` |
| `status` | completed |
| `scope` | local STT/TTS demo 후보의 private wav 5개 playback-ready 상태를 검증했다. |
| `acceptance_tests` | local STT candidate 1, TTS demo candidate 1, playback-ready 5, speaker 자동 재생 0, external provider call 0, raw audio public artifact 0, human score detail public row 0, production claim 0 |
| `evidence` | `docs/VOICE_DEMO_PLAYBACK_SMOKE.md`, `evals/reports/voice_demo_playback_smoke_report.md` |

## 후속 작업 결과

| field | value |
| --- | --- |
| `id` | `HD-VOICE-API-LOCAL-RUNTIME-ROUTE-SMOKE-001` |
| `depends_on` | `HD-VOICE-DEMO-PLAYBACK-SMOKE-001` |
| `status` | completed |
| `scope` | local-only voice runtime API route를 기본 비활성화 상태와 explicit local flag 상태에서 contract smoke로 검증했다. |
| `acceptance_tests` | default disabled 1, explicit flag contract response 1, validation reject 2, external provider call 0, raw audio/transcript public artifact 0, secret leakage 0 |
| `evidence` | `docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md`, `evals/reports/voice_api_local_runtime_route_smoke_report.md` |

## 후속 작업 결과

| field | value |
| --- | --- |
| `id` | `HD-VOICE-DEMO-RUNBOOK-REFRESH-001` |
| `depends_on` | `HD-VOICE-API-LOCAL-RUNTIME-ROUTE-SMOKE-001` |
| `status` | completed |
| `scope` | portfolio demo runbook에 최신 local voice playback smoke와 local voice API route smoke 결과를 반영하고, demo에서 말할 allowed/forbidden claim을 갱신했다. |
| `acceptance_tests` | runbook link updated, voice API route smoke metric reflected, production voice app claim 0, raw audio/transcript public artifact 0, secret leakage 0 |
| `evidence` | `docs/PORTFOLIO_DEMO_RUNBOOK.md`, `evals/reports/portfolio_demo_runbook_refresh_report.md` |

## 다음 작업 지시서

| field | value |
| --- | --- |
| `id` | `HD-SUBMISSION-REFRESH-AUDIT-V2-001` |
| `depends_on` | `HD-VOICE-DEMO-RUNBOOK-REFRESH-001` |
| `status` | completed |
| `scope` | 갱신된 README, demo runbook, voice evidence link, 금지 claim, public-safe scan을 제출 직전 기준으로 재검증했다. |
| `acceptance_tests` | README link current, runbook refresh reflected, forbidden claim only in boundary sections, private path/secret/raw audio public leakage 0, production voice app claim 0 |
| `evidence` | `docs/SUBMISSION_REFRESH_AUDIT_V2.md`, `evals/reports/submission_refresh_audit_v2_report.md` |

## 다음 작업 지시서

| field | value |
| --- | --- |
| `id` | `HD-PORTFOLIO-FINAL-PACKAGE-INDEX-001` |
| `depends_on` | `HD-SUBMISSION-REFRESH-AUDIT-V2-001` |
| `status` | completed |
| `scope` | README, final ablation, demo runbook, voice evidence, forbidden claim을 한 화면에서 따라갈 수 있는 제출용 index를 정리했다. |
| `acceptance_tests` | final index document count 1, required link count, forbidden claim section exists, private path/secret/raw payload leakage 0, production success claim 0 |
| `evidence` | `docs/PORTFOLIO_FINAL_PACKAGE_INDEX.md`, `evals/reports/portfolio_final_package_index_report.md` |

## 다음 작업 지시서

| field | value |
| --- | --- |
| `id` | `HD-README-LANDING-POLISH-001` |
| `depends_on` | `HD-PORTFOLIO-FINAL-PACKAGE-INDEX-001` |
| `scope` | README 첫 화면을 채용 담당자가 60초 안에 읽을 수 있도록 더 짧게 재배치한다. |
| `acceptance_tests` | top summary under 1 screen, final package index linked, forbidden claim unchanged, private path/secret leakage 0, production success claim 0 |
| `risk_level` | Low |
| `rollback_plan` | README와 관련 테스트만 revert한다. |
