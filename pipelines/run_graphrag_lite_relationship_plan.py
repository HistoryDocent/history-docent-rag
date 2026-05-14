from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    write_public_retrieval_result_rows,
)


GRAPHRAG_LITE_RELATIONSHIP_PLAN_REPORT_VERSION = "graphrag-lite-relationship-plan-report/v1"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "graphrag_lite_relationship_plan_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "graphrag_lite_relationship_plan_rows.jsonl"
)
PlanDecision = Literal["ready_for_graphrag_lite_input_only_approval", "blocked"]


class GraphRagLiteRelationshipPlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GraphRagLitePlanSummary(GraphRagLiteRelationshipPlanModel):
    planned_query_type_count: int = Field(ge=0)
    planned_dev_query_count: int = Field(ge=0)
    planned_test_query_count: int = Field(ge=0)
    strategy_count: int = Field(ge=0)
    baseline_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    planned_solar_call_count: int = Field(ge=0)
    planned_raw_text_public_count: int = Field(ge=0)
    planned_private_path_public_count: int = Field(ge=0)
    min_required_citation_recoverability: float = Field(ge=0.0, le=1.0)
    target_recall_at_5_delta: float
    target_mrr_delta: float
    target_ndcg_at_5_delta: float
    max_latency_p95_ms: float = Field(ge=0.0)
    decision: PlanDecision


class GraphRagLiteStrategyRow(GraphRagLiteRelationshipPlanModel):
    strategy_id: str = Field(min_length=1)
    role: Literal["baseline", "candidate"]
    query_type: Literal["relationship"]
    execution_stage: Literal["reference", "input_only"]
    graph_component: str = Field(min_length=1)
    final_citation_source: Literal["source_child_chunk"]
    solar_call_count: int = Field(ge=0)
    raw_text_public_allowed: bool
    target_metric_family: str = Field(min_length=1)
    success_gate: str = Field(min_length=1)
    risk_tag: str = Field(min_length=1)


