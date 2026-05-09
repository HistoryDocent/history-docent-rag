# Roadmap

## Phase 0. Repository Foundation

- create public repository
- add safety-focused `.gitignore`
- define project scope
- define data policy
- define evaluation plan

## Phase 1. Parser Normalization

- load Upstage Parser outputs from private local path
- reconstruct global page numbers
- preserve element-level metadata
- generate parser quality report

## Phase 2. Structure-Preserving Chunking

- create parent and child chunks
- preserve section path and page provenance
- filter OCR noise and invalid summary artifacts
- export public sample chunks

## Phase 3. Retrieval Baselines

- implement BM25 baseline
- implement dense retrieval
- implement hybrid retrieval
- record Recall@k, MRR, nDCG, latency

## Phase 4. Citation RAG

- implement evidence packing
- implement Solar Pro 3 provider
- generate answer with citations
- detect unsupported claims

## Phase 5. API

- implement FastAPI chat endpoint
- add readiness health check
- add validation, rate limit, retry, timeout, and structured logs

## Phase 6. Evaluation Harness

- create dev, holdout, external, and stress eval sets
- implement retrieval and generation graders
- report confidence intervals
- create ablation report

## Phase 7. Advanced Retrieval Experiments

- add RAPTOR-lite for overview questions
- add GraphRAG-lite for relationship questions
- add query-type router only if metrics justify it

## Phase 8. Voice Demo

- add STT/TTS demo after backend validation
- preserve short-answer and citation display behavior
- keep voice UI separate from the RAG backend if it grows large
