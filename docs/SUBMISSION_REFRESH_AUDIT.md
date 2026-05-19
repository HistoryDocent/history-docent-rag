# Submission Refresh Audit

## 결론

`HD-SUBMISSION-REFRESH-001`은 제출 직전 public repository audit refresh gate다.

이번 단계의 목적은 새 RAG 성능 실험이 아니다. README 링크, demo runbook, screenshot artifact, 금지 claim, public-safe scan, 검증 명령을 다시 확인해 취업 포트폴리오 제출 전에 공개 가능한 상태를 고정하는 것이다.

이 문서는 public-safe 감사 결과만 기록한다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 감사 범위

| 영역 | 감사 기준 |
| --- | --- |
| README | 핵심 결과 표와 문서 링크가 최신 산출물을 포함한다. |
| Demo runbook | backend/frontend local demo 순서와 금지 claim이 문서화되어 있다. |
| Screenshot artifact | voice UI visual QA screenshot 3개가 공개 가능한 경로에 존재한다. |
| Claim boundary | production, locked improvement, voice app completion 표현을 성공 claim으로 사용하지 않는다. |
| Public safety | private absolute path, secret-like string, env assignment, raw payload가 public artifact에 없다. |
| Verification | backend, frontend, lint, audit, whitespace, leak scan을 실행할 수 있다. |

## 필수 산출물

| artifact | 상태 |
| --- | --- |
| `README.md` | PASS |
| `docs/PORTFOLIO_DEMO_RUNBOOK.md` | PASS |
| `evals/reports/portfolio_demo_runbook_report.md` | PASS |
| `docs/SUBMISSION_READY_CHECKLIST.md` | PASS |
| `evals/reports/submission_ready_report.md` | PASS |
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

frontend:

```powershell
cd frontend
npm run check
npm audit --audit-level=high
```

public leak scan:

```powershell
rg -n "([A-Za-z]:\\|UPSTAGE_API_KEY\s*=|sk-[A-Za-z0-9])" README.md docs evals\reports tests app pipelines retrieval configs frontend -g "*.md" -g "*.py" -g "*.toml" -g "*.ts" -g "*.tsx" -g "*.json" -g "*.css" -g "*.html" -g "*.mjs" -g "!frontend/node_modules/**" -g "!frontend/dist/**"
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

## 금지 Claim

- production 성능 검증 완료
- locked test에서 최종 성능 개선 입증
- GraphRAG로 성능 개선
- RAPTOR로 성능 개선
- HyDE로 최종 검색 성능 개선
- Solar Pro 3 답변 품질 최종 개선
- 음성 관광 앱 완성
- 전체 도서 데이터 공개

## 담당 관점 감사

| 담당 관점 | 판단 |
| --- | --- |
| 제품 | 제출 메시지는 서울/한양 관광 도슨트 RAG 백엔드로 충분히 좁혀져 있다. |
| RAG 아키텍처 | 기본선, 보류 후보, 기각 후보가 ledger와 final ablation에 분리되어 있다. |
| 평가 | dev, live-dev-subset, locked retrieval-only 결과를 섞지 않는다. |
| 보안 | public artifact에는 secret, private path, raw payload를 남기지 않는다. |
| 데이터 | audit grain은 `submission_refresh_id + artifact_type + check_id + claim_boundary`로 둔다. |
| 포트폴리오 | 시연 가능한 것은 contract-only API와 browser voice-ready UI이며, production voice app은 claim하지 않는다. |
| 외부 감사 | 제출 전 추가 기능보다 문서 링크, 검증 명령, 금지 claim 유지가 우선이라는 판단이 타당하다. |

## Data Mart Grain

`fact_submission_refresh_gate`의 grain은 `submission_refresh_id + artifact_type + check_id + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `submission_refresh_id` | `HD-SUBMISSION-REFRESH-001` |
| `artifact_type` | README, docs, report, screenshot, test, command |
| `check_id` | link, artifact, claim, leak, command, git_status |
| `claim_boundary` | public-safe-summary, contract-only, fixture-only, no-live-call |
| `status` | PASS, WARN, FAIL |
| `evidence_artifact` | public-safe 근거 문서 또는 리포트 |

금지 필드:

- raw query
- raw answer
- raw evidence
- prompt
- chunk text
- private path
- secret

## 다음 작업

필수 포트폴리오 제출 gate는 설명 리허설까지 완료됐다.

후속 개발을 이어간다면 실제 음성 입출력 범위, 비용, 개인정보 처리를 별도 계획으로 분리한다.
