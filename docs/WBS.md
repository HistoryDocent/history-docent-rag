# WBS

## Phase 0. 재시작 문서화

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 0.1 | PRD 작성 | `docs/PRD.md` | 제품 목적, MVP, non-goal 명시 | `docs: add restart plan docs` |
| 0.2 | WBS 작성 | `docs/WBS.md` | phase, 산출물, commit 단위 명시 | `docs: add restart plan docs` |
| 0.3 | Checklist 작성 | `docs/CHECKLIST.md` | 평가 gate, 공개 금지 항목 명시 | `docs: add restart plan docs` |
| 0.4 | TODO 작성 | `docs/TODO.md` | 즉시 작업과 후속 작업 분리 | `docs: add restart plan docs` |
| 0.5 | Notebook guide 작성 | `docs/NOTEBOOK_GUIDE.md` | numbered notebook 규칙 명시 | `docs: add restart plan docs` |
| 0.6 | Portfolio strategy 작성 | `docs/PORTFOLIO_STRATEGY.md` | README/이력서/면접 메시지 명시 | `docs: add restart plan docs` |
| 0.7 | Eval gates 작성 | `docs/EVAL_GATES.md` | 정량/정성 gate 명시 | `docs: add restart plan docs` |
| 0.8 | Notebook skeleton 생성 | `notebooks/*.ipynb` | 00~13 단계 생성 | `docs: add restart plan docs` |

## Phase 1. 데이터 계약

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 1.1 | data manifest schema | `app/domain/schemas.py` | Pydantic schema와 unit test 통과 | `feat: add data manifest schema` |
| 1.2 | normalized block schema | `app/domain/schemas.py` | block 필수 field 검증 | `feat: add normalized block schema` |
| 1.3 | sample data 정책 | `data_samples/*` | private path와 원문 과다 노출 없음 | `test: add public sample leakage checks` |
| 1.4 | parser normalization test | `tests/test_parser_normalization.py` | page/global/field 검증 | `test: add parser normalization validation` |

## Phase 2. Parser Normalization

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 2.1 | parser loader | `pipelines/normalize_parser_output.py` | private input에서 block 생성 | `feat: add parser normalization pipeline` |
| 2.2 | global page 복구 | normalization module | `page_global` 역전 0 | `feat: recover global page provenance` |
| 2.3 | quality flags | normalization module | OCR/base64/empty text flag 집계 가능 | `feat: add parser quality flags` |
| 2.4 | quality report | report generator | 집계 report 생성 | `feat: add parser quality report` |
| 2.5 | notebook 검증 | `02`, `03` notebooks | 집계표와 failure case 출력 | `docs: add parser quality notebooks` |

## Phase 3. Place Catalog

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 3.1 | seed catalog | `configs/place_catalog.seed.yaml` | 초기 7개 장소 등록 | `feat: add seoul place catalog seed` |
| 3.2 | place schema | domain schema | place id/name/alias 검증 | `feat: add place schema` |
| 3.3 | place search | place service | alias 검색 테스트 통과 | `feat: add place search` |
| 3.4 | notebook 검증 | `05_place_catalog_validation.ipynb` | 장소별 alias/related term 확인 | `docs: add place catalog validation notebook` |

## Phase 4. Chunking

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 4.1 | chunk schema | domain schema | child/parent 검증 | `feat: add chunk schemas` |
| 4.2 | parent-child builder | chunking pipeline | orphan child 0 | `feat: add parent child chunking` |
| 4.3 | citation backtracking | chunk metadata | citation recoverability 99% 이상 | `test: add chunk provenance tests` |
| 4.4 | notebook 분석 | `04_chunking_quality_analysis.ipynb` | chunk 품질 집계표 | `docs: add chunk quality notebook` |

## Phase 5. Retrieval Baseline

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 5.1 | BM25 baseline | retrieval module | Recall@k/MRR 측정 | `feat: add bm25 retrieval baseline` |
| 5.2 | 평가셋 확장 workflow | expansion report | 목표 105개 대비 부족분과 public gate 기록 | `평가: retrieval 평가셋 확장 리포트 추가` |
| 5.3 | benchmark 공개 범위 정책 | data policy, gitignore | full dev/test는 private, public은 sample/report만 허용 | `문서: benchmark 공개 범위 정책 고정` |
| 5.4 | private dev/test 평가셋 확장 | retrieval eval dataset | query type별 private dev/test split 고정 | `test: expand retrieval eval dataset` |
| 5.5 | chunking ablation | chunking experiment runner | C0-C6 비교와 winner 기록 | `test: add chunking ablation runner` |
| 5.6 | Dense retrieval | retrieval module | 동일 평가셋 비교 가능 | `feat: add dense retrieval baseline` |
| 5.7 | Hybrid retrieval | retrieval module | weighted/RRF 비교 가능 | `feat: add hybrid retrieval experiment` |
| 5.8 | Neural embedding comparison | retrieval module | BGE-M3, multilingual-E5, multilingual-MiniLM 비교 | `평가: neural embedding 검색 비교 실험 추가` |
| 5.9 | Reranker comparison | retrieval module | top30/top50 rerank 비교 | `feat: add reranker comparison` |
| 5.9 | evaluation harness | evals module | query type별 metric과 latency 출력 | `test: add retrieval evaluation harness` |
| 5.10 | notebooks | `06`, `07`, `09` notebooks | baseline/chunking/dense/hybrid 비교표 생성 | `docs: add retrieval evaluation notebooks` |

## Phase 6. Query Rewrite와 Citation RAG

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 6.1 | rewrite contract | application module | invalid JSON 0 | `feat: add place aware query rewrite` |
| 6.2 | answer contract | schema/service | answer/spoken_answer/citations 반환 | `feat: add citation rag answer contract` |
| 6.3 | Solar provider | provider abstraction | fake provider와 real provider 분리 | `feat: add solar provider abstraction` |
| 6.4 | evidence packing | application module | citation recoverability 유지 | `feat: add evidence packing policies` |
| 6.5 | generation eval | eval harness | Correct-with-Evidence와 unsupported claim 측정 | `test: add generation evaluation harness` |
| 6.6 | notebook | `08`, `10` notebooks | rewrite/evidence/generation ablation | `docs: add citation rag notebooks` |

## Phase 7. FastAPI 백엔드

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 7.1 | API contract | FastAPI routers | `/health`, `/places/search`, `/chat` | `feat: add fastapi chat contract` |
| 7.2 | rate limit | core module | 429 test 통과 | `feat: add api rate limiter` |
| 7.3 | cache | cache interface | cache hit 시 provider 미호출 | `feat: add response cache interface` |
| 7.4 | retry/timeout | provider policy | 429/5xx retry, 4xx retry 금지 | `feat: add provider retry policy` |
| 7.5 | security tests | tests | raw error/secret 노출 0 | `test: add api resilience tests` |

## Phase 8. 고급 RAG 실험

| ID | 작업 | 산출물 | 완료 기준 | Commit |
| --- | --- | --- | --- | --- |
| 8.1 | RAPTOR-lite | experiment module | overview/place_story만 비교 | `feat: add raptor lite experiment` |
| 8.2 | GraphRAG-lite | experiment module | relationship만 비교 | `feat: add graphrag lite experiment` |
| 8.3 | final report | docs/notebook | query type별 최종 판단 | `docs: add final ablation report` |
