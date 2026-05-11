from __future__ import annotations

import argparse
from pathlib import Path

from app.domain.retrieval import (
    REQUIRED_QUERY_TYPES,
    RETRIEVAL_EVAL_TARGET_DEV_PER_QUERY_TYPE,
    RETRIEVAL_EVAL_TARGET_TEST_PER_QUERY_TYPE,
    RetrievalEvalDatasetSummary,
    RetrievalEvalExpansionSummary,
    RetrievalEvalItem,
    RetrievalEvalTargetResolvabilitySummary,
    build_retrieval_target_inventory,
    collect_retrieval_eval_dataset_failures,
    collect_retrieval_eval_expansion_readiness_failures,
    collect_retrieval_eval_review_readiness_failures,
    collect_retrieval_eval_target_resolvability_failures,
    load_retrieval_eval_jsonl,
    summarize_retrieval_eval_dataset,
    summarize_retrieval_eval_expansion,
    summarize_retrieval_eval_target_resolvability,
)
from pipelines.build_retrieval_eval_target_report import (
    PRIVATE_CHUNKS_PATH_ALIAS,
    load_child_chunks_from_report,
)


DEFAULT_CHUNKS_PATH = Path("private_data") / "reports" / "parent_child_chunks.json"
DEFAULT_DEV_DATASET_PATH = (
    Path("private_data") / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
)
DEFAULT_TEST_DATASET_PATH = (
    Path("private_data") / "evals" / "datasets" / "retrieval_eval_test.jsonl"
)
DEFAULT_REPORT_PATH = Path(
    "evals/reports/retrieval_eval_private_benchmark_readiness_report.md"
)
RETRIEVAL_EVAL_PRIVATE_BENCHMARK_REPORT_VERSION = (
    "retrieval-eval-private-benchmark-readiness/v1"
)
PRIVATE_DEV_TARGET_QUERY_COUNT = (
    len(REQUIRED_QUERY_TYPES) * RETRIEVAL_EVAL_TARGET_DEV_PER_QUERY_TYPE
)
PRIVATE_TEST_TARGET_QUERY_COUNT = (
    len(REQUIRED_QUERY_TYPES) * RETRIEVAL_EVAL_TARGET_TEST_PER_QUERY_TYPE
)
PRIVATE_BENCHMARK_TARGET_QUERY_COUNT = (
    PRIVATE_DEV_TARGET_QUERY_COUNT + PRIVATE_TEST_TARGET_QUERY_COUNT
)
PRIVATE_BENCHMARK_ANSWERABLE_QUERY_COUNT = 90
PRIVATE_BENCHMARK_NO_ANSWER_QUERY_COUNT = 15


def build_retrieval_eval_private_benchmark_report(
    *,
    dev_dataset_path: Path = DEFAULT_DEV_DATASET_PATH,
    test_dataset_path: Path = DEFAULT_TEST_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> RetrievalEvalExpansionSummary:
    items = _load_benchmark_items(
        dev_dataset_path=dev_dataset_path,
        test_dataset_path=test_dataset_path,
    )
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    children = load_child_chunks_from_report(chunks_path)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(children),
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_retrieval_eval_private_benchmark_report_markdown(
            items=items,
            dataset_summary=dataset_summary,
            expansion_summary=expansion_summary,
            target_summary=target_summary,
            dev_dataset_path=dev_dataset_path,
            test_dataset_path=test_dataset_path,
            chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
        ),
        encoding="utf-8",
    )
    return expansion_summary


