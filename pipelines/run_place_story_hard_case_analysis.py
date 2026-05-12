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
from app.application.evidence_packing import EvidencePack
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
from pipelines.run_solar_generation_contract_v2_live_comparison import (
    DEFAULT_RESULT_ROWS_PATH as DEFAULT_LIVE_COMPARISON_ROWS_PATH,
)
from pipelines.run_solar_generation_v2_tradeoff_analysis import (
    SolarGenerationV2PairedMetricRow,
)
from pipelines.run_solar_live_generation_smoke import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_DATASET_PATH,
    DEFAULT_RETRIEVAL_RUN_LABEL,
    write_jsonl_rows,
)


PLACE_STORY_HARD_CASE_ANALYSIS_REPORT_VERSION = "place-story-hard-case-analysis-report/v1"
DEFAULT_QUERY_ID = "q-dev-place-story-001"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "place_story_hard_case_analysis_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "place_story_hard_case_analysis_rows.jsonl"
)

RootCauseDecision = Literal[
    "generation_contract_candidate",
    "retrieval_or_packing_miss",
    "target_grain_mismatch",
    "monitor_only",
]


class PlaceStoryHardCaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlaceStoryHardCaseDiagnosticRow(PlaceStoryHardCaseModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    retrieval_run_label: str = Field(min_length=1)
    retrieval_method: str = Field(min_length=1)
    retrieval_candidate_count: int = Field(ge=0)
    packed_evidence_count: int = Field(ge=0)
    target_child_covered: bool
    target_parent_covered: bool
    target_doc_covered: bool
    target_min_retrieval_rank: int | None = Field(default=None, ge=1)
    target_min_pack_rank: int | None = Field(default=None, ge=1)
    citation_recoverability: float = Field(ge=0.0, le=1.0)
    evidence_order_relevance_proxy: float = Field(ge=0.0, le=1.0)
    duplicate_parent_rate: float = Field(ge=0.0, le=1.0)
    duplicate_doc_rate: float = Field(ge=0.0, le=1.0)
    query_rewrite_changed: bool
    query_rewrite_applied_rule_count: int = Field(ge=0)
    generation_correctness_regression: bool
    generation_unsupported_regression: bool
    generation_citation_precision_delta: float | None = None
    generation_citation_recall_delta: float | None = None
    generation_citation_count_delta: int | None = None
    root_cause_decision: RootCauseDecision
    diagnostic_tags: tuple[str, ...]
    next_action: str = Field(min_length=1)


class PlaceStoryHardCaseSummary(PlaceStoryHardCaseModel):
    analyzed_query_count: int = Field(ge=0)
    target_child_covered_count: int = Field(ge=0)
    target_parent_covered_count: int = Field(ge=0)
    target_doc_covered_count: int = Field(ge=0)
    generation_regression_count: int = Field(ge=0)
    retrieval_or_packing_miss_count: int = Field(ge=0)
    root_cause_decision: RootCauseDecision


class PlaceStoryHardCaseAnalysisReport(PlaceStoryHardCaseModel):
    report_version: str = PLACE_STORY_HARD_CASE_ANALYSIS_REPORT_VERSION
    analysis_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    generation_rows_alias: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: PlaceStoryHardCaseSummary
    diagnostic_rows: tuple[PlaceStoryHardCaseDiagnosticRow, ...]
    root_cause_distribution: dict[str, int]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_place_story_hard_case_analysis(
    *,
    query_id: str = DEFAULT_QUERY_ID,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    generation_rows_path: Path = DEFAULT_LIVE_COMPARISON_ROWS_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    retrieval_backend: ChatRetrievalBackend | None = None,
) -> PlaceStoryHardCaseAnalysisReport:
    _validate_private_rows_path(result_rows_path, label="result")
    item = _load_target_item(dataset_path=dataset_path, query_id=query_id)
    generation_row = _load_generation_row(
        generation_rows_path=generation_rows_path,
        query_id=query_id,
    )
    backend = retrieval_backend or PrivateArtifactRetrievalBackend(chunks_path=chunks_path)
    retrieval = backend.retrieve(command=_command_from_item(item), item=item)
    diagnostic = build_place_story_hard_case_diagnostic_row(
        item=item,
        evidence_pack=retrieval.evidence_pack,
        retrieval_method=retrieval.retrieval_method,
        retrieval_candidate_count=retrieval.retrieval_candidate_count,
        query_rewrite_changed=retrieval.query_rewrite_changed,
        query_rewrite_applied_rule_count=len(retrieval.query_rewrite_applied_rules),
        generation_row=generation_row,
    )
    provisional_report = build_place_story_hard_case_analysis_report(
        diagnostic_rows=[diagnostic],
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        generation_rows_path=generation_rows_path,
    )
    provisional_markdown = build_place_story_hard_case_analysis_markdown(provisional_report)
    report = build_place_story_hard_case_analysis_report(
        diagnostic_rows=[diagnostic],
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        generation_rows_path=generation_rows_path,
        report_text=provisional_markdown,
    )
    failures = collect_place_story_hard_case_analysis_failures(report)
    if failures:
        raise ValueError(f"place story hard-case analysis gate failed: {failures}")

    rows = build_public_place_story_hard_case_rows(report)
    write_jsonl_rows(path=result_rows_path, rows=rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_place_story_hard_case_analysis_markdown(report),
        encoding="utf-8",
    )
    return report


def build_place_story_hard_case_diagnostic_row(
    *,
    item: RetrievalEvalItem,
    evidence_pack: EvidencePack,
    retrieval_method: str,
    retrieval_candidate_count: int,
    query_rewrite_changed: bool,
    query_rewrite_applied_rule_count: int,
    generation_row: SolarGenerationV2PairedMetricRow | None = None,
) -> PlaceStoryHardCaseDiagnosticRow:
    target_child_ids, target_parent_ids, target_doc_ids = _target_ids(item)
    target_min_retrieval_rank = _min_retrieval_rank(
        evidence_pack=evidence_pack,
        child_ids=target_child_ids,
        parent_ids=target_parent_ids,
        doc_ids=target_doc_ids,
    )
    target_min_pack_rank = _min_pack_rank(
        evidence_pack=evidence_pack,
        child_ids=target_child_ids,
        parent_ids=target_parent_ids,
        doc_ids=target_doc_ids,
    )
    generation_correctness_regression = bool(
        generation_row and generation_row.correct_with_evidence_delta < 0
    )
    generation_unsupported_regression = bool(
        generation_row and generation_row.unsupported_claim_delta > 0
    )
    root_cause = _root_cause_decision(
        evidence_pack=evidence_pack,
        generation_correctness_regression=generation_correctness_regression,
        generation_unsupported_regression=generation_unsupported_regression,
    )
    tags = _diagnostic_tags(
        evidence_pack=evidence_pack,
        target_min_retrieval_rank=target_min_retrieval_rank,
        target_min_pack_rank=target_min_pack_rank,
        query_rewrite_changed=query_rewrite_changed,
        generation_correctness_regression=generation_correctness_regression,
        generation_unsupported_regression=generation_unsupported_regression,
        generation_row=generation_row,
    )
    return PlaceStoryHardCaseDiagnosticRow(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        retrieval_run_label=DEFAULT_RETRIEVAL_RUN_LABEL,
        retrieval_method=retrieval_method,
        retrieval_candidate_count=retrieval_candidate_count,
        packed_evidence_count=len(evidence_pack.evidence),
        target_child_covered=evidence_pack.target_child_covered,
        target_parent_covered=evidence_pack.target_parent_covered,
        target_doc_covered=evidence_pack.target_doc_covered,
        target_min_retrieval_rank=target_min_retrieval_rank,
        target_min_pack_rank=target_min_pack_rank,
        citation_recoverability=evidence_pack.citation_recoverability,
        evidence_order_relevance_proxy=evidence_pack.evidence_order_relevance_proxy,
        duplicate_parent_rate=evidence_pack.duplicate_parent_rate,
        duplicate_doc_rate=evidence_pack.duplicate_doc_rate,
        query_rewrite_changed=query_rewrite_changed,
        query_rewrite_applied_rule_count=query_rewrite_applied_rule_count,
        generation_correctness_regression=generation_correctness_regression,
        generation_unsupported_regression=generation_unsupported_regression,
        generation_citation_precision_delta=(
            generation_row.citation_precision_delta if generation_row else None
        ),
        generation_citation_recall_delta=(
            generation_row.citation_recall_delta if generation_row else None
        ),
        generation_citation_count_delta=(
            generation_row.citation_count_delta if generation_row else None
        ),
        root_cause_decision=root_cause,
        diagnostic_tags=tuple(tags),
        next_action=_next_action(root_cause),
    )


def build_place_story_hard_case_analysis_report(
    *,
    diagnostic_rows: list[PlaceStoryHardCaseDiagnosticRow],
    dataset_path: Path,
    chunks_path: Path,
    generation_rows_path: Path,
    report_text: str = "",
) -> PlaceStoryHardCaseAnalysisReport:
    diagnostics = tuple(diagnostic_rows)
    public_rows = [row.model_dump(mode="json") for row in diagnostics]
    analysis_id = _analysis_id(diagnostics)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=PLACE_STORY_HARD_CASE_ANALYSIS_REPORT_VERSION,
        run_id=analysis_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    report = PlaceStoryHardCaseAnalysisReport(
        analysis_id=analysis_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        generation_rows_alias="<private solar_generation_contract_v2_live_comparison_results.jsonl>",
        source_fingerprint=_stable_digest(
            {
                "dataset_path": str(dataset_path),
                "chunks_path": str(chunks_path),
                "generation_rows_path": str(generation_rows_path),
                "diagnostics": [row.model_dump(mode="json") for row in diagnostics],
            },
        )[:16],
        summary=build_place_story_hard_case_summary(diagnostics),
        diagnostic_rows=diagnostics,
        root_cause_distribution=dict(
            sorted(Counter(row.root_cause_decision for row in diagnostics).items()),
        ),
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_qualitative_assessment(report)},
    )


