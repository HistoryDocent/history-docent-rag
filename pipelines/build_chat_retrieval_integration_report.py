from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field

from app.api.app import create_app
from app.api.v1.chat import CHAT_API_CONTRACT_VERSION, get_chat_service, public_chat_response_row
from app.application.chat_retrieval import StaticRetrievalBackend
from app.application.chat_service import ChatContractService
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
)


CHAT_RETRIEVAL_INTEGRATION_REPORT_VERSION = "chat-retrieval-integration-report/v1"
DEFAULT_REPORT_PATH = Path("evals/reports/chat_retrieval_integration_report.md")


class ChatRetrievalIntegrationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ChatRetrievalIntegrationSummary(ChatRetrievalIntegrationModel):
    request_count: int = Field(ge=0)
    success_count: int = Field(ge=0)
    retrieval_backed_request_count: int = Field(ge=0)
    retrieval_success_count: int = Field(ge=0)
    answered_count: int = Field(ge=0)
    abstained_count: int = Field(ge=0)
    citation_count: int = Field(ge=0)
    evidence_id_count: int = Field(ge=0)
    retrieval_candidate_count: int = Field(ge=0)
    classifier_dry_run_count: int = Field(ge=0)
    classifier_route_policy_changed_count: int = Field(ge=0)
    classifier_active_route_applied_count: int = Field(ge=0)
    classifier_fallback_count: int = Field(ge=0)
    classifier_guarded_route_candidate_count: int = Field(ge=0)
    classifier_guard_applied_count: int = Field(ge=0)
    classifier_guarded_route_policy_changed_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    latency_p95_ms: float = Field(ge=0.0)
    retrieval_latency_p95_ms: float = Field(ge=0.0)


class ChatRetrievalIntegrationReport(ChatRetrievalIntegrationModel):
    report_version: str = CHAT_RETRIEVAL_INTEGRATION_REPORT_VERSION
    contract_version: str = CHAT_API_CONTRACT_VERSION
    summary: ChatRetrievalIntegrationSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def build_report(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> ChatRetrievalIntegrationReport:
    rows = run_integration_smoke_rows()
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=CHAT_RETRIEVAL_INTEGRATION_REPORT_VERSION,
        run_id="chat-retrieval-integration",
        result_rows=rows,
        report_text="",
    )
    provisional = _build_report_from_rows(rows=rows, output_quality=provisional_quality)
    report_text = build_chat_retrieval_integration_report_markdown(provisional)
    quality = measure_public_retrieval_artifact_quality(
        report_version=CHAT_RETRIEVAL_INTEGRATION_REPORT_VERSION,
        run_id="chat-retrieval-integration",
        result_rows=rows,
        report_text=report_text,
    )
    report = _build_report_from_rows(rows=rows, output_quality=quality)
    failures = collect_chat_retrieval_integration_failures(report)
    if failures:
        raise ValueError(f"chat retrieval integration gate failed: {failures}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_chat_retrieval_integration_report_markdown(report),
        encoding="utf-8",
    )
    print(
        "chat_retrieval_integration "
        "status=PASS "
        f"request_count={report.summary.request_count} "
        f"retrieval_backed_request_count={report.summary.retrieval_backed_request_count} "
        f"retrieval_success_count={report.summary.retrieval_success_count} "
        f"classifier_dry_run_count={report.summary.classifier_dry_run_count} "
        f"live_solar_call_count={report.summary.live_solar_call_count}"
    )
    return report


def run_integration_smoke_rows() -> list[dict[str, Any]]:
    app = create_app()
    app.dependency_overrides[get_chat_service] = lambda: ChatContractService(
        retrieval_backend=StaticRetrievalBackend(),
    )
    client = TestClient(app, raise_server_exceptions=False)
    cases = [
        {
            "case_id": "retrieval_backed_answerable",
            "payload": {
                "request_id": "api-integration-answer",
                "query": "경복궁을 한양 맥락에서 설명해줘",
                "query_type": "place_story",
                "language": "ko",
                "place_context": ["gyeongbokgung"],
                "retrieval_mode": "retrieval_backed",
            },
        },
        {
            "case_id": "retrieval_backed_no_answer",
            "payload": {
                "request_id": "api-integration-no-answer",
                "query": "이 자료에 없는 현대 스포츠 기록을 알려줘",
                "query_type": "no_answer",
                "language": "ko",
                "retrieval_mode": "retrieval_backed",
            },
        },
        {
            "case_id": "contract_only_regression",
            "payload": {
                "request_id": "api-integration-contract",
                "query": "경복궁 설명",
                "query_type": "place_story",
                "retrieval_mode": "contract_only",
            },
        },
    ]
    rows: list[dict[str, Any]] = []
    for case in cases:
        response = client.post("/api/v1/chat", json=case["payload"])
        body = response.json()
        row = {
            "case_id": case["case_id"],
            "endpoint": "api/v1/chat",
            "method": "POST",
            "status_code": response.status_code,
            "error_code": _error_code(body),
        }
        if response.status_code == 200:
            row.update(public_chat_response_row(body))
        rows.append(row)
    app.dependency_overrides.clear()
    return rows