def build_retrieval_eval_private_benchmark_report_markdown(
    *,
    items: list[RetrievalEvalItem],
    dataset_summary: RetrievalEvalDatasetSummary,
    expansion_summary: RetrievalEvalExpansionSummary,
    target_summary: RetrievalEvalTargetResolvabilitySummary,
    dev_dataset_path: Path,
    test_dataset_path: Path,
    chunks_path_alias: str,
) -> str:
    contract_failures = collect_retrieval_eval_dataset_failures(dataset_summary)
    expansion_failures = collect_retrieval_eval_expansion_readiness_failures(
        expansion_summary
    )
    review_failures = collect_retrieval_eval_review_readiness_failures(
        expansion_summary
    )
    target_failures = collect_retrieval_eval_target_resolvability_failures(
        target_summary
    )
    safety_failures = _public_safety_failures(
        expansion_summary=expansion_summary,
        target_summary=target_summary,
    )
    rubric_failures = _rubric_failures(items)
    gate_failures = _unique_failures(
        contract_failures
        + expansion_failures
        + review_failures
        + target_failures
        + safety_failures
        + rubric_failures
    )
    query_type_rows = "\n".join(
        _query_type_benchmark_row(items, expansion_summary, query_type)
        for query_type in REQUIRED_QUERY_TYPES
    )
    answerable_without_child_target_count = _answerable_without_child_target_count(items)
    requires_context_without_user_context_count = (
        _requires_context_without_user_context_count(items)
    )
    voice_followup_query_count = sum(
        1 for item in items if item.query.query_type == "voice_followup"
    )
    return f"""# Retrieval Eval Private Benchmark Readiness Report

## 목적

private dev 70개와 private test 35개가 같은 retrieval ablation benchmark로 사용할 준비가 되었는지 검수한다.

이 리포트는 성능 개선 결과가 아니다. dev/test split, review status, target resolvability, public-safety gate를 통과했는지 확인하는 benchmark readiness report다.

full dev/test benchmark는 public repository에 직접 저장하지 않는다. public에는 seed/sample과 집계 report만 남기고, full benchmark path는 public report에서 alias로만 표기한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{RETRIEVAL_EVAL_PRIVATE_BENCHMARK_REPORT_VERSION}` |
| dev_dataset_path | `{_public_dataset_path_alias(dev_dataset_path)}` |
| test_dataset_path | `{_public_dataset_path_alias(test_dataset_path)}` |
| chunks_path_alias | `{chunks_path_alias}` |
| dataset_version | `{expansion_summary.dataset_version}` |
| benchmark_readiness_status | `{"PASS" if not gate_failures else "FAIL"}` |
| expansion_readiness_status | `{"PASS" if not expansion_failures else "FAIL"}` |
| review_readiness_status | `{"PASS" if not review_failures else "FAIL"}` |
| target_resolvability_status | `{"PASS" if not target_failures else "FAIL"}` |
| public_safety_status | `{"PASS" if not safety_failures else "FAIL"}` |

## Benchmark Contract

검수 단위는 `RetrievalEvalItem` 1개다.

통과 기준:

1. 전체 query 수는 {PRIVATE_BENCHMARK_TARGET_QUERY_COUNT}개다.
2. query type별 dev {RETRIEVAL_EVAL_TARGET_DEV_PER_QUERY_TYPE}개, test {RETRIEVAL_EVAL_TARGET_TEST_PER_QUERY_TYPE}개다.
3. dev split은 {PRIVATE_DEV_TARGET_QUERY_COUNT}개이고 모두 `review_status=reviewed`다.
4. test split은 {PRIVATE_TEST_TARGET_QUERY_COUNT}개이고 모두 `review_status=locked`다.
5. answerable query는 {PRIVATE_BENCHMARK_ANSWERABLE_QUERY_COUNT}개, `no_answer` query는 {PRIVATE_BENCHMARK_NO_ANSWER_QUERY_COUNT}개다.
6. answerable query는 child target을 가진다.
7. 모든 child/parent/doc target은 검색 가능한 corpus에 존재한다.
8. public-safe field에 원문 직접 인용, private path, secret-like 값이 없다.

## 정량 리포트

| metric | value |
| --- | ---: |
| target_query_count | {expansion_summary.target_query_count} |
| current_query_count | {expansion_summary.current_query_count} |
| overall_shortfall_count | {expansion_summary.overall_shortfall_count} |
| dev_query_count | {expansion_summary.dev_query_count} |
| test_query_count | {expansion_summary.test_query_count} |
| dev_test_current_query_count | {expansion_summary.dev_test_current_query_count} |
| dev_test_shortfall_count | {expansion_summary.dev_test_shortfall_count} |
| answerable_query_count | {target_summary.answerable_query_count} |
| no_answer_query_count | {target_summary.no_answer_query_count} |
| draft_query_count | {expansion_summary.draft_query_count} |
| reviewed_query_count | {expansion_summary.reviewed_query_count} |
| locked_query_count | {expansion_summary.locked_query_count} |
| voice_followup_query_count | {voice_followup_query_count} |
| voice_followup_context_missing_count | {dataset_summary.voice_followup_context_missing_count} |
| requires_context_without_user_context_count | {requires_context_without_user_context_count} |
| answerable_without_child_target_count | {answerable_without_child_target_count} |
| answerable_without_child_or_parent_target_count | {target_summary.answerable_without_child_or_parent_target_count} |
| no_answer_with_positive_target_count | {target_summary.no_answer_with_positive_target_count} |
| judgment_target_count | {target_summary.judgment_target_count} |
| child_target_count | {target_summary.child_target_count} |
| parent_target_count | {target_summary.parent_target_count} |
| doc_target_count | {target_summary.doc_target_count} |
| missing_child_target_count | {target_summary.missing_child_target_count} |
| missing_parent_target_count | {target_summary.missing_parent_target_count} |
| missing_doc_target_count | {target_summary.missing_doc_target_count} |
| public_raw_text_leakage_count | {_public_safety_count(expansion_summary.public_raw_text_leakage_count, target_summary.public_raw_text_leakage_count)} |
| private_path_leakage_count | {_public_safety_count(expansion_summary.private_path_leakage_count, target_summary.private_path_leakage_count)} |
| secret_like_leakage_count | {_public_safety_count(expansion_summary.secret_like_leakage_count, target_summary.secret_like_leakage_count)} |

## Query Type Benchmark Matrix

| query_type | dev | test | draft | reviewed | locked | target_dev | target_test | dev_shortfall | test_shortfall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

## Gate Result

```text
contract_failures={contract_failures}
expansion_readiness_failures={expansion_failures}
review_readiness_failures={review_failures}
target_resolvability_failures={target_failures}
public_safety_failures={safety_failures}
rubric_failures={rubric_failures}
gate_failures={gate_failures}
```

## 정성 리포트

- private benchmark는 dev {expansion_summary.dev_query_count}개, test {expansion_summary.test_query_count}개로 구성된다.
- dev는 chunking/embedding/retriever tuning과 실패 분석에 사용한다.
- test는 최종 비교와 회귀 확인에만 사용하고, 실험 중간 의사결정에는 사용하지 않는다.
- {target_summary.answerable_query_count}개 answerable query는 child target을 포함한다. 이후 metric 계산은 child target을 우선한다.
- {target_summary.no_answer_query_count}개 `no_answer` query는 `expected_behavior=abstain`이며 positive judgment가 없다.
- target resolvability는 ID 존재를 검증한다. 역사적 정답성의 최종 보장은 이후 retrieval 실패 분석과 generation review에서 다시 확인해야 한다.

## 다음 단계

1. BM25 기준 chunking ablation runner를 구현한다.
2. dev split에서 chunking 후보를 비교하고, test split은 최종 확인 전까지 열지 않는다.
3. winner 선정 시 `Recall@1/3/5`, `MRR`, `nDCG@5`, `latency_p95`와 query type breakdown을 함께 기록한다.
"""


