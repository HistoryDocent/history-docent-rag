# Project Redesign

## Final Product Identity

History Docent RAG is an evidence-centric backend for Korean history question answering.

The portfolio claim is narrow:

> I rebuilt a Korean history PDF RAG pipeline around parser quality, citation provenance, retrieval evaluation, and grounded answer generation.

The project should not be positioned as a finished consumer chatbot until the RAG backend is validated.

## Design Principles

1. Evidence before answer.
2. Parser quality is part of RAG quality.
3. Every answer must trace back to document, page, section, and chunk.
4. Retrieval and generation metrics must be separated.
5. New RAG techniques must beat the baseline by query type, not by narrative.
6. Public repo must not leak copyrighted source text.

## Core Pipeline

```text
source documents
-> parser outputs
-> canonical elements
-> quality flags
-> parent/child chunks
-> retrieval indexes
-> query rewrite
-> retrieval router
-> evidence packer
-> answer generator
-> citations and eval logs
```

## Module Plan

### 1. Parser Normalization

Input:

- original PDF metadata
- Upstage Parser JSON outputs

Output:

- `normalized_blocks.jsonl`
- `data_manifest.json`
- `parser_quality_report.md`

Required fields:

- `doc_id`
- `doc_title`
- `parser_run_id`
- `page_global`
- `page_in_batch`
- `batch_file`
- `element_id`
- `element_type`
- `bbox`
- `raw_text`
- `normalized_text`
- `quality_flags`

### 2. Chunking

Default chunking:

- child chunk: paragraph-level search unit
- parent chunk: section-level context unit

Required metadata:

- `chunk_id`
- `parent_chunk_id`
- `doc_id`
- `page_start`
- `page_end`
- `section_path`
- `element_ids`
- `quality_flags`

### 3. Retrieval

Baseline:

- BM25

Main candidate:

- hybrid retrieval: BM25 + dense retrieval
- query rewrite
- parent context expansion
- citation backtracking

Experimental candidates:

- RAPTOR-lite for overview questions
- GraphRAG-lite for relationship questions

### 4. Generation

Provider:

- Upstage Solar Pro 3 through a provider abstraction

Answer contract:

- `answer`
- `citations`
- `unsupported_claims`
- `retrieval_trace`
- `latency_ms`
- `estimated_cost`

### 5. API

Initial endpoints:

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `POST /api/v1/chat`

Non-negotiable requirements:

- schema validation
- timeout
- retry for provider 429/5xx only
- rate limit
- no stack trace exposure
- structured logs

## RAG Technique Decision

Default:

```text
Hybrid + Query Rewrite + Parent-Child + Citation RAG
```

Reason:

- Korean history questions often contain exact names, dates, dynasties, and events.
- BM25 is strong for exact historical terms.
- dense retrieval helps abstract and paraphrased questions.
- parent-child chunking restores context without overloading the prompt.
- citation RAG makes the answer auditable.

RAPTOR-lite:

- useful for overview and flow questions
- used as experiment, not default
- summaries are navigation nodes, not final evidence

GraphRAG-lite:

- useful for person/event/institution relationship questions
- used as experiment, not default
- graph triples are retrieval hints, not final evidence

## Explicit Non-Goals

- no public release of full copyrighted source text
- no large frontend before backend validation
- no voice UI before query rewrite and answer style control
- no GraphRAG-first architecture
- no vague metric claims without confidence intervals