def build_place_story_hard_case_summary(
    diagnostics: tuple[PlaceStoryHardCaseDiagnosticRow, ...],
) -> PlaceStoryHardCaseSummary:
    retrieval_or_packing_miss_count = sum(
        1
        for row in diagnostics
        if row.root_cause_decision == "retrieval_or_packing_miss"
    )
    generation_regression_count = sum(
        1
        for row in diagnostics
        if row.generation_correctness_regression or row.generation_unsupported_regression
    )
    root_cause = (
        diagnostics[0].root_cause_decision if len(diagnostics) == 1 else "monitor_only"
    )
    return PlaceStoryHardCaseSummary(
        analyzed_query_count=len(diagnostics),
        target_child_covered_count=sum(1 for row in diagnostics if row.target_child_covered),
        target_parent_covered_count=sum(1 for row in diagnostics if row.target_parent_covered),
        target_doc_covered_count=sum(1 for row in diagnostics if row.target_doc_covered),
        generation_regression_count=generation_regression_count,
        retrieval_or_packing_miss_count=retrieval_or_packing_miss_count,
        root_cause_decision=root_cause,
    )


def build_public_place_story_hard_case_rows(
    report: PlaceStoryHardCaseAnalysisReport,
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
            "target_child_covered": row.target_child_covered,
            "target_parent_covered": row.target_parent_covered,
            "target_doc_covered": row.target_doc_covered,
            "target_min_retrieval_rank": row.target_min_retrieval_rank,
            "target_min_pack_rank": row.target_min_pack_rank,
            "citation_recoverability": row.citation_recoverability,
            "evidence_order_relevance_proxy": row.evidence_order_relevance_proxy,
            "duplicate_parent_rate": row.duplicate_parent_rate,
            "duplicate_doc_rate": row.duplicate_doc_rate,
            "query_rewrite_changed": row.query_rewrite_changed,
            "query_rewrite_applied_rule_count": row.query_rewrite_applied_rule_count,
            "generation_correctness_regression": row.generation_correctness_regression,
            "generation_unsupported_regression": row.generation_unsupported_regression,
            "generation_citation_precision_delta": row.generation_citation_precision_delta,
            "generation_citation_recall_delta": row.generation_citation_recall_delta,
            "generation_citation_count_delta": row.generation_citation_count_delta,
            "root_cause_decision": row.root_cause_decision,
            "diagnostic_tags": list(row.diagnostic_tags),
        }
        for row in report.diagnostic_rows
    ]