def main() -> int:
    args = _parse_args()
    items = _load_benchmark_items(
        dev_dataset_path=args.dev_dataset,
        test_dataset_path=args.test_dataset,
    )
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    children = load_child_chunks_from_report(args.chunks)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(children),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        build_retrieval_eval_private_benchmark_report_markdown(
            items=items,
            dataset_summary=dataset_summary,
            expansion_summary=expansion_summary,
            target_summary=target_summary,
            dev_dataset_path=args.dev_dataset,
            test_dataset_path=args.test_dataset,
            chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
        ),
        encoding="utf-8",
    )
    gate_failures = _unique_failures(
        collect_retrieval_eval_dataset_failures(dataset_summary)
        + collect_retrieval_eval_expansion_readiness_failures(expansion_summary)
        + collect_retrieval_eval_review_readiness_failures(expansion_summary)
        + collect_retrieval_eval_target_resolvability_failures(target_summary)
        + _public_safety_failures(
            expansion_summary=expansion_summary,
            target_summary=target_summary,
        )
        + _rubric_failures(items)
    )
    print(
        "retrieval_eval_private_benchmark "
        f"benchmark_readiness_status={'PASS' if not gate_failures else 'FAIL'} "
        f"query_count={dataset_summary.query_count} "
        f"dev_query_count={expansion_summary.dev_query_count} "
        f"test_query_count={expansion_summary.test_query_count} "
        f"gate_failures={len(gate_failures)}"
    )
    return 0 if not gate_failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build private retrieval eval benchmark readiness report."
    )
    parser.add_argument("--dev-dataset", type=Path, default=DEFAULT_DEV_DATASET_PATH)
    parser.add_argument("--test-dataset", type=Path, default=DEFAULT_TEST_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def _load_benchmark_items(
    *,
    dev_dataset_path: Path,
    test_dataset_path: Path,
) -> list[RetrievalEvalItem]:
    return load_retrieval_eval_jsonl(dev_dataset_path) + load_retrieval_eval_jsonl(
        test_dataset_path
    )


def _query_type_benchmark_row(
    items: list[RetrievalEvalItem],
    summary: RetrievalEvalExpansionSummary,
    query_type: str,
) -> str:
    row = summary.query_type_rows[query_type]
    review_counts = {
        status: sum(
            1
            for item in items
            if item.query.query_type == query_type and item.metadata.review_status == status
        )
        for status in ("draft", "reviewed", "locked")
    }
    return (
        f"| {query_type} | {row.dev_query_count} | {row.test_query_count} | "
        f"{review_counts['draft']} | {review_counts['reviewed']} | "
        f"{review_counts['locked']} | {row.target_dev_query_count} | "
        f"{row.target_test_query_count} | {row.dev_shortfall_count} | "
        f"{row.test_shortfall_count} |"
    )


def _rubric_failures(items: list[RetrievalEvalItem]) -> list[str]:
    failures: list[str] = []
    dev_items = [item for item in items if item.metadata.split == "dev"]
    test_items = [item for item in items if item.metadata.split == "test"]
    if len(items) != PRIVATE_BENCHMARK_TARGET_QUERY_COUNT:
        failures.append("private_benchmark_query_count_mismatch")
    if len(dev_items) != PRIVATE_DEV_TARGET_QUERY_COUNT:
        failures.append("private_benchmark_dev_query_count_mismatch")
    if len(test_items) != PRIVATE_TEST_TARGET_QUERY_COUNT:
        failures.append("private_benchmark_test_query_count_mismatch")
    if any(item.metadata.review_status != "reviewed" for item in dev_items):
        failures.append("private_benchmark_dev_status_not_reviewed")
    if any(item.metadata.review_status != "locked" for item in test_items):
        failures.append("private_benchmark_test_status_not_locked")
    if any(
        _query_type_split_count(items, query_type, "dev")
        != RETRIEVAL_EVAL_TARGET_DEV_PER_QUERY_TYPE
        for query_type in REQUIRED_QUERY_TYPES
    ):
        failures.append("private_benchmark_dev_query_type_count_mismatch")
    if any(
        _query_type_split_count(items, query_type, "test")
        != RETRIEVAL_EVAL_TARGET_TEST_PER_QUERY_TYPE
        for query_type in REQUIRED_QUERY_TYPES
    ):
        failures.append("private_benchmark_test_query_type_count_mismatch")
    if _answerable_query_count(items) != PRIVATE_BENCHMARK_ANSWERABLE_QUERY_COUNT:
        failures.append("private_benchmark_answerability_distribution_mismatch")
    if _no_answer_query_count(items) != PRIVATE_BENCHMARK_NO_ANSWER_QUERY_COUNT:
        failures.append("private_benchmark_answerability_distribution_mismatch")
    if _requires_context_without_user_context_count(items):
        failures.append("requires_context_without_user_context")
    if _answerable_without_child_target_count(items):
        failures.append("answerable_without_child_target")
    return _unique_failures(failures)


def _query_type_split_count(
    items: list[RetrievalEvalItem],
    query_type: str,
    split: str,
) -> int:
    return sum(
        1
        for item in items
        if item.query.query_type == query_type and item.metadata.split == split
    )


def _answerable_query_count(items: list[RetrievalEvalItem]) -> int:
    return sum(1 for item in items if item.query.expected_behavior == "retrieve")


def _no_answer_query_count(items: list[RetrievalEvalItem]) -> int:
    return sum(1 for item in items if item.query.expected_behavior == "abstain")


def _requires_context_without_user_context_count(
    items: list[RetrievalEvalItem],
) -> int:
    return sum(
        1
        for item in items
        if item.metadata.requires_context and not item.query.user_context
    )


def _answerable_without_child_target_count(items: list[RetrievalEvalItem]) -> int:
    return sum(
        1
        for item in items
        if item.query.expected_behavior == "retrieve"
        and not any(judgment.relevant_child_ids for judgment in item.judgments)
    )


def _public_safety_failures(
    *,
    expansion_summary: RetrievalEvalExpansionSummary,
    target_summary: RetrievalEvalTargetResolvabilitySummary,
) -> list[str]:
    failures: list[str] = []
    if (
        expansion_summary.public_raw_text_leakage_count
        or target_summary.public_raw_text_leakage_count
    ):
        failures.append("public_raw_text_leakage")
    if (
        expansion_summary.private_path_leakage_count
        or target_summary.private_path_leakage_count
    ):
        failures.append("private_path_leakage")
    if (
        expansion_summary.secret_like_leakage_count
        or target_summary.secret_like_leakage_count
    ):
        failures.append("secret_like_leakage")
    return failures


def _public_safety_count(expansion_count: int, target_count: int) -> int:
    return max(expansion_count, target_count)


def _unique_failures(failures: list[str]) -> list[str]:
    return list(dict.fromkeys(failures))


def _public_dataset_path_alias(dataset_path: Path) -> str:
    if _is_private_benchmark_dataset_path(dataset_path):
        return f"<private retrieval eval dataset: {dataset_path.name}>"
    if dataset_path.is_absolute():
        try:
            relative_path = dataset_path.relative_to(Path.cwd())
        except ValueError:
            return f"<public retrieval eval dataset: {dataset_path.name}>"
        if _is_private_benchmark_dataset_path(relative_path):
            return f"<private retrieval eval dataset: {dataset_path.name}>"
        return relative_path.as_posix()
    if ".." in dataset_path.parts:
        return f"<public retrieval eval dataset: {dataset_path.name}>"
    return dataset_path.as_posix()


def _is_private_benchmark_dataset_path(dataset_path: Path) -> bool:
    normalized_parts = tuple(part.lower() for part in dataset_path.parts)
    return (
        "private_data" in normalized_parts
        or dataset_path.name.startswith("retrieval_eval_dev")
        or dataset_path.name.startswith("retrieval_eval_test")
    )


if __name__ == "__main__":
    raise SystemExit(main())
