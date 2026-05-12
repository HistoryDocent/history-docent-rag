from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.chat_retrieval import ChatRetrievalBackend, PrivateArtifactRetrievalBackend
from app.application.chat_service import ChatCommand
from app.application.evidence_packing import EvidencePack, PackedEvidence
from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
    is_repository_private_write_path,
    project_path,
)
from app.domain.retrieval import QueryType, RetrievalEvalItem, load_retrieval_eval_jsonl
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from pipelines.run_solar_live_generation_smoke import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_DATASET_PATH,
    DEFAULT_RETRIEVAL_RUN_LABEL,
)


PLACE_STORY_TARGET_GRAIN_COVERAGE_REPORT_VERSION = (
    "place-story-target-grain-coverage-report/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "place_story_target_grain_coverage_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "place_story_target_grain_coverage_rows.jsonl"
)

FailureTag = Literal[
    "target_too_narrow",
    "retrieval_semantic_miss",
    "lexical_alias_miss",
    "evidence_rank_too_low",
    "packing_order_bad",
    "child_covered",
    "parent_covered",
    "doc_covered",
    "no_hard_case",
]
CoverageDecision = Literal[
    "continue_retrieval_coverage_diagnostic",
    "repair_top_rank_retrieval_coverage",
    "inspect_judgment_target_grain",
    "proceed_to_generation_prompt_repair",
]


class PlaceStoryCoverageModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlaceStoryTargetGrainCoverageRow(PlaceStoryCoverageModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    retrieval_run_label: str = Field(min_length=1)
    retrieval_method: str = Field(min_length=1)
    retrieval_candidate_count: int = Field(ge=0)
    packed_evidence_count: int = Field(ge=0)
    total_latency_ms: float = Field(ge=0.0)
    target_child_covered: bool
    target_parent_covered: bool
    target_doc_covered: bool
    target_child_min_retrieval_rank: int | None = Field(default=None, ge=1)
    target_parent_min_retrieval_rank: int | None = Field(default=None, ge=1)
    target_doc_min_retrieval_rank: int | None = Field(default=None, ge=1)
    target_child_min_pack_rank: int | None = Field(default=None, ge=1)
    target_parent_min_pack_rank: int | None = Field(default=None, ge=1)
    target_doc_min_pack_rank: int | None = Field(default=None, ge=1)
    any_target_min_retrieval_rank: int | None = Field(default=None, ge=1)
    any_target_min_pack_rank: int | None = Field(default=None, ge=1)
    reciprocal_rank: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    citation_recoverability: float = Field(ge=0.0, le=1.0)
    evidence_order_relevance_proxy: float = Field(ge=0.0, le=1.0)
    duplicate_parent_rate: float = Field(ge=0.0, le=1.0)
    duplicate_doc_rate: float = Field(ge=0.0, le=1.0)
    query_rewrite_changed: bool
    query_rewrite_applied_rule_count: int = Field(ge=0)
    hard_case: bool
    failure_tags: tuple[FailureTag, ...]
    next_action: str = Field(min_length=1)


class PlaceStoryTargetGrainCoverageSummary(PlaceStoryCoverageModel):
    analyzed_query_count: int = Field(ge=0)
    target_child_covered_count: int = Field(ge=0)
    target_parent_covered_count: int = Field(ge=0)
    target_doc_covered_count: int = Field(ge=0)
    doc_only_covered_count: int = Field(ge=0)
    full_grain_miss_count: int = Field(ge=0)
    hard_case_count: int = Field(ge=0)
    target_child_recall_at_1: float = Field(ge=0.0, le=1.0)
    target_child_recall_at_3: float = Field(ge=0.0, le=1.0)
    target_child_recall_at_5: float = Field(ge=0.0, le=1.0)
    target_parent_recall_at_1: float = Field(ge=0.0, le=1.0)
    target_parent_recall_at_3: float = Field(ge=0.0, le=1.0)
    target_parent_recall_at_5: float = Field(ge=0.0, le=1.0)
    target_doc_recall_at_1: float = Field(ge=0.0, le=1.0)
    target_doc_recall_at_3: float = Field(ge=0.0, le=1.0)
    target_doc_recall_at_5: float = Field(ge=0.0, le=1.0)
    child_or_parent_recall_at_5: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)
    citation_recoverability_avg: float = Field(ge=0.0, le=1.0)
    duplicate_parent_rate_avg: float = Field(ge=0.0, le=1.0)
    evidence_order_relevance_proxy_avg: float = Field(ge=0.0, le=1.0)
    recommended_decision: CoverageDecision


