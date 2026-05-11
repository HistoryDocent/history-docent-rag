from __future__ import annotations

import argparse
from pathlib import Path

from app.domain.retrieval import (
    REQUIRED_QUERY_TYPES,
    RetrievalEvalDatasetSummary,
    RetrievalEvalExpansionSummary,
    RetrievalEvalItem,
    RetrievalEvalTargetResolvabilitySummary,
    build_retrieval_target_inventory,
    collect_retrieval_eval_dataset_failures,
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


DEFAULT_CHUNKS_PATH = Path("private_data/reports/parent_child_chunks.json")
DEFAULT_DATASET_PATH = Path("private_data/evals/datasets/retrieval_eval_dev.jsonl")
DEFAULT_REPORT_PATH = Path("evals/reports/retrieval_eval_private_dev_review_report.md")
RETRIEVAL_EVAL_REVIEW_REPORT_VERSION = "retrieval-eval-review/v1"
PRIVATE_DEV_FIRST_REVIEW_TARGET_PER_QUERY_TYPE = 5
PRIVATE_DEV_FIRST_REVIEW_TARGET_QUERY_COUNT = (
    len(REQUIRED_QUERY_TYPES) * PRIVATE_DEV_FIRST_REVIEW_TARGET_PER_QUERY_TYPE
)


def build_retrieval_eval_review_report(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> RetrievalEvalExpansionSummary:
    items = load_retrieval_eval_jsonl(dataset_path)
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    children = load_child_chunks_from_report(chunks_path)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(children),
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_retrieval_eval_review_report_markdown(
            items=items,
            dataset_summary=dataset_summary,
            expansion_summary=expansion_summary,
            target_summary=target_summary,
            dataset_path=dataset_path,
            chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
        ),
        encoding="utf-8",
    )
    return expansion_summary


def build_retrieval_eval_review_report_markdown(
    *,
    items: list[RetrievalEvalItem],
    dataset_summary: RetrievalEvalDatasetSummary,
    expansion_summary: RetrievalEvalExpansionSummary,
    target_summary: RetrievalEvalTargetResolvabilitySummary,
    dataset_path: Path,
    chunks_path_alias: str,
) -> str:
    contract_failures = collect_retrieval_eval_dataset_failures(dataset_summary)
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
        + review_failures
        + target_failures
        + safety_failures
        + rubric_failures
    )
    query_type_rows = "\n".join(
        _query_type_review_row(items, expansion_summary, query_type)
        for query_type in REQUIRED_QUERY_TYPES
    )
    query_type_balance_text = _query_type_balance_text(items)
    answerable_without_child_target_count = _answerable_without_child_target_count(items)
    requires_context_without_user_context_count = (
        _requires_context_without_user_context_count(items)
    )
    voice_followup_query_count = sum(
        1 for item in items if item.query.query_type == "voice_followup"
    )
    return f"""# Retrieval Eval Private Dev Review Report

## 목적

private dev 1차 평가셋 35개를 retrieval ablation에 사용할 수 있는 `reviewed` 상태로 승격했는지 검수한다.

이 리포트는 성능 개선 결과가 아니다. 질문 의도, query type, answerability, context 필요성, target ID 매핑, 공개 안전성을 확인한 정량/정성 review gate다.

full dev/test benchmark는 public repository에 직접 저장하지 않는다. public에는 seed/sample과 집계 report만 남기고, full benchmark path는 public report에서 alias로만 표기한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{RETRIEVAL_EVAL_REVIEW_REPORT_VERSION}` |
| dataset_path | `{_public_dataset_path_alias(dataset_path)}` |
| chunks_path_alias | `{chunks_path_alias}` |
| dataset_version | `{expansion_summary.dataset_version}` |
| review_gate_status | `{"PASS" if not gate_failures else "FAIL"}` |
| target_resolvability_status | `{"PASS" if not target_failures else "FAIL"}` |
| public_safety_status | `{"PASS" if not safety_failures else "FAIL"}` |

## Review Rubric

검수 단위는 `RetrievalEvalItem` 1개다.

통과 기준:

1. `dataset_version`은 `retrieval-eval-dataset/v2`다.
2. `split=dev`이고 `review_status=reviewed`다.
3. query type은 7개 모두 포함하고, 이번 1차분은 query type별 dev {PRIVATE_DEV_FIRST_REVIEW_TARGET_PER_QUERY_TYPE}개다.
4. `voice_followup`은 `requires_context=true`와 `user_context`를 모두 가진다.
5. `no_answer`는 `expected_behavior=abstain`, `answerability=unanswerable`, positive judgment 없음이다.
6. answerable query는 positive judgment와 child target을 가진다.
7. 모든 child/parent/doc target은 검색 가능한 corpus에 존재한다.
8. public-safe field에 원문 직접 인용, private path, secret-like 값이 없다.

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {dataset_summary.query_count} |
| dev_query_count | {expansion_summary.dev_query_count} |
| test_query_count | {expansion_summary.test_query_count} |
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

## Query Type Review Matrix

| query_type | dev | draft | reviewed | locked | target_dev | remaining_dev_shortfall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

## Gate Result

```text
contract_failures={contract_failures}
review_readiness_failures={review_failures}
target_resolvability_failures={target_failures}
public_safety_failures={safety_failures}
rubric_failures={rubric_failures}
gate_failures={gate_failures}
```

## 정성 리포트

- 1차 private dev {dataset_summary.query_count}개는 {query_type_balance_text}.
- {target_summary.answerable_query_count}개 answerable query는 child target을 포함한다. 이후 metric 계산은 child target을 우선한다.
- {target_summary.no_answer_query_count}개 `no_answer` query는 `expected_behavior=abstain`이며 positive judgment가 없다.
- {voice_followup_query_count}개 `voice_followup` query는 `requires_context=true`와 `user_context`를 가진다.
- target resolvability는 ID 존재를 검증한다. 역사적 정답성의 최종 보장은 이후 retrieval 실패 분석과 generation review에서 다시 확인해야 한다.
- 자동 gate는 query wording이 실제 지시어형인지, `no_answer`가 실제 corpus 밖인지, rationale이 near-verbatim이 아닌지를 의미론적으로 증명하지 않는다. 이 항목은 review rubric의 수동 검수 범위로 남긴다.

## 한계

- 이번 리포트는 dev 1차 35개에 대한 review다. dev 목표 70개와 test 목표 35개는 아직 남아 있다.
- 단일 review pass이므로 최종 locked test 작성 전에는 추가 cross-check가 필요하다.
- 이 리포트는 retrieval/generation 성능 개선을 주장하지 않는다.
"""