def collect_place_story_hard_case_analysis_failures(
    report: PlaceStoryHardCaseAnalysisReport,
) -> list[str]:
    failures: list[str] = []
    if report.summary.analyzed_query_count == 0:
        failures.append("empty_place_story_analysis")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_place_story_hard_case_analysis_markdown(
    report: PlaceStoryHardCaseAnalysisReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    diagnostic_rows = "\n".join(
        _format_diagnostic_row(row) for row in report.diagnostic_rows
    )
    distribution_rows = "\n".join(
        f"| {decision} | {count} |"
        for decision, count in report.root_cause_distribution.items()
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Place Story Hard-case Analysis Report

## 목적

`q-dev-place-story-001` 실패가 청킹 문제인지, retrieval/evidence packing 문제인지, generation contract 문제인지 분리한다.

이 문서는 추가 Solar Pro 3 호출 결과가 아니다. private retrieval dataset, private chunk artifact, 기존 generation comparison metric row를 사용하되 raw query, raw answer, evidence text, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| analysis_id | `{report.analysis_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| generation_rows | `{report.generation_rows_alias}` |
| source_fingerprint | `{report.source_fingerprint}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| analyzed_query_count | {summary.analyzed_query_count} |
| target_child_covered_count | {summary.target_child_covered_count} |
| target_parent_covered_count | {summary.target_parent_covered_count} |
| target_doc_covered_count | {summary.target_doc_covered_count} |
| generation_regression_count | {summary.generation_regression_count} |
| retrieval_or_packing_miss_count | {summary.retrieval_or_packing_miss_count} |
| root_cause_decision | `{summary.root_cause_decision}` |

## Root Cause Distribution

| root_cause_decision | count |
| --- | ---: |
{distribution_rows}

## Query Diagnostic Rows

| query_id | query_type | method | candidates | packed | child | parent | doc | target retrieval rank | target pack rank | citation recoverability | order proxy | duplicate parent | duplicate doc | rewrite | generation regression | root cause | tags |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
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

{_conclusion_text(summary.root_cause_decision)}
"""


def build_qualitative_assessment(
    report: PlaceStoryHardCaseAnalysisReport,
) -> dict[str, str]:
    decision = report.summary.root_cause_decision
    return {
        "root_cause": _root_cause_text(decision),
        "chunking_decision": _chunking_decision_text(decision),
        "generation_decision": _generation_decision_text(decision),
        "data_boundary": (
            "public report에는 metric, rank, boolean, tag만 남기며 raw query/answer/evidence/chunk text는 포함하지 않는다."
        ),
        "next_action": _next_action(decision),
    }


def _load_target_item(*, dataset_path: Path, query_id: str) -> RetrievalEvalItem:
    items = load_retrieval_eval_jsonl(project_path(dataset_path))
    for item in items:
        if item.query.query_id == query_id:
            return item
    raise ValueError(f"target query_id not found: {query_id}")


def _load_generation_row(
    *,
    generation_rows_path: Path,
    query_id: str,
) -> SolarGenerationV2PairedMetricRow | None:
    resolved = project_path(generation_rows_path)
    if not resolved.exists():
        return None
    for line in resolved.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = SolarGenerationV2PairedMetricRow.model_validate(json.loads(line))
        if row.query_id == query_id:
            return row
    return None


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


def _min_retrieval_rank(
    *,
    evidence_pack: EvidencePack,
    child_ids: set[str],
    parent_ids: set[str],
    doc_ids: set[str],
) -> int | None:
    ranks = [
        evidence.source_rank
        for evidence in evidence_pack.evidence
        if _matches_target(
            child_id=evidence.child_id,
            parent_id=evidence.parent_id,
            doc_id=evidence.doc_id,
            child_ids=child_ids,
            parent_ids=parent_ids,
            doc_ids=doc_ids,
        )
    ]
    return min(ranks) if ranks else None


def _min_pack_rank(
    *,
    evidence_pack: EvidencePack,
    child_ids: set[str],
    parent_ids: set[str],
    doc_ids: set[str],
) -> int | None:
    ranks = [
        evidence.pack_rank
        for evidence in evidence_pack.evidence
        if _matches_target(
            child_id=evidence.child_id,
            parent_id=evidence.parent_id,
            doc_id=evidence.doc_id,
            child_ids=child_ids,
            parent_ids=parent_ids,
            doc_ids=doc_ids,
        )
    ]
    return min(ranks) if ranks else None


def _matches_target(
    *,
    child_id: str,
    parent_id: str,
    doc_id: str,
    child_ids: set[str],
    parent_ids: set[str],
    doc_ids: set[str],
) -> bool:
    return child_id in child_ids or parent_id in parent_ids or doc_id in doc_ids


def _root_cause_decision(
    *,
    evidence_pack: EvidencePack,
    generation_correctness_regression: bool,
    generation_unsupported_regression: bool,
) -> RootCauseDecision:
    if (
        evidence_pack.target_child_covered
        and evidence_pack.target_parent_covered
        and evidence_pack.target_doc_covered
        and (generation_correctness_regression or generation_unsupported_regression)
    ):
        return "generation_contract_candidate"
    if not (
        evidence_pack.target_child_covered
        or evidence_pack.target_parent_covered
        or evidence_pack.target_doc_covered
    ):
        return "retrieval_or_packing_miss"
    if not evidence_pack.target_child_covered and (
        evidence_pack.target_parent_covered or evidence_pack.target_doc_covered
    ):
        return "target_grain_mismatch"
    return "monitor_only"


def _diagnostic_tags(
    *,
    evidence_pack: EvidencePack,
    target_min_retrieval_rank: int | None,
    target_min_pack_rank: int | None,
    query_rewrite_changed: bool,
    generation_correctness_regression: bool,
    generation_unsupported_regression: bool,
    generation_row: SolarGenerationV2PairedMetricRow | None,
) -> list[str]:
    tags: list[str] = []
    if evidence_pack.target_child_covered:
        tags.append("target_child_in_pack")
    if evidence_pack.target_parent_covered:
        tags.append("target_parent_in_pack")
    if evidence_pack.target_doc_covered:
        tags.append("target_doc_in_pack")
    if target_min_retrieval_rank is not None:
        tags.append(f"target_retrieval_rank_{target_min_retrieval_rank}")
    if target_min_pack_rank is not None:
        tags.append(f"target_pack_rank_{target_min_pack_rank}")
    if evidence_pack.citation_recoverability >= 1.0:
        tags.append("citation_recoverable")
    if query_rewrite_changed:
        tags.append("query_rewrite_changed")
    else:
        tags.append("query_rewrite_not_changed")
    if generation_correctness_regression:
        tags.append("generation_correctness_regression")
    if generation_unsupported_regression:
        tags.append("generation_unsupported_regression")
    if generation_row and generation_row.citation_count_delta < 0:
        tags.append("v2_citation_count_reduction")
    if generation_row and generation_row.citation_precision_delta < 0:
        tags.append("v2_precision_regression")
    if generation_row and generation_row.citation_recall_delta < 0:
        tags.append("v2_recall_regression")
    if not tags:
        tags.append("no_diagnostic_signal")
    return tags


def _next_action(decision: RootCauseDecision) -> str:
    if decision == "generation_contract_candidate":
        return "v2 selected evidence prompt repair 계획을 작성한다."
    if decision == "retrieval_or_packing_miss":
        return "retrieval candidate와 evidence packing 정책을 먼저 재검토한다."
    if decision == "target_grain_mismatch":
        return "judgment target grain과 parent-child chunk boundary를 점검한다."
    return "monitoring case로 유지하고 추가 live 호출은 보류한다."


def _root_cause_text(decision: RootCauseDecision) -> str:
    if decision == "generation_contract_candidate":
        return "retrieval/evidence pack은 target을 포함했지만 v2 generation에서 regression이 발생했다."
    if decision == "retrieval_or_packing_miss":
        return "target evidence가 pack에 들어오지 않아 retrieval 또는 packing 문제가 우선이다."
    if decision == "target_grain_mismatch":
        return "doc-level target은 들어왔지만 child/parent target이 빠져 judgment grain 점검이 필요하다."
    return "명확한 blocker는 아니며 추가 관찰 대상으로 둔다."


def _chunking_decision_text(decision: RootCauseDecision) -> str:
    if decision == "target_grain_mismatch":
        return "청킹 전체 재실험보다 judgment target grain과 top-rank retrieval coverage를 먼저 점검한다."
    if decision == "retrieval_or_packing_miss":
        return "retrieval 또는 packing miss가 우선이므로 청킹 후보 재검토는 그 다음이다."
    return "현재 분석 결과만으로는 청킹 재실험을 우선순위로 둘 근거가 부족하다."


def _generation_decision_text(decision: RootCauseDecision) -> str:
    if decision == "generation_contract_candidate":
        return "target evidence가 pack에 포함된 상태에서 v2 generation regression이 확인되어 prompt/schema repair가 우선이다."
    if decision == "target_grain_mismatch":
        return "v2 generation regression은 확인됐지만 target child/parent가 pack에 없어 prompt repair만으로 해결된다고 단정할 수 없다."
    if decision == "retrieval_or_packing_miss":
        return "generation contract 수정 전에 retrieval/evidence pack 입력 품질을 먼저 회복해야 한다."
    return "generation regression monitor로 유지한다."


def _conclusion_text(decision: RootCauseDecision) -> str:
    if decision == "target_grain_mismatch":
        return (
            "현재 증거만 보면 `place_story` 실패를 청킹 문제나 generation 문제 하나로 단정할 수 없다.\n\n"
            "target doc은 pack에 들어왔지만 target child/parent는 빠졌고, target doc도 rank 5에 위치했다. 따라서 다음 작업은 전체 청킹 재실험이 아니라 judgment target grain, retrieval top-rank coverage, v2 selected evidence prompt를 순서대로 분리하는 것이다."
        )
    if decision == "generation_contract_candidate":
        return (
            "target evidence가 retrieval/evidence pack에 들어왔는데 generation v2에서 correctness와 unsupported claim이 악화됐다. 다음 작업은 청킹 재실험이 아니라 v2 selected evidence prompt repair다."
        )
    if decision == "retrieval_or_packing_miss":
        return (
            "target evidence가 pack에 들어오지 않았다. 다음 작업은 generation prompt 수정이 아니라 retrieval/evidence packing 원인 분석이다."
        )
    return "현재 query는 monitor case다. 추가 live 호출 없이 다음 hard-case를 더 모은 뒤 판단한다."


def _format_diagnostic_row(row: PlaceStoryHardCaseDiagnosticRow) -> str:
    tags = ", ".join(row.diagnostic_tags)
    generation_regression = (
        row.generation_correctness_regression or row.generation_unsupported_regression
    )
    rewrite = "yes" if row.query_rewrite_changed else "no"
    return (
        f"| {row.query_id} | {row.query_type} | {row.retrieval_method} | "
        f"{row.retrieval_candidate_count} | {row.packed_evidence_count} | "
        f"{_bool_cell(row.target_child_covered)} | "
        f"{_bool_cell(row.target_parent_covered)} | "
        f"{_bool_cell(row.target_doc_covered)} | "
        f"{_int_or_na(row.target_min_retrieval_rank)} | "
        f"{_int_or_na(row.target_min_pack_rank)} | "
        f"{row.citation_recoverability:.6f} | "
        f"{row.evidence_order_relevance_proxy:.6f} | "
        f"{row.duplicate_parent_rate:.6f} | "
        f"{row.duplicate_doc_rate:.6f} | "
        f"{rewrite} | {_bool_cell(generation_regression)} | "
        f"{row.root_cause_decision} | {tags} |"
    )


def _bool_cell(value: bool) -> str:
    return "1" if value else "0"


def _int_or_na(value: int | None) -> str:
    return "NA" if value is None else str(value)


def _analysis_id(rows: tuple[PlaceStoryHardCaseDiagnosticRow, ...]) -> str:
    digest = _stable_digest([row.model_dump(mode="json") for row in rows])[:8]
    return f"place-story-hard-case-q{len(rows)}-{digest}"


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()


def _validate_private_rows_path(path: Path, *, label: str) -> None:
    if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
        raise ValueError(f"{label} rows must stay under repository private_data")
    if has_private_data_segment(path) and not is_repository_private_write_path(path):
        raise ValueError(f"{label} rows must stay under repository private_data")


def main() -> int:
    args = _parse_args()
    report = run_place_story_hard_case_analysis(
        query_id=args.query_id,
        dataset_path=args.dataset,
        chunks_path=args.chunks,
        generation_rows_path=args.generation_rows,
        report_path=args.report,
        result_rows_path=args.result_rows,
    )
    failures = collect_place_story_hard_case_analysis_failures(report)
    print(
        "place_story_hard_case_analysis "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"query_count={report.summary.analyzed_query_count} "
        f"root_cause={report.summary.root_cause_decision} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze place_story retrieval/generation hard-case boundary.",
    )
    parser.add_argument("--query-id", default=DEFAULT_QUERY_ID)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--generation-rows", type=Path, default=DEFAULT_LIVE_COMPARISON_ROWS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
