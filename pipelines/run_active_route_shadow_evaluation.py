from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.application.chat_retrieval import (
    PrivateArtifactRetrievalBackend,
    _search_with_route,
)
from app.application.query_type_classifier import (
    QUERY_TYPE_CLASSIFIER_ID,
    DeterministicQueryTypeClassifier,
    QueryTypeClassificationInput,
)
from app.application.query_type_route_guard import (
    RELATIONSHIP_ROUTE_GUARD_POLICY_ID,
    RelationshipRouteGuard,
    RelationshipRouteGuardInput,
)
from app.application.query_type_router import (
    DEFAULT_PACKING_POLICY_ID,
    DEFAULT_RETRIEVAL_CANDIDATE_ID,
    DEFAULT_ROUTE_POLICY_ID,
    QUERY_TYPE_ROUTER_POLICY_ID,
    RELATIONSHIP_ROUTE_POLICY_ID,
    QueryTypeRouteDecision,
    QueryTypeRouter,
)
from app.core.project_paths import is_repository_private_write_path, project_path
from app.domain.retrieval import (
    QueryType,
    RetrievedCandidate,
    RetrievalEvalItem,
    RetrievalJudgment,
    RetrievalRunResult,
    load_retrieval_eval_jsonl,
)
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    build_dataset_fingerprint,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from app.infrastructure.index.device import resolve_torch_device


ACTIVE_ROUTE_SHADOW_EVAL_REPORT_VERSION = "active-route-shadow-evaluation-report/v1"
WORK_ID = "HD-API-ROUTER-004"
DEFAULT_DATASET_PATH = Path("private_data/evals/datasets/retrieval_eval_dev.jsonl")
DEFAULT_CHUNKS_PATH = Path("private_data/reports/parent_child_chunks.json")
DEFAULT_RESULT_ROWS_PATH = Path(
    "private_data/evals/results/active_route_shadow_evaluation_rows.jsonl"
)
DEFAULT_DOC_PATH = Path("docs/ACTIVE_ROUTE_SHADOW_EVALUATION.md")
DEFAULT_REPORT_PATH = Path("evals/reports/active_route_shadow_evaluation_report.md")
DEFAULT_TOP_K = 5
MAX_OVERALL_MRR_REGRESSION = -0.01
MAX_OVERALL_NDCG_REGRESSION = -0.01
MAX_LATENCY_P95_DELTA_MS = 50.0

ShadowDecision = Literal[
    "ready_for_active_route_dry_run_contract",
    "keep_shadow_only",
    "reject_active_route_for_now",
]


class ActiveRouteShadowModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ActiveRouteShadowRetrievalRunner(Protocol):
    def search(
        self,
        *,
        item: RetrievalEvalItem,
        route_decision: QueryTypeRouteDecision,
    ) -> RetrievalRunResult:
        ...


class ActiveRouteShadowRow(ActiveRouteShadowModel):
    query_id: str = Field(min_length=1)
    gold_query_type: QueryType
    predicted_query_type: QueryType
    guarded_query_type: QueryType
    expected_behavior: Literal["retrieve", "abstain"]
    baseline_route_policy_id: str = Field(min_length=1)
    shadow_route_policy_id: str = Field(min_length=1)
    baseline_candidate_id: str = Field(min_length=1)
    shadow_candidate_id: str = Field(min_length=1)
    guard_decision: Literal["allow", "block", "fallback", "not_applicable"]
    decision_reason_tag: str = Field(min_length=1)
    candidate_route_applied: bool
    active_route_applied: bool
    no_answer_guard_applied: bool
    false_hybrid_route: bool
    missed_hybrid_route: bool
    no_answer_candidate_route: bool
    baseline_candidate_count: int = Field(ge=0)
    shadow_candidate_count: int = Field(ge=0)
    baseline_relevant_rank: int | None = Field(default=None, ge=1)
    shadow_relevant_rank: int | None = Field(default=None, ge=1)
    baseline_hit_at_1: bool
    baseline_hit_at_3: bool
    baseline_hit_at_5: bool
    shadow_hit_at_1: bool
    shadow_hit_at_3: bool
    shadow_hit_at_5: bool
    baseline_rr: float = Field(ge=0.0, le=1.0)
    shadow_rr: float = Field(ge=0.0, le=1.0)
    baseline_ndcg_at_5: float = Field(ge=0.0, le=1.0)
    shadow_ndcg_at_5: float = Field(ge=0.0, le=1.0)
    baseline_latency_ms: float = Field(ge=0.0)
    shadow_latency_ms: float = Field(ge=0.0)
    latency_delta_ms: float


class ActiveRouteMetricSummary(ActiveRouteShadowModel):
    candidate_id: str = Field(min_length=1)
    query_count: int = Field(ge=0)
    retrieve_query_count: int = Field(ge=0)
    no_answer_query_count: int = Field(ge=0)
    recall_at_1: float = Field(ge=0.0, le=1.0)
    recall_at_3: float = Field(ge=0.0, le=1.0)
    recall_at_5: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)
    no_answer_with_candidate_count: int = Field(ge=0)