def main() -> int:
    args = _parse_args()
    items = load_retrieval_eval_jsonl(args.dataset)
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    children = load_child_chunks_from_report(args.chunks)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(children),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        build_retrieval_eval_review_report_markdown(
            items=items,
            dataset_summary=dataset_summary,
            expansion_summary=expansion_summary,
            target_summary=target_summary,
            dataset_path=args.dataset,
            chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
        ),
        encoding="utf-8",
    )
    gate_failures = _unique_failures(
        collect_retrieval_eval_dataset_failures(dataset_summary)
        + collect_retrieval_eval_review_readiness_failures(expansion_summary)
        + collect_retrieval_eval_target_resolvability_failures(target_summary)
        + _public_safety_failures(
            expansion_summary=expansion_summary,
            target_summary=target_summary,
        )
        + _rubric_failures(items)
    )
    print(
        "retrieval_eval_review "
        f"review_gate_status={'PASS' if not gate_failures else 'FAIL'} "
        f"query_count={dataset_summary.query_count} "
        f"reviewed_query_count={expansion_summary.reviewed_query_count} "
        f"draft_query_count={expansion_summary.draft_query_count} "
        f"gate_failures={len(gate_failures)}"
    )
    return 0 if not gate_failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build private retrieval eval review report."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def _query_type_review_row(
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
        f"| {query_type} | {row.dev_query_count} | {review_counts['draft']} | "
        f"{review_counts['reviewed']} | {review_counts['locked']} | "
        f"{row.target_dev_query_count} | {row.dev_shortfall_count} |"
    )


def _rubric_failures(items: list[RetrievalEvalItem]) -> list[str]:
    failures: list[str] = []
    if len(items) != PRIVATE_DEV_FIRST_REVIEW_TARGET_QUERY_COUNT:
        failures.append("private_dev_first_review_query_count_mismatch")
    if any(
        _query_type_item_count(items, query_type)
        != PRIVATE_DEV_FIRST_REVIEW_TARGET_PER_QUERY_TYPE
        for query_type in REQUIRED_QUERY_TYPES
    ):
        failures.append("private_dev_first_review_query_type_count_mismatch")
    if any(item.metadata.split != "dev" for item in items):
        failures.append("non_dev_split")
    if any(item.metadata.review_status != "reviewed" for item in items):
        failures.append("dev_review_status_not_reviewed")
    if _requires_context_without_user_context_count(items):
        failures.append("requires_context_without_user_context")
    if _answerable_without_child_target_count(items):
        failures.append("answerable_without_child_target")
    return failures


def _query_type_item_count(items: list[RetrievalEvalItem], query_type: str) -> int:
    return sum(1 for item in items if item.query.query_type == query_type)


def _query_type_balance_text(items: list[RetrievalEvalItem]) -> str:
    counts = {
        query_type: _query_type_item_count(items, query_type)
        for query_type in REQUIRED_QUERY_TYPES
    }
    if all(
        count == PRIVATE_DEV_FIRST_REVIEW_TARGET_PER_QUERY_TYPE
        for count in counts.values()
    ):
        return (
            "query type별 dev "
            f"{PRIVATE_DEV_FIRST_REVIEW_TARGET_PER_QUERY_TYPE}개로 균형이 맞는다"
        )
    return f"query type별 dev 분포가 {counts}로 남아 있어 1차 review 기준을 충족하지 못한다"


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