class PlaceStoryTargetGrainCoverageReport(PlaceStoryCoverageModel):
    report_version: str = PLACE_STORY_TARGET_GRAIN_COVERAGE_REPORT_VERSION
    analysis_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    retrieval_run_label: str = Field(min_length=1)
    packing_policy_id: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: PlaceStoryTargetGrainCoverageSummary
    diagnostic_rows: tuple[PlaceStoryTargetGrainCoverageRow, ...]
    failure_tag_distribution: dict[str, int]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_place_story_target_grain_coverage(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    retrieval_backend: ChatRetrievalBackend | None = None,
) -> PlaceStoryTargetGrainCoverageReport:
    _validate_private_rows_path(result_rows_path, label="result")
    items = _load_place_story_dev_items(dataset_path=dataset_path)
    backend = retrieval_backend or PrivateArtifactRetrievalBackend(chunks_path=chunks_path)
    rows: list[PlaceStoryTargetGrainCoverageRow] = []
    for item in items:
        retrieval = backend.retrieve(command=_command_from_item(item), item=item)
        rows.append(
            build_place_story_target_grain_coverage_row(
                item=item,
                evidence_pack=retrieval.evidence_pack,
                retrieval_method=retrieval.retrieval_method,
                retrieval_candidate_count=retrieval.retrieval_candidate_count,
                total_latency_ms=round(
                    retrieval.retrieval_latency_ms + retrieval.query_rewrite_latency_ms,
                    6,
                ),
                query_rewrite_changed=retrieval.query_rewrite_changed,
                query_rewrite_applied_rule_count=len(retrieval.query_rewrite_applied_rules),
            ),
        )

    provisional = build_place_story_target_grain_coverage_report(
        diagnostic_rows=rows,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
    )
    provisional_markdown = build_place_story_target_grain_coverage_markdown(provisional)
    report = build_place_story_target_grain_coverage_report(
        diagnostic_rows=rows,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        report_text=provisional_markdown,
    )
    failures = collect_place_story_target_grain_coverage_failures(report)
    if failures:
        raise ValueError(f"place story target grain coverage gate failed: {failures}")

    result_rows = build_public_place_story_target_grain_coverage_rows(report)
    _write_jsonl_rows(path=result_rows_path, rows=result_rows)
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_place_story_target_grain_coverage_markdown(report),
        encoding="utf-8",
    )
    return report


