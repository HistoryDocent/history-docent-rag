# Notebooks

이 폴더는 분석, 검증, 의사결정 기록용이다.

핵심 구현은 `app/`, `pipelines/`, `retrieval/`, `evals/`에 둔다.

## 규칙

- notebook은 단계별 번호를 유지한다.
- 원본 PDF 본문 전체를 출력하지 않는다.
- 전체 parser JSON을 저장하지 않는다.
- 전체 chunk text를 저장하지 않는다.
- API key, `.env`, private absolute path를 출력하지 않는다.
- 결과는 집계표, redacted sample, failure summary 중심으로 저장한다.

## 목록

| 파일 | 목적 |
| --- | --- |
| `00_project_scope.ipynb` | 제품 범위와 평가 기준 확인 |
| `01_data_manifest_audit.ipynb` | 문서 manifest와 private/public 분리 확인 |
| `02_parser_quality_check.ipynb` | parser 품질 집계 |
| `03_normalized_blocks_validation.ipynb` | normalized block schema 검증 |
| `04_chunking_quality_analysis.ipynb` | parent/child chunk 품질 분석 |
| `05_place_catalog_validation.ipynb` | place catalog alias와 관련성 검증 |
| `06_bm25_baseline_evaluation.ipynb` | BM25 기준선 평가 |
| `07_dense_hybrid_retrieval_comparison.ipynb` | Dense/Hybrid 비교 |
| `08_query_rewrite_ablation.ipynb` | query rewrite on/off 비교 |
| `09_parent_child_retrieval_ablation.ipynb` | parent-child 효과 비교 |
| `10_citation_rag_generation_eval.ipynb` | citation RAG 생성 평가 |
| `11_raptor_lite_experiment.ipynb` | RAPTOR-lite 실험 |
| `12_graphrag_lite_experiment.ipynb` | GraphRAG-lite 실험 |
| `13_final_ablation_report.ipynb` | 최종 결과 정리 |
