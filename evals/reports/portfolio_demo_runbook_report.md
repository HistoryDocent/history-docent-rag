# Portfolio Demo Runbook Report

## 결론

`HD-PORTFOLIO-DEMO-001`은 통과이며, `HD-VOICE-DEMO-RUNBOOK-REFRESH-001` 기준으로 최신화했다.

포트폴리오 제출용 local demo runbook을 최신 음성 evidence에 맞게 갱신했다. 이번 결과는 contract-only API와 browser voice-ready UI, local voice demo stack decision, playback smoke, voice API route smoke를 안전하게 시연하는 절차이며, production 배포, live Solar Pro 3 품질 검증, STT/TTS production 품질 검증, private corpus 재현을 의미하지 않는다.

## 정량 결과

| metric | value |
| --- | ---: |
| demo_runbook_document_count | 1 |
| demo_step_count | 7 |
| runbook_command_block_count | 9 |
| required_artifact_link_count | 7 |
| forbidden_claim_count | 13 |
| troubleshooting_case_count | 5 |
| backend_demo_port_count | 1 |
| frontend_demo_port_count | 1 |
| contract_only_demo_count | 2 |
| fixture_demo_count | 1 |
| voice_playback_smoke_artifact_count | 2 |
| voice_route_smoke_artifact_count | 2 |
| default_disabled_voice_route_count | 1 |
| explicit_flag_voice_route_contract_count | 1 |
| live_solar_call_count | 0 |
| retrieval_execution_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| production_voice_app_claim_count | 0 |
| private_corpus_required_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## 정성 평가

| gate | result | 근거 |
| --- | --- | --- |
| Demo flow | PASS | README, final ablation, API sample, contract smoke, voice UI, local voice route smoke 순서로 설명 경로를 고정했다. |
| Backend clarity | PASS | `/api/v1/chat` contract-only request와 확인 필드를 분리했다. |
| Frontend clarity | PASS | fixture mode와 backend mode의 목적을 분리했다. |
| Voice route clarity | PASS | 기본 비활성화, explicit local flag contract, external provider call 0을 분리해 설명했다. |
| Security | PASS | API key, private corpus, private path, raw audio/transcript 없이 demo 가능하게 제한했다. |
| Evaluation | PASS | 실행 전 검증 명령, frontend smoke, voice route smoke command를 runbook에 포함했다. |
| Claim boundary | PASS | 금지 claim 13개를 유지하고 production/voice 완성 표현을 금지했다. |
| External audit | PASS | route smoke 이후 제출자가 실제로 말할 수 있는 claim만 runbook에 반영한 판단이 타당하다. |

## Data Mart Grain

`fact_portfolio_demo_runbook`의 grain은 `work_id + demo_step_id + command_surface + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-PORTFOLIO-DEMO-001` |
| `demo_step_id` | quick_check, api_contract, frontend_fixture, frontend_backend, local_voice_route_evidence, visual_evidence, interview_script |
| `command_surface` | python, pytest, ruff, npm, browser, document |
| `claim_boundary` | public-safe, contract-only, fixture-only, no-live-call |

금지 필드:

- raw answer
- raw evidence
- raw prompt
- chunk text
- private path
- secret

## Claim Boundary

허용:

- 포트폴리오 local demo runbook을 추가했다.
- contract-only API demo와 frontend fixture/backend mode demo 절차를 정리했다.
- voice UI visual QA artifact 확인 순서를 추가했다.
- local voice playback smoke와 local voice API route smoke 확인 순서를 추가했다.
- local voice route 기본 비활성화와 explicit flag contract smoke를 확인했다고 말할 수 있다.

금지:

- production 성능 검증 완료
- locked test에서 최종 성능 개선 입증
- GraphRAG로 성능 개선
- RAPTOR로 성능 개선
- HyDE로 최종 검색 성능 개선
- Solar Pro 3 답변 품질 최종 개선
- 음성 관광 앱 완성
- STT/TTS production 품질 검증 완료
- STT/TTS provider 최종 확정
- 실제 관광객 음성 품질 검증 완료
- microphone capture 구현 완료
- speaker playback 구현 완료
- 전체 도서 데이터 공개

## 다음 Gate

다음 작업 후보는 public repository audit refresh v2다.

권장 작업 단위:

- `id`: `HD-SUBMISSION-REFRESH-AUDIT-V2-001`
- `depends_on`: `HD-VOICE-DEMO-RUNBOOK-REFRESH-001`
- `scope`: 갱신된 README, demo runbook, voice evidence link, 금지 claim, public-safe scan을 제출 직전 기준으로 재검증
- `acceptance_tests`: README link current, runbook voice route smoke reflected, forbidden claim only in boundary sections, private path/secret/raw audio public leakage 0, production voice app claim 0
- `risk_level`: low
- `rollback_plan`: audit v2 문서와 테스트만 revert