def build_place_story_target_grain_coverage_row(
    *,
    item: RetrievalEvalItem,
    evidence_pack: EvidencePack,
    retrieval_method: str,
    retrieval_candidate_count: int,
    total_latency_ms: float,
    query_rewrite_changed: bool,
    query_rewrite_applied_rule_count: int,
) -> PlaceStoryTargetGrainCoverageRow:
    child_ids, parent_ids, doc_ids = _target_ids(item)
    child_retrieval_rank = _min_rank(
        evidence_pack=evidence_pack,
        target_ids=child_ids,
        grain="child",
        rank_field="source_rank",
    )
    parent_retrieval_rank = _min_rank(
        evidence_pack=evidence_pack,
        target_ids=parent_ids,
        grain="parent",
        rank_field="source_rank",
    )
    doc_retrieval_rank = _min_rank(
        evidence_pack=evidence_pack,
        target_ids=doc_ids,
        grain="doc",
        rank_field="source_rank",
    )
    child_pack_rank = _min_rank(
        evidence_pack=evidence_pack,
        target_ids=child_ids,
        grain="child",
        rank_field="pack_rank",
    )
    parent_pack_rank = _min_rank(
        evidence_pack=evidence_pack,
        target_ids=parent_ids,
        grain="parent",
        rank_field="pack_rank",
    )
    doc_pack_rank = _min_rank(
        evidence_pack=evidence_pack,
        target_ids=doc_ids,
        grain="doc",
        rank_field="pack_rank",
    )
    any_retrieval_rank = _min_existing_rank(
        [child_retrieval_rank, parent_retrieval_rank, doc_retrieval_rank],
    )
    any_pack_rank = _min_existing_rank([child_pack_rank, parent_pack_rank, doc_pack_rank])
    failure_tags = _failure_tags(
        child_retrieval_rank=child_retrieval_rank,
        parent_retrieval_rank=parent_retrieval_rank,
        doc_retrieval_rank=doc_retrieval_rank,
        any_retrieval_rank=any_retrieval_rank,
        any_pack_rank=any_pack_rank,
        query_rewrite_changed=query_rewrite_changed,
    )
    hard_case = any(
        tag
        in {
            "target_too_narrow",
            "retrieval_semantic_miss",
            "lexical_alias_miss",
            "evidence_rank_too_low",
            "packing_order_bad",
        }
        for tag in failure_tags
    )
    return PlaceStoryTargetGrainCoverageRow(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        retrieval_run_label=DEFAULT_RETRIEVAL_RUN_LABEL,
        retrieval_method=retrieval_method,
        retrieval_candidate_count=retrieval_candidate_count,
        packed_evidence_count=len(evidence_pack.evidence),
        total_latency_ms=total_latency_ms,
        target_child_covered=child_retrieval_rank is not None,
        target_parent_covered=parent_retrieval_rank is not None,
        target_doc_covered=doc_retrieval_rank is not None,
        target_child_min_retrieval_rank=child_retrieval_rank,
        target_parent_min_retrieval_rank=parent_retrieval_rank,
        target_doc_min_retrieval_rank=doc_retrieval_rank,
        target_child_min_pack_rank=child_pack_rank,
        target_parent_min_pack_rank=parent_pack_rank,
        target_doc_min_pack_rank=doc_pack_rank,
        any_target_min_retrieval_rank=any_retrieval_rank,
        any_target_min_pack_rank=any_pack_rank,
        reciprocal_rank=0.0 if any_retrieval_rank is None else round(1 / any_retrieval_rank, 6),
        ndcg_at_5=_ndcg_at_5(item=item, evidence=tuple(evidence_pack.evidence)),
        citation_recoverability=evidence_pack.citation_recoverability,
        evidence_order_relevance_proxy=evidence_pack.evidence_order_relevance_proxy,
        duplicate_parent_rate=evidence_pack.duplicate_parent_rate,
        duplicate_doc_rate=evidence_pack.duplicate_doc_rate,
        query_rewrite_changed=query_rewrite_changed,
        query_rewrite_applied_rule_count=query_rewrite_applied_rule_count,
        hard_case=hard_case,
        failure_tags=tuple(failure_tags),
        next_action=_next_action(failure_tags),
    )


def build_place_story_target_grain_coverage_report(
    *,
    diagnostic_rows: list[PlaceStoryTargetGrainCoverageRow],
    dataset_path: Path,
    chunks_path: Path,
    report_text: str = "",
) -> PlaceStoryTargetGrainCoverageReport:
    rows = tuple(diagnostic_rows)
    analysis_id = _analysis_id(rows)
    public_rows = [row.model_dump(mode="json") for row in rows]
    quality = measure_public_retrieval_artifact_quality(
        report_version=PLACE_STORY_TARGET_GRAIN_COVERAGE_REPORT_VERSION,
        run_id=analysis_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    report = PlaceStoryTargetGrainCoverageReport(
        analysis_id=analysis_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        retrieval_run_label=DEFAULT_RETRIEVAL_RUN_LABEL,
        packing_policy_id="P0_rank_order",
        source_fingerprint=_stable_digest(
            {
                "dataset_path": str(dataset_path),
                "chunks_path": str(chunks_path),
                "rows": [row.model_dump(mode="json") for row in rows],
            },
        )[:16],
        summary=build_place_story_target_grain_coverage_summary(rows),
        diagnostic_rows=rows,
        failure_tag_distribution=_failure_tag_distribution(rows),
        output_quality=quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_place_story_target_grain_coverage_qualitative(
                report,
            ),
        },
    )


