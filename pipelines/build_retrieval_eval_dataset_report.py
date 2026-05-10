from __future__ import annotations

import argparse
from pathlib import Path

from app.domain.retrieval import (
    REQUIRED_QUERY_TYPES,
    RETRIEVAL_EVAL_TARGET_DEV_PER_QUERY_TYPE,
    RETRIEVAL_EVAL_TARGET_TEST_PER_QUERY_TYPE,
    RetrievalEvalDatasetSummary,
    collect_retrieval_eval_dataset_failures,
    collect_retrieval_eval_split_readiness_failures,
    load_retrieval_eval_jsonl,
    summarize_retrieval_eval_dataset,
)


DEFAULT_DATASET_PATH = Path("evals/datasets/retrieval_eval_seed.jsonl")
DEFAULT_REPORT_PATH = Path("evals/reports/retrieval_eval_dataset_report.md")
RETRIEVAL_EVAL_DATASET_REPORT_VERSION = "retrieval-eval-dataset-report/v1"


def build_retrieval_eval_dataset_report(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> RetrievalEvalDatasetSummary:
    items = load_retrieval_eval_jsonl(dataset_path)
    summary = summarize_retrieval_eval_dataset(items)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_retrieval_eval_dataset_report_markdown(
            summary=summary,
            dataset_path=dataset_path,
        ),
        encoding="utf-8",
    )
    return summary


