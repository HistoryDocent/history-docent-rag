# History Docent RAG

Evidence-centric Korean history RAG backend built from Upstage Parser outputs.

## Project Positioning

This repository is not a general chatbot demo.

It is a portfolio-grade RAG backend project focused on:

- normalizing long-form Korean history PDF parser outputs
- preserving document structure and citation provenance
- comparing retrieval strategies with fixed evaluation sets
- generating grounded answers with source evidence
- measuring whether improvements are statistically meaningful

## Initial Scope

Included:

- Upstage Parser output normalization
- structure-preserving parent/child chunking
- BM25 baseline retrieval
- dense and hybrid retrieval experiments
- query rewrite for short or ambiguous voice-style questions
- citation-based RAG answer generation with Solar Pro 3
- retrieval and generation evaluation harness
- failure analysis and ablation reports

Excluded from the first public version:

- original PDFs
- full parser JSON
- full chunk text
- full vector database
- full raw evaluation CSV
- frontend service
- voice UI
- GraphRAG as the default pipeline
- full RAPTOR as the default pipeline

## Recommended Baseline Pipeline

```text
PDFs
-> Upstage Parser outputs
-> canonical element schema
-> parser quality checks
-> parent/child chunks
-> BM25 + vector indexes
-> query rewrite
-> hybrid retrieval
-> parent context expansion
-> evidence packing
-> Solar Pro 3 generation
-> answer with citations
-> evaluation logging
```

## RAG Strategy

The default production candidate is:

```text
Hybrid Retrieval + Query Rewrite + Parent-Child Chunking + Citation RAG
```

RAPTOR-lite and GraphRAG-lite are evaluation candidates, not the initial default.

## Repository Safety Policy

This public repository must not contain copyrighted source text at scale.

Allowed:

- code
- configs
- aggregate metrics
- small anonymized samples
- documentation

Forbidden:

- original books or PDFs
- complete parser outputs
- complete OCR text
- complete chunk files
- complete vector indexes
- secrets or API keys

## Current Status

Project initialized. Implementation starts from parser normalization and provenance recovery.
