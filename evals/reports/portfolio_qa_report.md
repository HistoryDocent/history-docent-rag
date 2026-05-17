# Portfolio QA Report

## 목적

`HD-PORTFOLIO-QA-001`은 final ablation report와 API response sample을 바탕으로 이력서/면접 제출 문구를 public-safe 형태로 고정한다.

이 리포트는 성능 개선 주장 문서가 아니다. 프로젝트 경험을 문제, 역할, 구현, 검증, 한계, 다음 개선으로 나누어 면접에서 방어 가능한 문장으로 압축했는지 검토한다.

raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `portfolio-qa-report/v1` |
| work_id | `HD-PORTFOLIO-QA-001` |
| source_final_ablation_report | `docs/FINAL_ABLATION_REPORT.md` |
| source_api_sample | `docs/API_RESPONSE_SAMPLE.md` |
| source_portfolio_strategy | `docs/PORTFOLIO_STRATEGY.md` |
| solar_call_count_for_this_report | 0 |
| cuda_required_for_this_report | false |

## 정량 리포트

| metric | value |
| --- | ---: |
| resume_one_line_count | 1 |
| resume_bullet_count | 5 |
| interview_answer_count | 10 |
| forbidden_claim_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| raw_payload_sample_count | 0 |

## 정성 리포트

- `message_fit`: 기술명 나열이 아니라 서울/한양 관광 도슨트 RAG 백엔드라는 문제 정의에서 시작한다.
- `role_clarity`: 데이터 계약, normalization, chunking, retrieval evaluation, answer contract, API contract를 본인 역할로 분리했다.
- `evidence_quality`: Recall@k, MRR, nDCG@5, latency, citation recoverability, locked retrieval boundary를 검증 근거로 둔다.
- `claim_boundary`: production 성능, locked 개선, GraphRAG/RAPTOR/HyDE 개선, 음성 앱 완성 claim을 금지한다.
- `failure_story`: HyDE와 relationship hybrid route를 기각한 이유를 면접 답변에 포함했다.
- `api_story`: `/api/v1/chat` sample은 품질 주장이 아니라 response contract 설명으로 제한했다.
- `security_boundary`: public 문서에는 저작권 원문과 private eval payload를 포함하지 않는다.
- `gate_status`: PASS

## Data Mart Grain

포트폴리오 QA의 fact grain은 `portfolio_message_id + audience + claim_boundary + evidence_artifact`다.

| field | 설명 |
| --- | --- |
| `portfolio_message_id` | resume one-line, resume bullet, interview answer 등 |
| `audience` | recruiter, interviewer, engineer |
| `claim_boundary` | dev-only, live-dev-subset, locked-retrieval-only, contract-only |
| `evidence_artifact` | public-safe 근거 문서 |
| `forbidden_claim_count` | 금지 표현 수 |

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- 문구는 제출용 초안이며 회사/직무별로 길이와 강조점 조정이 필요하다.
- 정량 수치는 대부분 dev 또는 locked retrieval-only 경계를 가진다.
- API sample은 synthetic fixture이며 실제 production 품질이 아니다.

다음 gate는 `HD-COLBERT-001`이다. 단, 제출 패키징 이후 후순위 실험으로 다룬다.
