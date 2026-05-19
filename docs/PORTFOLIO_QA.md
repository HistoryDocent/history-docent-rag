# Portfolio QA

## 결론

`HD-PORTFOLIO-QA-001`은 HistoryDocent 프로젝트를 이력서와 면접에서 설명하기 위한 제출 문구를 고정한다.

핵심 메시지는 "RAG 성능 개선을 최종 입증했다"가 아니다. 핵심은 도서 parser 결과를 citation 가능한 RAG corpus로 재구성하고, 청킹, retrieval, reranker, query rewrite, generation, advanced RAG 후보를 같은 gate로 비교해 채택과 기각을 근거 기반으로 판단했다는 점이다.

이 문서는 public-safe 제출 문구만 다룬다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 제출용 한 줄

```text
한국사 도서 parser 결과를 citation 가능한 RAG corpus로 정규화하고, 청킹·검색·리랭킹·query rewrite·고급 RAG 후보를 단계별로 비교해 서울/한양 관광 도슨트용 `/api/v1/chat` 응답 계약까지 구현한 AI 백엔드 프로젝트입니다.
```

## 이력서 프로젝트 문장

```text
HistoryDocent | 서울/한양 역사 관광 도슨트 RAG 백엔드 | 개인 프로젝트
- Upstage Parser 결과를 canonical element, normalized block, parent-child chunk로 정규화하고 page/section/citation provenance를 보존하는 데이터 파이프라인을 설계했습니다.
- BM25, dense retrieval, hybrid retrieval, BGE reranker, deterministic query rewrite, evidence packing, GraphRAG-lite, RAPTOR-lite, HyDE를 단계별로 비교하고 Recall@k, MRR, nDCG@5, latency, citation recoverability 기준으로 채택/보류/기각을 분리했습니다.
- 최종 제출용 기본선은 `C0 parent-child chunking + dense_multilingual_e5_small_voice_rewrite + P0_rank_order + Solar Pro 3 generation v1`로 고정했고, relationship hybrid route는 locked retrieval 비교에서 개선 주장을 통과하지 못해 shadow 후보로만 유지했습니다.
- FastAPI `/api/v1/chat` 계약에서 사용자용 답변 필드, `spoken_answer`, citation trace, no-answer abstain, classifier/router dry-run, active route flag dry-run을 public-safe sample로 문서화했습니다.
- 원본 PDF, 전체 parser output, 전체 chunk text, private eval payload, secret은 public repo에서 제외하고 집계 metric과 검증 리포트만 공개했습니다.
```

## README 제출 요약

```text
HistoryDocent는 서울을 방문한 사용자에게 한양의 역사 맥락을 설명하는 관광 도슨트 RAG 백엔드입니다. 도서 parser 결과를 citation 가능한 corpus로 재구성하고, 청킹부터 검색, 리랭킹, query rewrite, evidence packing, generation contract, GraphRAG-lite, RAPTOR-lite, HyDE, route guard까지 단계별로 비교했습니다. 좋은 수치만 선택하지 않고 latency, citation recall, locked retrieval 결과를 기준으로 여러 후보를 기각했으며, 공개 저장소에는 저작권 원문과 private benchmark payload를 포함하지 않았습니다.
```

## 면접 답변

### 1. 이 프로젝트를 한 이유

서울 관광에서 장소와 역사 맥락이 분리되는 문제가 있다고 봤습니다. 사용자가 경복궁, 광화문, 북촌처럼 특정 장소에서 질문할 때 단순 지식 답변이 아니라 근거가 추적되는 짧은 도슨트 답변이 필요하다고 판단했습니다. 그래서 프론트엔드나 음성 UI보다 먼저 parser 결과 정규화, citation 가능한 chunk, 검색 평가, `/api/v1/chat` 응답 계약을 백엔드 중심으로 만들었습니다.

### 2. 본인 역할

데이터 계약, parser normalization, parent-child chunking, retrieval evaluation harness, RAG ablation, generation answer contract, FastAPI chat contract를 설계하고 구현했습니다. 특히 public repo에 원문을 올릴 수 없는 제약이 있어서 private corpus와 public aggregate report를 분리하고, 결과는 metric과 claim boundary 중심으로 공개했습니다.

### 3. RAG를 어떻게 고도화했는가

한 번에 GraphRAG나 RAPTOR로 가지 않았습니다. 먼저 C0-C6 청킹 후보를 비교해 C0 parent-child chunking을 유지했고, BM25를 기준선으로 둔 뒤 neural dense, hybrid, reranker, query rewrite를 단계별로 비교했습니다. 최종적으로 `dense_multilingual_e5_small_voice_rewrite`가 dev 기준 Recall@5와 nDCG@5 균형이 좋아 non-rerank 기본 후보가 됐고, BGE reranker는 품질은 높았지만 latency 때문에 기본값에서 제외했습니다.

