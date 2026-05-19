# Portfolio Rehearsal Report

## 결론

`HD-PORTFOLIO-REHEARSAL-001`은 통과다.

이번 결과는 포트폴리오 제출 전 30초 요약, 3분 설명, 면접 답변, demo 순서, 금지 claim 회피를 고정한 것이다. production success, live Solar Pro 3 품질 검증, STT/TTS 품질 검증, private corpus 전체 재현을 의미하지 않는다.

## 정량 결과

| metric | value |
| --- | ---: |
| portfolio_rehearsal_document_count | 1 |
| portfolio_rehearsal_report_count | 1 |
| thirty_second_script_count | 1 |
| three_minute_section_count | 6 |
| interview_answer_count | 12 |
| rejected_candidate_explained_count | 8 |
| demo_step_count | 5 |
| allowed_claim_count | 8 |
| forbidden_claim_count | 8 |
| rehearsal_rubric_check_count | 5 |
| live_solar_call_count | 0 |
| retrieval_execution_count | 0 |
| private_corpus_required_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## 정성 평가

| gate | result | 근거 |
| --- | --- | --- |
| Message clarity | PASS | 30초 요약과 3분 설명이 문제, 데이터, RAG 평가, claim boundary를 포함한다. |
| Decision defensibility | PASS | C0, E5-small voice rewrite, P0, Solar Pro 3 v1 유지와 후보 기각 근거를 설명한다. |
| Rejection reasoning | PASS | GraphRAG-lite, RAPTOR-lite, HyDE, reranker, active route 등 8개 기각/보류 후보를 분리했다. |
| Demo readiness | PASS | README, final ablation, API sample, demo runbook, visual QA screenshot 순서가 고정됐다. |
| Claim boundary | PASS | 금지 claim 8개를 유지하고 production/voice 완성 표현을 금지했다. |
| Public safety | PASS | raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다. |
| External audit | PASS | 제출 직전 가장 큰 위험을 코드가 아니라 과장 claim으로 보고 설명 리허설을 분리한 판단이 타당하다. |

## Data Mart Grain

`fact_portfolio_rehearsal`의 grain은 `rehearsal_id + script_type + question_id + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `rehearsal_id` | `HD-PORTFOLIO-REHEARSAL-001` |
| `script_type` | thirty_second, three_minute, interview_answer, demo_step |
| `question_id` | 면접 질문 또는 demo step id |
| `claim_boundary` | public-safe-summary, dev-only, locked-retrieval-only, contract-only |
| `status` | PASS, WARN, FAIL |
| `evidence_artifact` | public-safe 근거 문서 |

금지 필드:

- raw query
- raw answer
- raw evidence
- prompt
- chunk text
- private path
- secret

## Claim Boundary

허용:

- 포트폴리오 설명 리허설 문서를 추가했다.
- 30초 요약, 3분 설명, 면접 답변, demo 순서, 금지 claim을 고정했다.
- 후보를 채택한 이유와 기각한 이유를 함께 설명할 수 있다.

금지:

- production 서비스 배포 완료
- STT/TTS 품질 검증 완료
- live Solar Pro 3 demo 성공
- retrieval/generation 성능 개선 추가 입증
- private corpus 전체 재현 가능

## 다음 Gate

필수 포트폴리오 제출 gate는 여기서 완료다.

후속 개발을 이어간다면 별도 승인 후 `HD-VOICE-STT-TTS-PROVIDER-BENCH-PLAN-001`에서 provider benchmark 전 공식 문서, 비용, 개인정보, live call budget, CUDA local 후보를 계획한다.