class ActiveRouteShadowSummary(ActiveRouteShadowModel):
    query_count: int = Field(ge=0)
    answerable_query_count: int = Field(ge=0)
    no_answer_query_count: int = Field(ge=0)
    baseline_retrieval_run_count: int = Field(ge=0)
    shadow_retrieval_run_count: int = Field(ge=0)
    routed_candidate_query_count: int = Field(ge=0)
    guard_applied_count: int = Field(ge=0)
    blocked_by_guard_count: int = Field(ge=0)
    fallback_default_count: int = Field(ge=0)
    false_hybrid_route_count: int = Field(ge=0)
    missed_hybrid_route_count: int = Field(ge=0)
    no_answer_candidate_route_count: int = Field(ge=0)
    active_route_applied_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    recall_at_1_delta: float
    recall_at_3_delta: float
    recall_at_5_delta: float
    mrr_delta: float
    ndcg_at_5_delta: float
    latency_p95_ms_delta: float
    relationship_recall_at_5_delta: float
    relationship_mrr_delta: float
    shadow_decision: ShadowDecision


class ActiveRouteQueryTypeDelta(ActiveRouteShadowModel):
    query_type: QueryType
    query_count: int = Field(ge=0)
    baseline_recall_at_5: float = Field(ge=0.0, le=1.0)
    shadow_recall_at_5: float = Field(ge=0.0, le=1.0)
    recall_at_5_delta: float
    baseline_mrr: float = Field(ge=0.0, le=1.0)
    shadow_mrr: float = Field(ge=0.0, le=1.0)
    mrr_delta: float