def build_retrieval_eval_dataset_report_markdown(
    *,
    summary: RetrievalEvalDatasetSummary,
    dataset_path: Path,
) -> str:
    contract_failures = collect_retrieval_eval_dataset_failures(summary)
    split_readiness_failures = collect_retrieval_eval_split_readiness_failures(summary)
    query_type_rows = "\n".join(
        f"| {query_type} | "
        f"{summary.query_type_by_split.get('seed', {}).get(query_type, 0)} | "
        f"{summary.query_type_by_split.get('dev', {}).get(query_type, 0)} | "
        f"{summary.query_type_by_split.get('test', {}).get(query_type, 0)} | "
        f"{RETRIEVAL_EVAL_TARGET_DEV_PER_QUERY_TYPE} | "
        f"{RETRIEVAL_EVAL_TARGET_TEST_PER_QUERY_TYPE} |"
        for query_type in REQUIRED_QUERY_TYPES
    )
    split_rows = "\n".join(
        f"| {split} | {count} |"
        for split, count in sorted(summary.split_distribution.items())
    )
    split_type_rows = "\n".join(
        f"| {split} | {query_type} | {count} |"
        for split, type_counts in sorted(summary.query_type_by_split.items())
        for query_type, count in sorted(type_counts.items())
    )
    return f"""# Retrieval Eval Dataset Report

## 목적

retrieval 평가셋 v2 contract와 split gate를 검증한다.

이 리포트는 성능 개선 결과가 아니다. Dense/Hybrid/Reranker 비교 전에 평가셋의 grain, split, judgment, 공개 정책을 고정하기 위한 정량/정성 보고서다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{RETRIEVAL_EVAL_DATASET_REPORT_VERSION}` |
| dataset_path | `{dataset_path.as_posix()}` |
| dataset_version | `{summary.dataset_version}` |
| contract_status | `{"PASS" if not contract_failures else "FAIL"}` |
| split_readiness_status | `{"PASS" if not split_readiness_failures else "FAIL"}` |

## v2 Contract

`RetrievalEvalItem`의 grain은 질문 1개다.

필수 metadata:

| field | 설명 |
| --- | --- |
| `split` | `seed`, `dev`, `test` 중 하나 |
| `difficulty` | `easy`, `medium`, `hard` 중 하나 |
| `place_ids` | public-safe place catalog id 목록 |
| `requires_context` | user_context 또는 대화 맥락 필요 여부 |
| `answerability` | `answerable` 또는 `unanswerable` |
| `review_status` | `draft`, `reviewed`, `locked` 중 하나 |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| judgment_count | {summary.judgment_count} |
| retrieve_query_count | {summary.retrieve_query_count} |
| abstain_query_count | {summary.abstain_query_count} |
| dataset_version_mismatch_count | {summary.dataset_version_mismatch_count} |
| query_type_min_shortfall_count | {summary.query_type_min_shortfall_count} |
| dev_query_count | {summary.dev_query_count} |
| test_query_count | {summary.test_query_count} |
| dev_target_shortfall_count | {summary.dev_target_shortfall_count} |
| test_target_shortfall_count | {summary.test_target_shortfall_count} |
| duplicate_query_id_count | {summary.duplicate_query_id_count} |
| missing_metadata_count | {summary.missing_metadata_count} |
| answerability_mismatch_count | {summary.answerability_mismatch_count} |
| voice_followup_context_missing_count | {summary.voice_followup_context_missing_count} |
| requires_context_count | {summary.requires_context_count} |
| place_id_count | {summary.place_id_count} |
| missing_required_query_type_count | {summary.missing_required_query_type_count} |
| missing_expected_target_count | {summary.missing_expected_target_count} |
| judgment_query_mismatch_count | {summary.judgment_query_mismatch_count} |
| public_raw_text_leakage_count | {summary.public_raw_text_leakage_count} |
| private_path_leakage_count | {summary.private_path_leakage_count} |

## Split Distribution

| split | query_count |
| --- | ---: |
{split_rows}

## Query Type Coverage

| query_type | current_seed | current_dev | current_test | target_dev | target_test |
| --- | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

## Query Type by Split

| split | query_type | query_count |
| --- | --- | ---: |
{split_type_rows}

## Metadata Distribution

| field | distribution |
| --- | --- |
| difficulty | `{summary.difficulty_distribution}` |
| answerability | `{summary.answerability_distribution}` |
| review_status | `{summary.review_status_distribution}` |

## Gate Result

```text
contract_failures={contract_failures}
split_readiness_failures={split_readiness_failures}
```

## 정성 리포트

- 현재 `seed` split은 smoke test다. 최종 성능 주장에는 사용하지 않는다.
- dev/test split readiness는 아직 FAIL이다. 이 리포트의 PASS/FAIL은 contract와 readiness를 분리해 해석한다.
- v2 metadata는 dev/test 확장 전에 query grain과 judgment 정책을 고정하기 위한 장치다.
- `voice_followup`은 `requires_context=true`를 강제해 대화 맥락 없는 검색과 구분한다.
- `no_answer`는 `answerability=unanswerable`과 positive judgment 없음으로 환각 방지 평가에 사용한다.
- public dataset에는 원문 answer, chunk text, OCR text, parser text, private path를 포함하지 않는다.

## 다음 단계

1. query type별 dev 10개, test 5개 목표를 채운다.
2. test split은 최종 ablation 전까지 튜닝에 사용하지 않는다.
3. Dense/Hybrid 비교는 이 v2 contract가 유지된 상태에서만 진행한다.
"""


def main() -> int:
    args = _parse_args()
    summary = build_retrieval_eval_dataset_report(
        dataset_path=args.dataset,
        report_path=args.report,
    )
    contract_failures = collect_retrieval_eval_dataset_failures(summary)
    split_readiness_failures = collect_retrieval_eval_split_readiness_failures(summary)
    print(
        "retrieval_eval_dataset "
        f"contract_status={'PASS' if not contract_failures else 'FAIL'} "
        f"split_readiness_status={'PASS' if not split_readiness_failures else 'FAIL'} "
        f"query_count={summary.query_count} "
        f"splits={','.join(sorted(summary.split_distribution))} "
        f"contract_failures={len(contract_failures)} "
        f"split_readiness_failures={len(split_readiness_failures)}"
    )
    return 0 if not contract_failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build retrieval eval dataset contract report."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
