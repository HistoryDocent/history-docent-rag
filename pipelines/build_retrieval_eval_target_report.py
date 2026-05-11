from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.domain.chunking import ChildChunk
from app.domain.retrieval import (
    RetrievalEvalTargetResolvabilitySummary,
    build_retrieval_target_inventory,
    collect_retrieval_eval_target_resolvability_failures,
    load_retrieval_eval_jsonl,
    summarize_retrieval_eval_target_resolvability,
)


DEFAULT_CHUNKS_PATH = Path("private_data") / "reports" / "parent_child_chunks.json"
DEFAULT_DATASET_PATH = Path("evals/datasets/retrieval_eval_seed.jsonl")
DEFAULT_REPORT_PATH = Path("evals/reports/retrieval_eval_target_resolvability_report.md")
RETRIEVAL_EVAL_TARGET_REPORT_VERSION = "retrieval-eval-target-resolvability/v1"
PRIVATE_CHUNKS_PATH_ALIAS = "<private parent_child_chunks report>"


def build_retrieval_eval_target_report(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> RetrievalEvalTargetResolvabilitySummary:
    items = load_retrieval_eval_jsonl(dataset_path)
    children = load_child_chunks_from_report(chunks_path)
    inventory = build_retrieval_target_inventory(children)
    summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=inventory,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_retrieval_eval_target_report_markdown(
            summary=summary,
            dataset_path=dataset_path,
            chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
        ),
        encoding="utf-8",
    )
    return summary


def load_child_chunks_from_report(chunks_path: Path) -> list[ChildChunk]:
    payload = json.loads(chunks_path.read_text(encoding="utf-8"))
    children_payload = payload.get("children")
    if not isinstance(children_payload, list):
        raise ValueError("parent_child_chunks payload must include children list")
    return [ChildChunk.model_validate(child_payload) for child_payload in children_payload]


def build_retrieval_eval_target_report_markdown(
    *,
    summary: RetrievalEvalTargetResolvabilitySummary,
    dataset_path: Path,
    chunks_path_alias: str,
) -> str:
    failures = collect_retrieval_eval_target_resolvability_failures(summary)
    next_steps = _target_report_next_steps(summary=summary, dataset_path=dataset_path)
    return f"""# Retrieval Eval Target Resolvability Report

## 목적

retrieval 평가셋의 judgment target이 실제 검색 corpus에 존재하는지 검증한다.

이 리포트는 성능 개선 결과가 아니다. dev/test 평가셋 확장과 retrieval ablation 전에 정답 target의 corpus 매핑 가능성을 고정하기 위한 정량/정성 보고서다.

full dev/test benchmark는 public repository에 직접 저장하지 않는다. public에는 seed/sample과 집계 report만 남기고, full benchmark path는 public report에서 alias로만 표기한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{RETRIEVAL_EVAL_TARGET_REPORT_VERSION}` |
| dataset_path | `{_public_dataset_path_alias(dataset_path)}` |
| chunks_path_alias | `{chunks_path_alias}` |
| target_resolvability_status | `{"PASS" if not failures else "FAIL"}` |

## Grain

`RetrievalEvalItem`의 grain은 질문 1개다.

target resolvability의 검증 grain은 judgment target 1개다.

검증 대상:

- `relevant_child_ids`
- `relevant_parent_ids`
- `relevant_doc_ids`

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| judgment_count | {summary.judgment_count} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| searchable_child_count | {summary.searchable_child_count} |
| searchable_parent_count | {summary.searchable_parent_count} |
| searchable_doc_count | {summary.searchable_doc_count} |
| judgment_target_count | {summary.judgment_target_count} |
| child_target_count | {summary.child_target_count} |
| resolved_child_target_count | {summary.resolved_child_target_count} |
| missing_child_target_count | {summary.missing_child_target_count} |
| parent_target_count | {summary.parent_target_count} |
| resolved_parent_target_count | {summary.resolved_parent_target_count} |
| missing_parent_target_count | {summary.missing_parent_target_count} |
| doc_target_count | {summary.doc_target_count} |
| resolved_doc_target_count | {summary.resolved_doc_target_count} |
| missing_doc_target_count | {summary.missing_doc_target_count} |
| answerable_without_child_or_parent_target_count | {summary.answerable_without_child_or_parent_target_count} |
| no_answer_with_positive_target_count | {summary.no_answer_with_positive_target_count} |
| public_raw_text_leakage_count | {summary.public_raw_text_leakage_count} |
| private_path_leakage_count | {summary.private_path_leakage_count} |
| secret_like_leakage_count | {summary.secret_like_leakage_count} |

## Gate Result

```text
target_resolvability_failures={failures}
```

## 정성 리포트

- target ID는 실제 검색 가능한 child corpus 기준으로 검증한다.
- answerable query는 최소 child 또는 parent target을 가져야 한다.
- `no_answer` query는 positive target을 가지면 안 된다.
- public report에는 원문 chunk text, parser text, OCR text, private path, secret-like 값을 포함하지 않는다.
- 이 gate를 통과해야 dev/test 평가셋 확장과 chunking ablation을 신뢰할 수 있다.

## 다음 단계

{next_steps}
"""


def _target_report_next_steps(
    *,
    summary: RetrievalEvalTargetResolvabilitySummary,
    dataset_path: Path,
) -> str:
    failures = collect_retrieval_eval_target_resolvability_failures(summary)
    if failures:
        return "\n".join(
            [
                "1. target resolvability failure를 먼저 해소한다.",
                "2. missing target, no-answer positive target, public-safety 값을 다시 검수한다.",
                "3. target_resolvability_status가 PASS가 된 뒤 dev/test 확장 또는 ablation으로 이동한다.",
            ]
        )
    is_private_dev = _is_private_benchmark_dataset_path(dataset_path) and (
        dataset_path.name.startswith("retrieval_eval_dev")
    )
    is_private_test = _is_private_benchmark_dataset_path(dataset_path) and (
        dataset_path.name.startswith("retrieval_eval_test")
    )
    if is_private_dev and summary.query_count >= 70:
        return "\n".join(
            [
                "1. private test lock report를 확인한다.",
                "2. private benchmark readiness report를 확인한다.",
                "3. chunking ablation은 동일 target contract를 유지한 상태에서 실행한다.",
            ]
        )
    if is_private_test and summary.query_count >= 35:
        return "\n".join(
            [
                "1. private benchmark readiness report를 확인한다.",
                "2. BM25 기준 chunking ablation runner를 구현한다.",
                "3. locked test split은 최종 확인 전까지 튜닝 의사결정에 사용하지 않는다.",
            ]
        )
    return "\n".join(
        [
            "1. private dev/test 평가 문항을 query type별로 확장한다.",
            "2. target resolvability gate를 통과한 평가셋만 retrieval 비교에 사용한다.",
            "3. chunking ablation은 동일 target contract를 유지한 상태에서 실행한다.",
        ]
    )


def main() -> int:
    args = _parse_args()
    summary = build_retrieval_eval_target_report(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        report_path=args.report,
    )
    failures = collect_retrieval_eval_target_resolvability_failures(summary)
    print(
        "retrieval_eval_target_resolvability "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"query_count={summary.query_count} "
        f"judgment_target_count={summary.judgment_target_count} "
        f"missing_child_targets={summary.missing_child_target_count} "
        f"missing_parent_targets={summary.missing_parent_target_count} "
        f"missing_doc_targets={summary.missing_doc_target_count} "
        f"failures={len(failures)}"
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build retrieval eval target resolvability report."
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


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
