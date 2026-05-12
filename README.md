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
- BM25 baseline 구현과 Dense/Hybrid retrieval 비교 실험
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
-> hybrid retrieval
-> place-aware query rewrite
-> parent context expansion
-> evidence packing
-> Solar Pro 3 generation
-> answer with citations
-> evaluation logging
```

## RAG 전략

현재 검증 중인 production 후보:

```text
Place-aware Retrieval + Query Rewrite + Parent-Child Chunking + Citation RAG
```

검색 method는 실험 결과에 따라 고정한다. dev 기준 현재 1차 후보는 `multilingual-e5-small` dense 단독이고, Hybrid는 reranker 적용 전 recall-oriented 후보로 유지한다.

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

BM25 기준 chunking ablation runner를 v2로 확장했고, private dev split 70개에서 C0-C6을 비교했다. smaller/larger child, micro-parent merge, overlap 0/2, fixed-size block baseline 모두 C0를 넘지 못해 `selected_variant_id=C0`으로 유지했다. C4/C6은 `short_standalone_child` gate를 통과하지 못했다. locked test split은 사용하지 않았다.

Dense retrieval baseline v1을 구현했고, private dev split 70개에서 BM25와 `sklearn-tfidf-svd-v1` dense를 비교했다. Dense v1은 `Recall@5=0.350000`, `MRR=0.261111`, `nDCG@5=0.220955`로 BM25보다 낮아 개선 후보로 채택하지 않는다. 이 결과는 BGE-M3 또는 multilingual-E5 같은 neural embedding 결과가 아니다.

BM25-Dense 보완성 분석을 추가했다. Dense D0는 단독 성능은 낮지만 BM25가 놓친 query 2개를 맞춰 oracle union `Recall@5=0.600000`, BM25 대비 `+0.033333`을 기록했다. 이는 실제 Hybrid 성능 개선이 아니라 Hybrid RRF/Weighted 실험을 진행할 근거다.

Hybrid RRF/Weighted retrieval을 구현했고, private dev split 70개에서 BM25, Dense D0, H1 RRF, H2/H3/H4 Weighted alpha를 같은 harness로 비교했다. `hybrid_weighted_alpha_0_3`은 `Recall@1=0.416667`, `MRR=0.479722`, `nDCG@5=0.347259`로 BM25보다 top-rank 지표가 아주 소폭 높았지만 `Recall@5=0.566667`로 동일하고 `latency_p95_ms=23.038700`으로 BM25 대비 크게 느려 선택 gate를 통과하지 못했다. 따라서 D0 기반 Hybrid는 production 후보로 채택하지 않는다.

Neural embedding 비교 실험을 추가했고, private dev split 70개에서 BM25, Dense D0, BGE-M3, multilingual-E5-small, multilingual-MiniLM을 비교했다. `dense_multilingual_e5_small`은 `Recall@5=0.733333`, `MRR=0.675556`, `nDCG@5=0.533797`, `latency_p95_ms=15.717100`으로 BM25보다 높은 dev 지표를 보였다. `dense_bge_m3`는 `Recall@5=0.800000`, `nDCG@5=0.567476`으로 가장 높았지만 `latency_p95_ms=57.088400`으로 느렸다. 이 결과는 locked test와 generation 평가 전의 dev-only 후보 선별 결과이며, 최종 개선 주장으로 쓰지 않는다.

Neural dense 기반 Hybrid 비교 실험을 추가했고, private dev split 70개에서 E5-small/BGE-M3 dense leg와 RRF/Weighted fusion을 비교했다. `hybrid_weighted_e5_small_alpha_0_5`는 `Recall@5=0.783333`으로 E5-small dense 단독보다 높았지만 `MRR=0.655278`, `nDCG@5=0.509310`, `latency_p95_ms=27.547000`으로 E5-small dense 단독보다 top-rank 품질과 latency가 불리했다. 따라서 현재 기본 검색 후보는 `dense_multilingual_e5_small`이고, `hybrid_weighted_e5_small_alpha_0_5`는 reranker 비교에 투입할 recall-oriented 후보로 둔다.

Reranker comparison v1을 추가했고, private dev split 70개에서 `dense_multilingual_e5_small_rerank_bge_m3_top20`을 실제 `BAAI/bge-reranker-v2-m3` CrossEncoder로 비교했다. 이 후보는 `Recall@5=0.833333`, `MRR=0.761667`, `nDCG@5=0.635787`로 가장 높았지만 `latency_p95_ms=13140.690300`으로 CPU 실서비스 기본 후보로는 부적합하다. 따라서 현재 선택은 `dense_multilingual_e5_small`을 기본 검색 후보로 유지하고, reranker는 품질 상한과 오프라인/고비용 옵션으로만 둔다.

Query rewrite comparison v1을 추가했고, private dev split 70개에서 `dense_multilingual_e5_small`, 전체 place rewrite, voice-only rewrite를 비교했다. 전체 place rewrite는 `Recall@5=0.833333`으로 올랐지만 `place_fact`, `place_story`, `route_context`의 top-rank 품질이 일부 악화됐다. `dense_multilingual_e5_small_voice_rewrite`는 `Recall@5=0.850000`, `MRR=0.758056`, `nDCG@5=0.615293`, `latency_p95_ms=19.560200`을 기록했고 `voice_followup Recall@5`를 0.300000에서 1.000000으로 올렸다. 이 결과는 dev-only 후보 선별이며 locked test와 generation 평가 전의 최종 개선 주장이 아니다.

Evidence packing comparison v1을 추가했고, private dev split 70개에서 `dense_multilingual_e5_small_voice_rewrite` 검색 결과를 고정한 뒤 P0-P4 packing 정책을 비교했다. `P0_rank_order`와 `P3_mmr_diversity`가 `target_child_covered=0.850000`, `target_parent_covered=0.866667`, `target_doc_covered=0.950000`, `citation_recoverability=1.000000`으로 가장 높았다. `P3`의 개선은 duplicate parent rate를 0.127857에서 0.124286으로 낮춘 수준이라 generation 전 기본 교체 근거가 부족하다. 따라서 citation RAG generation v1 기본값은 `P0_rank_order`로 유지하고, `P3`는 diversity 후보로 둔다.

Citation RAG answer contract v1을 추가했다. `answer`, `spoken_answer`, `citations`, `evidence_ids`, `place_ids`, `abstained`, `unsupported_claim_risk`를 `citation-rag-answer/v1` 계약으로 고정했고, citation은 `child_id`, `parent_id`, `doc_id`, `source_block_ids`, `citation_block_ids`로 역추적한다. Solar Pro 3 호출은 아직 포함하지 않았고, public-safe 계약 리포트 기준 `citation_recoverability_rate=1.000000`, `missing_citation_count=0`, `private_path_leakage_count=0`, `secret_like_leakage_count=0`이다.

Generation evaluation harness v1을 추가했다. `CitationRagAnswer`를 `Correct-with-Evidence`, `citation_precision`, `citation_recall`, `place_relevance`, `docent_usefulness`, `spoken_answer_naturalness`, `unsupported_claim_rate`, `abstention_accuracy`, `latency_p95_ms`, `solar_call_count`, `estimated_cost`로 평가하는 구조를 고정했다. 현재 리포트는 contract-only smoke run이며 Solar Pro 3 품질 주장이 아니다. public-safe gate 기준 원문 answer/chunk text, private path, secret 누출은 0이다.

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
| [Chunking Ablation v2 Report](evals/reports/chunking_ablation_v2_report.md) | BM25 dev-only C0-C6 chunking 비교 결과 |
| [Dense Retrieval Baseline Report](evals/reports/dense_retrieval_baseline_report.md) | BM25 대비 Dense v1 baseline 비교 결과 |
| [Retrieval Overlap Analysis Report](evals/reports/retrieval_overlap_analysis_report.md) | BM25와 Dense D0의 query 단위 보완성 분석 결과 |
| [Hybrid Retrieval Comparison Report](evals/reports/hybrid_retrieval_comparison_report.md) | BM25, Dense D0, Hybrid RRF/Weighted alpha 비교 결과 |
| [Neural Embedding Retrieval Comparison Report](evals/reports/neural_embedding_retrieval_comparison_report.md) | BM25, D0, BGE-M3, multilingual-E5-small, multilingual-MiniLM 비교 결과 |
| [Neural Dense Hybrid Retrieval Comparison Report](evals/reports/neural_dense_hybrid_retrieval_comparison_report.md) | E5-small/BGE-M3 dense leg 기반 Hybrid RRF/Weighted 비교 결과 |
| [Reranker Retrieval Comparison Report](evals/reports/reranker_retrieval_comparison_report.md) | E5-small dense 후보와 BGE reranker top20 비교 결과 |
| [Query Rewrite Retrieval Comparison Report](evals/reports/query_rewrite_retrieval_comparison_report.md) | E5-small dense와 deterministic place/voice rewrite 비교 결과 |
| [Evidence Packing Comparison Report](evals/reports/evidence_packing_comparison_report.md) | 고정된 retrieval 결과 위에서 P0-P4 evidence packing 정책 비교 결과 |
| [Citation RAG Answer Contract Report](evals/reports/citation_rag_answer_contract_report.md) | Solar Pro 3 연결 전 citation RAG 응답 계약과 public-safe gate 결과 |
| [Generation Evaluation Harness Report](evals/reports/generation_eval_harness_report.md) | Solar Pro 3 연결 전 citation RAG 답변 평가 metric과 public-safe gate 결과 |
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
