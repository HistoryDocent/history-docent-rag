# 평가 계획

## 평가 목표

그럴듯한 데모가 아니라, retrieval 또는 generation 변경이 한국사 grounded QA 품질을 실제로 개선하는지 측정한다.

## 평가셋 분리

### dev_synthetic

- 300~500개
- source chunk 기반 생성
- 빠른 실험용
- tuning 허용

### holdout_synthetic

- 500~1000개
- 문서, 섹션, 역사적 episode 단위로 group split
- 직접 tuning 금지

### external_human

- 200~300개
- 한국사 시험, 박물관, 도슨트형 질문 기반
- 포트폴리오의 핵심 신호

### stress_set

- 100~200개
- no-answer, wrong premise, 날짜 혼동, multi-hop, OCR noise 포함

## 필수 Field

각 평가 예시는 다음 field를 가져야 한다.

- `query`
- `gold_answer`
- `acceptable_aliases`
- `supporting_chunk_ids`
- `question_type`
- `difficulty`
- `answerable`
- `source_group_id`

## Retrieval Metrics

- `Recall@1`
- `Recall@3`
- `Recall@5`
- `MRR`
- `nDCG@5`
- latency percentile

## Generation Metrics

- factual correctness
- faithfulness
- answer relevancy
- citation precision
- citation recall
- abstention precision
- abstention recall

## 대표 Portfolio Metric

```text
Correct-with-Evidence
```

통과 조건:

1. 답변이 맞다.
2. citation evidence가 답변을 지지한다.
3. 핵심 unsupported claim이 없다.

## 필수 Ablation

한 번에 하나의 요소만 바꾼다.

- BM25 vs dense vs hybrid
- hybrid with query rewrite vs without query rewrite
- child-only vs parent-child
- with reranker vs without reranker
- with compression vs without compression
- baseline vs RAPTOR-lite
- baseline vs GraphRAG-lite

## 통계 판단 규칙

query 단위 paired comparison을 사용한다.

보고 항목:

- mean delta
- 95% bootstrap confidence interval
- query-type breakdown
- latency delta
- cost delta

개선 주장 금지 조건:

- confidence interval이 0을 지난다.
- latency 또는 cost가 증가했는데 tradeoff 설명이 없다.
- synthetic dev data에서만 개선된다.
