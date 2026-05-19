# Submission Ready Checklist

## 결론

`HD-SUBMISSION-READY-001`은 HistoryDocent public repository를 취업 포트폴리오에 첨부하기 전 최종 검수하는 gate다.

현재 제출 가능한 표현은 "production 성능 검증 완료"가 아니라 "평가 기반 RAG 의사결정 구조와 public-safe 제출 패키지를 구축했다"이다.

이 문서는 public-safe 검수 결과만 기록한다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 제출 범위

| 항목 | 제출 상태 | 기준 |
| --- | --- | --- |
| README 첫 화면 | PASS | 문제, 역할, 기술, 평가 기준, 데이터 정책이 첫 화면에 노출됨 |
| 포트폴리오 문구 | PASS | 이력서 한 줄, 프로젝트 문장, 면접 답변 10개 작성 |
| 최종 ablation 판단 | PASS | 채택, 보류, 기각, claim boundary 분리 |
| API sample | PASS | `/api/v1/chat` response contract를 public-safe sample로 문서화 |
| notebook skeleton | PASS | `00`부터 `13`까지 numbered notebook 존재 |
| raw data 공개 | PASS | 원본 PDF, 전체 parser output, 전체 chunk text, private eval payload 제외 |
| secret 공개 | PASS | API key, token, password 미기록 |

## 제출 전 자동 검증

| gate | 명령 | 통과 기준 |
| --- | --- | --- |
| unit/regression | `pytest -q` | 전체 테스트 통과 |
| lint | `ruff check .` | lint error 0 |
| public leak scan | `rg` 기반 secret/path scan | private absolute path, secret-like string, env assignment 0 |
| whitespace | `git diff --check` | whitespace error 0 |
| README link check | `tests/test_submission_ready.py` | README local markdown link missing 0 |

## 담당 관점 감사

| 담당 관점 | 감사 의견 |
| --- | --- |
| 제품 | 서울/한양 관광 도슨트 RAG 백엔드라는 목적이 명확하다. |
| RAG 아키텍처 | C0 chunking, E5-small voice rewrite, P0 packing, Solar Pro 3 v1의 기본선을 설명할 수 있다. |
| 평가 | dev, live-dev-subset, locked retrieval-only 결과를 혼동하지 않도록 claim boundary가 분리되어 있다. |
| 데이터 | fact grain은 `submission_gate_id + artifact_type + check_id + claim_boundary`로 둔다. |
| 보안 | public artifact에 원문, private payload, secret, private path를 포함하지 않는다. |
| 포트폴리오 | 최신 기법을 많이 붙인 프로젝트가 아니라, 채택과 기각을 실험으로 설명하는 프로젝트로 제시한다. |
| 외부 감사 | 제출 전 기능 추가보다 README, 문서 링크, 검증 명령, 금지 claim 유지가 우선이다. |

## 제출 허용 문장

```text
한국사 도서 parser 결과를 citation 가능한 RAG corpus로 정규화하고, 청킹·검색·리랭킹·query rewrite·고급 RAG 후보를 단계별로 비교해 서울/한양 관광 도슨트용 API 응답 계약까지 구현한 AI 백엔드 프로젝트입니다.
```

## 금지 Claim 유지

- production 성능 검증 완료
- locked test에서 최종 성능 개선 입증
- GraphRAG로 성능 개선
- RAPTOR로 성능 개선
- HyDE로 최종 검색 성능 개선
- Solar Pro 3 답변 품질 최종 개선
- 음성 관광 앱 완성
- 전체 도서 데이터 공개

## 남은 리스크

| risk | 영향 | 대응 |
| --- | --- | --- |
| production STT/TTS 미구현 | 실제 음성 입출력 품질을 주장할 수 없음 | browser voice-ready UI와 `spoken_answer` contract까지만 설명 |
| locked retrieval에서 relationship hybrid 개선 주장 실패 | active route 성능 개선 claim 불가 | shadow 후보로만 유지하고 기본 적용 금지 |
| private corpus 비공개 | 외부인이 전체 재현 불가 | public sample, aggregate metric, test harness, claim boundary 공개 |
| STT/TTS contract skeleton 미구현 | 실제 음성 입출력 품질을 아직 주장할 수 없음 | 후속 제품 개발 시 provider 호출 없는 adapter/interface skeleton부터 검증 |

## 최종 제출 판단

현재 상태는 "취업 포트폴리오 제출 전 감사 통과"로 기록한다.

다만 실서비스 운영 성공, production 성능 개선, 음성 앱 완성, 전체 데이터 공개는 주장하지 않는다.

## 다음 작업

다음 작업 후보는 `HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001`이다.

필수 포트폴리오 제출 gate, voice STT/TTS planning, voice STT/TTS contract skeleton, provider benchmark plan은 완료됐다. 후속 제품 개발을 이어간다면 provider 실제 호출 전 public-safe fixture와 no-live-call readiness를 먼저 검증한다.
