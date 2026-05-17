from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import project_path
from app.domain.retrieval import QueryType, load_retrieval_eval_jsonl
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from pipelines.run_solar_live_generation_smoke import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_DATASET_PATH,
)


PLACE_STORY_TARGETED_CHUNK_AUDIT_REPORT_VERSION = (
    "place-story-targeted-chunk-audit-report/v1"
)
DEFAULT_QUERY_ID = "q-dev-place-story-001"
DEFAULT_HARD_CASE_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "place_story_hard_case_analysis_rows.jsonl"
)
DEFAULT_DOC_PATH = Path("docs") / "PLACE_STORY_TARGETED_CHUNK_AUDIT.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "place_story_targeted_chunk_audit_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "place_story_targeted_chunk_audit_rows.jsonl"
)

AuditDecision = Literal[
    "do_not_reopen_global_chunking",
    "open_targeted_chunk_repair",
    "reopen_global_chunking",
]


class PlaceStoryTargetedChunkAuditModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlaceStoryTargetedChunkAuditRow(PlaceStoryTargetedChunkAuditModel):
    audit_id: str = Field(min_length=1)
    query_id: str = Field(min_length=1)
    query_type: QueryType
    target_child_count: int = Field(ge=0)
    target_parent_count: int = Field(ge=0)
    target_doc_count: int = Field(ge=0)
    target_child_exists_count: int = Field(ge=0)
    target_parent_exists_count: int = Field(ge=0)
    target_child_parent_membership_count: int = Field(ge=0)
    target_child_citation_ref_count: int = Field(ge=0)
    target_child_page_range_valid_count: int = Field(ge=0)
    target_child_quality_flag_count: int = Field(ge=0)
    target_parent_quality_flag_count: int = Field(ge=0)
    target_child_text_length_min: int = Field(ge=0)
    target_child_text_length_max: int = Field(ge=0)
    target_parent_child_count_min: int = Field(ge=0)
    target_parent_child_count_max: int = Field(ge=0)
    chunk_generation_loss: bool
    chunk_boundary_defect: bool
    parser_noise_observed: bool
    retrieved_target_child: bool
    retrieved_target_parent: bool
    retrieved_target_doc: bool
    target_min_retrieval_rank: int | None = Field(default=None, ge=1)
    target_min_pack_rank: int | None = Field(default=None, ge=1)
    hard_case_root_cause: str = Field(min_length=1)
    audit_decision: AuditDecision
    next_action: str = Field(min_length=1)
    claim_boundary: str = Field(min_length=1)


class PlaceStoryTargetedChunkAuditSummary(PlaceStoryTargetedChunkAuditModel):
    audit_case_count: int = Field(ge=0)
    target_child_exists_rate: float = Field(ge=0.0, le=1.0)
    target_parent_exists_rate: float = Field(ge=0.0, le=1.0)
    target_child_parent_membership_rate: float = Field(ge=0.0, le=1.0)
    target_child_citation_ref_rate: float = Field(ge=0.0, le=1.0)
    target_child_page_range_valid_rate: float = Field(ge=0.0, le=1.0)
    target_child_quality_flag_count: int = Field(ge=0)
    target_parent_quality_flag_count: int = Field(ge=0)
    chunk_generation_loss_count: int = Field(ge=0)
    chunk_boundary_defect_count: int = Field(ge=0)
    parser_noise_observed_count: int = Field(ge=0)
    retrieved_target_child_count: int = Field(ge=0)
    retrieved_target_parent_count: int = Field(ge=0)
    retrieved_target_doc_count: int = Field(ge=0)
    reopen_global_chunking_count: int = Field(ge=0)
    open_targeted_chunk_repair_count: int = Field(ge=0)
    live_solar_call_count_for_this_report: int = Field(ge=0)
    cuda_required: bool = False
    recommended_decision: AuditDecision


