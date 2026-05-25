# Submission Refresh Audit V2

## 결론

`HD-SUBMISSION-REFRESH-AUDIT-V2-001`은 통과다.

이번 감사는 `HD-VOICE-DEMO-RUNBOOK-REFRESH-001` 이후 제출 직전 공개 저장소 상태를 다시 확인한 것이다. 목적은 새 성능 실험이 아니라 README 링크, 최신 demo runbook, voice playback/route smoke evidence, screenshot artifact, 금지 claim, public-safe scan을 재검증하는 것이다.

이 문서는 public-safe 감사 결과만 기록한다. raw query, raw answer, raw evidence, raw audio, transcript, prompt, chunk text, private path, secret은 기록하지 않는다.

## 감사 범위

| 영역 | 감사 기준 |
| --- | --- |
| README | 최신 demo runbook refresh, voice playback smoke, voice API route smoke 링크를 포함한다. |
| Demo runbook | 최신 local voice route evidence와 allowed/forbidden claim이 반영되어 있다. |
| Voice evidence | playback smoke와 API route smoke가 production claim 없이 연결되어 있다. |
| Screenshot artifact | voice UI visual QA screenshot 3개가 공개 가능한 경로에 존재한다. |
| Claim boundary | production, locked improvement, voice app completion, STT/TTS final provider 표현을 성공 claim으로 사용하지 않는다. |
| Public safety | private absolute path, secret-like string, env assignment, raw payload, raw audio/transcript가 public artifact에 없다. |
| Verification | backend, frontend, lint, audit, whitespace, leak scan을 실행할 수 있다. |

## 필수 산출물

| artifact | 상태 |
| --- | --- |
| `README.md` | PASS |
| `docs/PORTFOLIO_DEMO_RUNBOOK.md` | PASS |
| `evals/reports/portfolio_demo_runbook_report.md` | PASS |
| `evals/reports/portfolio_demo_runbook_refresh_report.md` | PASS |
| `docs/VOICE_DEMO_PLAYBACK_SMOKE.md` | PASS |
| `evals/reports/voice_demo_playback_smoke_report.md` | PASS |
| `docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md` | PASS |
| `evals/reports/voice_api_local_runtime_route_smoke_report.md` | PASS |
| `docs/RAG_DECISION_LEDGER.md` | PASS |
| `evals/reports/assets/voice_ui_visual_qa_desktop_answerable.jpg` | PASS |
| `evals/reports/assets/voice_ui_visual_qa_mobile_no_answer.jpg` | PASS |
| `evals/reports/assets/voice_ui_visual_qa_desktop_error.jpg` | PASS |

## 최종 검증 명령

repo root:

```powershell
pytest -q
ruff check .
git diff --check
```

targeted regression:

```powershell
pytest tests/test_submission_refresh_audit_v2.py tests/test_portfolio_demo_runbook.py tests/test_portfolio_demo_runbook_refresh.py tests/test_voice_demo_playback_smoke.py tests/test_voice_api_local_runtime_route_smoke.py -q
```

frontend:

```powershell
cd frontend
npm run check
npm audit --audit-level=high
```

public leak scan:

```powershell
rg -n "([A-Za-z]:\\|UPSTAGE_API_KEY\s*=|sk-[A-Za-z0-9]|private_data[/\\])" README.md docs evals\reports tests app pipelines retrieval configs frontend -g "*.md" -g "*.py" -g "*.toml" -g "*.ts" -g "*.tsx" -g "*.json" -g "*.css" -g "*.html" -g "*.mjs" -g "!frontend/node_modules/**" -g "!frontend/dist/**"
```

public candidate scanner:

```powershell
@'
from pathlib import Path
from pipelines.build_parent_child_chunks import _collect_public_candidate_path_secret_leaks
leaks = _collect_public_candidate_path_secret_leaks(Path.cwd())
print("count", len(leaks))
if leaks:
    print("\n".join(leaks[:20]))
'@ | python -
```

최종 상태:

```powershell
git status -sb
```

## 허용 Claim

- 제출 전 public repository audit refresh v2를 완료했다.
- 최신 demo runbook, voice playback smoke, voice API route smoke 링크를 재검증했다.
- contract-only API와 browser voice-ready UI를 local demo 대상으로 설명할 수 있다.
- local voice API route는 기본 비활성화이며 explicit local flag에서 contract smoke를 통과했다.
- public artifact 기준 external provider call과 external audio transmission은 0으로 유지했다.

## 금지 Claim

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

## 담당 관점 감사

| 담당 관점 | 판단 |
| --- | --- |
| 제품 | 제출 demo는 RAG 의사결정, contract API, voice-ready UI, local voice route smoke로 충분히 좁혀져 있다. |
| RAG 아키텍처 | 채택/보류/기각 후보와 locked gate 결과가 ledger에 분리되어 있다. |
| 음성 | 무료 로컬 STT/TTS는 demo evidence 후보이며 production final provider로 확정하지 않는다. |
| 평가 | 최신 runbook refresh 이후의 smoke evidence를 제출 경로에 반영했다. |
| 보안 | public artifact에는 secret, private path, raw audio/transcript, raw payload를 남기지 않는다. |
| 데이터 | audit grain은 `submission_refresh_id + artifact_type + check_id + claim_boundary`로 유지한다. |
| 외부 감사 | 새 기능 추가보다 최신 제출 산출물의 링크, 검증 명령, 금지 claim을 다시 닫은 판단이 타당하다. |

## Data Mart Grain

`fact_submission_refresh_gate_v2`의 grain은 `submission_refresh_id + artifact_type + check_id + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `submission_refresh_id` | `HD-SUBMISSION-REFRESH-AUDIT-V2-001` |
| `artifact_type` | README, docs, report, screenshot, test, command |
| `check_id` | link, artifact, claim, leak, command, git_status |
| `claim_boundary` | public-safe-summary, contract-only, fixture-only, route-smoke-only, no-live-call |
| `status` | PASS, WARN, FAIL |
| `evidence_artifact` | public-safe 근거 문서 또는 리포트 |

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

## 다음 작업

필수 포트폴리오 제출 gate는 v2 감사 기준으로 완료됐다.

후속 개발을 이어간다면 `HD-PORTFOLIO-FINAL-PACKAGE-INDEX-001`을 권장한다. 제출자가 README, demo runbook, final ablation, voice evidence, forbidden claim을 한 화면에서 따라갈 수 있도록 최종 제출 index를 정리하는 작업이다.
