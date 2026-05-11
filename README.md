# History Docent RAG

서울을 방문한 한국인과 외국인에게 한양의 역사 맥락을 설명하는 역사 관광 도슨트 서비스의 RAG 백엔드 프로젝트.

원본 데이터는 `벌거벗은 한국사` 등 한국사 도서의 Upstage Parser 결과를 기반으로 한다.

## 프로젝트 정체성

이 저장소는 일반 챗봇 데모가 아니다.

목표는 다음이다.

- 서울 주요 관광지를 한양 역사 맥락과 연결한다.
- 한국사 도서 parser 결과를 정규화한다.
- 문서 구조와 citation provenance를 보존한다.
- 장소, 인물, 사건, 제도 중심으로 근거를 검색한다.
- 관광객에게 짧고 재미있게 설명할 수 있는 답변을 생성한다.
- 근거 기반 답변 품질을 고정 평가셋으로 검증한다.

## 포트폴리오 기준 역할

지원 직무:

- AI 백엔드
- RAG 엔지니어
- 데이터 기반 LLM 애플리케이션 개발

본인 역할:

- Upstage Parser 결과 정규화
- 서울/한양 장소 catalog 설계
- parent-child chunking 재설계
- BM25 baseline 구현과 Dense/Hybrid retrieval 비교 설계
- citation RAG answer contract 설계
- 단계별 evaluation gate 구축

핵심 기술:

- Python
- FastAPI
- Pydantic
- Upstage Parser
- Solar Pro 3
- BM25
- Dense Retrieval
- Hybrid Retrieval
- Jupyter Notebook
- pytest

## 1차 범위

포함:

- Upstage Parser 결과 정규화
- 서울/한양 장소 catalog 설계
- 구조 보존 parent/child chunking
- BM25 baseline retrieval
- dense retrieval 및 hybrid retrieval 실험 설계
- 장소명, 지시어, 짧은 음성형 질문을 위한 query rewrite
- Solar Pro 3 기반 citation RAG 답변 생성 계약
- retrieval/generation 평가 harness
- 실패 분석과 ablation report

1차 공개 버전에서 제외:

- 원본 PDF
- 전체 parser JSON
- 전체 chunk text
- 전체 vector database
- 전체 raw evaluation CSV
- frontend service
- voice UI
- 기본 pipeline으로서의 GraphRAG
- 기본 pipeline으로서의 full RAPTOR

## 목표 Pipeline과 현재 구현 범위

현재 구현 완료:

```text
PDF
-> Upstage Parser 결과
-> canonical element schema
-> parser 품질 검사
-> 서울/한양 장소 catalog
-> parent/child chunks
-> BM25 baseline
-> retrieval evaluation harness
-> public-safe aggregate reports
```

후속 구현 대상:

```text
chunking ablation
-> dense/vector indexes
-> place-aware query rewrite
-> hybrid retrieval
-> parent context expansion
-> evidence packing
-> Solar Pro 3 generation
-> answer with citations
-> evaluation logging
```

## RAG 전략

기본 production 후보:

```text
Place-aware Hybrid Retrieval + Query Rewrite + Parent-Child Chunking + Citation RAG
```

RAPTOR-lite와 GraphRAG-lite는 초기 기본 구조가 아니라 비교 실험군으로 둔다.

비교 실험의 순서와 후보군은 [Retrieval Ablation Plan](docs/RETRIEVAL_ABLATION_PLAN.md)에 고정한다.
이 계획은 chunking, embedding, hybrid retrieval, reranker, query rewrite, evidence packing, Solar Pro 3 generation, RAPTOR-lite, GraphRAG-lite를 한 번에 섞지 않고 단계별로 검증하기 위한 문서다.

## 제품 목표

최종 서비스는 서울 관광 중 사용할 수 있는 역사 도슨트다.

예상 사용자는 다음이다.

- 서울을 여행하는 한국인
- 서울을 방문한 외국인
- 경복궁, 광화문, 북촌, 종로, 한양도성 등에서 역사적 맥락을 알고 싶은 사용자

답변 스타일은 다음을 지향한다.

- 짧다.
- 현장에서 듣기 쉽다.
- 장소와 역사 사건을 연결한다.
- 과장된 이야기가 아니라 근거 있는 설명을 제공한다.
- 화면에는 citation을 표시하고, 음성 답변에는 자연스럽게 축약한다.

## 공개 저장소 데이터 정책

이 public repository에는 저작권이 있는 원문 텍스트를 대량으로 포함하지 않는다.

허용:

- 코드
- 설정 파일
- 집계 metric
- 소량의 익명화 sample
- 문서