### 4. GraphRAG와 RAPTOR를 왜 기본값으로 쓰지 않았는가

GraphRAG-lite는 relationship 질문군에 한정해 비교했고 nDCG@5 개선이 없었습니다. RAPTOR-lite도 overview/place_story 질문군에서 기준선을 넘지 못했습니다. 그래서 "최신 기법을 적용했다"가 아니라 "질문 유형을 나눠 실험했고 개선이 없어서 기본값에서 제외했다"로 판단했습니다.

### 5. 실패하거나 기각한 사례

HyDE는 5개 live-dev-subset에서는 Recall@5가 올랐지만 MRR과 latency trade-off가 있었고, 40개 확대 live 비교에서는 MRR, nDCG@5, latency가 악화되어 기본 route로 기각했습니다. relationship hybrid route도 dev shadow에서는 유망했지만 locked relationship subset에서 MRR delta가 음수라 active route 개선 주장을 보류했습니다. 이 프로젝트의 강점은 좋은 결과만 남긴 것이 아니라 기각 근거를 문서화한 점입니다.

### 6. Solar Pro 3는 어디에 쓰였는가

Solar Pro 3는 LLM generation이 필요한 순간에만 사용하도록 분리했습니다. provider contract, live smoke, generation baseline, repaired v2 비교는 진행했지만, 최종 문구에서는 Solar Pro 3 품질 개선을 입증했다고 말하지 않습니다. 현재 기본 generation은 v1을 유지하고, API sample은 `contract_only` fixture로 응답 구조만 보여줍니다.

### 7. 음성 서비스는 어디까지 구현됐는가

음성 앱 자체는 아직 구현하지 않았습니다. 대신 음성 UI에 연결될 백엔드 계약으로 `spoken_answer`를 사용자용 답변 필드와 분리했습니다. 화면에는 citation trace를 보여주고, 음성에는 citation 표기 없이 짧게 들을 수 있는 답변을 제공하는 구조를 먼저 고정했습니다.

### 8. 데이터 공개와 보안은 어떻게 처리했는가

원본 PDF, 전체 parser output, 전체 chunk text, private eval payload, secret은 public repo에 올리지 않았습니다. 공개 문서에는 raw query, raw answer, raw evidence, prompt, chunk text, private path를 남기지 않고, 집계 metric과 sanitized sample만 기록했습니다.

### 9. 이 프로젝트에서 가장 중요한 의사결정

active route를 바로 켜지 않은 결정입니다. dev shadow에서는 relationship route가 좋아 보였지만 locked retrieval paired comparison에서 개선 주장을 통과하지 못했습니다. 그래서 active route는 API flag dry-run과 shadow 관찰 필드로만 남기고 기본 적용하지 않았습니다. 실서비스라면 이런 보수적인 gate가 필요하다고 봤습니다.

### 10. 다음 개선

먼저 제출 문구와 README를 안정화한 뒤, hard subset에 한해 ColBERT style late interaction을 검토할 수 있습니다. 다만 새 실험은 기존 final ablation 기준선을 깨지 않도록 별도 branch 또는 명확한 work_id로 분리해야 합니다.

## 금지 표현

- production 성능 검증 완료
- locked test에서 최종 성능 개선 입증
- GraphRAG로 성능 개선
- RAPTOR로 성능 개선
- HyDE로 최종 검색 성능 개선
- Solar Pro 3 답변 품질 최종 개선
- 음성 관광 앱 완성
- 전체 도서 데이터 공개

## 제출 전 검수

| check | status | 기준 |
| --- | --- | --- |
| 문제 정의 | PASS | 서울/한양 관광 도슨트 RAG 백엔드로 설명 |
| 본인 역할 | PASS | 데이터 계약, RAG 평가, API 계약 중심 |
| 검증 근거 | PASS | Recall@k, MRR, nDCG@5, latency, citation recoverability, locked boundary |
| 과장 표현 제거 | PASS | production/locked 개선/음성 앱 완성 claim 금지 |
| public safety | PASS | raw query, raw answer, raw evidence, prompt, chunk text, private path, secret 미기록 |
| 면접 방어 가능성 | PASS | 채택뿐 아니라 기각 사유 포함 |

## 다음 작업

다음 작업은 `HD-PORTFOLIO-DEMO-001`이다.

다만 이 작업은 제출 패키징 이후의 후순위 실험이다. 실행 전에는 hard subset, 비교 기준, latency/cost gate, claim boundary를 별도로 승인받아야 한다.
