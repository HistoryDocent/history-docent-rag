# Portfolio Demo Runbook Report

## 결론

`HD-PORTFOLIO-DEMO-001`은 통과다.

포트폴리오 제출용 local demo runbook을 추가했다. 이번 결과는 contract-only API와 browser voice-ready UI, local voice demo stack decision을 안전하게 시연하는 절차이며, production 배포, live Solar Pro 3 품질 검증, STT/TTS production 품질 검증, private corpus 재현을 의미하지 않는다.

## 정량 결과

| metric | value |
| --- | ---: |
| demo_runbook_document_count | 1 |
| demo_step_count | 6 |
| runbook_command_block_count | 8 |
| required_artifact_link_count | 3 |
| forbidden_claim_count | 10 |
| troubleshooting_case_count | 5 |
| backend_demo_port_count | 1 |
| frontend_demo_port_count | 1 |
| contract_only_demo_count | 2 |
| fixture_demo_count | 1 |
| live_solar_call_count | 0 |
| retrieval_execution_count | 0 |
| private_corpus_required_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## 정성 평가

| gate | result | 근거 |
| --- | --- | --- |
| Demo flow | PASS | README, final ablation, API sample, contract smoke, voice UI 순서로 설명 경로를 고정했다. |
| Backend clarity | PASS | `/api/v1/chat` contract-only request와 확인 필드를 분리했다. |
| Frontend clarity | PASS | fixture mode와 backend mode의 목적을 분리했다. |
| Security | PASS | API key, private corpus, private path 없이 demo 가능하게 제한했다. |
| Evaluation | PASS | 실행 전 검증 명령과 smoke command를 runbook에 포함했다. |
| Claim boundary | PASS | 금지 claim 10개를 유지하고 production/voice 완성 표현을 금지했다. |
| External audit | PASS | 추가 RAG 실험보다 제출자가 재현 가능한 demo 순서를 먼저 고정한 판단이 타당하다. |

## Data Mart Grain

`fact_portfolio_demo_runbook`의 grain은 `work_id + demo_step_id + command_surface + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-PORTFOLIO-DEMO-001` |
| `demo_step_id` | quick_check, api_contract, frontend_fixture, frontend_backend, visual_evidence, interview_script |
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

금지:

- production 서비스 배포 완료
- STT/TTS production 품질 검증 완료
- 실제 관광객 음성 품질 검증 완료
- live Solar Pro 3 demo 성공
- retrieval/generation 성능 개선 추가 입증
- private corpus 전체 재현 가능

## 다음 Gate

다음 작업 후보는 local voice demo playback smoke다.

권장 작업 단위:

- `id`: `HD-VOICE-DEMO-PLAYBACK-SMOKE-001`
- `depends_on`: `HD-VOICE-DEMO-STACK-DECISION-001`
- `scope`: local STT/TTS demo 후보를 한 번의 playback smoke로 검증하되 production provider 확정 claim은 하지 않음
- `acceptance_tests`: local STT candidate 1, TTS demo candidate 1, external provider call 0, external audio transmission 0, production claim 0
- `risk_level`: medium
- `rollback_plan`: voice demo playback smoke 문서와 테스트만 revert