def collect_chat_retrieval_integration_failures(
    report: ChatRetrievalIntegrationReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.request_count != 3:
        failures.append("unexpected_contract_case_count")
    if summary.success_count != 3:
        failures.append("unexpected_success_count")
    if summary.retrieval_backed_request_count != 2:
        failures.append("retrieval_backed_case_missing")
    if summary.retrieval_success_count != 1:
        failures.append("retrieval_success_case_missing")
    if summary.answered_count != 2:
        failures.append("answered_case_count_mismatch")
    if summary.abstained_count != 1:
        failures.append("abstained_case_missing")
    if summary.citation_count < 2:
        failures.append("citation_count_below_expected")
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    if summary.classifier_dry_run_count != summary.success_count:
        failures.append("classifier_dry_run_missing")
    if summary.classifier_active_route_applied_count:
        failures.append("classifier_dry_run_changed_active_route")
    if summary.classifier_guarded_route_candidate_count != summary.success_count:
        failures.append("guarded_route_candidate_missing")
    return failures


def build_chat_retrieval_integration_report_markdown(
    report: ChatRetrievalIntegrationReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Chat Retrieval Integration Report

## 목적

FastAPI `/api/v1/chat`의 `retrieval_backed` mode가 retrieval, evidence packing, citation answer assembly를 같은 응답 계약으로 연결하는지 검증한다.

이 문서는 검색 성능 개선 주장이 아니다. public report에서는 fixture retrieval backend로 API integration grain과 leakage gate만 검증한다. private corpus 기반 dense retrieval smoke는 별도 local 검증 대상으로 둔다.

## 정량 리포트

| metric | value |
| --- | ---: |
| request_count | {summary.request_count} |
| success_count | {summary.success_count} |
| retrieval_backed_request_count | {summary.retrieval_backed_request_count} |
| retrieval_success_count | {summary.retrieval_success_count} |
| answered_count | {summary.answered_count} |
| abstained_count | {summary.abstained_count} |
| citation_count | {summary.citation_count} |
| evidence_id_count | {summary.evidence_id_count} |
| retrieval_candidate_count | {summary.retrieval_candidate_count} |
| classifier_dry_run_count | {summary.classifier_dry_run_count} |
| classifier_route_policy_changed_count | {summary.classifier_route_policy_changed_count} |
| classifier_active_route_applied_count | {summary.classifier_active_route_applied_count} |
| classifier_fallback_count | {summary.classifier_fallback_count} |
| classifier_guarded_route_candidate_count | {summary.classifier_guarded_route_candidate_count} |
| classifier_guard_applied_count | {summary.classifier_guard_applied_count} |
| classifier_guarded_route_policy_changed_count | {summary.classifier_guarded_route_policy_changed_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| latency_p95_ms | {summary.latency_p95_ms:.6f} |
| retrieval_latency_p95_ms | {summary.retrieval_latency_p95_ms:.6f} |

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

`retrieval_backed` mode는 기존 `contract_only` mode를 대체하지 않고 병렬 경로로 추가했다. 검색된 evidence는 `P0_rank_order` packing과 `citation-rag-answer/v1` assembler를 통과해야만 답변에 포함된다.
"""


def _build_report_from_rows(
    *,
    rows: list[dict[str, Any]],
    output_quality: PublicRetrievalArtifactQuality,
) -> ChatRetrievalIntegrationReport:
    summary = _summarize_rows(rows)
    return ChatRetrievalIntegrationReport(
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment=_build_qualitative_assessment(
            summary=summary,
            output_quality=output_quality,
        ),
    )


def _summarize_rows(rows: list[dict[str, Any]]) -> ChatRetrievalIntegrationSummary:
    success_rows = [row for row in rows if row.get("status_code") == 200]
    retrieval_rows = [
        row for row in success_rows if row.get("retrieval_mode") == "retrieval_backed"
    ]
    latencies = [
        float(row["latency_ms"])
        for row in success_rows
        if isinstance(row.get("latency_ms"), int | float)
    ]
    retrieval_latencies = [
        float(row["retrieval_latency_ms"])
        for row in retrieval_rows
        if isinstance(row.get("retrieval_latency_ms"), int | float)
    ]
    return ChatRetrievalIntegrationSummary(
        request_count=len(rows),
        success_count=len(success_rows),
        retrieval_backed_request_count=len(retrieval_rows),
        retrieval_success_count=sum(
            1
            for row in retrieval_rows
            if (row.get("retrieval_candidate_count") or 0) > 0
            and row.get("abstained") is False
        ),
        answered_count=sum(1 for row in success_rows if row.get("abstained") is False),
        abstained_count=sum(1 for row in success_rows if row.get("abstained") is True),
        citation_count=sum(int(row.get("citation_count") or 0) for row in success_rows),
        evidence_id_count=sum(
            int(row.get("evidence_id_count") or 0) for row in success_rows
        ),
        retrieval_candidate_count=sum(
            int(row.get("retrieval_candidate_count") or 0) for row in retrieval_rows
        ),
        classifier_dry_run_count=sum(
            1 for row in success_rows if row.get("classifier_dry_run_enabled") is True
        ),
        classifier_route_policy_changed_count=sum(
            1
            for row in success_rows
            if row.get("classifier_route_policy_changed") is True
        ),
        classifier_active_route_applied_count=sum(
            1
            for row in success_rows
            if row.get("classifier_active_route_applied") is True
        ),
        classifier_fallback_count=sum(
            1 for row in success_rows if row.get("classifier_fallback_used") is True
        ),
        classifier_guarded_route_candidate_count=sum(
            1 for row in success_rows if row.get("guard_policy_id")
        ),
        classifier_guard_applied_count=sum(
            1 for row in success_rows if row.get("guard_applied") is True
        ),
        classifier_guarded_route_policy_changed_count=sum(
            1
            for row in success_rows
            if row.get("guarded_route_policy_changed") is True
        ),
        live_solar_call_count=sum(
            int(row.get("solar_call_count") or 0) for row in success_rows
        ),
        latency_p95_ms=_percentile(latencies, 0.95),
        retrieval_latency_p95_ms=_percentile(retrieval_latencies, 0.95),
    )


def _build_qualitative_assessment(
    *,
    summary: ChatRetrievalIntegrationSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> dict[str, str]:
    failures = collect_public_retrieval_artifact_failures(output_quality)
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    return {
        "integration_scope": (
            "`retrieval_backed` request가 retrieval outcome, evidence packing, citation "
            "assembler를 거쳐 동일한 ChatResponse로 반환되는지 검증했다."
        ),
        "grain_boundary": (
            "public result row grain은 API smoke case 1건이다. row에는 query/answer/chunk text를 "
            "저장하지 않는다."
        ),
        "retrieval_boundary": (
            "public report는 fixture retrieval backend를 사용한다. private dense backend는 "
            "원문 chunk와 embedding cache를 public에 노출하지 않기 위해 별도 local 경로로만 사용한다."
        ),
        "no_answer_policy": (
            "no_answer retrieval_backed request는 evidence 없이 abstained=true를 반환해야 한다."
        ),
        "provider_boundary": (
            "Solar Pro 3 live generation은 호출하지 않고, provider_call_count와 solar_call_count를 0으로 유지한다."
        ),
        "classifier_router_boundary": (
            "classifier/router dry-run은 API 응답에 포함하지만 retrieval_backed route 선택에는 적용하지 않는다."
        ),
        "guarded_route_boundary": (
            "guarded_route_candidate는 관찰 필드이며 retrieval_backed route 선택에는 적용하지 않는다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def _error_code(body: dict[str, Any]) -> str | None:
    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return code if isinstance(code, str) else None


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percentile)
    return round(sorted_values[index], 6)


def main() -> int:
    args = _parse_args()
    build_report(report_path=args.report)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build chat retrieval integration public-safe report."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