def build_place_story_target_grain_coverage_summary(
    rows: tuple[PlaceStoryTargetGrainCoverageRow, ...],
) -> PlaceStoryTargetGrainCoverageSummary:
    child_or_parent_at_5 = [
        _covered_at(row.target_child_min_retrieval_rank, 5)
        or _covered_at(row.target_parent_min_retrieval_rank, 5)
        for row in rows
    ]
    return PlaceStoryTargetGrainCoverageSummary(
        analyzed_query_count=len(rows),
        target_child_covered_count=sum(1 for row in rows if row.target_child_covered),
        target_parent_covered_count=sum(1 for row in rows if row.target_parent_covered),
        target_doc_covered_count=sum(1 for row in rows if row.target_doc_covered),
        doc_only_covered_count=sum(
            1
            for row in rows
            if row.target_doc_covered
            and not row.target_child_covered
            and not row.target_parent_covered
        ),
        full_grain_miss_count=sum(
            1
            for row in rows
            if not row.target_child_covered
            and not row.target_parent_covered
            and not row.target_doc_covered
        ),
        hard_case_count=sum(1 for row in rows if row.hard_case),
        target_child_recall_at_1=_recall_at(rows, grain="child", k=1),
        target_child_recall_at_3=_recall_at(rows, grain="child", k=3),
        target_child_recall_at_5=_recall_at(rows, grain="child", k=5),
        target_parent_recall_at_1=_recall_at(rows, grain="parent", k=1),
        target_parent_recall_at_3=_recall_at(rows, grain="parent", k=3),
        target_parent_recall_at_5=_recall_at(rows, grain="parent", k=5),
        target_doc_recall_at_1=_recall_at(rows, grain="doc", k=1),
        target_doc_recall_at_3=_recall_at(rows, grain="doc", k=3),
        target_doc_recall_at_5=_recall_at(rows, grain="doc", k=5),
        child_or_parent_recall_at_5=_mean_bool(child_or_parent_at_5),
        mrr=_mean_float([row.reciprocal_rank for row in rows]),
        ndcg_at_5=_mean_float([row.ndcg_at_5 for row in rows]),
        latency_p95_ms=_percentile_float([row.total_latency_ms for row in rows], 0.95),
        citation_recoverability_avg=_mean_float(
            [row.citation_recoverability for row in rows],
        ),
        duplicate_parent_rate_avg=_mean_float([row.duplicate_parent_rate for row in rows]),
        evidence_order_relevance_proxy_avg=_mean_float(
            [row.evidence_order_relevance_proxy for row in rows],
        ),
        recommended_decision=_recommended_decision(rows),
    )


def build_public_place_story_target_grain_coverage_rows(
    report: PlaceStoryTargetGrainCoverageReport,
) -> list[dict[str, Any]]:
    return [
        {
            "analysis_id": report.analysis_id,
            "query_id": row.query_id,
            "query_type": row.query_type,
            "retrieval_run_label": row.retrieval_run_label,
            "retrieval_method": row.retrieval_method,
            "retrieval_candidate_count": row.retrieval_candidate_count,
            "packed_evidence_count": row.packed_evidence_count,
            "total_latency_ms": row.total_latency_ms,
            "target_child_covered": row.target_child_covered,
            "target_parent_covered": row.target_parent_covered,
            "target_doc_covered": row.target_doc_covered,
            "target_child_min_retrieval_rank": row.target_child_min_retrieval_rank,
            "target_parent_min_retrieval_rank": row.target_parent_min_retrieval_rank,
            "target_doc_min_retrieval_rank": row.target_doc_min_retrieval_rank,
            "target_child_min_pack_rank": row.target_child_min_pack_rank,
            "target_parent_min_pack_rank": row.target_parent_min_pack_rank,
            "target_doc_min_pack_rank": row.target_doc_min_pack_rank,
            "any_target_min_retrieval_rank": row.any_target_min_retrieval_rank,
            "any_target_min_pack_rank": row.any_target_min_pack_rank,
            "reciprocal_rank": row.reciprocal_rank,
            "ndcg_at_5": row.ndcg_at_5,
            "citation_recoverability": row.citation_recoverability,
            "evidence_order_relevance_proxy": row.evidence_order_relevance_proxy,
            "duplicate_parent_rate": row.duplicate_parent_rate,
            "duplicate_doc_rate": row.duplicate_doc_rate,
            "query_rewrite_changed": row.query_rewrite_changed,
            "query_rewrite_applied_rule_count": row.query_rewrite_applied_rule_count,
            "hard_case": row.hard_case,
            "failure_tags": list(row.failure_tags),
        }
        for row in report.diagnostic_rows
    ]


