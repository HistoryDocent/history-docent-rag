from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field

from app.api.app import create_app
from app.api.v1.chat import CHAT_API_CONTRACT_VERSION, public_chat_response_row
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
)


CHAT_API_CONTRACT_REPORT_VERSION = "chat-api-contract-report/v1"
DEFAULT_REPORT_PATH = Path("evals/reports/chat_api_contract_report.md")


class ChatApiContractReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ChatApiContractSummary(ChatApiContractReportModel):
    request_count: int = Field(ge=0)
    success_count: int = Field(ge=0)
    validation_error_count: int = Field(ge=0)
    provider_unavailable_count: int = Field(ge=0)
    answered_count: int = Field(ge=0)
    abstained_count: int = Field(ge=0)
    citation_count: int = Field(ge=0)
    evidence_id_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    latency_p95_ms: float = Field(ge=0.0)


class ChatApiContractReport(ChatApiContractReportModel):
    report_version: str = CHAT_API_CONTRACT_REPORT_VERSION
    contract_version: str = CHAT_API_CONTRACT_VERSION
    summary: ChatApiContractSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def build_report(*, report_path: Path = DEFAULT_REPORT_PATH) -> ChatApiContractReport:
    rows = run_contract_smoke_rows()
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=CHAT_API_CONTRACT_REPORT_VERSION,
        run_id="chat-api-contract",
        result_rows=rows,
        report_text="",
    )
    provisional = _build_report_from_rows(rows=rows, output_quality=provisional_quality)
    report_text = build_chat_api_contract_report_markdown(provisional)
    quality = measure_public_retrieval_artifact_quality(
        report_version=CHAT_API_CONTRACT_REPORT_VERSION,
        run_id="chat-api-contract",
        result_rows=rows,
        report_text=report_text,
    )
    report = _build_report_from_rows(rows=rows, output_quality=quality)
    failures = collect_chat_api_contract_failures(report)
    if failures:
        raise ValueError(f"chat API contract gate failed: {failures}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_chat_api_contract_report_markdown(report),
        encoding="utf-8",
    )
    print(
        "chat_api_contract "
        "status=PASS "
        f"request_count={report.summary.request_count} "
        f"success_count={report.summary.success_count} "
        f"validation_error_count={report.summary.validation_error_count} "
        f"provider_unavailable_count={report.summary.provider_unavailable_count} "
        f"live_solar_call_count={report.summary.live_solar_call_count}"
    )
    return report


