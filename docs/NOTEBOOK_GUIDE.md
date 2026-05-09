# Notebook Guide

## 목적

notebook은 구현체가 아니라 분석, 검증, 의사결정 기록이다.

핵심 로직은 Python module에 둔다.

## 번호 규칙

파일명은 두 자리 번호와 목적을 사용한다.

```text
00_project_scope.ipynb
01_data_manifest_audit.ipynb
02_parser_quality_check.ipynb
...
13_final_ablation_report.ipynb
```

## 작성 구조

각 notebook은 같은 구조를 가진다.

1. 목적
2. 입력
3. 실행 조건
4. 정량 지표
5. 정성 검수
6. 결과 표
7. 실패 사례
8. 판단
9. 다음 작업

## 금지

- 원본 PDF 본문 전체 출력
- 전체 parser JSON 출력
- 전체 chunk text 출력
- API key 출력
- `.env` 출력
- 긴 OCR 원문 출력
- base64 image 출력

## 허용

- 집계표
- 분포 그래프
- redacted sample
- metric table
- failure case 요약
- schema 예시

## Notebook 목록

| 번호 | 파일 | 목적 |
| --- | --- | --- |
| 00 | `00_project_scope.ipynb` | 제품 범위와 평가 기준 확인 |
| 01 | `01_data_manifest_audit.ipynb` | 문서 manifest와 private/public 분리 확인 |
| 02 | `02_parser_quality_check.ipynb` | parser 품질 집계 |
| 03 | `03_normalized_blocks_validation.ipynb` | normalized block schema 검증 |
| 04 | `04_chunking_quality_analysis.ipynb` | parent/child chunk 품질 분석 |
| 05 | `05_place_catalog_validation.ipynb` | place catalog alias와 관련성 검증 |
| 06 | `06_bm25_baseline_evaluation.ipynb` | BM25 기준선 평가 |
| 07 | `07_dense_hybrid_retrieval_comparison.ipynb` | Dense/Hybrid 비교 |
| 08 | `08_query_rewrite_ablation.ipynb` | query rewrite on/off 비교 |
| 09 | `09_parent_child_retrieval_ablation.ipynb` | parent-child 효과 비교 |
| 10 | `10_citation_rag_generation_eval.ipynb` | citation RAG 생성 평가 |
| 11 | `11_raptor_lite_experiment.ipynb` | RAPTOR-lite 실험 |
| 12 | `12_graphrag_lite_experiment.ipynb` | GraphRAG-lite 실험 |
| 13 | `13_final_ablation_report.ipynb` | 최종 결과 정리 |

## Commit 규칙

notebook은 실행 결과가 너무 커지면 저장하지 않는다.

필요하면 결과는 `evals/reports/`에 집계 markdown으로 저장한다.
