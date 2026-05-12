from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.chat import CHAT_API_CONTRACT_VERSION, ChatResponse, public_chat_response_row
from app.application.chat_service import ChatCommand, ChatContractService
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
)


CHAT_PRIVATE_RETRIEVAL_SMOKE_REPORT_VERSION = "chat-private-retrieval-smoke-report/v1"
DEFAULT_REPORT_PATH = Path("evals/reports/chat_private_retrieval_smoke_report.md")


class ChatPrivateRetrievalSmokeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ChatPrivateRetrievalSmokeSummary(ChatPrivateRetrievalSmokeModel):
    request_count: int = Field(ge=0)
    success_count: int = Field(ge=0)
    answered_count: int = Field(ge=0)
    citation_count: int = Field(ge=0)
    evidence_id_count: int = Field(ge=0)
    retrieval_candidate_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    latency_ms: float = Field(ge=0.0)
    retrieval_latency_ms: float = Field(ge=0.0)


class ChatPrivateRetrievalSmokeReport(ChatPrivateRetrievalSmokeModel):
    report_version: str = CHAT_PRIVATE_RETRIEVAL_SMOKE_REPORT_VERSION
    contract_version: str = CHAT_API_CONTRACT_VERSION
    retrieval_method: str
    summary: ChatPrivateRetrievalSmokeSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def build_report(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> ChatPrivateRetrievalSmokeReport:
    response = _run_private_smoke_response()
    row = public_chat_response_row(response.model_dump(mode="json"))
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=CHAT_PRIVATE_RETRIEVAL_SMOKE_REPORT_VERSION,
        run_id="chat-private-retrieval-smoke",
        result_rows=[row],
        report_text="",
    )
    provisional = _build_report_from_row(row=row, output_quality=provisional_quality)
    report_text = build_chat_private_retrieval_smoke_report_markdown(provisional)
    quality = measure_public_retrieval_artifact_quality(
        report_version=CHAT_PRIVATE_RETRIEVAL_SMOKE_REPORT_VERSION,
        run_id="chat-private-retrieval-smoke",
        result_rows=[row],
        report_text=report_text,
    )
    report = _build_report_from_row(row=row, output_quality=quality)
    failures = collect_chat_private_retrieval_smoke_failures(report)
    if failures:
        raise ValueError(f"chat private retrieval smoke gate failed: {failures}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_chat_private_retrieval_smoke_report_markdown(report),
        encoding="utf-8",
    )
    print(
        "chat_private_retrieval_smoke "
        "status=PASS "
        f"citation_count={report.summary.citation_count} "
        f"evidence_count={report.summary.evidence_count} "
        f"retrieval_candidate_count={report.summary.retrieval_candidate_count} "
        f"live_solar_call_count={report.summary.live_solar_call_count}"
    )
    return report


def collect_chat_private_retrieval_smoke_failures(
    report: ChatPrivateRetrievalSmokeReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.success_count != 1:
        failures.append("private_smoke_success_missing")
    if summary.answered_count != 1:
        failures.append("private_smoke_answer_missing")
    if summary.citation_count == 0:
        failures.append("private_smoke_citation_missing")
    if summary.evidence_count == 0:
        failures.append("private_smoke_evidence_missing")
    if summary.retrieval_candidate_count == 0:
        failures.append("private_smoke_retrieval_candidate_missing")
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    return failures


def build_chat_private_retrieval_smoke_report_markdown(
    report: ChatPrivateRetrievalSmokeReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Chat Private Retrieval Smoke Report

## 목적

private `parent_child_chunks` artifact와 `multilingual-e5-small` dense retriever를 사용해 `/chat` retrieval-backed service가 실제 local corpus에서 evidence를 찾아 citation answer contract로 조립되는지 확인한다.

이 문서는 검색 성능 개선 주장이 아니다. 단일 smoke request이며, latency에는 model load와 cache load 비용이 포함될 수 있다.

## 정량 리포트

| metric | value |
| --- | ---: |
| request_count | {summary.request_count} |
| success_count | {summary.success_count} |
| answered_count | {summary.answered_count} |
| citation_count | {summary.citation_count} |
| evidence_id_count | {summary.evidence_id_count} |
| retrieval_candidate_count | {summary.retrieval_candidate_count} |
| evidence_count | {summary.evidence_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| latency_ms | {summary.latency_ms:.6f} |
| retrieval_latency_ms | {summary.retrieval_latency_ms:.6f} |

## 실행 경계

| field | value |
| --- | --- |
| retrieval_method | `{report.retrieval_method}` |
| private_corpus | `<private parent_child_chunks artifact>` |
| embedding_cache | `<private dense embedding cache>` |
| solar_live_generation | disabled |

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

실제 private corpus에서 retrieval candidate와 citation-ready evidence가 반환됐다. 그러나 답변 본문은 아직 Solar Pro 3 live generation이 아니라 contract draft이므로, 역사 해설 품질이나 최종 RAG 성능으로 주장하지 않는다.
"""


def _run_private_smoke_response() -> ChatResponse:
    service = ChatContractService()
    result = service.handle(
        ChatCommand(
            request_id="private-smoke-chat-retrieval",
            query="경복궁을 한양 맥락에서 설명해줘",
            query_type="place_story",
            language="ko",
            place_context=("gyeongbokgung",),
            retrieval_mode="retrieval_backed",
        )
    )
    return ChatResponse.from_service_result(result)


def _build_report_from_row(
    *,
    row: dict[str, Any],
    output_quality: PublicRetrievalArtifactQuality,
) -> ChatPrivateRetrievalSmokeReport:
    summary = ChatPrivateRetrievalSmokeSummary(
        request_count=1,
        success_count=1,
        answered_count=0 if row.get("abstained") is True else 1,
        citation_count=int(row.get("citation_count") or 0),
        evidence_id_count=int(row.get("evidence_id_count") or 0),
        retrieval_candidate_count=int(row.get("retrieval_candidate_count") or 0),
        evidence_count=int(row.get("evidence_id_count") or 0),
        live_solar_call_count=int(row.get("solar_call_count") or 0),
        latency_ms=float(row.get("latency_ms") or 0.0),
        retrieval_latency_ms=float(row.get("retrieval_latency_ms") or 0.0),
    )
    return ChatPrivateRetrievalSmokeReport(
        retrieval_method=str(row.get("retrieval_method") or "unknown"),
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment=_build_qualitative_assessment(
            summary=summary,
            output_quality=output_quality,
        ),
    )


def _build_qualitative_assessment(
    *,
    summary: ChatPrivateRetrievalSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> dict[str, str]:
    failures = collect_public_retrieval_artifact_failures(output_quality)
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    return {
        "private_smoke_scope": (
            "local private artifact를 사용해 retrieval-backed service path를 1회 smoke 검증했다."
        ),
        "evidence_boundary": (
            "응답과 report에는 evidence id와 citation id만 남기며 raw chunk text는 저장하지 않는다."
        ),
        "latency_boundary": (
            "latency는 단일 local smoke 값이며 model load/cache load가 섞일 수 있어 SLO나 성능 주장으로 쓰지 않는다."
        ),
        "generation_boundary": (
            "Solar Pro 3 live generation은 호출하지 않았고 contract draft만 사용했다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def main() -> int:
    args = _parse_args()
    build_report(report_path=args.report)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build chat private retrieval smoke public-safe report."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
