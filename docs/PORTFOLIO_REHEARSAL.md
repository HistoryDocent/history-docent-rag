# Portfolio Rehearsal

## 결론

`HD-PORTFOLIO-REHEARSAL-001`은 취업 포트폴리오 제출 전 설명 리허설 gate다.

핵심 메시지는 "RAG 성능 개선을 최종 입증했다"가 아니다. 핵심은 도서 parser 결과를 citation 가능한 RAG corpus로 재구성하고, 같은 평가 gate로 후보를 비교해 채택, 보류, 기각을 설명할 수 있다는 점이다.

이 문서는 public-safe 설명 스크립트만 기록한다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 30초 요약

```text
HistoryDocent는 서울을 방문한 사용자에게 한양의 역사 맥락을 설명하는 관광 도슨트 RAG 백엔드입니다. 도서 parser 결과를 normalized block과 parent-child chunk로 정리하고, BM25, dense, hybrid, reranker, query rewrite, GraphRAG-lite, RAPTOR-lite, HyDE를 같은 평가 기준으로 비교했습니다. 최종 메시지는 성능 개선 확정이 아니라, `C0 chunking + E5-small voice rewrite + P0 evidence packing + Solar Pro 3 v1`을 현재 기본선으로 두고 여러 후보를 latency, citation risk, locked 결과 때문에 기각했다는 점입니다.
```

## 3분 설명 스크립트

### 1. 문제 정의

서울 관광에서는 장소명과 역사 맥락이 분리되는 경우가 많다. 사용자가 경복궁, 광화문, 북촌처럼 특정 장소를 물을 때 단순 지식 답변보다 근거를 추적할 수 있는 짧은 도슨트 답변이 필요하다고 봤다.

### 2. 데이터와 제약

입력은 한국사 도서 PDF를 parser로 추출한 결과다. 다만 원본 PDF, 전체 parser JSON, 전체 chunk text는 public repo에 올릴 수 없으므로 private corpus와 public aggregate report를 분리했다. 공개 저장소에는 schema, code, fixture, aggregate metric, sanitized sample만 남겼다.

### 3. RAG 설계

먼저 parser output을 normalized block으로 정리하고 citation provenance를 보존했다. 이후 C0-C6 청킹 후보를 비교했고 C0 parent-child chunking을 유지했다. retrieval은 BM25 기준선에서 dense, hybrid, reranker, query rewrite를 순서대로 비교했고, 현재 non-rerank 기본 후보는 `dense_multilingual_e5_small_voice_rewrite`다.

### 4. 기각 판단

GraphRAG-lite는 relationship 질문에서 기본값으로 승격할 근거가 없었고, RAPTOR-lite는 overview/place_story 질문에서 기준선을 넘지 못했다. HyDE는 작은 live subset에서는 Recall@5가 올랐지만 40개 확대 비교에서 MRR, nDCG@5, latency가 악화되어 기본 route로 기각했다. relationship hybrid route도 locked retrieval에서 MRR delta가 음수라 active route 개선 주장을 보류했다.

### 5. API와 demo

FastAPI `/api/v1/chat` 계약에는 `answer`, `spoken_answer`, `citations`, `abstained`, router dry-run, active route flag dry-run이 포함된다. public demo는 `contract_only` API와 browser voice-ready UI까지만 보여준다. STT/TTS 품질 검증, production 배포, live Solar Pro 3 voice demo는 아직 claim하지 않는다.

### 6. 마무리

이 프로젝트의 강점은 최신 기법을 모두 붙인 것이 아니라, 같은 gate로 비교하고 실제로 기각할 후보를 기각했다는 점이다. 포트폴리오에서는 좋은 수치보다 판단 기준과 claim boundary를 설명한다.

## Demo 순서

| 순서 | 화면 또는 문서 | 말할 내용 |
| ---: | --- | --- |
| 1 | `README.md` | 문제 정의, 현재 stack, 금지 claim을 먼저 보여준다. |
| 2 | `docs/FINAL_ABLATION_REPORT.md` | 채택, 보류, 기각을 같은 표에서 설명한다. |
| 3 | `docs/API_RESPONSE_SAMPLE.md` | `/api/v1/chat`의 `spoken_answer`와 citation trace 계약을 설명한다. |
| 4 | `docs/PORTFOLIO_DEMO_RUNBOOK.md` | contract-only API와 frontend fixture/backend mode demo 순서를 설명한다. |
| 5 | visual QA screenshots | browser voice-ready UI의 answerable, no-answer, sanitized error 상태를 보여준다. |

## 면접 질문 답변

### 1. 왜 이 프로젝트를 만들었나

서울 관광에서 장소와 역사 맥락을 함께 설명하는 도슨트 경험을 만들고 싶었다. 그래서 음성 앱 전체보다 먼저, 근거 추적이 가능한 RAG 백엔드와 평가 체계를 만들었다.

### 2. 본인 역할은 무엇인가

데이터 계약, parser normalization, parent-child chunking, retrieval evaluation, generation contract, FastAPI `/api/v1/chat`, public-safe 포트폴리오 문서화를 직접 설계하고 구현했다.

### 3. 청킹은 왜 C0를 유지했나

C0-C6 후보를 BM25 고정 조건에서 비교했고 C0가 selection gate를 통과했다. 일부 작은 failure만 보고 전역 청킹을 바꾸면 이후 retrieval, packing, generation 결과가 모두 비교 불가능해지므로 targeted chunk audit만 열었다.

### 4. embedding/retrieval은 무엇을 선택했나