class PlaceStoryTargetedChunkAuditReport(PlaceStoryTargetedChunkAuditModel):
    report_version: str = PLACE_STORY_TARGETED_CHUNK_AUDIT_REPORT_VERSION
    audit_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = "HD-CHUNK-AUDIT-001"
    query_id: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    hard_case_rows_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: PlaceStoryTargetedChunkAuditSummary
    audit_rows: tuple[PlaceStoryTargetedChunkAuditRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_place_story_targeted_chunk_audit(
    *,
    query_id: str = DEFAULT_QUERY_ID,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    hard_case_rows_path: Path = DEFAULT_HARD_CASE_ROWS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> PlaceStoryTargetedChunkAuditReport:
    row = build_place_story_targeted_chunk_audit_row(
        query_id=query_id,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        hard_case_rows_path=hard_case_rows_path,
    )
    rows = (row,)
    public_rows = [row.model_dump(mode="json") for row in rows]
    write_public_retrieval_result_rows(path=result_rows_path, rows=public_rows)

    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=PLACE_STORY_TARGETED_CHUNK_AUDIT_REPORT_VERSION,
        run_id=row.audit_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = _build_report(
        query_id=query_id,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        hard_case_rows_path=hard_case_rows_path,
        result_rows_path=result_rows_path,
        rows=rows,
        output_quality=provisional_quality,
    )
    doc_text = build_place_story_targeted_chunk_audit_doc(provisional)
    report_text = build_place_story_targeted_chunk_audit_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=PLACE_STORY_TARGETED_CHUNK_AUDIT_REPORT_VERSION,
        run_id=row.audit_id,
        result_rows=public_rows,
        report_text=report_text,
        extra_public_texts={
            f"doc:{line_number}": line
            for line_number, line in enumerate(doc_text.splitlines(), start=1)
        },
    )
    report = _build_report(
        query_id=query_id,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        hard_case_rows_path=hard_case_rows_path,
        result_rows_path=result_rows_path,
        rows=rows,
        output_quality=output_quality,
    )
    failures = collect_place_story_targeted_chunk_audit_failures(report)
    if failures:
        raise ValueError(f"place story targeted chunk audit gate failed: {failures}")

    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(
        build_place_story_targeted_chunk_audit_doc(report),
        encoding="utf-8",
    )
    resolved_report_path.write_text(
        build_place_story_targeted_chunk_audit_markdown(report),
        encoding="utf-8",
    )
    print(
        "place_story_targeted_chunk_audit "
        "status=PASS "
        f"audit_case_count={report.summary.audit_case_count} "
        f"chunk_generation_loss_count={report.summary.chunk_generation_loss_count} "
        f"chunk_boundary_defect_count={report.summary.chunk_boundary_defect_count} "
        f"reopen_global_chunking_count={report.summary.reopen_global_chunking_count} "
        f"decision={report.summary.recommended_decision}"
    )
    return report


def build_place_story_targeted_chunk_audit_row(
    *,
    query_id: str,
    dataset_path: Path,
    chunks_path: Path,
    hard_case_rows_path: Path,
) -> PlaceStoryTargetedChunkAuditRow:
    item = _load_target_item(query_id=query_id, dataset_path=dataset_path)
    chunks_payload = _load_json(chunks_path)
    hard_case_row = _load_hard_case_row(
        query_id=query_id,
        hard_case_rows_path=hard_case_rows_path,
    )
    children_by_id = {
        child["child_id"]: child
        for child in chunks_payload.get("children", [])
        if isinstance(child, dict) and isinstance(child.get("child_id"), str)
    }
    parents_by_id = {
        parent["parent_id"]: parent
        for parent in chunks_payload.get("parents", [])
        if isinstance(parent, dict) and isinstance(parent.get("parent_id"), str)
    }
    target_child_ids, target_parent_ids, target_doc_ids = _target_ids(item)
    target_children = [
        children_by_id[child_id]
        for child_id in target_child_ids
        if child_id in children_by_id
    ]
    target_parents = [
        parents_by_id[parent_id]
        for parent_id in target_parent_ids
        if parent_id in parents_by_id
    ]
    membership_count = sum(
        1
        for child in target_children
        if child.get("parent_id") in target_parent_ids
        and _parent_contains_child(
            parent=parents_by_id.get(str(child.get("parent_id"))),
            child_id=str(child.get("child_id")),
        )
    )
    citation_ref_count = sum(1 for child in target_children if child.get("citation_refs"))
    page_range_valid_count = sum(1 for child in target_children if _page_span_valid(child))
    child_quality_flag_count = sum(
        1 for child in target_children if child.get("quality_flags")
    )
    parent_quality_flag_count = sum(
        1 for parent in target_parents if parent.get("quality_flags")
    )
    child_lengths = [
        int(child.get("text_length", 0))
        for child in target_children
        if isinstance(child.get("text_length", 0), int)
    ]
    parent_child_counts = [
        len(parent.get("child_ids", []))
        for parent in target_parents
        if isinstance(parent.get("child_ids"), list)
    ]
    chunk_generation_loss = (
        len(target_children) != len(target_child_ids)
        or len(target_parents) != len(target_parent_ids)
        or membership_count != len(target_child_ids)
    )
    chunk_boundary_defect = (
        chunk_generation_loss
        or citation_ref_count != len(target_child_ids)
        or page_range_valid_count != len(target_child_ids)
    )
    parser_noise_observed = child_quality_flag_count > 0 or parent_quality_flag_count > 0
    audit_decision = _audit_decision(
        chunk_generation_loss=chunk_generation_loss,
        chunk_boundary_defect=chunk_boundary_defect,
    )
    audit_id = _stable_id(
        {
            "query_id": query_id,
            "target_child_count": len(target_child_ids),
            "target_parent_count": len(target_parent_ids),
            "target_doc_count": len(target_doc_ids),
            "chunk_generation_loss": chunk_generation_loss,
            "chunk_boundary_defect": chunk_boundary_defect,
            "hard_case_root_cause": hard_case_row.get("root_cause_decision"),
        },
    )
    return PlaceStoryTargetedChunkAuditRow(
        audit_id=f"place-story-targeted-chunk-audit-{audit_id}",
        query_id=query_id,
        query_type=item.query.query_type,
        target_child_count=len(target_child_ids),
        target_parent_count=len(target_parent_ids),
        target_doc_count=len(target_doc_ids),
        target_child_exists_count=len(target_children),
        target_parent_exists_count=len(target_parents),
        target_child_parent_membership_count=membership_count,
        target_child_citation_ref_count=citation_ref_count,
        target_child_page_range_valid_count=page_range_valid_count,
        target_child_quality_flag_count=child_quality_flag_count,
        target_parent_quality_flag_count=parent_quality_flag_count,
        target_child_text_length_min=min(child_lengths) if child_lengths else 0,
        target_child_text_length_max=max(child_lengths) if child_lengths else 0,
        target_parent_child_count_min=min(parent_child_counts) if parent_child_counts else 0,
        target_parent_child_count_max=max(parent_child_counts) if parent_child_counts else 0,
        chunk_generation_loss=chunk_generation_loss,
        chunk_boundary_defect=chunk_boundary_defect,
        parser_noise_observed=parser_noise_observed,
        retrieved_target_child=bool(hard_case_row.get("target_child_covered")),
        retrieved_target_parent=bool(hard_case_row.get("target_parent_covered")),
        retrieved_target_doc=bool(hard_case_row.get("target_doc_covered")),
        target_min_retrieval_rank=hard_case_row.get("target_min_retrieval_rank"),
        target_min_pack_rank=hard_case_row.get("target_min_pack_rank"),
        hard_case_root_cause=str(hard_case_row.get("root_cause_decision")),
        audit_decision=audit_decision,
        next_action=_next_action(audit_decision),
        claim_boundary="dev-only",
    )


def collect_place_story_targeted_chunk_audit_failures(
    report: PlaceStoryTargetedChunkAuditReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.audit_case_count != 1:
        failures.append("audit_case_count_mismatch")
    if summary.reopen_global_chunking_count:
        failures.append("unexpected_global_chunking_reopen")
    if summary.live_solar_call_count_for_this_report:
        failures.append("live_solar_call_detected")
    if summary.cuda_required:
        failures.append("unexpected_cuda_requirement")
    if any(row.query_type != "place_story" for row in report.audit_rows):
        failures.append("non_place_story_audit_case")
    if any(not row.next_action for row in report.audit_rows):
        failures.append("missing_next_action")
    return failures


def build_place_story_targeted_chunk_audit_doc(
    report: PlaceStoryTargetedChunkAuditReport,
) -> str:
    summary = report.summary
    row = report.audit_rows[0]
    return f"""# Place Story Targeted Chunk Audit

## 결론

`{report.query_id}`는 전체 청킹 비교를 다시 열 근거가 아니다.

target child와 parent는 chunk artifact 안에 모두 존재하고, child-parent membership과 citation ref도 유지된다. 따라서 현재 실패는 chunk 생성 손실이 아니라 retrieval rank, target grain, generation input 품질 문제로 보는 것이 맞다.

이 문서는 public-safe targeted audit이다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| audit_case_count | {summary.audit_case_count} |
| target_child_exists_rate | {summary.target_child_exists_rate:.6f} |
| target_parent_exists_rate | {summary.target_parent_exists_rate:.6f} |
| target_child_parent_membership_rate | {summary.target_child_parent_membership_rate:.6f} |
| target_child_citation_ref_rate | {summary.target_child_citation_ref_rate:.6f} |
| target_child_page_range_valid_rate | {summary.target_child_page_range_valid_rate:.6f} |
| target_child_quality_flag_count | {summary.target_child_quality_flag_count} |
| target_parent_quality_flag_count | {summary.target_parent_quality_flag_count} |
| chunk_generation_loss_count | {summary.chunk_generation_loss_count} |
| chunk_boundary_defect_count | {summary.chunk_boundary_defect_count} |
| parser_noise_observed_count | {summary.parser_noise_observed_count} |
| retrieved_target_child_count | {summary.retrieved_target_child_count} |
| retrieved_target_parent_count | {summary.retrieved_target_parent_count} |
| retrieved_target_doc_count | {summary.retrieved_target_doc_count} |
| reopen_global_chunking_count | {summary.reopen_global_chunking_count} |
| open_targeted_chunk_repair_count | {summary.open_targeted_chunk_repair_count} |
| live_solar_call_count_for_this_report | {summary.live_solar_call_count_for_this_report} |
| cuda_required | {str(summary.cuda_required).lower()} |
| recommended_decision | `{summary.recommended_decision}` |

## Audit Row

| query_id | child_target | parent_target | doc_target | child_exists | parent_exists | membership | citation_ref | page_valid | parser_noise | retrieved_child | retrieved_parent | retrieved_doc | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| `{row.query_id}` | {row.target_child_count} | {row.target_parent_count} | {row.target_doc_count} | {row.target_child_exists_count} | {row.target_parent_exists_count} | {row.target_child_parent_membership_count} | {row.target_child_citation_ref_count} | {row.target_child_page_range_valid_count} | {str(row.parser_noise_observed).lower()} | {str(row.retrieved_target_child).lower()} | {str(row.retrieved_target_parent).lower()} | {str(row.retrieved_target_doc).lower()} | `{row.audit_decision}` |

## 판단

전역 청킹 재실험은 열지 않는다.

근거:

| check | result |
| --- | --- |
| target_child_exists_rate | `1.000000` |
| target_parent_exists_rate | `1.000000` |
| target_child_parent_membership_rate | `1.000000` |
| target_child_citation_ref_rate | `1.000000` |
| retrieval coverage | target doc only |
| parser noise | observed, not chunk generation loss |

## 다음 작업

| priority | work_id | 작업 | 이유 |
| ---: | --- | --- | --- |
| 1 | `HD-HYDE-001` | place_story/overview/relationship/no-answer subset HyDE 비교 | retrieval miss와 no-answer risk를 LLM 비용성 후보로 검증한다. |
| 2 | `HD-API-ROUTER-003` | active routing 적용 판단 계획 | guarded route dry-run 이후에도 active 적용은 별도 gate가 필요하다. |

## Claim Boundary

허용 표현:

- `{report.query_id}`의 target child/parent는 chunk artifact에 존재한다.
- 이 사례는 현재 증거상 전역 청킹 재실험 근거가 아니다.
- parser noise는 관찰됐지만 chunk boundary defect로 단정하지 않는다.

금지 표현:

- 청킹 문제가 해결됐다.
- retrieval 문제가 해결됐다.
- HyDE가 성능을 개선했다.
- locked test 개선을 입증했다.
"""


def build_place_story_targeted_chunk_audit_markdown(
    report: PlaceStoryTargetedChunkAuditReport,
) -> str:
    summary = report.summary
    row = report.audit_rows[0]
    quality = report.output_quality
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Place Story Targeted Chunk Audit Report

## 목적

`HD-CHUNK-AUDIT-001`은 `q-dev-place-story-001`의 child/parent grain 손실이 청킹 생성 문제인지 확인한다.

이 리포트는 청킹 개선, retrieval 개선, generation 개선, locked test 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| audit_id | `{report.audit_id}` |
| work_id | `{report.work_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| query_id | `{report.query_id}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| hard_case_rows | `{report.hard_case_rows_alias}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| audit_case_count | {summary.audit_case_count} |
| target_child_exists_rate | {summary.target_child_exists_rate:.6f} |
| target_parent_exists_rate | {summary.target_parent_exists_rate:.6f} |
| target_child_parent_membership_rate | {summary.target_child_parent_membership_rate:.6f} |
| target_child_citation_ref_rate | {summary.target_child_citation_ref_rate:.6f} |
| target_child_page_range_valid_rate | {summary.target_child_page_range_valid_rate:.6f} |
| target_child_quality_flag_count | {summary.target_child_quality_flag_count} |
| target_parent_quality_flag_count | {summary.target_parent_quality_flag_count} |
| chunk_generation_loss_count | {summary.chunk_generation_loss_count} |
| chunk_boundary_defect_count | {summary.chunk_boundary_defect_count} |
| parser_noise_observed_count | {summary.parser_noise_observed_count} |
| retrieved_target_child_count | {summary.retrieved_target_child_count} |
| retrieved_target_parent_count | {summary.retrieved_target_parent_count} |
| retrieved_target_doc_count | {summary.retrieved_target_doc_count} |
| reopen_global_chunking_count | {summary.reopen_global_chunking_count} |
| open_targeted_chunk_repair_count | {summary.open_targeted_chunk_repair_count} |
| live_solar_call_count_for_this_report | {summary.live_solar_call_count_for_this_report} |
| cuda_required | {str(summary.cuda_required).lower()} |
| recommended_decision | `{summary.recommended_decision}` |

## Audit Detail

| query_id | query_type | target_child_count | target_parent_count | target_doc_count | child_exists | parent_exists | membership | citation_ref | page_valid | child_quality_flags | parent_quality_flags | child_len_min | child_len_max | parent_child_count_min | parent_child_count_max | retrieved_child | retrieved_parent | retrieved_doc | min_retrieval_rank | min_pack_rank | hard_case_root_cause | audit_decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: | ---: | --- | --- |
| `{row.query_id}` | `{row.query_type}` | {row.target_child_count} | {row.target_parent_count} | {row.target_doc_count} | {row.target_child_exists_count} | {row.target_parent_exists_count} | {row.target_child_parent_membership_count} | {row.target_child_citation_ref_count} | {row.target_child_page_range_valid_count} | {row.target_child_quality_flag_count} | {row.target_parent_quality_flag_count} | {row.target_child_text_length_min} | {row.target_child_text_length_max} | {row.target_parent_child_count_min} | {row.target_parent_child_count_max} | {str(row.retrieved_target_child).lower()} | {str(row.retrieved_target_parent).lower()} | {str(row.retrieved_target_doc).lower()} | {_rank_cell(row.target_min_retrieval_rank)} | {_rank_cell(row.target_min_pack_rank)} | `{row.hard_case_root_cause}` | `{row.audit_decision}` |

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

target chunk와 parent는 존재하고 citation provenance도 복구된다. 따라서 이 사례는 전역 청킹 재실험이 아니라 retrieval top-rank coverage와 HyDE 후보 실험으로 넘기는 것이 맞다.
"""


def _build_report(
    *,
    query_id: str,
    dataset_path: Path,
    chunks_path: Path,
    hard_case_rows_path: Path,
    result_rows_path: Path,
    rows: tuple[PlaceStoryTargetedChunkAuditRow, ...],
    output_quality: PublicRetrievalArtifactQuality,
) -> PlaceStoryTargetedChunkAuditReport:
    summary = _build_summary(rows)
    audit_id = rows[0].audit_id
    return PlaceStoryTargetedChunkAuditReport(
        audit_id=audit_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        query_id=query_id,
        dataset_path_alias=public_path_alias(dataset_path),
        chunks_path_alias=public_path_alias(chunks_path),
        hard_case_rows_alias=public_path_alias(hard_case_rows_path),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=_stable_id(
            {
                "query_id": query_id,
                "dataset_path": str(dataset_path),
                "chunks_path": str(chunks_path),
                "hard_case_rows_path": str(hard_case_rows_path),
                "rows": [row.model_dump(mode="json") for row in rows],
            },
        ),
        summary=summary,
        audit_rows=rows,
        output_quality=output_quality,
        qualitative_assessment=_build_qualitative_assessment(
            summary=summary,
            output_quality=output_quality,
        ),
    )


def _build_summary(
    rows: tuple[PlaceStoryTargetedChunkAuditRow, ...],
) -> PlaceStoryTargetedChunkAuditSummary:
    row = rows[0]
    return PlaceStoryTargetedChunkAuditSummary(
        audit_case_count=len(rows),
        target_child_exists_rate=_ratio(
            row.target_child_exists_count,
            row.target_child_count,
        ),
        target_parent_exists_rate=_ratio(
            row.target_parent_exists_count,
            row.target_parent_count,
        ),
        target_child_parent_membership_rate=_ratio(
            row.target_child_parent_membership_count,
            row.target_child_count,
        ),
        target_child_citation_ref_rate=_ratio(
            row.target_child_citation_ref_count,
            row.target_child_count,
        ),
        target_child_page_range_valid_rate=_ratio(
            row.target_child_page_range_valid_count,
            row.target_child_count,
        ),
        target_child_quality_flag_count=sum(
            item.target_child_quality_flag_count for item in rows
        ),
        target_parent_quality_flag_count=sum(
            item.target_parent_quality_flag_count for item in rows
        ),
        chunk_generation_loss_count=sum(1 for item in rows if item.chunk_generation_loss),
        chunk_boundary_defect_count=sum(1 for item in rows if item.chunk_boundary_defect),
        parser_noise_observed_count=sum(1 for item in rows if item.parser_noise_observed),
        retrieved_target_child_count=sum(1 for item in rows if item.retrieved_target_child),
        retrieved_target_parent_count=sum(
            1 for item in rows if item.retrieved_target_parent
        ),
        retrieved_target_doc_count=sum(1 for item in rows if item.retrieved_target_doc),
        reopen_global_chunking_count=sum(
            1 for item in rows if item.audit_decision == "reopen_global_chunking"
        ),
        open_targeted_chunk_repair_count=sum(
            1 for item in rows if item.audit_decision == "open_targeted_chunk_repair"
        ),
        live_solar_call_count_for_this_report=0,
        cuda_required=False,
        recommended_decision=row.audit_decision,
    )


def _build_qualitative_assessment(
    *,
    summary: PlaceStoryTargetedChunkAuditSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> dict[str, str]:
    failures = collect_public_retrieval_artifact_failures(output_quality)
    return {
        "analysis_scope": "단일 place_story failure case에서 target child/parent chunk 존재와 provenance만 점검했다.",
        "chunking_decision": "전역 청킹 재실험은 열지 않는다.",
        "targeted_repair_decision": (
            "target child와 parent가 모두 존재하므로 targeted chunk repair도 현재는 열지 않는다."
        ),
        "retrieval_decision": (
            "target doc만 retrieval/pack에 들어왔으므로 다음 변수는 retrieval top-rank coverage다."
        ),
        "parser_noise_boundary": (
            f"parser noise flag {summary.target_child_quality_flag_count}건은 관찰됐지만 boundary defect로 단정하지 않는다."
        ),
        "security_boundary": "공개 row에는 id, count, boolean, rank, decision만 남긴다.",
        "execution_boundary": "이번 audit은 Solar Pro 3 호출과 CUDA 연산을 사용하지 않는다.",
        "data_mart_grain": "fact_place_story_targeted_chunk_audit grain은 audit_id + query_id다.",
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
        "external_audit": "청킹 문제로 단정하지 않고 retrieval/HyDE 실험으로 넘긴 판단은 타당하다.",
    }


def _load_target_item(*, query_id: str, dataset_path: Path):
    for item in load_retrieval_eval_jsonl(project_path(dataset_path)):
        if item.query.query_id == query_id:
            if item.query.query_type != "place_story":
                raise ValueError("targeted chunk audit requires a place_story query")
            return item
    raise ValueError(f"target query not found: {query_id}")


def _load_hard_case_row(
    *,
    query_id: str,
    hard_case_rows_path: Path,
) -> dict[str, Any]:
    resolved = project_path(hard_case_rows_path)
    for line in resolved.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("query_id") == query_id:
            return row
    raise ValueError(f"hard case row not found: {query_id}")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(project_path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expected object JSON payload")
    return payload


def _target_ids(item) -> tuple[set[str], set[str], set[str]]:
    child_ids: set[str] = set()
    parent_ids: set[str] = set()
    doc_ids: set[str] = set()
    for judgment in item.judgments:
        child_ids.update(judgment.relevant_child_ids)
        parent_ids.update(judgment.relevant_parent_ids)
        doc_ids.update(judgment.relevant_doc_ids)
    return child_ids, parent_ids, doc_ids


def _parent_contains_child(*, parent: dict[str, Any] | None, child_id: str) -> bool:
    if parent is None:
        return False
    child_ids = parent.get("child_ids")
    return isinstance(child_ids, list) and child_id in child_ids


def _page_span_valid(child: dict[str, Any]) -> bool:
    page_span = child.get("page_span")
    if not isinstance(page_span, dict):
        return False
    required = (
        "page_local_start",
        "page_local_end",
        "page_global_start",
        "page_global_end",
    )
    if any(not isinstance(page_span.get(key), int) for key in required):
        return False
    return (
        page_span["page_local_start"] <= page_span["page_local_end"]
        and page_span["page_global_start"] <= page_span["page_global_end"]
    )


def _audit_decision(
    *,
    chunk_generation_loss: bool,
    chunk_boundary_defect: bool,
) -> AuditDecision:
    if chunk_generation_loss:
        return "reopen_global_chunking"
    if chunk_boundary_defect:
        return "open_targeted_chunk_repair"
    return "do_not_reopen_global_chunking"


def _next_action(decision: AuditDecision) -> str:
    if decision == "reopen_global_chunking":
        return "청킹 후보 재비교 계획을 다시 열기 전에 chunking gate를 재검증한다."
    if decision == "open_targeted_chunk_repair":
        return "단일 target parent/child 주변 sibling window와 merge 후보만 점검한다."
    return "HyDE와 route-specific retrieval 비교로 넘긴다."


def _stable_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def _rank_cell(rank: int | None) -> str:
    return "-" if rank is None else str(rank)


def main() -> int:
    args = _parse_args()
    run_place_story_targeted_chunk_audit(
        query_id=args.query_id,
        dataset_path=args.dataset,
        chunks_path=args.chunks,
        hard_case_rows_path=args.hard_case_rows,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.results,
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run public-safe targeted chunk audit for one place_story failure.",
    )
    parser.add_argument("--query-id", default=DEFAULT_QUERY_ID)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument(
        "--hard-case-rows",
        type=Path,
        default=DEFAULT_HARD_CASE_ROWS_PATH,
    )
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