class ActiveRouteShadowEvaluationReport(ActiveRouteShadowModel):
    report_version: str = ACTIVE_ROUTE_SHADOW_EVAL_REPORT_VERSION
    work_id: str = WORK_ID
    run_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    dataset_fingerprint: str = Field(min_length=8)
    classifier_id: str = QUERY_TYPE_CLASSIFIER_ID
    router_policy_id: str = QUERY_TYPE_ROUTER_POLICY_ID
    guard_policy_id: str = RELATIONSHIP_ROUTE_GUARD_POLICY_ID
    baseline_route_policy_id: str = DEFAULT_ROUTE_POLICY_ID
    shadow_candidate_route_policy_id: str = RELATIONSHIP_ROUTE_POLICY_ID
    packing_policy_id: str = DEFAULT_PACKING_POLICY_ID
    top_k: int = Field(ge=1)
    resolved_device: str = Field(min_length=1)
    baseline_summary: ActiveRouteMetricSummary
    shadow_summary: ActiveRouteMetricSummary
    comparison_summary: ActiveRouteShadowSummary
    rows: tuple[ActiveRouteShadowRow, ...]
    query_type_deltas: tuple[ActiveRouteQueryTypeDelta, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


class PrivateActiveRouteShadowRetrievalRunner:
    def __init__(
        self,
        *,
        chunks_path: Path = DEFAULT_CHUNKS_PATH,
        top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self.backend = PrivateArtifactRetrievalBackend(chunks_path=chunks_path, top_k=top_k)
        self.top_k = top_k

    def search(
        self,
        *,
        item: RetrievalEvalItem,
        route_decision: QueryTypeRouteDecision,
    ) -> RetrievalRunResult:
        if item.query.expected_behavior == "abstain" or not route_decision.should_retrieve:
            return _empty_result(item=item)
        state = self.backend._load_state()
        rewrite = state.rewriter.rewrite(item)
        result = _search_with_route(
            route_decision=route_decision,
            state=state,
            item=item,
            query_text=rewrite.rewritten_query_text,
            top_k=self.top_k,
        )
        return result.model_copy(
            update={"latency_ms": round(result.latency_ms + rewrite.latency_ms, 6)}
        )


def run_active_route_shadow_evaluation(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    top_k: int = DEFAULT_TOP_K,
    retrieval_runner: ActiveRouteShadowRetrievalRunner | None = None,
) -> ActiveRouteShadowEvaluationReport:
    _validate_private_result_path(result_rows_path)
    items = load_retrieval_eval_jsonl(project_path(dataset_path))
    runner = retrieval_runner or PrivateActiveRouteShadowRetrievalRunner(
        chunks_path=chunks_path,
        top_k=top_k,
    )
    rows = build_active_route_shadow_rows(items=items, retrieval_runner=runner)
    provisional = _build_report(
        rows=rows,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        result_rows_path=result_rows_path,
        top_k=top_k,
        output_quality=PublicRetrievalArtifactQuality(
            result_row_count=0,
            report_version=ACTIVE_ROUTE_SHADOW_EVAL_REPORT_VERSION,
            run_id="pending",
            public_raw_text_leakage_count=0,
            private_path_leakage_count=0,
            secret_like_leakage_count=0,
            forbidden_result_field_count=0,
        ),
    )
    public_rows = build_public_active_route_shadow_rows(provisional)
    doc_text = build_active_route_shadow_evaluation_doc(provisional)
    report_text = build_active_route_shadow_evaluation_report_markdown(provisional)
    quality = measure_public_retrieval_artifact_quality(
        report_version=ACTIVE_ROUTE_SHADOW_EVAL_REPORT_VERSION,
        run_id=provisional.run_id,
        result_rows=public_rows,
        report_text=report_text,
        extra_public_texts={
            f"doc:{line_number}": line
            for line_number, line in enumerate(doc_text.splitlines(), start=1)
        },
    )
    report = _build_report(
        rows=rows,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        result_rows_path=result_rows_path,
        top_k=top_k,
        output_quality=quality,
    )
    failures = collect_active_route_shadow_evaluation_failures(report)
    if failures:
        raise ValueError(f"active route shadow evaluation gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_active_route_shadow_rows(report),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(
        build_active_route_shadow_evaluation_doc(report),
        encoding="utf-8",
    )
    resolved_report_path.write_text(
        build_active_route_shadow_evaluation_report_markdown(report),
        encoding="utf-8",
    )
    print(
        "active_route_shadow_evaluation "
        "status=PASS "
        f"query_count={report.comparison_summary.query_count} "
        f"routed_candidate_query_count="
        f"{report.comparison_summary.routed_candidate_query_count} "
        f"false_hybrid_route_count="
        f"{report.comparison_summary.false_hybrid_route_count} "
        f"no_answer_candidate_route_count="
        f"{report.comparison_summary.no_answer_candidate_route_count} "
        f"mrr_delta={report.comparison_summary.mrr_delta:.6f} "
        f"decision={report.comparison_summary.shadow_decision}",
    )
    return report


def build_active_route_shadow_rows(
    *,
    items: list[RetrievalEvalItem],
    retrieval_runner: ActiveRouteShadowRetrievalRunner,
) -> tuple[ActiveRouteShadowRow, ...]:
    classifier = DeterministicQueryTypeClassifier()
    guard = RelationshipRouteGuard()
    router = QueryTypeRouter()
    rows: list[ActiveRouteShadowRow] = []
    for item in items:
        classification = classifier.classify(
            QueryTypeClassificationInput(
                query_text=item.query.query_text,
                user_context=item.query.user_context,
                place_ids=tuple(item.metadata.place_ids),
                has_dialog_context=item.metadata.requires_context,
            )
        )
        guard_decision = guard.apply(
            RelationshipRouteGuardInput(
                query_text=item.query.query_text,
                classification=classification,
            )
        )
        baseline_route = _baseline_route(router=router, item=item)
        shadow_route = _shadow_route(
            router=router,
            item=item,
            guarded_query_type=guard_decision.guarded_query_type,
        )
        baseline_result = retrieval_runner.search(
            item=item,
            route_decision=baseline_route,
        )
        shadow_result = retrieval_runner.search(
            item=item,
            route_decision=shadow_route,
        )
        candidate_route_applied = (
            item.query.expected_behavior == "retrieve"
            and shadow_route.route_policy_id == RELATIONSHIP_ROUTE_POLICY_ID
        )
        guard_label = _guard_label(
            original_query_type=guard_decision.original_query_type,
            guarded_query_type=guard_decision.guarded_query_type,
            guard_applied=guard_decision.guard_applied,
        )
        rows.append(
            _build_row(
                item=item,
                baseline_route=baseline_route,
                shadow_route=shadow_route,
                baseline_result=baseline_result,
                shadow_result=shadow_result,
                predicted_query_type=classification.predicted_query_type,
                guarded_query_type=guard_decision.guarded_query_type,
                guard_decision=guard_label,
                decision_reason_tag=_decision_reason_tag(
                    item=item,
                    candidate_route_applied=candidate_route_applied,
                    guard_label=guard_label,
                ),
                candidate_route_applied=candidate_route_applied,
            )
        )
    return tuple(rows)


def build_public_active_route_shadow_rows(
    report: ActiveRouteShadowEvaluationReport,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [
        {
            "row_type": "summary",
            "run_id": report.run_id,
            "work_id": report.work_id,
            "query_count": report.comparison_summary.query_count,
            "answerable_query_count": report.comparison_summary.answerable_query_count,
            "no_answer_query_count": report.comparison_summary.no_answer_query_count,
            "routed_candidate_query_count": (
                report.comparison_summary.routed_candidate_query_count
            ),
            "false_hybrid_route_count": (
                report.comparison_summary.false_hybrid_route_count
            ),
            "no_answer_candidate_route_count": (
                report.comparison_summary.no_answer_candidate_route_count
            ),
            "active_route_applied_count": (
                report.comparison_summary.active_route_applied_count
            ),
            "live_solar_call_count": report.comparison_summary.live_solar_call_count,
            "mrr_delta": report.comparison_summary.mrr_delta,
            "ndcg_at_5_delta": report.comparison_summary.ndcg_at_5_delta,
            "shadow_decision": report.comparison_summary.shadow_decision,
        },
        _metric_row(report.run_id, "baseline", report.baseline_summary),
        _metric_row(report.run_id, "shadow", report.shadow_summary),
    ]
    rows.extend(_public_query_shadow_row(report.run_id, row) for row in report.rows)
    rows.extend(
        {
            "row_type": "query_type_delta",
            "run_id": report.run_id,
            "query_type": row.query_type,
            "query_count": row.query_count,
            "baseline_recall_at_5": row.baseline_recall_at_5,
            "shadow_recall_at_5": row.shadow_recall_at_5,
            "recall_at_5_delta": row.recall_at_5_delta,
            "baseline_mrr": row.baseline_mrr,
            "shadow_mrr": row.shadow_mrr,
            "mrr_delta": row.mrr_delta,
        }
        for row in report.query_type_deltas
    )
    return rows


def collect_active_route_shadow_evaluation_failures(
    report: ActiveRouteShadowEvaluationReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.comparison_summary
    if summary.query_count <= 0:
        failures.append("empty_query_set")
    if summary.active_route_applied_count:
        failures.append("active_route_applied")
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    if summary.no_answer_candidate_route_count:
        failures.append("no_answer_candidate_route_detected")
    if summary.false_hybrid_route_count:
        failures.append("false_hybrid_route_detected")
    return failures


def build_active_route_shadow_evaluation_doc(
    report: ActiveRouteShadowEvaluationReport,
) -> str:
    summary = report.comparison_summary
    return f"""# Active Route Shadow Evaluation

## 결론

`HD-API-ROUTER-004`는 active route를 실제로 켠 작업이 아니다.

dev reviewed query set에서 current baseline route와 `relationship_hybrid_weighted_e5_v1` shadow route를 paired 비교했다. active route 적용 여부는 `{summary.shadow_decision}`로 기록한다.

이 문서는 public-safe 결과 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 핵심 수치

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| routed_candidate_query_count | {summary.routed_candidate_query_count} |
| false_hybrid_route_count | {summary.false_hybrid_route_count} |
| no_answer_candidate_route_count | {summary.no_answer_candidate_route_count} |
| active_route_applied_count | {summary.active_route_applied_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| Recall@5 delta | {summary.recall_at_5_delta:.6f} |
| MRR delta | {summary.mrr_delta:.6f} |
| nDCG@5 delta | {summary.ndcg_at_5_delta:.6f} |
| latency_p95_ms delta | {summary.latency_p95_ms_delta:.6f} |
| relationship Recall@5 delta | {summary.relationship_recall_at_5_delta:.6f} |

## 판단

- active route는 아직 production route가 아니다.

- `relationship` hybrid route만 다음 API flag dry-run 후보가 될 수 있다.

- no-answer query는 candidate route에서 차단됐다.

- locked test 실행은 별도 승인 전까지 금지한다.
"""


def build_active_route_shadow_evaluation_report_markdown(
    report: ActiveRouteShadowEvaluationReport,
) -> str:
    summary = report.comparison_summary
    quality = report.output_quality
    query_type_rows = "\n".join(
        _format_query_type_delta_row(row) for row in report.query_type_deltas
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Active Route Shadow Evaluation Report

## 목적

`HD-API-ROUTER-004`는 active routing을 켜기 전 shadow route가 기존 baseline보다 안전한지 paired 방식으로 검토한다.

이 리포트는 dev-shadow-only 평가다. production routing, locked test 개선, Solar Pro 3 답변 품질 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| work_id | `{report.work_id}` |
| run_id | `{report.run_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| result_path | `{report.result_path}` |
| dataset_fingerprint | `{report.dataset_fingerprint}` |
| classifier_id | `{report.classifier_id}` |
| router_policy_id | `{report.router_policy_id}` |
| guard_policy_id | `{report.guard_policy_id}` |
| baseline_route_policy_id | `{report.baseline_route_policy_id}` |
| shadow_candidate_route_policy_id | `{report.shadow_candidate_route_policy_id}` |
| packing_policy_id | `{report.packing_policy_id}` |
| top_k | {report.top_k} |
| resolved_device | `{report.resolved_device}` |
| live_solar_call_count | {summary.live_solar_call_count} |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| baseline_retrieval_run_count | {summary.baseline_retrieval_run_count} |
| shadow_retrieval_run_count | {summary.shadow_retrieval_run_count} |
| routed_candidate_query_count | {summary.routed_candidate_query_count} |
| guard_applied_count | {summary.guard_applied_count} |
| blocked_by_guard_count | {summary.blocked_by_guard_count} |
| fallback_default_count | {summary.fallback_default_count} |
| false_hybrid_route_count | {summary.false_hybrid_route_count} |
| missed_hybrid_route_count | {summary.missed_hybrid_route_count} |
| no_answer_candidate_route_count | {summary.no_answer_candidate_route_count} |
| active_route_applied_count | {summary.active_route_applied_count} |
| Recall@1 delta | {summary.recall_at_1_delta:.6f} |
| Recall@3 delta | {summary.recall_at_3_delta:.6f} |
| Recall@5 delta | {summary.recall_at_5_delta:.6f} |
| MRR delta | {summary.mrr_delta:.6f} |
| nDCG@5 delta | {summary.ndcg_at_5_delta:.6f} |
| latency_p95_ms delta | {summary.latency_p95_ms_delta:.6f} |
| relationship Recall@5 delta | {summary.relationship_recall_at_5_delta:.6f} |
| relationship MRR delta | {summary.relationship_mrr_delta:.6f} |
| shadow_decision | `{summary.shadow_decision}` |

## Candidate Metrics

| candidate | query_count | retrieve_query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_with_candidate_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{_format_metric_row("baseline", report.baseline_summary)}
{_format_metric_row("shadow", report.shadow_summary)}

## Query Type Delta

| query_type | query_count | baseline Recall@5 | shadow Recall@5 | Recall@5 delta | baseline MRR | shadow MRR | MRR delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

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

## Claim Boundary

허용 표현:

- dev shadow evaluation을 실행했다.
- active route는 아직 적용하지 않았다.
- `relationship` hybrid route의 active 적용 여부를 paired metric으로 검토했다.
- no-answer query는 candidate route에서 차단했다.

금지 표현:

- active routing으로 production 성능이 개선됐다.
- locked test에서 개선을 입증했다.
- Solar Pro 3 답변 품질이 개선됐다.
- HyDE, GraphRAG, RAPTOR가 active route로 채택됐다.

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- 이 평가는 dev-shadow-only다.
- generation 품질을 직접 평가하지 않았다.
- active route default enable은 아직 금지해야 한다.
"""


def _build_report(
    *,
    rows: tuple[ActiveRouteShadowRow, ...],
    dataset_path: Path,
    chunks_path: Path,
    result_rows_path: Path,
    top_k: int,
    output_quality: PublicRetrievalArtifactQuality,
) -> ActiveRouteShadowEvaluationReport:
    run_id = _build_run_id(rows)
    baseline_summary = _metric_summary(
        rows=rows,
        candidate_id=DEFAULT_RETRIEVAL_CANDIDATE_ID,
        prefix="baseline",
    )
    shadow_summary = _metric_summary(
        rows=rows,
        candidate_id="active_route_shadow_candidate",
        prefix="shadow",
    )
    query_type_deltas = _query_type_deltas(rows)
    summary = _comparison_summary(
        rows=rows,
        baseline_summary=baseline_summary,
        shadow_summary=shadow_summary,
        query_type_deltas=query_type_deltas,
    )
    return ActiveRouteShadowEvaluationReport(
        run_id=run_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias=public_path_alias(dataset_path),
        chunks_path_alias=public_path_alias(chunks_path),
        result_path=public_path_alias(result_rows_path),
        dataset_fingerprint=build_dataset_fingerprint(
            load_retrieval_eval_jsonl(project_path(dataset_path))
        ),
        top_k=top_k,
        resolved_device=resolve_torch_device("auto"),
        baseline_summary=baseline_summary,
        shadow_summary=shadow_summary,
        comparison_summary=summary,
        rows=rows,
        query_type_deltas=query_type_deltas,
        output_quality=output_quality.model_copy(update={"run_id": run_id}),
        qualitative_assessment=_qualitative_assessment(summary),
    )


def _build_row(
    *,
    item: RetrievalEvalItem,
    baseline_route: QueryTypeRouteDecision,
    shadow_route: QueryTypeRouteDecision,
    baseline_result: RetrievalRunResult,
    shadow_result: RetrievalRunResult,
    predicted_query_type: QueryType,
    guarded_query_type: QueryType,
    guard_decision: Literal["allow", "block", "fallback", "not_applicable"],
    decision_reason_tag: str,
    candidate_route_applied: bool,
) -> ActiveRouteShadowRow:
    baseline_rank = _relevant_rank(item, baseline_result.candidates)
    shadow_rank = _relevant_rank(item, shadow_result.candidates)
    false_hybrid_route = candidate_route_applied and item.query.query_type != "relationship"
    missed_hybrid_route = (
        item.query.query_type == "relationship" and not candidate_route_applied
    )
    no_answer_candidate_route = (
        item.query.expected_behavior == "abstain" and bool(shadow_result.candidates)
    )
    return ActiveRouteShadowRow(
        query_id=item.query.query_id,
        gold_query_type=item.query.query_type,
        predicted_query_type=predicted_query_type,
        guarded_query_type=guarded_query_type,
        expected_behavior=item.query.expected_behavior,
        baseline_route_policy_id=baseline_route.route_policy_id,
        shadow_route_policy_id=shadow_route.route_policy_id,
        baseline_candidate_id=baseline_route.selected_candidate_id,
        shadow_candidate_id=shadow_route.selected_candidate_id,
        guard_decision=guard_decision,
        decision_reason_tag=decision_reason_tag,
        candidate_route_applied=candidate_route_applied,
        active_route_applied=False,
        no_answer_guard_applied=item.query.expected_behavior == "abstain",
        false_hybrid_route=false_hybrid_route,
        missed_hybrid_route=missed_hybrid_route,
        no_answer_candidate_route=no_answer_candidate_route,
        baseline_candidate_count=len(baseline_result.candidates),
        shadow_candidate_count=len(shadow_result.candidates),
        baseline_relevant_rank=baseline_rank,
        shadow_relevant_rank=shadow_rank,
        baseline_hit_at_1=_hit_at_k(baseline_rank, 1),
        baseline_hit_at_3=_hit_at_k(baseline_rank, 3),
        baseline_hit_at_5=_hit_at_k(baseline_rank, 5),
        shadow_hit_at_1=_hit_at_k(shadow_rank, 1),
        shadow_hit_at_3=_hit_at_k(shadow_rank, 3),
        shadow_hit_at_5=_hit_at_k(shadow_rank, 5),
        baseline_rr=_rr(baseline_rank),
        shadow_rr=_rr(shadow_rank),
        baseline_ndcg_at_5=_ndcg_at_5(item, baseline_result.candidates),
        shadow_ndcg_at_5=_ndcg_at_5(item, shadow_result.candidates),
        baseline_latency_ms=baseline_result.latency_ms,
        shadow_latency_ms=shadow_result.latency_ms,
        latency_delta_ms=round(
            shadow_result.latency_ms - baseline_result.latency_ms,
            6,
        ),
    )


def _baseline_route(
    *,
    router: QueryTypeRouter,
    item: RetrievalEvalItem,
) -> QueryTypeRouteDecision:
    if item.query.expected_behavior == "abstain":
        return router.route("no_answer")
    return _default_answerable_route(router=router, query_type=item.query.query_type)


def _shadow_route(
    *,
    router: QueryTypeRouter,
    item: RetrievalEvalItem,
    guarded_query_type: QueryType,
) -> QueryTypeRouteDecision:
    if item.query.expected_behavior == "abstain":
        return router.route("no_answer")
    if guarded_query_type == "relationship":
        return router.route("relationship")
    return _default_answerable_route(router=router, query_type=item.query.query_type)


def _default_answerable_route(
    *,
    router: QueryTypeRouter,
    query_type: QueryType,
) -> QueryTypeRouteDecision:
    return router.route("place_fact").model_copy(
        update={
            "query_type": query_type,
            "production_default": True,
            "rejected_candidate_ids": (),
        }
    )


def _empty_result(*, item: RetrievalEvalItem) -> RetrievalRunResult:
    return RetrievalRunResult(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        method="dense",
        candidates=[],
        latency_ms=0.0,
    )


def _guard_label(
    *,
    original_query_type: QueryType,
    guarded_query_type: QueryType,
    guard_applied: bool,
) -> Literal["allow", "block", "fallback", "not_applicable"]:
    if original_query_type != "relationship":
        return "not_applicable"
    if not guard_applied:
        return "allow"
    if guarded_query_type == "relationship":
        return "fallback"
    return "block"


def _decision_reason_tag(
    *,
    item: RetrievalEvalItem,
    candidate_route_applied: bool,
    guard_label: str,
) -> str:
    if item.query.expected_behavior == "abstain":
        return "no_answer_abstain"
    if candidate_route_applied:
        return "safe_relationship_shadow_route"
    if guard_label == "block":
        return "blocked_by_relationship_guard"
    return "fallback_to_default_route"


def _metric_summary(
    *,
    rows: tuple[ActiveRouteShadowRow, ...],
    candidate_id: str,
    prefix: Literal["baseline", "shadow"],
) -> ActiveRouteMetricSummary:
    retrieve_rows = [row for row in rows if row.expected_behavior == "retrieve"]
    no_answer_rows = [row for row in rows if row.expected_behavior == "abstain"]
    return ActiveRouteMetricSummary(
        candidate_id=candidate_id,
        query_count=len(rows),
        retrieve_query_count=len(retrieve_rows),
        no_answer_query_count=len(no_answer_rows),
        recall_at_1=_mean(_row_value(row, f"{prefix}_hit_at_1") for row in retrieve_rows),
        recall_at_3=_mean(_row_value(row, f"{prefix}_hit_at_3") for row in retrieve_rows),
        recall_at_5=_mean(_row_value(row, f"{prefix}_hit_at_5") for row in retrieve_rows),
        mrr=_mean(_row_value(row, f"{prefix}_rr") for row in retrieve_rows),
        ndcg_at_5=_mean(_row_value(row, f"{prefix}_ndcg_at_5") for row in retrieve_rows),
        latency_p95_ms=_percentile(
            [float(_row_value(row, f"{prefix}_latency_ms")) for row in rows],
            0.95,
        ),
        no_answer_with_candidate_count=sum(
            1
            for row in no_answer_rows
            if int(_row_value(row, f"{prefix}_candidate_count")) > 0
        ),
    )


def _comparison_summary(
    *,
    rows: tuple[ActiveRouteShadowRow, ...],
    baseline_summary: ActiveRouteMetricSummary,
    shadow_summary: ActiveRouteMetricSummary,
    query_type_deltas: tuple[ActiveRouteQueryTypeDelta, ...],
) -> ActiveRouteShadowSummary:
    relationship_delta = next(
        (row for row in query_type_deltas if row.query_type == "relationship"),
        None,
    )
    mrr_delta = round(shadow_summary.mrr - baseline_summary.mrr, 6)
    ndcg_delta = round(shadow_summary.ndcg_at_5 - baseline_summary.ndcg_at_5, 6)
    latency_delta = round(
        shadow_summary.latency_p95_ms - baseline_summary.latency_p95_ms,
        6,
    )
    return ActiveRouteShadowSummary(
        query_count=len(rows),
        answerable_query_count=sum(1 for row in rows if row.expected_behavior == "retrieve"),
        no_answer_query_count=sum(1 for row in rows if row.expected_behavior == "abstain"),
        baseline_retrieval_run_count=sum(
            1 for row in rows if row.baseline_candidate_count > 0
        ),
        shadow_retrieval_run_count=sum(1 for row in rows if row.shadow_candidate_count > 0),
        routed_candidate_query_count=sum(1 for row in rows if row.candidate_route_applied),
        guard_applied_count=sum(1 for row in rows if row.guard_decision == "block"),
        blocked_by_guard_count=sum(
            1 for row in rows if row.decision_reason_tag == "blocked_by_relationship_guard"
        ),
        fallback_default_count=sum(
            1 for row in rows if row.decision_reason_tag == "fallback_to_default_route"
        ),
        false_hybrid_route_count=sum(1 for row in rows if row.false_hybrid_route),
        missed_hybrid_route_count=sum(1 for row in rows if row.missed_hybrid_route),
        no_answer_candidate_route_count=sum(
            1 for row in rows if row.no_answer_candidate_route
        ),
        active_route_applied_count=sum(1 for row in rows if row.active_route_applied),
        live_solar_call_count=0,
        recall_at_1_delta=round(
            shadow_summary.recall_at_1 - baseline_summary.recall_at_1,
            6,
        ),
        recall_at_3_delta=round(
            shadow_summary.recall_at_3 - baseline_summary.recall_at_3,
            6,
        ),
        recall_at_5_delta=round(
            shadow_summary.recall_at_5 - baseline_summary.recall_at_5,
            6,
        ),
        mrr_delta=mrr_delta,
        ndcg_at_5_delta=ndcg_delta,
        latency_p95_ms_delta=latency_delta,
        relationship_recall_at_5_delta=(
            relationship_delta.recall_at_5_delta if relationship_delta else 0.0
        ),
        relationship_mrr_delta=relationship_delta.mrr_delta if relationship_delta else 0.0,
        shadow_decision=_shadow_decision(
            mrr_delta=mrr_delta,
            ndcg_delta=ndcg_delta,
            latency_delta=latency_delta,
            relationship_delta=relationship_delta,
            rows=rows,
        ),
    )


def _query_type_deltas(
    rows: tuple[ActiveRouteShadowRow, ...],
) -> tuple[ActiveRouteQueryTypeDelta, ...]:
    grouped: dict[QueryType, list[ActiveRouteShadowRow]] = defaultdict(list)
    for row in rows:
        grouped[row.gold_query_type].append(row)
    deltas: list[ActiveRouteQueryTypeDelta] = []
    for query_type in sorted(grouped):
        query_rows = grouped[query_type]
        retrieve_rows = [row for row in query_rows if row.expected_behavior == "retrieve"]
        baseline_recall = _mean(row.baseline_hit_at_5 for row in retrieve_rows)
        shadow_recall = _mean(row.shadow_hit_at_5 for row in retrieve_rows)
        baseline_mrr = _mean(row.baseline_rr for row in retrieve_rows)
        shadow_mrr = _mean(row.shadow_rr for row in retrieve_rows)
        deltas.append(
            ActiveRouteQueryTypeDelta(
                query_type=query_type,
                query_count=len(query_rows),
                baseline_recall_at_5=baseline_recall,
                shadow_recall_at_5=shadow_recall,
                recall_at_5_delta=round(shadow_recall - baseline_recall, 6),
                baseline_mrr=baseline_mrr,
                shadow_mrr=shadow_mrr,
                mrr_delta=round(shadow_mrr - baseline_mrr, 6),
            )
        )
    return tuple(deltas)


def _shadow_decision(
    *,
    mrr_delta: float,
    ndcg_delta: float,
    latency_delta: float,
    relationship_delta: ActiveRouteQueryTypeDelta | None,
    rows: tuple[ActiveRouteShadowRow, ...],
) -> ShadowDecision:
    if any(row.false_hybrid_route or row.no_answer_candidate_route for row in rows):
        return "reject_active_route_for_now"
    if relationship_delta is None or relationship_delta.recall_at_5_delta <= 0:
        return "keep_shadow_only"
    if mrr_delta < MAX_OVERALL_MRR_REGRESSION:
        return "keep_shadow_only"
    if ndcg_delta < MAX_OVERALL_NDCG_REGRESSION:
        return "keep_shadow_only"
    if latency_delta > MAX_LATENCY_P95_DELTA_MS:
        return "keep_shadow_only"
    return "ready_for_active_route_dry_run_contract"


def _qualitative_assessment(summary: ActiveRouteShadowSummary) -> dict[str, str]:
    return {
        "architecture": (
            "active route를 바로 켜지 않고 relationship route만 shadow 후보로 비교했다."
        ),
        "retrieval": (
            "baseline은 dense voice rewrite, shadow는 guard를 통과한 relationship에만 hybrid route를 적용한다."
        ),
        "safety": (
            f"false_hybrid_route_count={summary.false_hybrid_route_count}, "
            f"no_answer_candidate_route_count={summary.no_answer_candidate_route_count}로 기록했다."
        ),
        "evaluation": (
            "dev reviewed split 기준 paired metric이며 locked test 또는 production 개선 주장이 아니다."
        ),
        "decision": f"shadow_decision={summary.shadow_decision}.",
        "public_policy": (
            "public report에는 query id, route label, aggregate metric만 남기고 원문 계열 필드는 금지한다."
        ),
    }


def _relevant_rank(
    item: RetrievalEvalItem,
    candidates: list[RetrievedCandidate],
) -> int | None:
    relevance = _relevance_by_identifier(item)
    for candidate in candidates:
        if _candidate_relevance(candidate, relevance) > 0:
            return candidate.rank
    return None


def _hit_at_k(rank: int | None, k: int) -> bool:
    return rank is not None and rank <= k


def _rr(rank: int | None) -> float:
    if rank is None:
        return 0.0
    return round(1 / rank, 6)


def _ndcg_at_5(
    item: RetrievalEvalItem,
    candidates: list[RetrievedCandidate],
) -> float:
    relevance = _relevance_by_identifier(item)
    gains = [_candidate_relevance(candidate, relevance) for candidate in candidates[:5]]
    ideal_gains = sorted(relevance.values(), reverse=True)[:5]
    ideal_gains.extend([0] * max(0, 5 - len(ideal_gains)))
    idcg = _dcg(ideal_gains)
    if idcg == 0:
        return 0.0
    return round(_dcg(gains) / idcg, 6)


def _relevance_by_identifier(item: RetrievalEvalItem) -> dict[str, int]:
    relevance: dict[str, int] = {}
    for judgment in item.judgments:
        for identifier in _primary_relevance_targets(judgment):
            relevance[identifier] = max(
                relevance.get(identifier, 0),
                judgment.relevance_grade,
            )
    return relevance


def _primary_relevance_targets(judgment: RetrievalJudgment) -> list[str]:
    if judgment.relevant_child_ids:
        return list(judgment.relevant_child_ids)
    if judgment.relevant_parent_ids:
        return list(judgment.relevant_parent_ids)
    return list(judgment.relevant_doc_ids)


def _candidate_relevance(
    candidate: RetrievedCandidate,
    relevance: dict[str, int],
) -> int:
    return max(
        relevance.get(candidate.child_id, 0),
        relevance.get(candidate.parent_id, 0),
        relevance.get(candidate.doc_id, 0),
    )


def _dcg(gains: list[int]) -> float:
    import math

    return round(
        sum((2**gain - 1) / math.log2(index + 2) for index, gain in enumerate(gains)),
        6,
    )


def _mean(values: object) -> float:
    materialized = [float(value) for value in values]
    if not materialized:
        return 0.0
    return round(sum(materialized) / len(materialized), 6)


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 6)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 6)


def _row_value(row: ActiveRouteShadowRow, name: str) -> object:
    return getattr(row, name)


def _metric_row(
    run_id: str,
    role: str,
    metric: ActiveRouteMetricSummary,
) -> dict[str, object]:
    return {
        "row_type": "candidate_metric",
        "run_id": run_id,
        "role": role,
        "candidate_id": metric.candidate_id,
        "query_count": metric.query_count,
        "retrieve_query_count": metric.retrieve_query_count,
        "no_answer_query_count": metric.no_answer_query_count,
        "recall_at_1": metric.recall_at_1,
        "recall_at_3": metric.recall_at_3,
        "recall_at_5": metric.recall_at_5,
        "mrr": metric.mrr,
        "ndcg_at_5": metric.ndcg_at_5,
        "latency_p95_ms": metric.latency_p95_ms,
        "no_answer_with_candidate_count": metric.no_answer_with_candidate_count,
    }


def _public_query_shadow_row(
    run_id: str,
    row: ActiveRouteShadowRow,
) -> dict[str, object]:
    return {
        "row_type": "query_shadow_result",
        "run_id": run_id,
        "query_id": row.query_id,
        "gold_query_type": row.gold_query_type,
        "predicted_query_type": row.predicted_query_type,
        "guarded_query_type": row.guarded_query_type,
        "expected_behavior": row.expected_behavior,
        "baseline_route_policy_id": row.baseline_route_policy_id,
        "shadow_route_policy_id": row.shadow_route_policy_id,
        "baseline_candidate_id": row.baseline_candidate_id,
        "shadow_candidate_id": row.shadow_candidate_id,
        "guard_decision": row.guard_decision,
        "decision_reason_tag": row.decision_reason_tag,
        "candidate_route_applied": row.candidate_route_applied,
        "active_route_applied": row.active_route_applied,
        "no_answer_guard_applied": row.no_answer_guard_applied,
        "false_hybrid_route": row.false_hybrid_route,
        "missed_hybrid_route": row.missed_hybrid_route,
        "no_answer_candidate_route": row.no_answer_candidate_route,
        "baseline_candidate_count": row.baseline_candidate_count,
        "shadow_candidate_count": row.shadow_candidate_count,
        "baseline_relevant_rank": row.baseline_relevant_rank,
        "shadow_relevant_rank": row.shadow_relevant_rank,
        "baseline_hit_at_5": row.baseline_hit_at_5,
        "shadow_hit_at_5": row.shadow_hit_at_5,
        "baseline_rr": row.baseline_rr,
        "shadow_rr": row.shadow_rr,
        "baseline_ndcg_at_5": row.baseline_ndcg_at_5,
        "shadow_ndcg_at_5": row.shadow_ndcg_at_5,
        "latency_delta_ms": row.latency_delta_ms,
    }


def _format_metric_row(role: str, metric: ActiveRouteMetricSummary) -> str:
    return (
        f"| {role} | {metric.query_count} | {metric.retrieve_query_count} | "
        f"{metric.recall_at_1:.6f} | {metric.recall_at_3:.6f} | "
        f"{metric.recall_at_5:.6f} | {metric.mrr:.6f} | "
        f"{metric.ndcg_at_5:.6f} | {metric.latency_p95_ms:.6f} | "
        f"{metric.no_answer_with_candidate_count} |"
    )


def _format_query_type_delta_row(row: ActiveRouteQueryTypeDelta) -> str:
    return (
        f"| `{row.query_type}` | {row.query_count} | "
        f"{row.baseline_recall_at_5:.6f} | {row.shadow_recall_at_5:.6f} | "
        f"{row.recall_at_5_delta:.6f} | {row.baseline_mrr:.6f} | "
        f"{row.shadow_mrr:.6f} | {row.mrr_delta:.6f} |"
    )


def _build_run_id(rows: tuple[ActiveRouteShadowRow, ...]) -> str:
    payload = [
        {
            "query_id": row.query_id,
            "baseline_route_policy_id": row.baseline_route_policy_id,
            "shadow_route_policy_id": row.shadow_route_policy_id,
            "candidate_route_applied": row.candidate_route_applied,
            "baseline_relevant_rank": row.baseline_relevant_rank,
            "shadow_relevant_rank": row.shadow_relevant_rank,
        }
        for row in rows
    ]
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    return f"active-route-shadow-eval-q{len(rows)}-{digest}"


def _validate_private_result_path(path: Path) -> None:
    if not is_repository_private_write_path(path):
        raise ValueError("active route shadow result rows must be under private_data")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run active route shadow evaluation without enabling active routing.",
    )
    parser.add_argument("--dataset-path", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--result-rows-path", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--doc-path", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    args = parser.parse_args()
    run_active_route_shadow_evaluation(
        dataset_path=args.dataset_path,
        chunks_path=args.chunks_path,
        result_rows_path=args.result_rows_path,
        doc_path=args.doc_path,
        report_path=args.report_path,
        top_k=args.top_k,
    )


if __name__ == "__main__":
    main()
