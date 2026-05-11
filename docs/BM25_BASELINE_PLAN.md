# BM25 Baseline Plan

## 목적

BM25를 Dense/Hybrid retrieval 비교의 기준선으로 고정한다.

이번 단계는 BM25 구현 전 계약 단계다. 검색 성능 개선을 주장하지 않는다.

## 입력 계약

BM25 index의 입력 단위는 `RetrievalDocument`다.

| field | 목적 |
| --- | --- |
| `retrieval_doc_id` | 검색 index 내부 문서 ID. 기본값은 `child_id` |
| `child_id` | citation 가능한 최소 검색 단위 |
| `parent_id` | parent context expansion 기준 |
| `doc_id` | 문서 단위 fallback relevance 판정 |
| `doc_title` | 사용자 설명과 실패 분석용 문서명 |
| `page_span` | citation page range 복구 |
| `source_block_ids` | 원문 block provenance |
| `context_block_ids` | heading 등 검색 문맥 보강 대상 |
| `text_hash` | 원문 미공개 상태에서 중복/변경 추적 |
| `text_length` | 길이 분포와 retrieval bias 분석 |
| `element_type_mix` | paragraph/table/list 등 구조 분석 |
| `citation_block_ids` | 최종 citation 복구 기준 |
| `search_text` | private runtime에서만 사용하는 검색 본문 |
| `context_text` | private runtime에서만 사용하는 heading/context text |

public repository에는 `search_text`, `context_text`, 전체 chunk text를 올리지 않는다.

## 평가 계약

모든 retrieval method는 같은 `RetrievalEvalItem`을 사용한다.

필수 metric:

- `Recall@1`
- `Recall@3`
- `Recall@5`
- `MRR`
- `nDCG@5`
- `latency_p50_ms`
- `latency_p95_ms`

추가 gate:

- `missing_result_count`
- `abstain_with_candidate_count`
- query type별 breakdown

Relevance 판정은 가장 세밀한 target을 우선한다.

```text
relevant_child_ids가 있으면 child 기준
없으면 relevant_parent_ids 기준
없으면 relevant_doc_ids 기준
```

동일 `method + query_id` 결과가 중복되면 metric 계산을 중단한다. 중복 결과를 조용히 덮어쓰면 recall/MRR/nDCG와 latency 표본 수가 서로 달라지기 때문이다.

## BM25 구현 원칙

- tokenizer는 한국어 공백/기호 기반 baseline으로 시작한다.
- query rewrite, place expansion, dense reranking은 baseline에 넣지 않는다.
- BM25의 역할은 "가장 단순한 lexical baseline"이다.
- 이후 Dense/Hybrid가 BM25보다 나은지 같은 평가셋으로 비교한다.

## 실험 순서

1. `<private parent_child_chunks report>`에서 `ChildChunk`를 읽는다.
2. `RetrievalDocument`로 변환한다.
3. private runtime에서만 `search_text`를 포함한다.
4. `evals/datasets/retrieval_eval_seed.jsonl`을 로드한다.
5. BM25 top-k 결과를 `RetrievalRunResult`로 저장한다.
6. `compute_retrieval_metrics`로 전체 metric을 계산한다.
7. query type별 metric을 별도 집계한다.
8. `evals/reports/bm25_baseline_report.md`에 정량/정성 리포트를 남긴다.

## 예상 실패 분석 항목

| 실패 유형 | 설명 |
| --- | --- |
| 장소명만 맞고 시대 맥락 불일치 | 예: 경복궁은 맞지만 조선 초 국가 설계 근거가 아님 |
| 인물명 lexical over-match | 예: 정도전 언급은 있으나 한양 천도와 무관 |
| 영어 질문 recall 하락 | 영어 query가 한국어 chunk와 lexical match가 약함 |
| 음성형 후속 질문 실패 | "그 사람", "거기"가 이전 맥락 없이 검색됨 |
| route 질문 분산 실패 | 여러 장소를 하나의 설명 흐름으로 묶지 못함 |
| no-answer false positive | corpus 밖 질문에도 관련 없는 역사 chunk를 반환 |

## 다음 구현 단위

다음 commit 후보:

```text
검색: BM25 baseline 구현과 평가 리포트 추가
```

포함 범위:

- BM25 index builder
- BM25 retriever
- retrieval eval runner
- `evals/results/bm25_baseline_results.jsonl`
- `evals/reports/bm25_baseline_report.md`
- `notebooks/06_bm25_baseline_evaluation.ipynb` 실행 기록 보강
