# Portfolio Demo Runbook Refresh Report

## 결론

`HD-VOICE-DEMO-RUNBOOK-REFRESH-001`은 통과다.

`docs/PORTFOLIO_DEMO_RUNBOOK.md`에 최신 무료 로컬 음성 evidence를 반영했다. 이번 작업은 제출용 demo 순서와 claim boundary 갱신이며, production 음성 관광 앱 완성, STT/TTS provider 최종 확정, 실제 관광객 음성 품질 검증을 의미하지 않는다.

## 정량 결과

| metric | value |
| --- | ---: |
| refreshed_runbook_document_count | 1 |
| refresh_report_count | 1 |
| regression_test_file_count | 1 |
| demo_step_count | 7 |
| voice_demo_stack_decision_artifact_count | 1 |
| voice_playback_smoke_artifact_count | 2 |
| voice_route_smoke_artifact_count | 2 |
| default_disabled_voice_route_count | 1 |
| explicit_flag_voice_route_contract_count | 1 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| private_corpus_required_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| production_voice_app_claim_count | 0 |
| forbidden_claim_count | 13 |

## 정성 평가

| gate | result | 근거 |
| --- | --- | --- |
| Demo sequence | PASS | RAG decision, `/api/v1/chat`, frontend, playback smoke, voice route smoke 순서로 설명 경로를 갱신했다. |
| Voice evidence | PASS | `VOICE_DEMO_STACK_DECISION`, `VOICE_DEMO_PLAYBACK_SMOKE`, `VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE`를 같은 demo 흐름에 연결했다. |
| Security | PASS | API key, raw audio, transcript, private corpus, private path 없이 공개 runbook을 유지했다. |
| Claim boundary | PASS | 허용 claim과 금지 claim을 분리했고 production voice app claim을 금지했다. |
| Evaluation | PASS | `pytest`, `ruff`, frontend smoke, route smoke command를 runbook에 남겼다. |
| External audit | PASS | 이미 끝난 route smoke를 제출용 설명에 반영하는 작업이므로 추가 모델 호출보다 runbook 갱신이 우선이라는 판단이 타당하다. |

## Claim Boundary

허용:

- 포트폴리오 demo runbook을 최신 음성 route smoke 상태로 갱신했다.
- local voice playback smoke에서 private wav 5개 playback-ready 상태를 확인했다.
- local voice API route smoke에서 기본 비활성화와 explicit local flag contract를 확인했다.
- 해당 demo evidence에서 external provider call과 external audio transmission은 0으로 유지했다.

금지:

- production 성능 검증 완료
- locked test에서 최종 성능 개선 입증
- GraphRAG로 성능 개선
- RAPTOR로 성능 개선
- HyDE로 최종 검색 성능 개선
- Solar Pro 3 답변 품질 최종 개선
- production 음성 관광 앱 완성
- STT/TTS production 품질 검증 완료
- STT/TTS provider 최종 확정
- 실제 관광객 음성 품질 검증 완료
- microphone capture 구현 완료
- speaker playback 구현 완료
- 전체 도서 데이터 공개

## Data Mart Grain

`fact_portfolio_demo_runbook_refresh`의 grain은 `work_id + demo_step_id + artifact_family + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-VOICE-DEMO-RUNBOOK-REFRESH-001` |
| `demo_step_id` | quick_check, api_contract, frontend_fixture, frontend_backend, local_voice_route_evidence, visual_evidence, interview_script |
| `artifact_family` | rag_decision, api_contract, frontend, voice_stack, playback_smoke, route_smoke, visual_evidence |
| `claim_boundary` | public-safe, contract-only, route-smoke-only, no-live-call, no-production-claim |

금지 필드:

- raw answer
- raw transcript
- raw audio
- raw prompt
- private path
- secret

## 다음 Gate

다음 작업 후보는 `HD-SUBMISSION-REFRESH-AUDIT-V2-001`이다.

권장 작업 단위:

- `id`: `HD-SUBMISSION-REFRESH-AUDIT-V2-001`
- `depends_on`: `HD-VOICE-DEMO-RUNBOOK-REFRESH-001`
- `scope`: 갱신된 runbook과 README, voice evidence link, 금지 claim, public-safe scan을 제출 직전 기준으로 재검증
- `acceptance_tests`: README link current, demo runbook refresh reflected, forbidden claim only in boundary sections, private path/secret/raw audio public leakage 0, production voice app claim 0
- `risk_level`: low
- `rollback_plan`: audit v2 문서와 테스트만 revert
