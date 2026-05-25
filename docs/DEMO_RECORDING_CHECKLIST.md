# Demo Recording Checklist

## 결론

`HD-DEMO-RECORDING-CHECKLIST-001`은 통과다.

이 문서는 포트폴리오 화면 녹화 또는 면접 시연 전에 확인할 preflight checklist다. 목적은 실제 녹화 파일을 만드는 것이 아니라, 녹화 중 private path, secret, raw payload, raw audio/transcript, 과장 claim이 노출되지 않도록 점검 순서를 고정하는 것이다.

## 녹화 전 화면 순서

| 순서 | 화면 | 확인할 내용 | 노출 금지 |
| ---: | --- | --- | --- |
| 1 | `README.md` | 60초 요약, 현재 공개 가능한 결론, 바로 볼 문서 | private 경로, `.env`, secret |
| 2 | `docs/PORTFOLIO_WALKTHROUGH_SCRIPT.md` | 3분 내레이션과 click path | raw query, raw answer |
| 3 | `docs/PORTFOLIO_FINAL_PACKAGE_INDEX.md` | 제출자가 먼저 열 문서와 evidence map | 원본 PDF, 전체 parser JSON |
| 4 | `docs/FINAL_ABLATION_REPORT.md` | 채택/보류/기각 판단 | private eval payload |
| 5 | `docs/API_RESPONSE_SAMPLE.md` | `/api/v1/chat` contract와 citation/no-answer 경계 | live key, raw provider payload |
| 6 | `docs/PORTFOLIO_DEMO_RUNBOOK.md` | local demo 순서와 금지 claim | private audio file path |
| 7 | `docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md` | local voice route 기본 비활성화와 explicit flag smoke | raw audio, transcript |
| 8 | `docs/SUBMISSION_REFRESH_AUDIT_V2.md` | public-safe 감사 결과 | secret-like token, local private path |

## 녹화 전 터미널 Checklist

| check | 통과 기준 |
| --- | --- |
| shell prompt | private directory 전체 경로가 크게 노출되지 않게 한다. |
| command history | `set`, `Get-ChildItem Env:`, `.env` 출력, credential 확인 명령을 실행하지 않는다. |
| test output | 필요한 경우 `pytest tests/test_demo_recording_checklist.py -q`처럼 짧은 targeted output만 보여준다. |
| git output | `git log -1 --oneline`, `git status --short` 정도만 사용한다. remote credential, token, private path 출력은 금지한다. |
| browser tab | README와 docs만 열고 private data/audio/output 폴더는 열지 않는다. |
| audio playback | private wav 재생 화면이나 파일 경로를 공개하지 않는다. |
| API demo | live Solar Pro 3 호출이나 external STT/TTS provider 호출을 녹화 중 실행하지 않는다. |
| cleanup | 녹화 전 열린 terminal/browser tab에 secret, raw payload, private path가 없는지 확인한다. |

## 말해도 되는 문장

- 평가 기반 RAG 의사결정 구조를 구현했다.
- 같은 gate로 후보를 비교하고 채택/보류/기각을 문서화했다.
- `/api/v1/chat` contract와 `spoken_answer`, citation, no-answer 경계를 정의했다.
- 무료 로컬 음성은 demo 후보, playback-ready, route smoke까지만 검증했다.
- 제출 전 public-safe audit을 통과했다.

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
| demo_recording_checklist_document_count | 1 |
| demo_recording_checklist_report_count | 1 |
| regression_test_file_count | 1 |
| recording_screen_sequence_count | 8 |
| terminal_preflight_check_count | 8 |
| allowed_claim_count | 5 |
| forbidden_claim_count | 13 |
| recording_artifact_created_count | 0 |
| live_solar_call_count | 0 |
| retrieval_execution_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_env_assignment_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| public_raw_audio_transcript_leakage_count | 0 |
| production_success_claim_count | 0 |
| production_voice_app_claim_count | 0 |

## Data Mart Grain

`fact_demo_recording_preflight`의 grain은 `recording_checklist_id + screen_step_id + terminal_check_id + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `recording_checklist_id` | `HD-DEMO-RECORDING-CHECKLIST-001` |
| `screen_step_id` | 녹화 전 화면 순서 |
| `terminal_check_id` | 터미널 출력 preflight 항목 |
| `claim_boundary` | public-safe-recording, no-live-call, no-production-claim |
| `status` | PASS, WARN, FAIL |

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

이 checklist는 실제 녹화 전 마지막 안전장치로 타당하다. 새 기능이나 새 실험을 추가하지 않고, 이미 정리된 walkthrough script와 submission audit을 기준으로 화면/터미널 노출 리스크를 줄인다.

후속 gate `HD-GITHUB-PUSH-READINESS-001`과 `HD-GITHUB-PUSH-EXECUTION-APPROVAL-001`도 완료했다. 다음 gate는 `HD-GITHUB-PUSH-EXECUTION-001`이다. 사용자가 명시적으로 `git push 실행 승인` 또는 동등한 문장으로 승인한 경우에만 진행한다.