def run_contract_smoke_rows() -> list[dict[str, Any]]:
    client = TestClient(create_app(), raise_server_exceptions=False)
    cases = [
        {
            "case_id": "answerable_contract",
            "payload": {
                "request_id": "api-contract-answer",
                "query": "경복궁을 한양 맥락에서 짧게 설명해줘",
                "query_type": "place_story",
                "language": "ko",
                "place_context": ["gyeongbokgung"],
            },
        },
        {
            "case_id": "no_answer_contract",
            "payload": {
                "request_id": "api-contract-no-answer",
                "query": "이 자료에 없는 현대 스포츠 기록을 알려줘",
                "query_type": "no_answer",
                "language": "ko",
            },
        },
        {
            "case_id": "validation_error",
            "payload": {
                "request_id": "api-contract-validation",
                "query": " ",
                "query_type": "place_story",
            },
        },
        {
            "case_id": "solar_disabled",
            "payload": {
                "request_id": "api-contract-solar-disabled",
                "query": "경복궁을 설명해줘",
                "query_type": "place_story",
                "provider_mode": "solar_pro_3",
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
    return rows


def collect_chat_api_contract_failures(report: ChatApiContractReport) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.request_count != 4:
        failures.append("unexpected_contract_case_count")
    if summary.success_count != 2:
        failures.append("unexpected_success_count")
    if summary.validation_error_count != 1:
        failures.append("validation_error_case_missing")
    if summary.provider_unavailable_count != 1:
        failures.append("provider_disabled_case_missing")
    if summary.answered_count != 1:
        failures.append("answered_case_missing")
    if summary.abstained_count != 1:
        failures.append("abstained_case_missing")
    if summary.citation_count < 1:
        failures.append("citation_case_missing")
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    return failures


def build_chat_api_contract_report_markdown(
    report: ChatApiContractReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Chat API Contract Report

## 목적

FastAPI `/api/v1/chat` 계약을 live Solar Pro 3 호출 없이 검증한다.

이 문서는 답변 품질 개선 주장이 아니다. 외부 입력 validation, 표준 error envelope, `answer`, `spoken_answer`, `citations`, `evidence_ids`, `abstained`, provider boundary가 public-safe 구조로 동작하는지 확인한다.

## 정량 리포트

| metric | value |
| --- | ---: |
| request_count | {summary.request_count} |
| success_count | {summary.success_count} |
| validation_error_count | {summary.validation_error_count} |
| provider_unavailable_count | {summary.provider_unavailable_count} |
| answered_count | {summary.answered_count} |
| abstained_count | {summary.abstained_count} |
| citation_count | {summary.citation_count} |
| evidence_id_count | {summary.evidence_id_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| latency_p95_ms | {summary.latency_p95_ms:.6f} |

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

현재 API는 contract-only service를 통해 citation RAG answer contract를 노출한다. Solar Pro 3 live 호출은 명시적으로 차단하며, provider 연결은 별도 승인 후 private dev subset에서 smoke test로 검증한다.
"""


def _build_report_from_rows(
    *,
    rows: list[dict[str, Any]],
    output_quality: PublicRetrievalArtifactQuality,
) -> ChatApiContractReport:
    summary = _summarize_rows(rows)
    return ChatApiContractReport(
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment=_build_qualitative_assessment(
            summary=summary,
            output_quality=output_quality,
        ),
    )


def _summarize_rows(rows: list[dict[str, Any]]) -> ChatApiContractSummary:
    error_counts = Counter(row.get("error_code") for row in rows)
    success_rows = [row for row in rows if row.get("status_code") == 200]
    latencies = [
        float(row["latency_ms"])
        for row in success_rows
        if isinstance(row.get("latency_ms"), int | float)
    ]
    return ChatApiContractSummary(
        request_count=len(rows),
        success_count=len(success_rows),
        validation_error_count=error_counts.get("validation_error", 0),
        provider_unavailable_count=error_counts.get("provider_unavailable", 0),
        answered_count=sum(1 for row in success_rows if row.get("abstained") is False),
        abstained_count=sum(1 for row in success_rows if row.get("abstained") is True),
        citation_count=sum(int(row.get("citation_count") or 0) for row in success_rows),
        evidence_id_count=sum(
            int(row.get("evidence_id_count") or 0) for row in success_rows
        ),
        live_solar_call_count=sum(
            int(row.get("solar_call_count") or 0) for row in success_rows
        ),
        latency_p95_ms=_percentile(latencies, 0.95),
    )


def _build_qualitative_assessment(
    *,
    summary: ChatApiContractSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> dict[str, str]:
    failures = collect_public_retrieval_artifact_failures(output_quality)
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    return {
        "api_scope": (
            "`POST /api/v1/chat`는 contract-only answer path와 no-answer abstain path를 "
            "검증했다."
        ),
        "validation_boundary": (
            "blank query는 422 error envelope로 반환하고 request body 원문을 report에 남기지 않는다."
        ),
        "provider_boundary": (
            "provider_mode=solar_pro_3 요청은 503 provider_unavailable로 차단해 live 비용과 "
            "secret 노출을 방지한다."
        ),
        "citation_boundary": (
            "answerable 응답은 recoverable citation과 evidence_id를 포함하고, no-answer 응답은 "
            "citation 없이 abstained=true를 반환한다."
        ),
        "claim_boundary": (
            "이 리포트는 API 계약 검증이며 검색 또는 생성 품질 개선 주장이 아니다."
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
        description="Build FastAPI chat contract public-safe report."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
