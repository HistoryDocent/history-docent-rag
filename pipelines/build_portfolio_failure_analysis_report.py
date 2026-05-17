from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.retrieval import QueryType
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)


PORTFOLIO_FAILURE_ANALYSIS_REPORT_VERSION = "portfolio-failure-analysis-report/v1"
DEFAULT_DOC_PATH = Path("docs/PORTFOLIO_FAILURE_ANALYSIS.md")
DEFAULT_REPORT_PATH = Path("evals/reports/portfolio_failure_analysis_report.md")
DEFAULT_RESULT_PATH = Path(
    "private_data/evals/results/portfolio_failure_analysis_rows.jsonl"
)

FailureCategory = Literal[
    "retrieval_miss",
    "chunk_boundary_risk",
    "query_type_misroute",
    "evidence_packing_gap",
    "generation_contract_gap",
    "parser_noise",
    "no_answer_risk",
]

RiskLevel = Literal["low", "medium", "high"]


class PortfolioFailureAnalysisModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PortfolioFailureCase(PortfolioFailureAnalysisModel):
    case_id: str = Field(min_length=1)
    query_id: str = Field(min_length=1)
    query_type: QueryType
    split_scope: str = Field(min_length=1)
    pipeline_stage: str = Field(min_length=1)
    primary_failure_category: FailureCategory
    risk_level: RiskLevel
    observed_signal: str = Field(min_length=1)
    decision_impact: str = Field(min_length=1)
    next_action: str = Field(min_length=1)
    source_artifact: str = Field(min_length=1)
    claim_boundary: str = Field(min_length=1)


class PortfolioFailureCategorySummary(PortfolioFailureAnalysisModel):
    primary_failure_category: FailureCategory
    count: int = Field(ge=0)


class PortfolioFailureStageSummary(PortfolioFailureAnalysisModel):
    pipeline_stage: str = Field(min_length=1)
    count: int = Field(ge=0)


class PortfolioFailureAnalysisSummary(PortfolioFailureAnalysisModel):
    case_count: int = Field(ge=0)
    unique_query_count: int = Field(ge=0)
    high_risk_count: int = Field(ge=0)
    medium_risk_count: int = Field(ge=0)
    low_risk_count: int = Field(ge=0)
    chunk_boundary_audit_candidate_count: int = Field(ge=0)
    query_type_misroute_count: int = Field(ge=0)
    retrieval_miss_count: int = Field(ge=0)
    generation_contract_gap_count: int = Field(ge=0)
    no_answer_risk_count: int = Field(ge=0)
    reopen_global_chunking_count: int = Field(ge=0)
    next_hyde_candidate_count: int = Field(ge=0)
    live_solar_call_count_for_this_report: int = Field(ge=0)
    cuda_required: bool = False


class PortfolioFailureAnalysisReport(PortfolioFailureAnalysisModel):
    report_version: str = PORTFOLIO_FAILURE_ANALYSIS_REPORT_VERSION
    run_id: str
    generated_at_utc: str
    work_id: str = "HD-PORTFOLIO-002"
    result_path: str
    summary: PortfolioFailureAnalysisSummary
    category_breakdown: tuple[PortfolioFailureCategorySummary, ...]
    stage_breakdown: tuple[PortfolioFailureStageSummary, ...]
    failure_cases: tuple[PortfolioFailureCase, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def build_portfolio_failure_analysis_report(
    *,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_path: Path = DEFAULT_RESULT_PATH,
) -> PortfolioFailureAnalysisReport:
    cases = _portfolio_failure_cases()
    result_rows = [case.model_dump(mode="json") for case in cases]
    run_id = _build_run_id(result_rows)
    write_public_retrieval_result_rows(path=result_path, rows=result_rows)

    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=PORTFOLIO_FAILURE_ANALYSIS_REPORT_VERSION,
        run_id=run_id,
        result_rows=result_rows,
        report_text="",
    )
    provisional = _build_report(
        cases=cases,
        result_path=result_path,
        run_id=run_id,
        output_quality=provisional_quality,
    )
    doc_text = build_portfolio_failure_analysis_doc(provisional)
    report_text = build_portfolio_failure_analysis_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=PORTFOLIO_FAILURE_ANALYSIS_REPORT_VERSION,
        run_id=run_id,
        result_rows=result_rows,
        report_text=report_text,
        extra_public_texts={
            f"doc:{line_number}": line
            for line_number, line in enumerate(doc_text.splitlines(), start=1)
        },
    )
    report = _build_report(
        cases=cases,
        result_path=result_path,
        run_id=run_id,
        output_quality=output_quality,
    )
    failures = collect_portfolio_failure_analysis_failures(report)
    if failures:
        raise ValueError(f"portfolio failure analysis gate failed: {failures}")

    doc_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(build_portfolio_failure_analysis_doc(report), encoding="utf-8")
    report_path.write_text(
        build_portfolio_failure_analysis_markdown(report),
        encoding="utf-8",
    )
    print(
        "portfolio_failure_analysis "
        "status=PASS "
        f"case_count={report.summary.case_count} "
        f"high_risk_count={report.summary.high_risk_count} "
        f"chunk_boundary_audit_candidate_count="
        f"{report.summary.chunk_boundary_audit_candidate_count} "
        f"reopen_global_chunking_count={report.summary.reopen_global_chunking_count} "
        f"live_solar_call_count={report.summary.live_solar_call_count_for_this_report}"
    )
    return report


