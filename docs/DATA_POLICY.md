# Data Policy

## Public Repository Rule

This repository is public. It must not contain copyrighted source material at scale.

## Forbidden

- original PDFs
- full parser JSON outputs
- full OCR text
- full generated chunks
- vector database files
- full raw evaluation CSV or JSONL containing source text
- API keys
- local `.env` files

## Allowed

- code
- schemas
- configs
- aggregate metrics
- small redacted samples
- documentation
- manually written evaluation examples without large copied passages

## Sample Data Rule

Samples must be small enough to demonstrate schema and behavior only.

Recommended limits:

- parser sample: 1 to 2 pages
- chunk sample: 5 to 10 chunks
- evaluation sample: 10 to 20 examples

## Commit Check

Before every push:

```bash
git status
git diff --cached --stat
git diff --cached
```

Reject commits containing:

- secrets
- source PDFs
- bulk parser output
- bulk OCR text
- vector DB artifacts