현재 non-rerank 기본 후보는 `dense_multilingual_e5_small_voice_rewrite`다. BGE-M3는 Recall@5 상한은 높았지만 latency 부담이 있어 기본값보다 quality ceiling 후보로 둔다.

### 5. reranker는 왜 기본값이 아닌가

BGE reranker는 품질 상한은 좋았지만 CPU p95 latency가 커서 관광 도슨트 API 기본값으로 쓰기 어렵다고 판단했다.

### 6. GraphRAG는 왜 기본값이 아닌가

GraphRAG-lite는 relationship 질문군에서만 실험했고 nDCG@5 개선 근거가 부족했다. 그래서 "GraphRAG를 적용해 성능이 올랐다"가 아니라 "관계 질문군에 한정해 비교했고 기본값에서 제외했다"고 설명한다.

### 7. RAPTOR는 왜 기본값이 아닌가

RAPTOR-lite는 overview/place_story 질문군에서 비교했지만 기준선을 넘지 못했고 nDCG@5가 하락했다. 따라서 장문 요약형 RAG 후보로 보관하되 기본 route로 쓰지 않는다.

### 8. HyDE는 왜 기각했나

5개 live-dev-subset에서는 Recall@5가 올랐지만 MRR과 latency trade-off가 있었다. 40개 확대 live 비교에서는 MRR, nDCG@5, latency가 악화되어 기본 retrieval route로 채택하지 않았다.

### 9. active routing은 왜 켜지 않았나

relationship route가 dev shadow에서는 유망했지만 locked retrieval paired comparison에서 개선 주장을 통과하지 못했다. 그래서 API에는 dry-run과 shadow 관찰 필드만 두고 실제 active route 적용은 0으로 유지했다.

### 10. Solar Pro 3는 어디에 쓰였나

Solar Pro 3는 generation이 필요한 순간에만 사용했다. provider contract, live smoke, generation baseline, repaired v2 비교를 했지만, 최종 제출에서는 Solar Pro 3 품질 개선을 입증했다고 말하지 않는다.

### 11. 음성 서비스는 어디까지인가

완성된 음성 앱은 아니다. 현재 1차 산출물은 `spoken_answer`를 포함한 RAG API와 browser voice-ready UI skeleton, contract smoke, visual QA다. STT/TTS 품질 검증은 별도 단계다.

### 12. public repo에서 전체 재현이 가능한가

전체 private corpus 재현은 불가능하다. 저작권 원문, 전체 parser output, 전체 chunk text, private eval payload는 공개하지 않는다. 대신 code, schema, fixture, aggregate report, public-safe sample로 설계와 판단 과정을 검토할 수 있게 했다.

## 기각 후보 설명 체크

| 후보 | 면접 설명 |
| --- | --- |
| `C1 smaller child` | C0 대비 Recall@5가 크게 낮아 기각했다. |
| BGE-M3 기본값 | 품질 상한 후보지만 latency 때문에 기본값으로 두지 않았다. |
| BGE reranker 기본값 | 품질은 좋지만 p95 latency가 커서 기본 API route에서 제외했다. |
| GraphRAG-lite | relationship 질문에서 기준선을 넘는 근거가 없어 기본값으로 쓰지 않았다. |
| RAPTOR-lite | overview/place_story 질문에서 nDCG@5가 하락해 기본값에서 제외했다. |
| HyDE | 확대 live 비교에서 MRR, nDCG@5, latency가 악화되어 기본 route로 기각했다. |
| active route default | locked retrieval에서 relationship hybrid 개선 주장이 실패해 기본 활성화하지 않았다. |
| Solar Pro 3 repaired v2 | citation precision은 올랐지만 citation recall이 낮아져 기본 generation contract로 채택하지 않았다. |

## 금지 Claim

- production 성능 검증 완료
- locked test에서 최종 성능 개선 입증
- GraphRAG로 성능 개선
- RAPTOR로 성능 개선
- HyDE로 최종 검색 성능 개선
- Solar Pro 3 답변 품질 최종 개선
- 음성 관광 앱 완성
- 전체 도서 데이터 공개

## 허용 Claim

- 평가 기반 RAG 의사결정 구조를 만들었다.
- 도서 parser 결과를 citation 가능한 RAG corpus로 정규화했다.
- C0 parent-child chunking을 현재 기준선으로 유지했다.
- `dense_multilingual_e5_small_voice_rewrite`를 현재 non-rerank 기본 후보로 둔다.
- 여러 고급 RAG 후보를 질문 유형별로 비교했고 일부는 기본값에서 제외했다.
- `/api/v1/chat` contract와 `spoken_answer` field를 구현했다.
- browser voice-ready UI skeleton, contract smoke, visual QA를 완료했다.
- public repo에는 private corpus와 secret을 포함하지 않는다.

## 리허설 채점표

| check | 통과 기준 |
| --- | --- |
| 30초 요약 | 문제, 데이터, RAG 평가, claim boundary가 모두 들어간다. |
| 3분 설명 | 문제, 제약, RAG 설계, 기각 판단, API/demo, 한계를 순서대로 말한다. |
| 기각 후보 설명 | 최소 5개 후보를 기각 사유와 함께 말한다. |
| 금지 claim 회피 | 금지 claim 8개를 성공 표현으로 말하지 않는다. |
| public safety | raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 말하지 않는다. |

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

## 다음 작업

필수 포트폴리오 제출 gate는 여기서 완료다.

후속 개발을 이어간다면 `HD-VOICE-STT-TTS-PLAN-001`로 실제 STT/TTS demo 범위, 비용, 개인정보 처리, 실패 대응을 별도 계획으로 분리한다.