class GraphRagLiteRelationshipPlanReport(GraphRagLiteRelationshipPlanModel):
    report_version: str = GRAPHRAG_LITE_RELATIONSHIP_PLAN_REPORT_VERSION
    plan_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    summary: GraphRagLitePlanSummary
    strategy_rows: tuple[GraphRagLiteStrategyRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_graphrag_lite_relationship_plan(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> GraphRagLiteRelationshipPlanReport:
    strategy_rows = build_graphrag_lite_strategy_rows()
    summary = build_graphrag_lite_plan_summary(strategy_rows)
    plan_id = build_graphrag_lite_plan_id(strategy_rows)
    public_rows = build_public_graphrag_lite_plan_rows(
        plan_id=plan_id,
        summary=summary,
        strategy_rows=strategy_rows,
    )
    provisional = build_graphrag_lite_relationship_plan_report(
        plan_id=plan_id,
        summary=summary,
        strategy_rows=strategy_rows,
        report_text="",
    )
    report_text = build_graphrag_lite_relationship_plan_markdown(provisional)
    report = build_graphrag_lite_relationship_plan_report(
        plan_id=plan_id,
        summary=summary,
        strategy_rows=strategy_rows,
        report_text=report_text,
    )
    failures = collect_graphrag_lite_relationship_plan_failures(report)
    if failures:
        raise ValueError(f"graphrag-lite relationship plan gate failed: {failures}")
    write_public_retrieval_result_rows(path=result_rows_path, rows=public_rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_graphrag_lite_relationship_plan_markdown(report),
        encoding="utf-8",
    )
    print(
        "graphrag_lite_relationship_plan "
        "status=PASS "
        f"strategy_count={report.summary.strategy_count} "
        f"candidate_count={report.summary.candidate_count} "
        f"planned_solar_call_count={report.summary.planned_solar_call_count} "
        f"decision={report.summary.decision}",
    )
    return report


def build_graphrag_lite_relationship_plan_report(
    *,
    plan_id: str,
    summary: GraphRagLitePlanSummary,
    strategy_rows: tuple[GraphRagLiteStrategyRow, ...],
    report_text: str,
) -> GraphRagLiteRelationshipPlanReport:
    public_rows = build_public_graphrag_lite_plan_rows(
        plan_id=plan_id,
        summary=summary,
        strategy_rows=strategy_rows,
    )
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=GRAPHRAG_LITE_RELATIONSHIP_PLAN_REPORT_VERSION,
        run_id=plan_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    report = GraphRagLiteRelationshipPlanReport(
        plan_id=plan_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        summary=summary,
        strategy_rows=strategy_rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_graphrag_lite_plan_qualitative_assessment(report),
        },
    )


def build_graphrag_lite_strategy_rows() -> tuple[GraphRagLiteStrategyRow, ...]:
    return (
        GraphRagLiteStrategyRow(
            strategy_id="hybrid_weighted_e5_small_alpha_0_5_reference",
            role="baseline",
            query_type="relationship",
            execution_stage="reference",
            graph_component="none",
            final_citation_source="source_child_chunk",
            solar_call_count=0,
            raw_text_public_allowed=False,
            target_metric_family="retrieval_reference",
            success_gate="relationship dev baseline metric is the comparison floor",
            risk_tag="already_measured_reference",
        ),
        GraphRagLiteStrategyRow(
            strategy_id="graphrag_lite_entity_path_v1",
            role="candidate",
            query_type="relationship",
            execution_stage="input_only",
            graph_component="entity_path",
            final_citation_source="source_child_chunk",
            solar_call_count=0,
            raw_text_public_allowed=False,
            target_metric_family="relationship_entity_coverage",
            success_gate="Recall@5 and MRR improve without citation recoverability loss",
            risk_tag="entity_canonicalization_error",
        ),
        GraphRagLiteStrategyRow(
            strategy_id="graphrag_lite_community_hint_v1",
            role="candidate",
            query_type="relationship",
            execution_stage="input_only",
            graph_component="community_hint",
            final_citation_source="source_child_chunk",
            solar_call_count=0,
            raw_text_public_allowed=False,
            target_metric_family="relationship_context_bridge",
            success_gate="nDCG@5 improves while final citation remains source chunk only",
            risk_tag="summary_as_citation_forbidden",
        ),
    )


def build_graphrag_lite_plan_summary(
    strategy_rows: tuple[GraphRagLiteStrategyRow, ...],
) -> GraphRagLitePlanSummary:
    planned_query_types = {row.query_type for row in strategy_rows}
    planned_solar_calls = sum(row.solar_call_count for row in strategy_rows)
    public_raw_text_count = sum(1 for row in strategy_rows if row.raw_text_public_allowed)
    decision: PlanDecision = (
        "ready_for_graphrag_lite_input_only_approval"
        if planned_query_types == {"relationship"}
        and planned_solar_calls == 0
        and public_raw_text_count == 0
        else "blocked"
    )
    return GraphRagLitePlanSummary(
        planned_query_type_count=len(planned_query_types),
        planned_dev_query_count=10,
        planned_test_query_count=5,
        strategy_count=len(strategy_rows),
        baseline_count=sum(1 for row in strategy_rows if row.role == "baseline"),
        candidate_count=sum(1 for row in strategy_rows if row.role == "candidate"),
        planned_solar_call_count=planned_solar_calls,
        planned_raw_text_public_count=public_raw_text_count,
        planned_private_path_public_count=0,
        min_required_citation_recoverability=0.99,
        target_recall_at_5_delta=0.03,
        target_mrr_delta=0.03,
        target_ndcg_at_5_delta=0.03,
        max_latency_p95_ms=2500.0,
        decision=decision,
    )


def build_public_graphrag_lite_plan_rows(
    *,
    plan_id: str,
    summary: GraphRagLitePlanSummary,
    strategy_rows: tuple[GraphRagLiteStrategyRow, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "plan_id": plan_id,
            "planned_query_type_count": summary.planned_query_type_count,
            "planned_dev_query_count": summary.planned_dev_query_count,
            "planned_test_query_count": summary.planned_test_query_count,
            "strategy_count": summary.strategy_count,
            "baseline_count": summary.baseline_count,
            "candidate_count": summary.candidate_count,
            "planned_solar_call_count": summary.planned_solar_call_count,
            "min_required_citation_recoverability": (summary.min_required_citation_recoverability),
            "target_recall_at_5_delta": summary.target_recall_at_5_delta,
            "target_mrr_delta": summary.target_mrr_delta,
            "target_ndcg_at_5_delta": summary.target_ndcg_at_5_delta,
            "max_latency_p95_ms": summary.max_latency_p95_ms,
            "decision": summary.decision,
        },
    ]
    rows.extend(
        {
            "row_type": "strategy",
            "plan_id": plan_id,
            "strategy_id": row.strategy_id,
            "role": row.role,
            "query_type": row.query_type,
            "execution_stage": row.execution_stage,
            "graph_component": row.graph_component,
            "final_citation_source": row.final_citation_source,
            "solar_call_count": row.solar_call_count,
            "raw_text_public_allowed": row.raw_text_public_allowed,
            "target_metric_family": row.target_metric_family,
            "risk_tag": row.risk_tag,
        }
        for row in strategy_rows
    )
    return rows


def collect_graphrag_lite_relationship_plan_failures(
    report: GraphRagLiteRelationshipPlanReport,
) -> list[str]:
    failures: list[str] = []
    failures.extend(collect_public_retrieval_artifact_failures(report.output_quality))
    if report.summary.decision == "blocked":
        failures.append("plan_decision_blocked")
    if {row.query_type for row in report.strategy_rows} != {"relationship"}:
        failures.append("non_relationship_query_type_present")
    if report.summary.planned_solar_call_count != 0:
        failures.append("planned_solar_call_count_must_be_zero")
    if report.summary.baseline_count != 1:
        failures.append("baseline_count_must_be_one")
    if report.summary.candidate_count < 1:
        failures.append("candidate_count_must_be_positive")
    if any(row.final_citation_source != "source_child_chunk" for row in report.strategy_rows):
        failures.append("final_citation_must_be_source_child_chunk")
    if report.summary.planned_raw_text_public_count:
        failures.append("raw_text_public_plan_not_allowed")
    return failures


def build_graphrag_lite_relationship_plan_markdown(
    report: GraphRagLiteRelationshipPlanReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    strategy_rows = "\n".join(_format_strategy_row(row) for row in report.strategy_rows)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# GraphRAG-lite Relationship Plan Report

## 결론

GraphRAG-lite는 기본 RAG pipeline이 아니라 `relationship` 질문 전용 input-only 실험군으로 제한한다.

이번 단계는 계획과 runner skeleton 검증이다. GraphRAG-lite 실행 결과, 성능 개선, production 채택 주장이 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| plan_id | `{report.plan_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| decision | `{summary.decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| planned_query_type_count | {summary.planned_query_type_count} |
| planned_dev_query_count | {summary.planned_dev_query_count} |
| planned_test_query_count | {summary.planned_test_query_count} |
| strategy_count | {summary.strategy_count} |
| baseline_count | {summary.baseline_count} |
| candidate_count | {summary.candidate_count} |
| planned_solar_call_count | {summary.planned_solar_call_count} |
| planned_raw_text_public_count | {summary.planned_raw_text_public_count} |
| planned_private_path_public_count | {summary.planned_private_path_public_count} |
| min_required_citation_recoverability | {summary.min_required_citation_recoverability:.6f} |
| target_recall_at_5_delta | {summary.target_recall_at_5_delta:.6f} |
| target_mrr_delta | {summary.target_mrr_delta:.6f} |
| target_ndcg_at_5_delta | {summary.target_ndcg_at_5_delta:.6f} |
| max_latency_p95_ms | {summary.max_latency_p95_ms:.6f} |

## Strategy Rows

| strategy_id | role | query_type | stage | graph_component | final_citation_source | solar_call_count | risk_tag |
| --- | --- | --- | --- | --- | --- | ---: | --- |
{strategy_rows}

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

## 다음 구현 조건

다음 단계에서만 실제 input-only 비교를 실행한다.

- `relationship` dev 10개만 사용한다.
- baseline은 기존 hybrid/dense 계열 최상위 reference를 사용한다.
- candidate는 entity path와 community hint를 source child chunk 후보로 되돌린다.
- graph summary나 community summary는 citation으로 쓰지 않는다.
- Solar Pro 3 호출은 0으로 유지한다.
- public report에는 raw query, raw answer, raw evidence, chunk text, private path, secret을 기록하지 않는다.
"""


def build_graphrag_lite_plan_qualitative_assessment(
    report: GraphRagLiteRelationshipPlanReport,
) -> dict[str, str]:
    failures = collect_graphrag_lite_relationship_plan_failures(report)
    return {
        "scope": "relationship query type 전용 GraphRAG-lite input-only 실험 계획이다.",
        "baseline_boundary": "기존 hybrid/dense reference를 비교 floor로 두고 청킹 재실험은 열지 않는다.",
        "candidate_boundary": "entity path와 community hint는 retrieval 후보 보조 정보이며 최종 citation이 아니다.",
        "citation_boundary": "최종 citation은 source child chunk에서만 허용한다.",
        "llm_call_boundary": "계획 단계와 다음 input-only 단계 모두 Solar Pro 3 호출 0을 유지한다.",
        "data_mart_grain": "`fact_graphrag_lite_relationship_eval`의 grain은 plan_id-strategy_id-query_type-metric_family다.",
        "security_boundary": "public artifact에 raw query, raw evidence, chunk text, private path, secret을 기록하지 않는다.",
        "external_audit": "청킹이 아니라 relationship 관계 검색 실패 유형만 분리해 변수 폭발을 막았다.",
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def build_graphrag_lite_plan_id(
    strategy_rows: tuple[GraphRagLiteStrategyRow, ...],
) -> str:
    payload = [
        {
            "strategy_id": row.strategy_id,
            "role": row.role,
            "query_type": row.query_type,
            "stage": row.execution_stage,
            "graph_component": row.graph_component,
        }
        for row in strategy_rows
    ]
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:8]
    return f"graphrag-lite-relationship-plan-s{len(strategy_rows)}-{digest}"


def _format_strategy_row(row: GraphRagLiteStrategyRow) -> str:
    return (
        f"| `{row.strategy_id}` | {row.role} | {row.query_type} | "
        f"{row.execution_stage} | {row.graph_component} | "
        f"{row.final_citation_source} | {row.solar_call_count} | {row.risk_tag} |"
    )


def main() -> int:
    args = _parse_args()
    report = run_graphrag_lite_relationship_plan(
        report_path=args.report,
        result_rows_path=args.result_rows,
    )
    return 0 if not collect_graphrag_lite_relationship_plan_failures(report) else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build GraphRAG-lite relationship input-only plan report.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