금지:

- 원본 도서 또는 PDF
- 전체 parser output
- 전체 OCR text
- 전체 chunk file
- 전체 vector index
- secret 또는 API key

## 문서 언어 정책

공개 README와 docs 하위 문서는 한글로 작성한다.

코드, API field, config key, metric 이름은 영어를 유지한다.

## 현재 상태

프로젝트 재시작 계획과 평가 gate 정리 완료.

canonical source를 `History_Docent`로 고정했고, 원본 PDF와 Upstage Parser 산출물의 `source_inventory` gate를 통과했다.

`data_manifest`와 `normalized_blocks` schema를 고정했고, parser normalization pipeline과 parser quality report도 통과했다.

parent-child chunking 전략과 gate를 문서로 고정했고, 실제 chunking pipeline도 통과했다.

BM25 baseline retrieval input contract와 seed 평가셋을 고정했다.

BM25 baseline retriever를 구현했고, seed 평가셋 기준 정량/정성 리포트를 생성했다.

현재 BM25 baseline 결과는 `Recall@5=0.250000`, `MRR=0.152778`, `nDCG@5=0.120124`다. 이 수치는 성능 개선 주장이 아니라 Dense/Hybrid/query rewrite 비교를 위한 기준선이다.

서울/한양 장소 catalog seed를 공개 가능한 형태로 작성했고, alias/relation/public leakage gate를 통과했다.

retrieval evaluation harness를 공통화했고, BM25 baseline을 새 harness에서 재현했다.

실서비스 기준의 RAG ablation 비교 실험 계획을 문서화했다.

retrieval 평가셋 v2 metadata contract와 dev/test split readiness gate를 추가했다. 현재 seed-only 상태라 contract gate는 통과하고 split readiness gate는 실패 상태다.

retrieval judgment target resolvability gate를 추가해 seed 평가셋의 child/parent/doc target이 실제 검색 corpus에 매핑되는지 검증했다.

retrieval 평가셋 확장 리포트를 추가했다. public seed 기준 현재 `contract_status=PASS`, `review_readiness_status=PASS`, `expansion_readiness_status=INCOMPLETE`, `target_query_count=105`, `current_query_count=14`, `overall_shortfall_count=91`, `dev_test_shortfall_count=105`다.

105개 full benchmark는 public repository에 직접 올리지 않고 local private storage에서 관리한다. public에는 seed/sample과 집계 report만 남긴다.

private dev 평가셋 70개를 작성하고 review rubric 기준으로 `reviewed` 승격했다. public-safe 집계 리포트 기준 `review_gate_status=PASS`, `target_resolvability_status=PASS`, `missing_child_target_count=0`, `public_raw_text_leakage_count=0`이다. private dev 원본 JSONL은 public repository에 commit하지 않는다.

private test 평가셋 35개를 작성하고 `locked` 상태로 고정했다. public-safe 집계 리포트 기준 `test_lock_gate_status=PASS`, `target_resolvability_status=PASS`, `benchmark_readiness_status=PASS`, `missing_child_target_count=0`, `public_raw_text_leakage_count=0`이다. private test 원본 JSONL은 public repository에 commit하지 않는다.

BM25 기준 chunking ablation runner를 구현했고, private dev split 70개에서 C0/C1/C2를 비교했다. 모든 variant가 chunking gate를 통과했지만 C1/C2가 개선 조건을 충족하지 못해 `selected_variant_id=C0`으로 유지했다. locked test split은 사용하지 않았다.

다음 단계는 C0 chunking을 기준으로 Dense retrieval baseline과 Hybrid retrieval을 같은 dev/test contract에서 비교하는 것이다.

## 실행 전략

단계별 구현 순서, 정량/정성 평가 기준, 포트폴리오 산출물 기준은 [실행 전략](docs/EXECUTION_STRATEGY.md)에 정리한다.

## 개발 문서

