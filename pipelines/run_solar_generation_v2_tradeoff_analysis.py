from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
    is_repository_private_write_path,
    project_path,
)
from app.domain.retrieval import QueryType
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from pipelines.run_solar_generation_contract_v2_live_comparison import (
    DEFAULT_RESULT_ROWS_PATH as DEFAULT_LIVE_COMPARISON_ROWS_PATH,
)
from pipelines.run_solar_live_generation_smoke import write_jsonl_rows


SOLAR_GENERATION_V2_TRADEOFF_ANALYSIS_REPORT_VERSION = (
    "solar-generation-v2-tradeoff-analysis-report/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "solar_generation_v2_tradeoff_analysis_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_generation_v2_tradeoff_analysis_rows.jsonl"
)

FailureSurface = Literal[
    "generation_contract_candidate",
    "citation_selection",
    "latency_cost",
    "no_regression",
]
AdoptionDecision = Literal["reject_default_contract", "continue_experiment", "eligible"]


class SolarGenerationV2TradeoffModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SolarGenerationV2PairedMetricRow(SolarGenerationV2TradeoffModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    baseline_answer_policy_id: str = Field(min_length=1)
    candidate_answer_policy_id: str = Field(min_length=1)
    v1_correct_with_evidence: bool
    v2_correct_with_evidence: bool
    correct_with_evidence_delta: int
    v1_citation_precision: float = Field(ge=0.0, le=1.0)
    v2_citation_precision: float = Field(ge=0.0, le=1.0)
    citation_precision_delta: float
    v1_citation_recall: float = Field(ge=0.0, le=1.0)
    v2_citation_recall: float = Field(ge=0.0, le=1.0)
    citation_recall_delta: float
    unsupported_claim_delta: int
    v1_citation_count: int = Field(ge=0)
    v2_citation_count: int = Field(ge=0)
    citation_count_delta: int
    latency_ms_delta: float


class SolarGenerationV2TradeoffDiagnosticRow(SolarGenerationV2TradeoffModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    failure_surface: FailureSurface
    diagnostic_tags: tuple[str, ...]
    adoption_blocker: bool
    primary_interpretation: str = Field(min_length=1)
    next_action: str = Field(min_length=1)
    correct_with_evidence_delta: int
    citation_precision_delta: float
    citation_recall_delta: float
    unsupported_claim_delta: int
    citation_count_delta: int
    latency_ms_delta: float


class SolarGenerationV2TradeoffSummary(SolarGenerationV2TradeoffModel):
    row_count: int = Field(ge=0)
    answerable_row_count: int = Field(ge=0)
    precision_gain_count: int = Field(ge=0)
    precision_regression_count: int = Field(ge=0)
    recall_regression_count: int = Field(ge=0)
    correctness_regression_count: int = Field(ge=0)
    unsupported_regression_count: int = Field(ge=0)
    citation_count_reduction_count: int = Field(ge=0)
    adoption_blocker_count: int = Field(ge=0)
    mean_citation_count_delta: float
    mean_latency_ms_delta: float
    adoption_decision: AdoptionDecision


class SolarGenerationV2TradeoffAnalysisReport(SolarGenerationV2TradeoffModel):
    report_version: str = SOLAR_GENERATION_V2_TRADEOFF_ANALYSIS_REPORT_VERSION
    analysis_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    source_result_rows_alias: str = Field(min_length=1)
    source_rows_fingerprint: str = Field(min_length=8)
    summary: SolarGenerationV2TradeoffSummary
    diagnostic_rows: tuple[SolarGenerationV2TradeoffDiagnosticRow, ...]
    failure_surface_distribution: dict[str, int]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_solar_generation_v2_tradeoff_analysis(
    *,
    source_rows_path: Path = DEFAULT_LIVE_COMPARISON_ROWS_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> SolarGenerationV2TradeoffAnalysisReport:
    _validate_private_rows_path(source_rows_path, label="source")
    _validate_private_rows_path(result_rows_path, label="result")
    source_rows = load_live_comparison_rows(source_rows_path)
    provisional_report = build_solar_generation_v2_tradeoff_analysis_report(
        source_rows=source_rows,
        source_rows_path=source_rows_path,
    )
    provisional_markdown = build_solar_generation_v2_tradeoff_analysis_markdown(
        provisional_report,
    )
    report = build_solar_generation_v2_tradeoff_analysis_report(
        source_rows=source_rows,
        source_rows_path=source_rows_path,
        report_text=provisional_markdown,
    )
    failures = collect_solar_generation_v2_tradeoff_analysis_failures(report)
    if failures:
        raise ValueError(f"solar generation v2 tradeoff analysis gate failed: {failures}")

    rows = build_public_solar_generation_v2_tradeoff_rows(report)
    write_jsonl_rows(path=result_rows_path, rows=rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_solar_generation_v2_tradeoff_analysis_markdown(report),
        encoding="utf-8",
    )
    return report


def load_live_comparison_rows(path: Path) -> list[SolarGenerationV2PairedMetricRow]:
    resolved = project_path(path)
    if not resolved.exists():
        raise ValueError("live comparison result rows are required")
    rows = [
        SolarGenerationV2PairedMetricRow.model_validate(json.loads(line))
        for line in resolved.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError("live comparison result rows must not be empty")
    return rows


def build_solar_generation_v2_tradeoff_analysis_report(
    *,
    source_rows: list[SolarGenerationV2PairedMetricRow],
    source_rows_path: Path,
    report_text: str = "",
) -> SolarGenerationV2TradeoffAnalysisReport:
    diagnostics = tuple(
        build_solar_generation_v2_tradeoff_diagnostic_row(row) for row in source_rows
    )
    public_rows = [
        diagnostic.model_dump(mode="json") for diagnostic in diagnostics
    ]
    analysis_id = build_solar_generation_v2_tradeoff_analysis_id(diagnostics)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_GENERATION_V2_TRADEOFF_ANALYSIS_REPORT_VERSION,
        run_id=analysis_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    report = SolarGenerationV2TradeoffAnalysisReport(
        analysis_id=analysis_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        source_result_rows_alias="<private solar_generation_contract_v2_live_comparison_results.jsonl>",
        source_rows_fingerprint=_stable_digest(
            [row.model_dump(mode="json") for row in source_rows],
        )[:16],
        summary=build_tradeoff_summary(diagnostics),
        diagnostic_rows=diagnostics,
        failure_surface_distribution=dict(
            sorted(Counter(row.failure_surface for row in diagnostics).items()),
        ),
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_tradeoff_qualitative_assessment(report),
        },
    )


def build_solar_generation_v2_tradeoff_diagnostic_row(
    row: SolarGenerationV2PairedMetricRow,
) -> SolarGenerationV2TradeoffDiagnosticRow:
    tags = _diagnostic_tags(row)
    adoption_blocker = bool(
        set(tags)
        & {
            "correctness_regression",
            "unsupported_claim_regression",
            "no_answer_regression",
        },
    )
    return SolarGenerationV2TradeoffDiagnosticRow(
        query_id=row.query_id,
        query_type=row.query_type,
        failure_surface=_failure_surface(tags),
        diagnostic_tags=tuple(tags),
        adoption_blocker=adoption_blocker,
        primary_interpretation=_primary_interpretation(row=row, tags=tags),
        next_action=_next_action(row=row, tags=tags),
        correct_with_evidence_delta=row.correct_with_evidence_delta,
        citation_precision_delta=row.citation_precision_delta,
        citation_recall_delta=row.citation_recall_delta,
        unsupported_claim_delta=row.unsupported_claim_delta,
        citation_count_delta=row.citation_count_delta,
        latency_ms_delta=row.latency_ms_delta,
    )


def build_tradeoff_summary(
    diagnostics: tuple[SolarGenerationV2TradeoffDiagnosticRow, ...],
) -> SolarGenerationV2TradeoffSummary:
    answerable_rows = [row for row in diagnostics if row.query_type != "no_answer"]
    adoption_blocker_count = sum(1 for row in diagnostics if row.adoption_blocker)
    return SolarGenerationV2TradeoffSummary(
        row_count=len(diagnostics),
        answerable_row_count=len(answerable_rows),
        precision_gain_count=sum(
            1 for row in answerable_rows if row.citation_precision_delta > 0
        ),
        precision_regression_count=sum(
            1 for row in answerable_rows if row.citation_precision_delta < 0
        ),
        recall_regression_count=sum(
            1 for row in answerable_rows if row.citation_recall_delta < 0
        ),
        correctness_regression_count=sum(
            1 for row in answerable_rows if row.correct_with_evidence_delta < 0
        ),
        unsupported_regression_count=sum(
            1 for row in diagnostics if row.unsupported_claim_delta > 0
        ),
        citation_count_reduction_count=sum(
            1 for row in answerable_rows if row.citation_count_delta < 0
        ),
        adoption_blocker_count=adoption_blocker_count,
        mean_citation_count_delta=_mean(
            [float(row.citation_count_delta) for row in answerable_rows],
        ),
        mean_latency_ms_delta=_mean([row.latency_ms_delta for row in diagnostics]),
        adoption_decision=_adoption_decision(adoption_blocker_count),
    )


def build_public_solar_generation_v2_tradeoff_rows(
    report: SolarGenerationV2TradeoffAnalysisReport,
) -> list[dict[str, Any]]:
    return [
        {
            "analysis_id": report.analysis_id,
            "query_id": row.query_id,
            "query_type": row.query_type,
            "failure_surface": row.failure_surface,
            "diagnostic_tags": list(row.diagnostic_tags),
            "adoption_blocker": row.adoption_blocker,
            "correct_with_evidence_delta": row.correct_with_evidence_delta,
            "citation_precision_delta": row.citation_precision_delta,
            "citation_recall_delta": row.citation_recall_delta,
            "unsupported_claim_delta": row.unsupported_claim_delta,
            "citation_count_delta": row.citation_count_delta,
            "latency_ms_delta": row.latency_ms_delta,
        }
        for row in report.diagnostic_rows
    ]


def collect_solar_generation_v2_tradeoff_analysis_failures(
    report: SolarGenerationV2TradeoffAnalysisReport,
) -> list[str]:
    failures: list[str] = []
    if report.summary.row_count == 0:
        failures.append("empty_tradeoff_analysis")
    if report.summary.answerable_row_count == 0:
        failures.append("answerable_rows_missing")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_solar_generation_v2_tradeoff_analysis_markdown(
    report: SolarGenerationV2TradeoffAnalysisReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    diagnostic_rows = "\n".join(
        _format_diagnostic_row(row) for row in report.diagnostic_rows
    )
    distribution_rows = "\n".join(
        f"| {surface} | {count} |"
        for surface, count in report.failure_surface_distribution.items()
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Solar Pro 3 Generation v2 Trade-off Analysis Report

## 목적

Solar Pro 3 generation contract v2 live paired comparison 결과를 query 단위로 진단해 v2를 기본 contract로 채택할지 판단한다.

이 문서는 추가 Solar Pro 3 호출 결과가 아니다. 기존 live paired comparison의 private metric rows를 분석하며 raw query, raw answer, evidence text, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| analysis_id | `{report.analysis_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| source_result_rows | `{report.source_result_rows_alias}` |
| source_rows_fingerprint | `{report.source_rows_fingerprint}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| row_count | {summary.row_count} |
| answerable_row_count | {summary.answerable_row_count} |
| precision_gain_count | {summary.precision_gain_count} |
| precision_regression_count | {summary.precision_regression_count} |
| recall_regression_count | {summary.recall_regression_count} |
| correctness_regression_count | {summary.correctness_regression_count} |
| unsupported_regression_count | {summary.unsupported_regression_count} |
| citation_count_reduction_count | {summary.citation_count_reduction_count} |
| adoption_blocker_count | {summary.adoption_blocker_count} |
| mean_citation_count_delta | {summary.mean_citation_count_delta:.6f} |
| mean_latency_ms_delta | {summary.mean_latency_ms_delta:.6f} |
| adoption_decision | `{summary.adoption_decision}` |

## Failure Surface Distribution

| failure_surface | count |
| --- | ---: |
{distribution_rows}

## Query Diagnostic Rows

| query_id | query_type | failure_surface | tags | blocker | Correct delta | precision delta | recall delta | unsupported delta | citation count delta | latency delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
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

v2는 citation 수를 줄여 precision을 올린 positive case가 있지만, answerable query 중 correctness와 unsupported claim regression이 발생했다. 따라서 현재 v2는 기본 generation contract로 채택하지 않는다.

다음 실험은 청킹 재실험이 아니라 `place_story` hard-case와 selected evidence prompt repair를 분리해서 진행한다.
"""


def build_tradeoff_qualitative_assessment(
    report: SolarGenerationV2TradeoffAnalysisReport,
) -> dict[str, str]:
    summary = report.summary
    return {
        "decision": (
            "v2는 현재 기본 generation contract로 채택하지 않는다."
            if summary.adoption_decision == "reject_default_contract"
            else "v2는 추가 실험 후보로만 유지한다."
        ),
        "primary_tradeoff": (
            "selected evidence contract가 citation count를 줄여 precision은 올렸지만, 일부 query에서 근거 충족률과 unsupported claim이 악화됐다."
        ),
        "portfolio_message": (
            "기법을 적용한 뒤 무조건 채택하지 않고, paired metric으로 채택 보류 판단을 내린 점을 강조한다."
        ),
        "data_boundary": (
            "이 분석은 query-level metric과 tag만 public에 남기며 raw answer/evidence/chunk text는 포함하지 않는다."
        ),
        "next_experiment": (
            "`place_story` retrieval hard-case와 v2 selected evidence prompt repair를 분리한다."
        ),
    }


def _diagnostic_tags(row: SolarGenerationV2PairedMetricRow) -> list[str]:
    tags: list[str] = []
    if row.query_type == "no_answer" and (
        row.unsupported_claim_delta > 0 or row.citation_count_delta != 0
    ):
        tags.append("no_answer_regression")
    if row.correct_with_evidence_delta < 0:
        tags.append("correctness_regression")
    if row.unsupported_claim_delta > 0:
        tags.append("unsupported_claim_regression")
    if row.citation_precision_delta > 0:
        tags.append("precision_gain")
    if row.citation_precision_delta < 0:
        tags.append("precision_regression")
    if row.citation_recall_delta < 0:
        tags.append("recall_regression")
    if row.citation_count_delta < 0:
        tags.append("citation_count_reduction")
    if row.citation_count_delta <= -3 and (
        row.citation_recall_delta < 0 or row.correct_with_evidence_delta < 0
    ):
        tags.append("evidence_over_pruning_risk")
    if row.latency_ms_delta < 0:
        tags.append("latency_improvement")
    if row.latency_ms_delta > 0:
        tags.append("latency_regression")
    if not tags:
        tags.append("no_metric_change")
    return tags


def _failure_surface(tags: list[str]) -> FailureSurface:
    if "correctness_regression" in tags or "unsupported_claim_regression" in tags:
        return "generation_contract_candidate"
    if (
        "precision_regression" in tags
        or "recall_regression" in tags
        or "evidence_over_pruning_risk" in tags
    ):
        return "citation_selection"
    if "latency_regression" in tags:
        return "latency_cost"
    return "no_regression"


def _primary_interpretation(
    *,
    row: SolarGenerationV2PairedMetricRow,
    tags: list[str],
) -> str:
    if "correctness_regression" in tags or "unsupported_claim_regression" in tags:
        return "v2 selected evidence contract가 답변 근거 충족률을 떨어뜨린 blocker case다."
    if "precision_gain" in tags and "recall_regression" not in tags:
        return "v2가 citation 수를 줄이면서 precision을 개선했고 correctness는 유지했다."
    if "precision_regression" in tags:
        return "v2 evidence 선택이 target coverage보다 distractor 선택에 가까운 regression case다."
    if row.query_type == "no_answer":
        return "no-answer abstain path는 provider 호출 없이 유지됐다."
    return "v2가 correctness는 유지했지만 coverage 또는 latency trade-off를 추가 확인해야 한다."


def _next_action(
    *,
    row: SolarGenerationV2PairedMetricRow,
    tags: list[str],
) -> str:
    if row.query_type == "place_story":
        return "retrieval hard-case와 v2 prompt failure를 분리해 private raw review를 수행한다."
    if "correctness_regression" in tags or "unsupported_claim_regression" in tags:
        return "v2 prompt에 선택 근거 최소 coverage와 unsupported claim guard를 추가한다."
    if "precision_regression" in tags:
        return "selected rank 기준과 voice/query-type별 evidence 선택 규칙을 보정한다."
    if "recall_regression" in tags:
        return "multi-evidence query에서 최소 evidence rank 수를 늘리는 후보를 검토한다."
    if "precision_gain" in tags:
        return "positive case로 유지하되 locked test 전 최종 개선 주장에는 사용하지 않는다."
    return "regression monitoring case로 유지한다."


def _adoption_decision(adoption_blocker_count: int) -> AdoptionDecision:
    if adoption_blocker_count:
        return "reject_default_contract"
    return "eligible"


def _format_diagnostic_row(row: SolarGenerationV2TradeoffDiagnosticRow) -> str:
    tags = ", ".join(row.diagnostic_tags)
    return (
        f"| {row.query_id} | {row.query_type} | {row.failure_surface} | "
        f"{tags} | {str(row.adoption_blocker).lower()} | "
        f"{row.correct_with_evidence_delta} | "
        f"{row.citation_precision_delta:.6f} | "
        f"{row.citation_recall_delta:.6f} | "
        f"{row.unsupported_claim_delta} | "
        f"{row.citation_count_delta} | "
        f"{row.latency_ms_delta:.6f} |"
    )


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _validate_private_rows_path(path: Path, *, label: str) -> None:
    if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
        raise ValueError(f"{label} rows must stay under repository private_data")
    if has_private_data_segment(path) and not is_repository_private_write_path(path):
        raise ValueError(f"{label} rows must stay under repository private_data")


def build_solar_generation_v2_tradeoff_analysis_id(
    diagnostics: tuple[SolarGenerationV2TradeoffDiagnosticRow, ...],
) -> str:
    digest = _stable_digest([row.model_dump(mode="json") for row in diagnostics])[:8]
    return f"solar-generation-v2-tradeoff-q{len(diagnostics)}-{digest}"


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()


def main() -> int:
    args = _parse_args()
    report = run_solar_generation_v2_tradeoff_analysis(
        source_rows_path=args.source_rows,
        report_path=args.report,
        result_rows_path=args.result_rows,
    )
    failures = collect_solar_generation_v2_tradeoff_analysis_failures(report)
    print(
        "solar_generation_v2_tradeoff_analysis "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"row_count={report.summary.row_count} "
        f"adoption_decision={report.summary.adoption_decision} "
        f"adoption_blocker_count={report.summary.adoption_blocker_count} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze Solar Pro 3 generation contract v2 trade-offs.",
    )
    parser.add_argument("--source-rows", type=Path, default=DEFAULT_LIVE_COMPARISON_ROWS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
