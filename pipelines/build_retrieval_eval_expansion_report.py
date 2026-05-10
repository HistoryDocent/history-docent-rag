from __future__ import annotations

import argparse
from pathlib import Path

from app.domain.retrieval import (
    REQUIRED_QUERY_TYPES,
    RetrievalEvalDatasetSummary,
    RetrievalEvalExpansionSummary,
    RetrievalEvalTargetResolvabilitySummary,
    build_retrieval_target_inventory,
    collect_retrieval_eval_dataset_failures,
    collect_retrieval_eval_expansion_readiness_failures,
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
DEFAULT_DATASET_PATH = Path("evals/datasets/retrieval_eval_seed.jsonl")
DEFAULT_REPORT_PATH = Path("evals/reports/retrieval_eval_expansion_report.md")
RETRIEVAL_EVAL_EXPANSION_REPORT_VERSION = "retrieval-eval-expansion/v1"


def build_retrieval_eval_expansion_report(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> RetrievalEvalExpansionSummary:
    dataset_summary, expansion_summary, target_summary = _summarize_report_inputs(
        dataset_path=dataset_path,
        chunks_path=chunks_path,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_retrieval_eval_expansion_report_markdown(
            dataset_summary=dataset_summary,
            expansion_summary=expansion_summary,
            target_summary=target_summary,
            dataset_path=dataset_path,
            chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
        ),
        encoding="utf-8",
    )
    return expansion_summary


def build_retrieval_eval_expansion_report_markdown(
    *,
    dataset_summary: RetrievalEvalDatasetSummary,
    expansion_summary: RetrievalEvalExpansionSummary,
    target_summary: RetrievalEvalTargetResolvabilitySummary,
    dataset_path: Path,
    chunks_path_alias: str,
) -> str:
    contract_failures = collect_retrieval_eval_dataset_failures(dataset_summary)
    expansion_failures = collect_retrieval_eval_expansion_readiness_failures(
        expansion_summary
    )
    target_failures = collect_retrieval_eval_target_resolvability_failures(
        target_summary
    )
    blocking_failures = _unique_failures(
        contract_failures
        + target_failures
        + _public_safety_failures(
            expansion_summary=expansion_summary,
            target_summary=target_summary,
        )
    )
    row_text = "\n".join(
        _query_type_row_markdown(expansion_summary, query_type)
        for query_type in REQUIRED_QUERY_TYPES
    )
    authoring_status = "PASS" if not blocking_failures else "FAIL"
    expansion_status = "PASS" if not expansion_failures else "INCOMPLETE"
    return f"""# Retrieval Eval Expansion Report

## 목적

retrieval 평가셋을 seed smoke test에서 dev/test 비교 평가셋으로 확장하기 위한 작업 현황을 고정한다.

이 리포트는 성능 개선 결과가 아니다. 청킹, Dense, Hybrid, Reranker 비교 전에 질문 수량, split, review status, target resolvability, 공개 안전성을 확인하는 정량/정성 보고서다.

full dev/test benchmark는 public repository에 직접 저장하지 않는다. public에는 seed/sample과 집계 report만 남기고, full benchmark path는 public report에서 alias로만 표기한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{RETRIEVAL_EVAL_EXPANSION_REPORT_VERSION}` |
| dataset_path | `{_public_dataset_path_alias(dataset_path)}` |
| chunks_path_alias | `{chunks_path_alias}` |
| dataset_version | `{expansion_summary.dataset_version}` |
| authoring_status | `{authoring_status}` |
| expansion_readiness_status | `{expansion_status}` |
| target_resolvability_status | `{"PASS" if not target_failures else "FAIL"}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| target_query_count | {expansion_summary.target_query_count} |
| current_query_count | {expansion_summary.current_query_count} |
| overall_shortfall_count | {expansion_summary.overall_shortfall_count} |
| seed_query_count | {expansion_summary.seed_query_count} |
| dev_query_count | {expansion_summary.dev_query_count} |
| test_query_count | {expansion_summary.test_query_count} |
| dev_test_target_query_count | {expansion_summary.dev_test_target_query_count} |
| dev_test_current_query_count | {expansion_summary.dev_test_current_query_count} |
| dev_test_shortfall_count | {expansion_summary.dev_test_shortfall_count} |
| draft_query_count | {expansion_summary.draft_query_count} |
| reviewed_query_count | {expansion_summary.reviewed_query_count} |
| locked_query_count | {expansion_summary.locked_query_count} |
| public_raw_text_leakage_count | {_public_safety_count(expansion_summary.public_raw_text_leakage_count, target_summary.public_raw_text_leakage_count)} |
| private_path_leakage_count | {_public_safety_count(expansion_summary.private_path_leakage_count, target_summary.private_path_leakage_count)} |
| secret_like_leakage_count | {_public_safety_count(expansion_summary.secret_like_leakage_count, target_summary.secret_like_leakage_count)} |

## Query Type Expansion Matrix

| query_type | seed | dev | test | target_dev | target_test | dev_shortfall | test_shortfall | total_current | target_total | total_shortfall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{row_text}

## Target Resolvability Snapshot

| metric | value |
| --- | ---: |
| searchable_child_count | {target_summary.searchable_child_count} |
| searchable_parent_count | {target_summary.searchable_parent_count} |
| searchable_doc_count | {target_summary.searchable_doc_count} |
| judgment_target_count | {target_summary.judgment_target_count} |
| missing_child_target_count | {target_summary.missing_child_target_count} |
| missing_parent_target_count | {target_summary.missing_parent_target_count} |
| missing_doc_target_count | {target_summary.missing_doc_target_count} |
| answerable_without_child_or_parent_target_count | {target_summary.answerable_without_child_or_parent_target_count} |
| no_answer_with_positive_target_count | {target_summary.no_answer_with_positive_target_count} |

## Gate Result

```text
contract_failures={contract_failures}
expansion_readiness_failures={expansion_failures}
target_resolvability_failures={target_failures}
blocking_failures={blocking_failures}
```

## 정성 리포트

- 현재 평가셋은 query type별 seed 2개씩 총 14개다.
- 목표는 query type별 dev 10개, test 5개로 총 105개다.
- 현재 전체 부족분은 91개지만, dev/test split 기준 부족분은 105개다. seed는 smoke test로 유지하고 최종 비교 튜닝에는 사용하지 않는다.
- 다음 작성 우선순위는 `voice_followup`, `relationship`, `route_context`, `no_answer`다. 이 네 유형이 실제 도슨트 서비스 실패를 가장 많이 드러낸다.
- test split은 최종 ablation 확인 전까지 튜닝에 사용하지 않는다.
- public dataset에는 원문 answer, chunk text, OCR text, parser text, private path, secret-like 값을 넣지 않는다.
- public evaluation example은 원문 인용 없이 직접 작성한 paraphrase만 허용한다.
- gold judgment는 가능한 한 `relevant_child_ids`를 우선하고, child 판단이 어려울 때만 parent/doc target을 보조로 둔다.

## 다음 단계

1. query type별 private dev 후보 10개를 먼저 draft로 작성한다.
2. target resolvability gate를 통과한 항목만 reviewed로 승격한다.
3. private test 후보 5개는 dev 튜닝 후 별도 locked 상태로 고정한다.
4. 이후 chunking ablation runner를 BM25 기준으로 실행한다.
"""


def main() -> int:
    args = _parse_args()
    dataset_summary, expansion_summary, target_summary = _summarize_report_inputs(
        dataset_path=args.dataset,
        chunks_path=args.chunks,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        build_retrieval_eval_expansion_report_markdown(
            dataset_summary=dataset_summary,
            expansion_summary=expansion_summary,
            target_summary=target_summary,
            dataset_path=args.dataset,
            chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
        ),
        encoding="utf-8",
    )
    contract_failures = collect_retrieval_eval_dataset_failures(dataset_summary)
    target_failures = collect_retrieval_eval_target_resolvability_failures(
        target_summary
    )
    safety_failures = _public_safety_failures(
        expansion_summary=expansion_summary,
        target_summary=target_summary,
    )
    blocking_failures = _unique_failures(
        contract_failures + target_failures + safety_failures
    )
    expansion_failures = collect_retrieval_eval_expansion_readiness_failures(
        expansion_summary
    )
    print(
        "retrieval_eval_expansion "
        f"authoring_status={'PASS' if not blocking_failures else 'FAIL'} "
        f"expansion_readiness_status={'PASS' if not expansion_failures else 'INCOMPLETE'} "
        f"target_query_count={expansion_summary.target_query_count} "
        f"current_query_count={expansion_summary.current_query_count} "
        f"overall_shortfall_count={expansion_summary.overall_shortfall_count} "
        f"dev_test_shortfall_count={expansion_summary.dev_test_shortfall_count} "
        f"blocking_failures={len(blocking_failures)}"
    )
    return 0 if not blocking_failures else 1


def _summarize_report_inputs(
    *,
    dataset_path: Path,
    chunks_path: Path,
) -> tuple[
    RetrievalEvalDatasetSummary,
    RetrievalEvalExpansionSummary,
    RetrievalEvalTargetResolvabilitySummary,
]:
    items = load_retrieval_eval_jsonl(dataset_path)
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    children = load_child_chunks_from_report(chunks_path)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(children),
    )
    return dataset_summary, expansion_summary, target_summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build retrieval eval expansion readiness report."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def _query_type_row_markdown(
    summary: RetrievalEvalExpansionSummary,
    query_type: str,
) -> str:
    row = summary.query_type_rows[query_type]
    return (
        f"| {query_type} | {row.seed_query_count} | {row.dev_query_count} | "
        f"{row.test_query_count} | {row.target_dev_query_count} | "
        f"{row.target_test_query_count} | {row.dev_shortfall_count} | "
        f"{row.test_shortfall_count} | {row.current_total_query_count} | "
        f"{row.target_total_query_count} | {row.total_shortfall_count} |"
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