| 문서 | 목적 |
| --- | --- |
| [PRD](docs/PRD.md) | 제품 목적, MVP, non-goal, 성공 기준 |
| [Data Policy](docs/DATA_POLICY.md) | public/private 데이터와 benchmark 공개 범위 정책 |
| [Source Data Decision](docs/SOURCE_DATA_DECISION.md) | canonical source 선정과 첫 번째 데이터 gate |
| [Data Contracts](docs/DATA_CONTRACTS.md) | data manifest와 normalized block 계약 |
| [Normalization](docs/NORMALIZATION.md) | parser 결과를 NormalizedBlock으로 변환하는 규칙과 gate |
| [Parser Quality Report](docs/PARSER_QUALITY_REPORT.md) | 청킹 전 parser/block 품질 지표와 해석 |
| [Chunking Strategy](docs/CHUNKING_STRATEGY.md) | parent-child chunking grain, boundary, filtering, citation 정책 |
| [Chunking Gates](docs/CHUNKING_GATES.md) | chunking 구현 후 통과해야 할 정량 gate |
| [Chunking Quality Report](docs/CHUNKING_QUALITY_REPORT.md) | parent-child chunking 결과의 정량/정성 평가 |
| [Place Catalog](docs/PLACE_CATALOG.md) | 서울/한양 장소 seed, alias, relation, 공개 정책 |
| [Place Catalog Validation Report](evals/reports/place_catalog_validation_report.md) | 장소 catalog seed의 정량/정성 gate 결과 |
| [BM25 Baseline Plan](docs/BM25_BASELINE_PLAN.md) | BM25 baseline 입력 계약, metric, 실패 분석 계획 |
| [Retrieval Eval Dataset](docs/RETRIEVAL_EVAL_DATASET.md) | retrieval seed 평가셋의 정량/정성 품질 보고서 |
| [Retrieval Eval Review Rubric](docs/RETRIEVAL_EVAL_REVIEW_RUBRIC.md) | retrieval dev/test 평가셋의 draft/reviewed/locked 승격 기준 |
| [Retrieval Eval Dataset Report](evals/reports/retrieval_eval_dataset_report.md) | retrieval 평가셋 v2 contract와 split gate 결과 |
| [Retrieval Eval Target Resolvability Report](evals/reports/retrieval_eval_target_resolvability_report.md) | retrieval judgment target의 corpus 매핑 검증 결과 |
| [Retrieval Eval Expansion Report](evals/reports/retrieval_eval_expansion_report.md) | retrieval dev/test 평가셋 확장 현황과 부족분 |
| [Private Dev Eval Expansion Report](evals/reports/retrieval_eval_private_dev_expansion_report.md) | private dev reviewed 70개 집계 현황과 test 부족분 |
| [Private Dev Eval Target Report](evals/reports/retrieval_eval_private_dev_target_report.md) | private dev reviewed 70개 target resolvability 검증 결과 |
| [Private Dev Eval Review Report](evals/reports/retrieval_eval_private_dev_review_report.md) | private dev 70개 review gate 결과 |
| [Private Test Eval Target Report](evals/reports/retrieval_eval_private_test_target_report.md) | private test locked 35개 target resolvability 검증 결과 |
| [Private Test Eval Lock Report](evals/reports/retrieval_eval_private_test_lock_report.md) | private test 35개 lock gate 결과 |
| [Private Benchmark Readiness Report](evals/reports/retrieval_eval_private_benchmark_readiness_report.md) | private dev 70개와 test 35개의 ablation benchmark readiness 결과 |
| [Retrieval Ablation Plan](docs/RETRIEVAL_ABLATION_PLAN.md) | 실서비스 기준 RAG 비교 실험 순서, 논문 매핑, 선택 기준 |
| [BM25 Baseline Report](evals/reports/bm25_baseline_report.md) | BM25 baseline 실행 결과와 query type별 실패 분석 |
| [Retrieval Harness Report](evals/reports/retrieval_harness_report.md) | BM25/Dense/Hybrid 공통 평가 harness와 BM25 재현 결과 |
| [Chunking Ablation Report](evals/reports/chunking_ablation_report.md) | BM25 dev-only C0/C1/C2 chunking 비교 결과 |
| [WBS](docs/WBS.md) | 단계별 작업, 산출물, commit 단위 |
| [Checklist](docs/CHECKLIST.md) | 단계별 통과 기준과 공개 전 검수 |
| [TODO](docs/TODO.md) | 즉시 실행할 작업 목록 |
| [Notebook Guide](docs/NOTEBOOK_GUIDE.md) | numbered notebook 작성 규칙 |
| [Portfolio Strategy](docs/PORTFOLIO_STRATEGY.md) | README, 이력서, 면접 메시지 |
| [Eval Gates](docs/EVAL_GATES.md) | 정량/정성 평가와 개선 주장 규칙 |
| [Execution Strategy](docs/EXECUTION_STRATEGY.md) | 상세 실행 전략 |

## Notebook 체계

notebook은 분석과 검증 기록용이다. 핵심 구현은 Python module에 둔다.

경로:

```text
notebooks/
```

작성 규칙은 [Notebook Guide](docs/NOTEBOOK_GUIDE.md)를 따른다.