def collect_place_story_target_grain_coverage_failures(
    report: PlaceStoryTargetGrainCoverageReport,
) -> list[str]:
    failures: list[str] = []
    if report.summary.analyzed_query_count == 0:
        failures.append("empty_place_story_coverage_analysis")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_place_story_target_grain_coverage_markdown(
    report: PlaceStoryTargetGrainCoverageReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    diagnostic_rows = "\n".join(
        _format_diagnostic_row(row) for row in report.diagnostic_rows
    )
    failure_rows = "\n".join(
        f"| {tag} | {count} |"
        for tag, count in report.failure_tag_distribution.items()
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Place Story Target Grain Coverage Report

## 목적

`place_story` dev query 전체에서 child, parent, doc target grain별 retrieval/evidence coverage를 분리 진단한다.

이 문서는 청킹 재실험 결과가 아니며 Solar Pro 3 추가 호출도 아니다. private dev 평가셋과 private chunk artifact를 사용하지만 raw query, raw answer, evidence text, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| analysis_id | `{report.analysis_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| retrieval_run_label | `{report.retrieval_run_label}` |
| packing_policy_id | `{report.packing_policy_id}` |
| source_fingerprint | `{report.source_fingerprint}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| analyzed_query_count | {summary.analyzed_query_count} |
| target_child_covered_count | {summary.target_child_covered_count} |
| target_parent_covered_count | {summary.target_parent_covered_count} |
| target_doc_covered_count | {summary.target_doc_covered_count} |
| doc_only_covered_count | {summary.doc_only_covered_count} |
| full_grain_miss_count | {summary.full_grain_miss_count} |
| hard_case_count | {summary.hard_case_count} |
| target_child_recall_at_1 | {summary.target_child_recall_at_1:.6f} |
| target_child_recall_at_3 | {summary.target_child_recall_at_3:.6f} |
| target_child_recall_at_5 | {summary.target_child_recall_at_5:.6f} |
| target_parent_recall_at_1 | {summary.target_parent_recall_at_1:.6f} |
| target_parent_recall_at_3 | {summary.target_parent_recall_at_3:.6f} |
| target_parent_recall_at_5 | {summary.target_parent_recall_at_5:.6f} |
| target_doc_recall_at_1 | {summary.target_doc_recall_at_1:.6f} |
| target_doc_recall_at_3 | {summary.target_doc_recall_at_3:.6f} |
| target_doc_recall_at_5 | {summary.target_doc_recall_at_5:.6f} |
| child_or_parent_recall_at_5 | {summary.child_or_parent_recall_at_5:.6f} |
| MRR | {summary.mrr:.6f} |
| nDCG@5 | {summary.ndcg_at_5:.6f} |
| latency_p95_ms | {summary.latency_p95_ms:.6f} |
| citation_recoverability_avg | {summary.citation_recoverability_avg:.6f} |
| duplicate_parent_rate_avg | {summary.duplicate_parent_rate_avg:.6f} |
| evidence_order_relevance_proxy_avg | {summary.evidence_order_relevance_proxy_avg:.6f} |
| recommended_decision | `{summary.recommended_decision}` |

## Failure Tag Distribution

| failure_tag | count |
| --- | ---: |
{failure_rows}

## Query Diagnostic Rows

| query_id | method | candidates | packed | latency_ms | child | parent | doc | child_rank | parent_rank | doc_rank | any_rank | RR | nDCG@5 | citation | order_proxy | duplicate_parent | hard_case | tags |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{diagnostic_rows}

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | {quality.result_row_count} |
| public_raw_text_leakage_count | {quality.public_raw_text_leakage_count} |
| private_path_leakage_count | {quality.private_path_leakage_count} |
| secret_like_leakage_count | {quality.secret_like_leakage_count} |
| forbidden_result_field_count | {quality.forbidden_result_field_count} |

## 정성 리포트

{qualitative_rows}

## 결론

{_conclusion_text(summary)}
"""


def build_place_story_target_grain_coverage_qualitative(
    report: PlaceStoryTargetGrainCoverageReport,
) -> dict[str, str]:
    summary = report.summary
    return {
        "evaluation_scope": (
            "`place_story` dev query만 대상으로 child, parent, doc target grain을 분리 측정했다."
        ),
        "chunking_decision": _chunking_decision_text(summary),
        "retrieval_decision": _retrieval_decision_text(summary),
        "generation_decision": (
            "Solar Pro 3 v2 prompt repair는 retrieval 입력 품질 진단 뒤에 진행한다. 이번 실행의 live Solar call은 0이다."
        ),
        "data_mart_grain": (
            "`fact_place_story_coverage`의 grain은 query-run-strategy이며, fact에는 metric과 id만 남긴다."
        ),
        "public_policy": (
            "public report에는 query id, rank, boolean, metric, tag만 저장하고 raw query/evidence/chunk text는 저장하지 않는다."
        ),
        "next_action": _recommended_next_action_text(summary.recommended_decision),
    }


def _load_place_story_dev_items(*, dataset_path: Path) -> list[RetrievalEvalItem]:
    items = load_retrieval_eval_jsonl(project_path(dataset_path))
    selected = [
        item
        for item in items
        if item.query.query_type == "place_story"
        and item.metadata.split == "dev"
        and item.metadata.review_status == "reviewed"
    ]
    if not selected:
        raise ValueError("place_story target grain coverage requires reviewed dev rows")
    return selected


def _command_from_item(item: RetrievalEvalItem) -> ChatCommand:
    return ChatCommand(
        request_id=item.query.query_id,
        query=item.query.query_text,
        language=item.query.language,
        query_type=item.query.query_type,
        place_context=tuple(item.metadata.place_ids),
        voice_mode=item.query.query_type == "voice_followup",
        user_context=item.query.user_context,
        retrieval_mode="retrieval_backed",
        provider_mode="contract_only",
    )


def _target_ids(item: RetrievalEvalItem) -> tuple[set[str], set[str], set[str]]:
    child_ids: set[str] = set()
    parent_ids: set[str] = set()
    doc_ids: set[str] = set()
    for judgment in item.judgments:
        child_ids.update(judgment.relevant_child_ids)
        parent_ids.update(judgment.relevant_parent_ids)
        doc_ids.update(judgment.relevant_doc_ids)
    return child_ids, parent_ids, doc_ids


def _min_rank(
    *,
    evidence_pack: EvidencePack,
    target_ids: set[str],
    grain: Literal["child", "parent", "doc"],
    rank_field: Literal["source_rank", "pack_rank"],
) -> int | None:
    if not target_ids:
        return None
    ranks: list[int] = []
    for evidence in evidence_pack.evidence:
        identifier = {
            "child": evidence.child_id,
            "parent": evidence.parent_id,
            "doc": evidence.doc_id,
        }[grain]
        if identifier in target_ids:
            ranks.append(int(getattr(evidence, rank_field)))
    return min(ranks) if ranks else None


def _min_existing_rank(values: list[int | None]) -> int | None:
    existing = [value for value in values if value is not None]
    return min(existing) if existing else None


def _failure_tags(
    *,
    child_retrieval_rank: int | None,
    parent_retrieval_rank: int | None,
    doc_retrieval_rank: int | None,
    any_retrieval_rank: int | None,
    any_pack_rank: int | None,
    query_rewrite_changed: bool,
) -> list[FailureTag]:
    tags: list[FailureTag] = []
    if child_retrieval_rank is not None:
        tags.append("child_covered")
    if parent_retrieval_rank is not None:
        tags.append("parent_covered")
    if doc_retrieval_rank is not None:
        tags.append("doc_covered")
    if any_retrieval_rank is None:
        tags.append("retrieval_semantic_miss")
    if child_retrieval_rank is None and (
        parent_retrieval_rank is not None or doc_retrieval_rank is not None
    ):
        tags.append("target_too_narrow")
    if any_retrieval_rank is not None and any_retrieval_rank >= 4:
        tags.append("evidence_rank_too_low")
    if (
        any_retrieval_rank is not None
        and any_pack_rank is not None
        and any_retrieval_rank <= 3
        and any_pack_rank >= 4
    ):
        tags.append("packing_order_bad")
    if query_rewrite_changed and child_retrieval_rank is None and parent_retrieval_rank is None:
        tags.append("lexical_alias_miss")
    if not any(
        tag
        in {
            "target_too_narrow",
            "retrieval_semantic_miss",
            "lexical_alias_miss",
            "evidence_rank_too_low",
            "packing_order_bad",
        }
        for tag in tags
    ):
        tags.append("no_hard_case")
    return tags


def _next_action(tags: tuple[FailureTag, ...] | list[FailureTag]) -> str:
    tag_set = set(tags)
    if "retrieval_semantic_miss" in tag_set:
        return "semantic retrieval 또는 place-aware rewrite 후보를 비교한다."
    if "target_too_narrow" in tag_set:
        return "judgment target grain과 parent/doc context coverage를 점검한다."
    if "evidence_rank_too_low" in tag_set:
        return "top-rank retrieval coverage repair 후보를 비교한다."
    if "packing_order_bad" in tag_set:
        return "evidence packing order 정책을 비교한다."
    if "lexical_alias_miss" in tag_set:
        return "장소 alias와 지시어 rewrite 후보를 비교한다."
    return "현재 retrieval 입력은 monitor로 유지하고 generation prompt repair 후보로 넘긴다."


def _ndcg_at_5(*, item: RetrievalEvalItem, evidence: tuple[PackedEvidence, ...]) -> float:
    relevance_by_identifier = _relevance_by_identifier(item)
    ordered = sorted(evidence, key=lambda row: row.source_rank)[:5]
    gains = [
        max(
            relevance_by_identifier.get(row.child_id, 0),
            relevance_by_identifier.get(row.parent_id, 0),
            relevance_by_identifier.get(row.doc_id, 0),
        )
        for row in ordered
    ]
    ideal = sorted(relevance_by_identifier.values(), reverse=True)[:5]
    dcg = _dcg(gains)
    idcg = _dcg(ideal)
    if idcg == 0:
        return 0.0
    # Relaxed child/parent/doc grain can over-credit duplicate doc hits.
    return min(round(dcg / idcg, 6), 1.0)


def _relevance_by_identifier(item: RetrievalEvalItem) -> dict[str, int]:
    relevance: dict[str, int] = {}
    for judgment in item.judgments:
        for identifier in (
            judgment.relevant_child_ids
            + judgment.relevant_parent_ids
            + judgment.relevant_doc_ids
        ):
            relevance[identifier] = max(
                relevance.get(identifier, 0),
                judgment.relevance_grade,
            )
    return relevance


def _dcg(gains: list[int]) -> float:
    import math

    return sum(
        ((2**gain - 1) / math.log2(rank + 1))
        for rank, gain in enumerate(gains, start=1)
        if gain > 0
    )


def _recall_at(
    rows: tuple[PlaceStoryTargetGrainCoverageRow, ...],
    *,
    grain: Literal["child", "parent", "doc"],
    k: int,
) -> float:
    if not rows:
        return 0.0
    values = [_covered_at(_rank_for_grain(row, grain), k) for row in rows]
    return _mean_bool(values)


def _rank_for_grain(
    row: PlaceStoryTargetGrainCoverageRow,
    grain: Literal["child", "parent", "doc"],
) -> int | None:
    if grain == "child":
        return row.target_child_min_retrieval_rank
    if grain == "parent":
        return row.target_parent_min_retrieval_rank
    return row.target_doc_min_retrieval_rank


def _covered_at(rank: int | None, k: int) -> bool:
    return rank is not None and rank <= k


def _failure_tag_distribution(
    rows: tuple[PlaceStoryTargetGrainCoverageRow, ...],
) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter.update(row.failure_tags)
    return dict(sorted(counter.items()))


def _recommended_decision(
    rows: tuple[PlaceStoryTargetGrainCoverageRow, ...],
) -> CoverageDecision:
    if not rows:
        return "continue_retrieval_coverage_diagnostic"
    tag_distribution = _failure_tag_distribution(rows)
    if tag_distribution.get("retrieval_semantic_miss", 0) or tag_distribution.get(
        "evidence_rank_too_low",
        0,
    ):
        return "repair_top_rank_retrieval_coverage"
    if tag_distribution.get("target_too_narrow", 0):
        return "inspect_judgment_target_grain"
    if all(not row.hard_case for row in rows):
        return "proceed_to_generation_prompt_repair"
    return "continue_retrieval_coverage_diagnostic"


def _mean_bool(values: list[bool]) -> float:
    if not values:
        return 0.0
    return round(sum(1 for value in values if value) / len(values), 6)


def _mean_float(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _percentile_float(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percentile)
    return round(sorted_values[index], 6)


def _analysis_id(rows: tuple[PlaceStoryTargetGrainCoverageRow, ...]) -> str:
    digest = _stable_digest([row.model_dump(mode="json") for row in rows])[:8]
    return f"place-story-coverage-q{len(rows)}-{digest}"


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()


def _validate_private_rows_path(path: Path, *, label: str) -> None:
    if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
        raise ValueError(f"{label} rows must stay under repository private_data")
    if has_private_data_segment(path) and not is_repository_private_write_path(path):
        raise ValueError(f"{label} rows must stay under repository private_data")


def _write_jsonl_rows(*, path: Path, rows: list[dict[str, Any]]) -> None:
    resolved = project_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def _format_diagnostic_row(row: PlaceStoryTargetGrainCoverageRow) -> str:
    tags = ", ".join(row.failure_tags)
    return (
        f"| {row.query_id} | {row.retrieval_method} | "
        f"{row.retrieval_candidate_count} | {row.packed_evidence_count} | "
        f"{row.total_latency_ms:.6f} | "
        f"{_bool_cell(row.target_child_covered)} | "
        f"{_bool_cell(row.target_parent_covered)} | "
        f"{_bool_cell(row.target_doc_covered)} | "
        f"{_int_or_na(row.target_child_min_retrieval_rank)} | "
        f"{_int_or_na(row.target_parent_min_retrieval_rank)} | "
        f"{_int_or_na(row.target_doc_min_retrieval_rank)} | "
        f"{_int_or_na(row.any_target_min_retrieval_rank)} | "
        f"{row.reciprocal_rank:.6f} | {row.ndcg_at_5:.6f} | "
        f"{row.citation_recoverability:.6f} | "
        f"{row.evidence_order_relevance_proxy:.6f} | "
        f"{row.duplicate_parent_rate:.6f} | {_bool_cell(row.hard_case)} | {tags} |"
    )


def _bool_cell(value: bool) -> str:
    return "1" if value else "0"


def _int_or_na(value: int | None) -> str:
    return "NA" if value is None else str(value)


def _chunking_decision_text(summary: PlaceStoryTargetGrainCoverageSummary) -> str:
    if summary.full_grain_miss_count or summary.doc_only_covered_count:
        return (
            "청킹 전체 재실험으로 바로 가지 않고, child/parent가 parent/doc 내부에 묻히는지 hard subset에서 확인한다."
        )
    if summary.target_child_recall_at_5 < summary.target_doc_recall_at_5:
        return "doc coverage와 child coverage 차이가 있어 target grain review를 먼저 한다."
    return "현재 결과만으로는 청킹 재실험 우선순위가 낮다."


def _retrieval_decision_text(summary: PlaceStoryTargetGrainCoverageSummary) -> str:
    if summary.recommended_decision == "repair_top_rank_retrieval_coverage":
        return "deterministic rewrite v2 또는 parent/doc context boost를 우선 비교한다."
    if summary.recommended_decision == "inspect_judgment_target_grain":
        return "child-only target이 과도하게 좁은지 judgment grain review를 먼저 한다."
    if summary.recommended_decision == "proceed_to_generation_prompt_repair":
        return "retrieval 입력은 통과권으로 보고 generation v2 prompt repair로 넘어갈 수 있다."
    return "추가 hard-case 분류를 계속한다."


def _recommended_next_action_text(decision: CoverageDecision) -> str:
    if decision == "repair_top_rank_retrieval_coverage":
        return "HD-PLACE-STORY-007에서 hard subset을 고정하고 top-rank coverage repair 후보를 비교한다."
    if decision == "inspect_judgment_target_grain":
        return "HD-PLACE-STORY-007에서 judgment target grain review를 먼저 수행한다."
    if decision == "proceed_to_generation_prompt_repair":
        return "HD-SOLAR-009로 넘어가기 전에 v2 prompt repair 계획을 작성한다."
    return "hard-case row를 더 모은 뒤 rewrite/boost/chunking 재실험 여부를 분리한다."


def _conclusion_text(summary: PlaceStoryTargetGrainCoverageSummary) -> str:
    if summary.recommended_decision == "repair_top_rank_retrieval_coverage":
        return (
            "현재 우선순위는 청킹 재실험이 아니라 top-rank retrieval coverage repair다.\n\n"
            "child/parent/doc grain별 coverage와 rank를 기준으로 hard subset을 고정한 뒤 deterministic rewrite 또는 parent/doc context boost를 비교한다."
        )
    if summary.recommended_decision == "inspect_judgment_target_grain":
        return (
            "현재 우선순위는 judgment target grain review다.\n\n"
            "서사형 `place_story` 질문에서 child strict target이 과도하게 좁은지 parent/doc relaxed metric과 함께 검토한다."
        )
    if summary.recommended_decision == "proceed_to_generation_prompt_repair":
        return (
            "retrieval 입력 품질은 현재 기준에서 큰 blocker가 아니다.\n\n"
            "다음 단계는 Solar Pro 3 v2 prompt repair 계획이다."
        )
    return "추가 진단을 계속하고 청킹, retrieval, generation 원인을 분리한다."


def main() -> int:
    args = _parse_args()
    report = run_place_story_target_grain_coverage(
        dataset_path=args.dataset,
        chunks_path=args.chunks,
        report_path=args.report,
        result_rows_path=args.result_rows,
    )
    failures = collect_place_story_target_grain_coverage_failures(report)
    summary = report.summary
    print(
        "place_story_target_grain_coverage "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"query_count={summary.analyzed_query_count} "
        f"child_recall_at_5={summary.target_child_recall_at_5:.6f} "
        f"parent_recall_at_5={summary.target_parent_recall_at_5:.6f} "
        f"doc_recall_at_5={summary.target_doc_recall_at_5:.6f} "
        f"hard_case_count={summary.hard_case_count} "
        f"decision={summary.recommended_decision} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze place_story target grain coverage across reviewed dev rows.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