def collect_portfolio_failure_analysis_failures(
    report: PortfolioFailureAnalysisReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    case_ids = [case.case_id for case in report.failure_cases]
    if summary.case_count != 10:
        failures.append("failure_case_count_mismatch")
    if len(case_ids) != len(set(case_ids)):
        failures.append("duplicate_case_id")
    if summary.unique_query_count != len({case.query_id for case in report.failure_cases}):
        failures.append("unique_query_count_mismatch")
    if any(not case.primary_failure_category for case in report.failure_cases):
        failures.append("missing_primary_failure_category")
    if any(not case.next_action for case in report.failure_cases):
        failures.append("missing_next_action")
    if summary.reopen_global_chunking_count:
        failures.append("global_chunking_reopen_detected")
    if summary.live_solar_call_count_for_this_report:
        failures.append("live_solar_call_detected")
    if summary.cuda_required:
        failures.append("unexpected_cuda_requirement")
    if summary.chunk_boundary_audit_candidate_count < 1:
        failures.append("missing_chunk_boundary_audit_candidate")
    return failures


def build_portfolio_failure_analysis_doc(
    report: PortfolioFailureAnalysisReport,
) -> str:
    summary = report.summary
    category_rows = "\n".join(
        _format_category_row(row) for row in report.category_breakdown
    )
    stage_rows = "\n".join(_format_stage_row(row) for row in report.stage_breakdown)
    case_rows = "\n".join(_format_failure_case_doc_row(case) for case in report.failure_cases)
    return f"""# Portfolio Failure Analysis

## 결론

전체 청킹 비교 테스트를 다시 열지 않는다.

현재 10개 실패 사례 중 전역 청킹 재설계가 필요한 증거는 없다. 다만 `chunk_boundary_risk` 1건은 targeted chunk audit 후보로 남긴다. 다음 개발 우선순위는 HyDE가 아니라 실패 원인별 후속 작업을 분리한 뒤, `overview`, `relationship`, `no_answer` 일부 subset에서만 비용성 실험을 여는 것이다.

이 문서는 public-safe failure analysis다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| case_count | {summary.case_count} |
| unique_query_count | {summary.unique_query_count} |
| high_risk_count | {summary.high_risk_count} |
| medium_risk_count | {summary.medium_risk_count} |
| low_risk_count | {summary.low_risk_count} |
| chunk_boundary_audit_candidate_count | {summary.chunk_boundary_audit_candidate_count} |
| query_type_misroute_count | {summary.query_type_misroute_count} |
| retrieval_miss_count | {summary.retrieval_miss_count} |
| generation_contract_gap_count | {summary.generation_contract_gap_count} |
| no_answer_risk_count | {summary.no_answer_risk_count} |
| reopen_global_chunking_count | {summary.reopen_global_chunking_count} |
| next_hyde_candidate_count | {summary.next_hyde_candidate_count} |
| live_solar_call_count_for_this_report | {summary.live_solar_call_count_for_this_report} |
| cuda_required | {str(summary.cuda_required).lower()} |

## Category Breakdown

| primary_failure_category | count |
| --- | ---: |
{category_rows}

## Stage Breakdown

| pipeline_stage | count |
| --- | ---: |
{stage_rows}

## Failure Cases

| case_id | query_id | query_type | stage | primary_failure_category | risk | observed_signal | next_action |
| --- | --- | --- | --- | --- | --- | --- | --- |
{case_rows}

## 판단

청킹은 `C0 current parent-child`를 유지한다. 실패 10건 중 청킹 자체가 원인으로 강하게 확인된 사례는 없다. `q-dev-place-story-001`은 target doc은 잡지만 child/parent grain을 놓치는 사례라 targeted audit 후보지만, 전역 청킹 변경 근거는 아니다.

Retrieval 실패는 `place_story`, `relationship`, `overview`, `route_context`에 분포한다. 이 문제는 청킹 후보를 다시 늘리는 것보다 query type route, HyDE subset, hard-case retrieval audit으로 분리해야 한다.

Generation 실패는 Solar Pro 3 repaired v2의 기본값 승격을 막는 근거다. citation precision 개선만으로 채택하지 않고 citation recall, correctness, unsupported claim risk를 같이 봐야 한다.

No-answer는 검색기 단독으로는 후보를 반환할 수 있으므로 retrieval metric과 answer abstain contract를 분리해서 봐야 한다.

## 다음 작업

| priority | work_id | 작업 | 이유 |
| ---: | --- | --- | --- |
| 1 | `HD-HYDE-001` | overview/relationship/no-answer subset HyDE 비교 | retrieval miss와 abstain risk가 남아 있지만 LLM 비용과 hallucination guard가 필요하다. |
| 2 | `HD-CHUNK-AUDIT-001` | place_story 1건 targeted chunk audit | 전역 재청킹이 아니라 child/parent grain 손실 여부만 확인한다. |
| 3 | `HD-API-ROUTER-003` | active routing 적용 판단 계획 | guard dry-run은 완료됐지만 active route 적용은 별도 gate가 필요하다. |

## Claim Boundary

허용 표현:

- 실패 10건을 public-safe 방식으로 분류했다.
- 현재 증거로는 전체 청킹 재실험보다 targeted audit이 적절하다.
- HyDE는 다음 비용성 실험 후보이며 아직 개선을 입증하지 않았다.

금지 표현:

- 청킹 문제가 해결됐다.
- HyDE로 성능이 개선됐다.
- locked test 최종 성능 개선을 입증했다.
- production route 품질을 검증했다.
"""


def build_portfolio_failure_analysis_markdown(
    report: PortfolioFailureAnalysisReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    category_rows = "\n".join(
        _format_category_row(row) for row in report.category_breakdown
    )
    stage_rows = "\n".join(_format_stage_row(row) for row in report.stage_breakdown)
    case_rows = "\n".join(_format_failure_case_report_row(case) for case in report.failure_cases)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Portfolio Failure Analysis Report

## 목적

`HD-PORTFOLIO-002`는 제출용 포트폴리오에서 설명 가능한 실패 사례 10개를 public-safe aggregate로 정리한다.

이 리포트는 실패 분석과 다음 실험 설계 근거다. 청킹 개선, retrieval 개선, generation 개선, locked test 개선, production 성능 검증 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| run_id | `{report.run_id}` |
| work_id | `{report.work_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| result_path | `{report.result_path}` |
| live_solar_call_count_for_this_report | {summary.live_solar_call_count_for_this_report} |
| cuda_required | {str(summary.cuda_required).lower()} |

## 정량 리포트

| metric | value |
| --- | ---: |
| case_count | {summary.case_count} |
| unique_query_count | {summary.unique_query_count} |
| high_risk_count | {summary.high_risk_count} |
| medium_risk_count | {summary.medium_risk_count} |
| low_risk_count | {summary.low_risk_count} |
| chunk_boundary_audit_candidate_count | {summary.chunk_boundary_audit_candidate_count} |
| query_type_misroute_count | {summary.query_type_misroute_count} |
| retrieval_miss_count | {summary.retrieval_miss_count} |
| generation_contract_gap_count | {summary.generation_contract_gap_count} |
| no_answer_risk_count | {summary.no_answer_risk_count} |
| reopen_global_chunking_count | {summary.reopen_global_chunking_count} |
| next_hyde_candidate_count | {summary.next_hyde_candidate_count} |

## Category Breakdown

| primary_failure_category | count |
| --- | ---: |
{category_rows}

## Stage Breakdown

| pipeline_stage | count |
| --- | ---: |
{stage_rows}

## Failure Cases

| case_id | query_id | query_type | split_scope | pipeline_stage | primary_failure_category | risk_level | claim_boundary |
| --- | --- | --- | --- | --- | --- | --- | --- |
{case_rows}

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

## 해석

실패 사례는 전역 청킹 재설계보다 stage별 후속 실험으로 나누는 것이 맞다. 청킹은 C0를 유지하고, 특정 `place_story` grain miss만 targeted audit으로 본다. HyDE는 다음 실험 후보지만 아직 개선 주장이 아니다.
"""


def _build_report(
    *,
    cases: tuple[PortfolioFailureCase, ...],
    result_path: Path,
    run_id: str,
    output_quality: PublicRetrievalArtifactQuality,
) -> PortfolioFailureAnalysisReport:
    summary = _build_summary(cases)
    return PortfolioFailureAnalysisReport(
        run_id=run_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        result_path=public_path_alias(result_path),
        summary=summary,
        category_breakdown=tuple(_build_category_breakdown(cases)),
        stage_breakdown=tuple(_build_stage_breakdown(cases)),
        failure_cases=cases,
        output_quality=output_quality,
        qualitative_assessment=_build_qualitative_assessment(
            summary=summary,
            output_quality=output_quality,
        ),
    )


def _build_summary(
    cases: tuple[PortfolioFailureCase, ...],
) -> PortfolioFailureAnalysisSummary:
    risk_counter = Counter(case.risk_level for case in cases)
    category_counter = Counter(case.primary_failure_category for case in cases)
    return PortfolioFailureAnalysisSummary(
        case_count=len(cases),
        unique_query_count=len({case.query_id for case in cases}),
        high_risk_count=risk_counter["high"],
        medium_risk_count=risk_counter["medium"],
        low_risk_count=risk_counter["low"],
        chunk_boundary_audit_candidate_count=category_counter["chunk_boundary_risk"],
        query_type_misroute_count=category_counter["query_type_misroute"],
        retrieval_miss_count=category_counter["retrieval_miss"],
        generation_contract_gap_count=category_counter["generation_contract_gap"],
        no_answer_risk_count=category_counter["no_answer_risk"],
        reopen_global_chunking_count=0,
        next_hyde_candidate_count=sum(
            1 for case in cases if "HyDE" in case.next_action
        ),
        live_solar_call_count_for_this_report=0,
        cuda_required=False,
    )


def _build_category_breakdown(
    cases: tuple[PortfolioFailureCase, ...],
) -> list[PortfolioFailureCategorySummary]:
    counter = Counter(case.primary_failure_category for case in cases)
    return [
        PortfolioFailureCategorySummary(
            primary_failure_category=category,
            count=count,
        )
        for category, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _build_stage_breakdown(
    cases: tuple[PortfolioFailureCase, ...],
) -> list[PortfolioFailureStageSummary]:
    counter = Counter(case.pipeline_stage for case in cases)
    return [
        PortfolioFailureStageSummary(pipeline_stage=stage, count=count)
        for stage, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _build_qualitative_assessment(
    *,
    summary: PortfolioFailureAnalysisSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> dict[str, str]:
    failures = collect_public_retrieval_artifact_failures(output_quality)
    return {
        "analysis_scope": "기존 public-safe report와 query id 단위 결과만 사용해 실패 원인을 분류했다.",
        "chunking_decision": (
            "전역 청킹 재실험은 열지 않는다. chunk boundary 의심 1건은 targeted audit으로만 다룬다."
        ),
        "retrieval_decision": (
            f"retrieval miss {summary.retrieval_miss_count}건은 HyDE 또는 route-specific retrieval 후보로 분리한다."
        ),
        "generation_decision": (
            "generation contract gap은 Solar Pro 3 repaired v2 기본값 기각 근거로 유지한다."
        ),
        "no_answer_decision": (
            "no-answer risk는 retriever 단독 문제가 아니라 answer abstain contract와 함께 검증한다."
        ),
        "security_boundary": "case row에는 query id, category, metric signal, next action만 남긴다.",
        "execution_boundary": "이번 리포트는 Solar Pro 3 호출과 CUDA 연산을 사용하지 않는다.",
        "data_mart_grain": "fact_portfolio_failure_case grain은 run_id + case_id + query_id다.",
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
        "external_audit": "실패 분석은 개선 입증이 아니며 다음 실험의 범위를 줄이는 용도다.",
    }


def _portfolio_failure_cases() -> tuple[PortfolioFailureCase, ...]:
    return (
        PortfolioFailureCase(
            case_id="pf-failure-001",
            query_id="q-dev-place-fact-004",
            query_type="place_fact",
            split_scope="dev-only",
            pipeline_stage="query_type_classifier",
            primary_failure_category="query_type_misroute",
            risk_level="medium",
            observed_signal="place_fact가 relationship으로 분류되어 route policy가 바뀐 사례",
            decision_impact="active routing 적용 전 relationship guard가 필요하다.",
            next_action="active route 적용 전 guarded route dry-run 결과를 더 누적한다.",
            source_artifact="evals/reports/query_type_classifier_failure_analysis_report.md",
            claim_boundary="dev-only",
        ),
        PortfolioFailureCase(
            case_id="pf-failure-002",
            query_id="q-dev-overview-009",
            query_type="overview",
            split_scope="dev-only",
            pipeline_stage="query_type_classifier",
            primary_failure_category="query_type_misroute",
            risk_level="medium",
            observed_signal="overview가 relationship으로 분류되어 hybrid route로 이동할 수 있는 사례",
            decision_impact="classifier score만으로 route를 바꾸면 false hybrid route가 생긴다.",
            next_action="relationship route는 score margin과 관계 표현 guard를 함께 요구한다.",
            source_artifact="evals/reports/query_type_classifier_failure_analysis_report.md",
            claim_boundary="dev-only",
        ),
        PortfolioFailureCase(
            case_id="pf-failure-003",
            query_id="q-dev-place-fact-009",
            query_type="place_fact",
            split_scope="dev-only",
            pipeline_stage="query_type_classifier",
            primary_failure_category="query_type_misroute",
            risk_level="low",
            observed_signal="default route 내부 query type 경계가 흐린 사례",
            decision_impact="retrieval route는 유지되지만 포트폴리오 설명에서는 classifier 한계를 밝혀야 한다.",
            next_action="classifier label 개선은 active route보다 후순위로 둔다.",
            source_artifact="evals/reports/query_type_classifier_failure_analysis_report.md",
            claim_boundary="dev-only",
        ),
        PortfolioFailureCase(
            case_id="pf-failure-004",
            query_id="q-dev-place-story-001",
            query_type="place_story",
            split_scope="dev-only",
            pipeline_stage="chunking_retrieval_generation",
            primary_failure_category="chunk_boundary_risk",
            risk_level="high",
            observed_signal="target doc은 잡지만 target child와 parent grain이 빠지고 generation regression도 동반된 사례",
            decision_impact="전역 재청킹 근거는 아니지만 targeted chunk audit 후보로 남긴다.",
            next_action="HD-CHUNK-AUDIT-001에서 child/parent grain 손실만 별도 점검한다.",
            source_artifact="evals/reports/place_story_hard_case_analysis_report.md",
            claim_boundary="dev-only",
        ),
        PortfolioFailureCase(
            case_id="pf-failure-005",
            query_id="q-dev-route-context-009",
            query_type="route_context",
            split_scope="dev-only",
            pipeline_stage="retrieval",
            primary_failure_category="retrieval_miss",
            risk_level="medium",
            observed_signal="route_context query에서 target child miss가 남은 사례",
            decision_impact="여러 장소를 연결하는 route context는 단일 장소 retrieval과 다르게 봐야 한다.",
            next_action="route_context는 HyDE보다 route-level query rewrite와 packing audit을 먼저 비교한다.",
            source_artifact="evals/reports/query_rewrite_retrieval_comparison_report.md",
            claim_boundary="dev-only",
        ),
        PortfolioFailureCase(
            case_id="pf-failure-006",
            query_id="q-dev-place-story-008",
            query_type="place_story",
            split_scope="dev-only",
            pipeline_stage="retrieval",
            primary_failure_category="retrieval_miss",
            risk_level="medium",
            observed_signal="current retrieval 후보에서 target doc까지 miss한 hard case",
            decision_impact="route boost를 기본값으로 승격하기 전에 hard-case coverage를 봐야 한다.",
            next_action="HyDE 또는 place-aware rewrite 후보를 place_story hard subset에서만 비교한다.",
            source_artifact="evals/reports/place_story_full_dev_generation_input_impact_report.md",
            claim_boundary="dev-only",
        ),
        PortfolioFailureCase(
            case_id="pf-failure-007",
            query_id="q-dev-relationship-008",
            query_type="relationship",
            split_scope="dev-only",
            pipeline_stage="retrieval_router",
            primary_failure_category="retrieval_miss",
            risk_level="medium",
            observed_signal="global dense candidate에서는 relationship target miss가 남은 사례",
            decision_impact="relationship은 global default가 아니라 route-specific hybrid 후보가 필요하다.",
            next_action="HyDE relationship subset은 hybrid reference와 paired comparison으로만 연다.",
            source_artifact="evals/reports/neural_dense_hybrid_retrieval_comparison_report.md",
            claim_boundary="dev-only",
        ),
        PortfolioFailureCase(
            case_id="pf-failure-008",
            query_id="q-dev-overview-010",
            query_type="overview",
            split_scope="dev-only",
            pipeline_stage="retrieval",
            primary_failure_category="retrieval_miss",
            risk_level="medium",
            observed_signal="overview query에서 target doc miss가 남고 RAPTOR-lite도 기본값으로 승격하지 못한 사례",
            decision_impact="summary node를 붙였다는 사실만으로 overview 성능 개선을 주장하면 안 된다.",
            next_action="HyDE overview subset은 RAPTOR-lite reference와 함께 비교한다.",
            source_artifact="evals/reports/raptor_lite_input_only_report.md",
            claim_boundary="dev-input-only",
        ),
        PortfolioFailureCase(
            case_id="pf-failure-009",
            query_id="q-dev-relationship-001",
            query_type="relationship",
            split_scope="live-dev-subset",
            pipeline_stage="generation",
            primary_failure_category="generation_contract_gap",
            risk_level="medium",
            observed_signal="repaired v2에서 citation recall regression이 발생한 사례",
            decision_impact="precision 상승만으로 generation policy를 기본값으로 바꾸면 안 된다.",
            next_action="generation prompt 수정은 citation recall gate를 먼저 통과해야 한다.",
            source_artifact="evals/reports/solar_generation_v2_tradeoff_analysis_report.md",
            claim_boundary="live-dev-subset",
        ),
        PortfolioFailureCase(
            case_id="pf-failure-010",
            query_id="q-dev-no-answer-001",
            query_type="no_answer",
            split_scope="dev-only",
            pipeline_stage="retrieval_generation_contract",
            primary_failure_category="no_answer_risk",
            risk_level="high",
            observed_signal="retriever 단독으로는 no-answer query에도 후보가 생길 수 있는 사례",
            decision_impact="검색 성공과 답변 가능 여부를 같은 metric으로 섞으면 안 된다.",
            next_action="HyDE 실험 전 no-answer hallucination guard를 고정한다.",
            source_artifact="evals/reports/bm25_baseline_report.md",
            claim_boundary="dev-only",
        ),
    )


def _build_run_id(rows: list[dict[str, object]]) -> str:
    digest = hashlib.sha256(
        json.dumps(rows, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    return f"portfolio-failure-analysis-c{len(rows)}-{digest}"


def _format_category_row(row: PortfolioFailureCategorySummary) -> str:
    return f"| `{row.primary_failure_category}` | {row.count} |"


def _format_stage_row(row: PortfolioFailureStageSummary) -> str:
    return f"| `{row.pipeline_stage}` | {row.count} |"


def _format_failure_case_doc_row(case: PortfolioFailureCase) -> str:
    return (
        f"| `{case.case_id}` | `{case.query_id}` | `{case.query_type}` | "
        f"`{case.pipeline_stage}` | `{case.primary_failure_category}` | "
        f"`{case.risk_level}` | {case.observed_signal} | {case.next_action} |"
    )


def _format_failure_case_report_row(case: PortfolioFailureCase) -> str:
    return (
        f"| `{case.case_id}` | `{case.query_id}` | `{case.query_type}` | "
        f"`{case.split_scope}` | `{case.pipeline_stage}` | "
        f"`{case.primary_failure_category}` | `{case.risk_level}` | "
        f"`{case.claim_boundary}` |"
    )


def main() -> int:
    args = _parse_args()
    build_portfolio_failure_analysis_report(
        doc_path=args.doc,
        report_path=args.report,
        result_path=args.results,
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build public-safe portfolio failure analysis report.",
    )
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
