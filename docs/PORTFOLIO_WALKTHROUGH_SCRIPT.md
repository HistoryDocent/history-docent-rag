# Portfolio Walkthrough Script

## 결론

`HD-PORTFOLIO-WALKTHROUGH-SCRIPT-001`은 통과다.

이 문서는 HistoryDocent를 3분 안에 설명하기 위한 화면 이동 순서와 내레이션 스크립트다. 목적은 새 기능 추가나 성능 개선 주장이 아니라, README와 최종 제출 index 이후 실제 면접/화면 녹화에서 말할 순서를 고정하는 것이다.

## 범위

| 항목 | 판단 |
| --- | --- |
| 포함 | 3분 walkthrough script, 화면 이동 click path, 허용/금지 claim, 외부 감사 기준 |
| 제외 | 실제 영상 파일 생성, live Solar Pro 3 호출, STT/TTS provider 재평가, production 배포 |
| 기본 문서 | `README.md`, `docs/PORTFOLIO_FINAL_PACKAGE_INDEX.md`, `docs/FINAL_ABLATION_REPORT.md`, `docs/API_RESPONSE_SAMPLE.md`, `docs/PORTFOLIO_DEMO_RUNBOOK.md`, `docs/SUBMISSION_REFRESH_AUDIT_V2.md` |
| claim boundary | public-safe walkthrough only |

## 3분 Walkthrough Script

| 구간 | 시간 | 화면 | 말할 내용 |
| ---: | --- | --- | --- |
| 1 | 0:00-0:20 | `README.md` 첫 화면 | 이 프로젝트는 서울/한양 관광 도슨트용 citation RAG 백엔드다. 핵심은 production 성능 개선 완료가 아니라 평가 기반 RAG 의사결정 구조다. |
| 2 | 0:20-0:40 | `README.md`의 60초 요약 | parent-child chunking, E5-small voice rewrite, P0 evidence packing, citation answer contract를 현재 기준선으로 둔다. 음성은 무료 로컬 demo 후보와 route smoke까지만 주장한다. |
| 3 | 0:40-1:10 | `docs/PORTFOLIO_FINAL_PACKAGE_INDEX.md` | 제출자는 README, final ablation, API sample, demo runbook, voice evidence, submission audit 순서로 보면 된다. 공개 저장소에는 원본 PDF, 전체 parser JSON, 전체 chunk text, secret을 올리지 않는다. |
| 4 | 1:10-1:45 | `docs/FINAL_ABLATION_REPORT.md` | BM25, dense, hybrid, reranker, query rewrite, GraphRAG-lite, RAPTOR-lite, HyDE, ColBERT-style 후보를 같은 gate로 비교했다. 좋은 수치만 채택하지 않고 latency, citation recall, locked 결과 때문에 기각한 후보도 문서화했다. |
| 5 | 1:45-2:10 | `docs/API_RESPONSE_SAMPLE.md` | `/api/v1/chat`는 `answer`, `spoken_answer`, `citations`, `abstained`를 반환하는 contract를 갖는다. 관광객에게는 짧은 spoken answer를 주고, 검증에는 citation과 no-answer 경계를 남긴다. |
| 6 | 2:10-2:40 | `docs/PORTFOLIO_DEMO_RUNBOOK.md` | local demo는 contract-only API와 frontend fixture/backend mode를 기준으로 한다. 무료 로컬 음성은 playback smoke와 disabled-by-default local route smoke까지만 보여준다. |
| 7 | 2:40-3:00 | `docs/SUBMISSION_REFRESH_AUDIT_V2.md` | 제출 전 감사에서 private path, secret, raw audio/transcript, production claim 노출을 점검했다. 결론은 완성된 production 앱이 아니라 평가, 의사결정, 공개 경계가 정리된 포트폴리오다. |

## Demo Click Path

| step | artifact | 확인할 것 |
| ---: | --- | --- |
| 1 | `README.md` | 60초 요약, 바로 볼 문서, 현재 공개 가능한 결론 |
| 2 | `docs/PORTFOLIO_FINAL_PACKAGE_INDEX.md` | 제출자가 먼저 열 문서, evidence map, 면접에서 말할 순서 |
| 3 | `docs/FINAL_ABLATION_REPORT.md` | 채택/보류/기각 판단 |
| 4 | `docs/API_RESPONSE_SAMPLE.md` | `/api/v1/chat` 응답 계약 |
| 5 | `docs/PORTFOLIO_DEMO_RUNBOOK.md` | local demo 순서와 금지 claim |
| 6 | `docs/VOICE_DEMO_STACK_DECISION.md` | 무료 로컬 STT/TTS demo 후보와 final provider 미확정 경계 |
| 7 | `docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md` | local voice route 기본 비활성화와 explicit flag smoke |
| 8 | `docs/SUBMISSION_REFRESH_AUDIT_V2.md` | public-safe 감사 결과 |

## 말해도 되는 문장

- 도서 parser 결과를 citation 가능한 RAG corpus로 재구성했다.
- 청킹, 검색, 생성, 음성 demo 후보를 같은 gate로 비교했다.
- GraphRAG-lite, RAPTOR-lite, HyDE, ColBERT-style 후보도 비교했지만 기본 route로 채택하지 않았다.
- `/api/v1/chat` contract에는 `spoken_answer`, citation, no-answer 경계가 있다.
- 무료 로컬 음성은 demo 후보, playback-ready, route smoke까지만 검증했다.

## 말하면 안 되는 문장

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

## 정량 Gate

| metric | value |
| --- | ---: |
| portfolio_walkthrough_script_document_count | 1 |
| portfolio_walkthrough_script_report_count | 1 |
| regression_test_file_count | 1 |
| walkthrough_segment_count | 7 |
| target_duration_seconds | 180 |
| demo_click_path_step_count | 8 |
| first_open_artifact_count | 8 |
| forbidden_claim_count | 13 |
| recording_artifact_created_count | 0 |
| live_solar_call_count | 0 |
| retrieval_execution_count | 0 |
| external_provider_call_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_audio_transcript_leakage_count | 0 |
| production_success_claim_count | 0 |
| production_voice_app_claim_count | 0 |

## Data Mart Grain

`fact_portfolio_walkthrough_script`의 grain은 `walkthrough_id + segment_id + artifact_id + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `walkthrough_id` | `HD-PORTFOLIO-WALKTHROUGH-SCRIPT-001` |
| `segment_id` | 3분 script의 7개 구간 |
| `artifact_id` | 화면에서 열 문서 id |
| `claim_boundary` | public-safe-walkthrough, contract-only, route-smoke-only, no-production-claim |

금지 필드:

- raw query
- raw answer
- raw evidence
- raw audio
- transcript
- prompt
- chunk text
- private path
- secret

## 외부 감사 의견

이 walkthrough는 제출 운영 문서로 타당하다. 기존 evidence를 새로 해석하거나 성능 개선을 주장하지 않고, 이미 통과한 final package index와 audit v2를 따라가는 설명 순서만 고정했다.

후속 gate `HD-DEMO-RECORDING-CHECKLIST-001`, `HD-GITHUB-PUSH-READINESS-001`, `HD-GITHUB-PUSH-EXECUTION-APPROVAL-001`도 완료했다. 다음 gate는 `HD-GITHUB-PUSH-EXECUTION-001`이다. 사용자가 명시적으로 `git push 실행 승인` 또는 동등한 문장으로 승인한 경우에만 진행한다.
