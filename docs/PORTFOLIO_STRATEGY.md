# Portfolio Strategy

## 대표 메시지

```text
서울 관광객의 장소 기반 질문에 대해, 한국사 도서 parser 결과에서 근거를 검색하고 citation 기반 도슨트 답변을 생성하는 RAG 백엔드
```

현재 포트폴리오 핵심 메시지는 다음이다.

```text
도서 parser output을 citation 가능한 RAG corpus로 재구성하고, 청킹, retrieval, reranker, query rewrite, evidence packing, generation contract, GraphRAG-lite, query type router를 단계별로 비교해 채택/보류/기각을 근거 기반으로 정리한 프로젝트
```

## README 첫 화면 구성

1. 프로젝트 한 줄 정의
2. 문제 정의
3. 대상 사용자
4. 내 역할
5. 핵심 기술
6. 아키텍처
7. 평가 설계
8. 현재 stack과 결과 표
9. 데이터 공개 정책
10. 한계와 다음 개선

## 이력서 문장 초안

```text
HistoryDocent | 서울/한양 역사 관광 도슨트 RAG 백엔드 | 개인 프로젝트
- Upstage Parser 기반 한국사 도서 데이터를 element 단위로 정규화하고 page/section/chunk provenance를 보존하는 전처리 pipeline 설계
- 서울 주요 장소와 한양 역사 맥락을 연결하기 위해 place catalog, parent-child chunking, BM25 baseline, neural dense, Hybrid, BGE reranker, deterministic query rewrite, evidence packing, GraphRAG-lite, query type router 비교 실험 구현
- `dense_multilingual_e5_small_voice_rewrite`를 현재 non-rerank 기본 후보로 두고, relationship query에는 hybrid weighted E5 route 후보를 분리하는 deterministic router skeleton 구현
- Solar Pro 3 기반 citation RAG answer contract, generation evaluation harness, FastAPI `/api/v1/chat` contract와 retrieval-backed smoke 구현
- 저작권 원문과 private benchmark payload는 public repo에서 제외하고, 집계 metric과 public-safe report만 공개
```

“성능 개선 입증” 문장은 아직 쓰지 않는다. 대부분의 수치가 dev-only, live-dev-subset, locked-readiness-only 경계를 가진다.

## 면접 답변 포인트

### 왜 이 프로젝트를 했는가

서울 관광에서 장소와 역사 맥락이 분리되는 문제를 해결하기 위해 시작했다. 단순 챗봇이 아니라 원문 근거를 추적할 수 있는 RAG 백엔드로 범위를 좁혔다.

### 왜 GraphRAG를 처음부터 쓰지 않았는가

GraphRAG는 relationship 질문에 유리하지만 entity extraction과 canonicalization 오류가 전체 결과를 오염시킬 수 있다. 그래서 BM25/Hybrid/Parent-Child/Citation 구조를 기준선으로 먼저 만들고, GraphRAG-lite는 relationship 질문 전용 실험군으로 분리했다.

### 성능을 어떻게 검증했는가

retrieval과 generation을 분리했다. 현재는 BM25 baseline, retrieval evaluation harness, private dev 70개 reviewed 평가셋, private test 35개 locked 평가셋, BM25 dev-only chunking ablation v2, Dense retrieval baseline v1, BM25-Dense 보완성 분석, Hybrid RRF/Weighted 비교, neural embedding 비교, neural dense Hybrid 비교, BGE reranker 비교, deterministic query rewrite 비교까지 구축했다. 청킹 실험에서는 C0-C6을 비교했고 smaller/larger child, micro-parent merge, overlap 0/2, fixed-size block baseline 모두 C0를 넘지 못해 current parent-child chunking을 유지했다. Dense v1은 BM25보다 낮았지만 neural dense에서는 `multilingual-e5-small`이 `Recall@5=0.733333`, `MRR=0.675556`, `nDCG@5=0.533797`로 BM25 dev 기준선을 넘었고, BGE-M3는 `Recall@5=0.800000`으로 가장 높았지만 latency가 컸다. Neural dense Hybrid에서는 `hybrid_weighted_e5_small_alpha_0_5`가 `Recall@5=0.783333`으로 E5 dense 단독보다 높았지만 `MRR`, `nDCG@5`, latency가 나빠 기본 검색 후보로 채택하지 않았다. BGE reranker top20은 `Recall@5=0.833333`, `MRR=0.761667`, `nDCG@5=0.635787`로 가장 높았지만 `latency_p95_ms=13140.690300`이라 CPU 실시간 API 기본 후보에서 제외했다. Query rewrite에서는 전체 place rewrite가 평균 Recall@5는 올렸지만 일부 place/story query의 top-rank를 악화시켜 기본값에서 제외했고, voice-only rewrite가 `Recall@5=0.850000`, `MRR=0.758056`, `nDCG@5=0.615293`, `latency_p95_ms=19.560200`으로 가장 균형이 좋았다. Retrieval 비교는 Recall@k, MRR, nDCG, latency, no-answer candidate count로 진행하고, 최종 답변은 후속 generation 단계에서 Correct-with-Evidence와 citation precision/recall로 판단하도록 gate를 설계했다. 개선 여부는 locked test set에서 query 단위 paired comparison과 bootstrap confidence interval 조건을 만족한 뒤에만 주장한다.

### 무엇을 기각했는가

GraphRAG-lite는 relationship dev 10개에서 hybrid reference 대비 nDCG@5 개선이 없어 기본값으로 승격하지 않았다. Solar Pro 3 repaired v2는 citation precision은 올렸지만 citation recall이 떨어져 기본값에서 제외했다. `place_story_guarded_boost_v1`은 locked readiness에서 candidate 선택이 0건이라 production route로 채택하지 않았다. 이 프로젝트에서는 좋은 수치 하나만 보고 채택하지 않고, latency, citation recall, locked readiness를 함께 봤다.

### 저작권 데이터는 어떻게 처리했는가

원본 PDF, 전체 parser output, 전체 chunk text는 public repo에 올리지 않았다. 공개 repo에는 schema, code, aggregate metric, redacted sample만 포함했다.

### 음성 서비스와 RAG 백엔드는 어떻게 연결되는가

음성 UI보다 먼저 짧은 질문 처리, 지시어 해소, `spoken_answer`, citation display를 백엔드 계약으로 분리했다. 현재 검증 완료 범위는 retrieval 평가셋, BM25 baseline, chunking ablation v2, Dense baseline, BM25-Dense 보완성 분석, Hybrid retrieval 비교, neural embedding 비교, neural dense Hybrid 비교, reranker 비교, query rewrite 비교이며, `spoken_answer` 생성과 STT/TTS는 Solar Pro 3 generation 단계 이후로 분리했다.

## 금지 표현

- 음성 관광 앱 완성
- 상용 수준 서비스
- GraphRAG 적용 완료
- 성능 개선 입증
- 전체 도서 데이터 공개
- 최신 RAG 기법 다수 적용

## 제출 전 검수

- GitHub 링크가 public으로 열리는가
- README 첫 화면에서 문제/역할/기술/평가가 보이는가
- 원본 저작권 데이터가 없는가
- 미검증 수치가 없는가
- notebook이 원문을 대량 출력하지 않는가
- [Portfolio Result Summary](PORTFOLIO_RESULT_SUMMARY.md)의 claim boundary와 README 표현이 일치하는가
