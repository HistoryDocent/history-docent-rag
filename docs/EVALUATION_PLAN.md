# Evaluation Plan

## Evaluation Goal

Measure whether a retrieval or generation change improves grounded Korean history QA, not whether a demo looks plausible.

## Dataset Splits

### dev_synthetic

- 300 to 500 examples
- generated from known source chunks
- used for fast iteration
- allowed for tuning

### holdout_synthetic

- 500 to 1000 examples
- grouped by document, section, or historical episode
- not tuned against directly

### external_human

- 200 to 300 examples
- based on Korean history exam, museum, and docent-style questions
- primary portfolio signal

### stress_set

- 100 to 200 examples
- no-answer, wrong premise, date confusion, multi-hop, OCR noise

## Required Fields

Each eval example must include:

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
- latency by percentile

## Generation Metrics

- factual correctness
- faithfulness
- answer relevancy
- citation precision
- citation recall
- abstention precision
- abstention recall

## Primary Portfolio Metric

```text
Correct-with-Evidence
```

A response passes only when:

1. the answer is correct
2. cited evidence supports the answer
3. no unsupported critical claim is present

## Required Ablations

Run one change at a time:

- BM25 vs dense vs hybrid
- hybrid with and without query rewrite
- child-only vs parent-child
- with and without reranker
- with and without compression
- baseline vs RAPTOR-lite
- baseline vs GraphRAG-lite

## Statistical Rule

Use paired per-query comparison.

Report:

- mean delta
- 95% bootstrap confidence interval
- query-type breakdown
- latency delta
- cost delta

Do not claim improvement when:

- confidence interval crosses zero
- latency or cost increases without explicit tradeoff
- result only improves synthetic dev data
