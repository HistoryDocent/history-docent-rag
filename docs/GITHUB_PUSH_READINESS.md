# GitHub Push Readiness

## 결론

`HD-GITHUB-PUSH-READINESS-001`은 통과다.

이 문서는 public GitHub repository에 push하기 전 점검한 remote, branch, commit 범위, tracked artifact, secret/private path 노출 여부를 기록한다. 실제 push는 수행하지 않았다.

## 확인한 Git 상태

| 항목 | 기준 | 결과 |
| --- | --- | --- |
| remote | `origin`이 `https://github.com/HistoryDocent/history-docent-rag.git`를 가리킨다. | PASS |
| branch | 현재 branch는 `main`이다. | PASS |
| worktree | readiness 작성 전 `git status --short`가 clean이다. | PASS |
| recent commit scope | 최근 commit은 문서/테스트 중심 제출 운영 gate다. | PASS |
| push execution | 이 gate에서 `git push`를 실행하지 않는다. | PASS |

## Tracked Artifact 점검

허용:

- `.env.example`
- `frontend/.env.example`
- `data_samples/*.json`
- `evals/results/*.jsonl`
- `evals/reports/assets/*.jpg`

금지:

- 실제 `.env`, `.env.local`, credential file
- 원본 PDF
- 전체 parser JSON
- raw chunk text dump
- raw eval CSV
- private audio file
- private transcript
- private score sheet

## 실행 명령

```powershell
git status --short
git branch --show-current
git remote -v
git log -5 --oneline
git ls-files | rg -n "(^|/)(\.env|\.env\.|private_data|raw|audio|\.wav$|\.mp3$|\.pdf$|parser.*\.json|chunk.*\.json|eval.*\.csv)"
```

`git ls-files` 점검에서 허용 sample과 example 외 private/raw artifact는 추적하지 않는 것으로 판단한다.

## 말해도 되는 문장

- push 전 remote, branch, commit 범위, tracked artifact를 점검했다.
- public repo에 올리면 안 되는 원본/secret/private artifact가 tracked file에 없는지 확인했다.
- readiness gate에서는 실제 push를 실행하지 않았다.

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
| github_push_readiness_document_count | 1 |
| github_push_readiness_report_count | 1 |
| regression_test_file_count | 1 |
| expected_remote_count | 1 |
| current_branch_main_count | 1 |
| worktree_clean_before_readiness_count | 1 |
| recent_commit_scope_checked_count | 1 |
| tracked_env_example_count | 2 |
| tracked_non_example_env_file_count | 0 |
| tracked_private_path_count | 0 |
| tracked_raw_pdf_count | 0 |
| tracked_raw_audio_count | 0 |
| tracked_raw_eval_csv_count | 0 |
| push_execution_count | 0 |
| external_state_change_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_env_assignment_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| public_raw_audio_transcript_leakage_count | 0 |
| production_success_claim_count | 0 |
| production_voice_app_claim_count | 0 |

## Data Mart Grain

`fact_github_push_readiness`의 grain은 `readiness_id + git_check_id + artifact_class + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `readiness_id` | `HD-GITHUB-PUSH-READINESS-001` |
| `git_check_id` | remote, branch, worktree, commit_scope, tracked_artifact, push_execution |
| `artifact_class` | env_example, sample_json, report_asset, forbidden_private_raw |
| `claim_boundary` | public-safe-push-readiness, no-push-execution, no-production-claim |
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

이 readiness gate는 push 직전 안전장치로 타당하다. remote와 branch가 의도한 public repository를 가리키는지 확인했고, push 전 private/raw/secret artifact 추적 여부를 점검했다.

후속 gate `HD-GITHUB-PUSH-EXECUTION-APPROVAL-001`도 완료했다. 다음 gate는 `HD-GITHUB-PUSH-EXECUTION-001`이다. 사용자가 명시적으로 `git push 실행 승인` 또는 동등한 문장으로 승인한 경우에만 진행한다.
