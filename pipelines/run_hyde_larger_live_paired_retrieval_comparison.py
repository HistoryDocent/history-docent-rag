from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from app.core.project_paths import project_path
from app.domain.retrieval import QueryType, load_retrieval_eval_jsonl
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    write_public_retrieval_result_rows,
)
from app.providers.llm.solar_pro_3 import SolarPro3ProviderConfig
from pipelines.run_hyde_larger_dev_subset_readiness import (
    DEFAULT_EXPECTED_QUERY_COUNT_PER_TYPE,
    DEFAULT_LIVE_CALL_HARD_CAP,
    TARGET_QUERY_TYPES,
    build_hyde_larger_dev_readiness_rows,
    build_hyde_larger_dev_readiness_summary,
    _readiness_id as _larger_readiness_id,
)
from pipelines.run_hyde_live_paired_retrieval_comparison import (
    DEFAULT_TOP_K,
    HydeLivePairedRetrievalReport,
    HydePairRow,
    HydeRetrievalRunner,
    HydeTextProvider,
    PrivateHydeRetrievalRunner,
    _SolarHydeProvider,
    _build_pair_rows,
    _build_report,
    _format_query_type_delta_row,
    _format_report_pair_row,
    build_public_hyde_live_result_rows,
)
from pipelines.run_solar_generation_baseline import (
    DEFAULT_ENV_FILE_PATH,
    load_env_file_into_process,
)
from pipelines.run_solar_live_generation_smoke import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_DATASET_PATH,
    _validate_result_rows_path,
)


HYDE_LARGER_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION = (
    "hyde-larger-live-paired-retrieval-comparison-report/v1"
)
WORK_ID = "HD-HYDE-001D"
DEFAULT_DOC_PATH = (
    Path("docs") / "HYDE_LARGER_LIVE_PAIRED_RETRIEVAL_COMPARISON.md"
)
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "hyde_larger_live_paired_retrieval_comparison_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "hyde_larger_live_paired_retrieval_comparison_rows.jsonl"
)


def run_hyde_larger_live_paired_retrieval_comparison(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    env_file_path: Path | None = DEFAULT_ENV_FILE_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    target_query_types: tuple[QueryType, ...] = TARGET_QUERY_TYPES,
    expected_query_count_per_type: int = DEFAULT_EXPECTED_QUERY_COUNT_PER_TYPE,
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
    top_k: int = DEFAULT_TOP_K,
    hyde_provider: HydeTextProvider | None = None,
    retrieval_runner: HydeRetrievalRunner | None = None,
) -> HydeLivePairedRetrievalReport:
    _validate_result_rows_path(result_rows_path)
    readiness_rows = build_hyde_larger_dev_readiness_rows(
        dataset_path=dataset_path,
        target_query_types=target_query_types,
        expected_query_count_per_type=expected_query_count_per_type,
    )
    readiness_summary = build_hyde_larger_dev_readiness_summary(
        rows=readiness_rows,
        target_query_types=target_query_types,
        expected_query_count_per_type=expected_query_count_per_type,
        live_call_hard_cap=live_call_hard_cap,
    )
    readiness_id = _larger_readiness_id(
        rows=readiness_rows,
        summary=readiness_summary,
    )
    if readiness_summary.readiness_decision != "ready_for_hyde_larger_live_approval":
        raise ValueError("HyDE larger readiness gate is not ready for live approval")
    if readiness_summary.expected_hyde_generation_live_call_count > live_call_hard_cap:
        raise ValueError("HyDE larger live call hard cap would be exceeded")

    if hyde_provider is None and env_file_path is not None:
        load_env_file_into_process(env_file_path)
    provider = hyde_provider or _SolarHydeProvider(config=SolarPro3ProviderConfig.from_env())
    runner = retrieval_runner or PrivateHydeRetrievalRunner(
        chunks_path=chunks_path,
        top_k=top_k,
    )
    items_by_id = {
        item.query.query_id: item
        for item in load_retrieval_eval_jsonl(project_path(dataset_path))
    }
    items = [items_by_id[row.query_id] for row in readiness_rows]
    rows = _build_pair_rows(
        items=items,
        provider=provider,
        retrieval_runner=runner,
    )
    report = _build_larger_report(
        readiness_id=readiness_id,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        result_rows_path=result_rows_path,
        provider=provider,
        rows=rows,
        top_k=top_k,
        live_call_hard_cap=live_call_hard_cap,
        expected_query_count_per_type=expected_query_count_per_type,
        target_query_types=target_query_types,
        output_quality=PublicRetrievalArtifactQuality(
            result_row_count=0,
            report_version=HYDE_LARGER_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION,
            run_id="pending",
            public_raw_text_leakage_count=0,
            private_path_leakage_count=0,
            secret_like_leakage_count=0,
            forbidden_result_field_count=0,
        ),
    )
    public_rows = build_public_hyde_larger_live_result_rows(report)
    doc_text = build_hyde_larger_live_comparison_doc(report)
    report_text = build_hyde_larger_live_comparison_markdown(report)
    quality = measure_public_retrieval_artifact_quality(
        report_version=HYDE_LARGER_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION,
        run_id=report.comparison_id,
        result_rows=public_rows,
        report_text=report_text,
        extra_public_texts={
            f"doc:{line_number}": line
            for line_number, line in enumerate(doc_text.splitlines(), start=1)
        },
    )
    report = _build_larger_report(
        readiness_id=readiness_id,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        result_rows_path=result_rows_path,
        provider=provider,
        rows=rows,
        top_k=top_k,
        live_call_hard_cap=live_call_hard_cap,
        expected_query_count_per_type=expected_query_count_per_type,
        target_query_types=target_query_types,
        output_quality=quality,
    )
    failures = collect_hyde_larger_live_paired_retrieval_failures(
        report,
        expected_query_count_per_type=expected_query_count_per_type,
        target_query_types=target_query_types,
    )
    if failures:
        raise ValueError(f"HyDE larger live paired retrieval gate failed: {failures}")

    public_rows = build_public_hyde_larger_live_result_rows(report)
    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=public_rows,
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(
        build_hyde_larger_live_comparison_doc(report),
        encoding="utf-8",
    )
    resolved_report_path.write_text(
        build_hyde_larger_live_comparison_markdown(report),
        encoding="utf-8",
    )
    print(
        "hyde_larger_live_paired_retrieval "
        "status=PASS "
        f"query_count={report.comparison_summary.query_count} "
        f"hyde_generation_request_count="
        f"{report.comparison_summary.hyde_generation_request_count} "
        f"solar_api_call_count={report.comparison_summary.solar_api_call_count} "
        f"recall_at_5_delta={report.comparison_summary.recall_at_5_delta:.6f} "
        f"mrr_delta={report.comparison_summary.mrr_delta:.6f} "
        f"decision={report.comparison_summary.adoption_decision}",
    )
    return report


def _build_larger_report(
    *,
    readiness_id: str,
    dataset_path: Path,
    chunks_path: Path,
    result_rows_path: Path,
    provider: HydeTextProvider,
    rows: tuple[HydePairRow, ...],
    top_k: int,
    live_call_hard_cap: int,
    expected_query_count_per_type: int = DEFAULT_EXPECTED_QUERY_COUNT_PER_TYPE,
    target_query_types: tuple[QueryType, ...] = TARGET_QUERY_TYPES,
    output_quality: PublicRetrievalArtifactQuality,
) -> HydeLivePairedRetrievalReport:
    base = _build_report(
        readiness_id=readiness_id,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        result_rows_path=result_rows_path,
        provider=provider,
        rows=rows,
        top_k=top_k,
        live_call_hard_cap=live_call_hard_cap,
        output_quality=output_quality,
    )
    updated = base.model_copy(
        update={
            "report_version": HYDE_LARGER_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION,
            "work_id": WORK_ID,
            "output_quality": output_quality,
        },
    )
    return updated.model_copy(
        update={
            "qualitative_assessment": build_hyde_larger_live_assessment(
                updated,
                expected_query_count_per_type=expected_query_count_per_type,
                target_query_types=target_query_types,
            ),
        },
    )


def build_public_hyde_larger_live_result_rows(
    report: HydeLivePairedRetrievalReport,
) -> list[dict[str, Any]]:
    rows = build_public_hyde_live_result_rows(report)
    rows.extend(
        {
            "row_type": "query_type_delta",
            "comparison_id": report.comparison_id,
            "work_id": report.work_id,
            "query_type": row.query_type,
            "query_count": row.query_count,
            "baseline_recall_at_5": row.baseline_recall_at_5,
            "hyde_recall_at_5": row.hyde_recall_at_5,
            "recall_at_5_delta": row.recall_at_5_delta,
            "baseline_mrr": row.baseline_mrr,
            "hyde_mrr": row.hyde_mrr,
            "mrr_delta": row.mrr_delta,
        }
        for row in report.query_type_deltas
    )
    return rows


def collect_hyde_larger_live_paired_retrieval_failures(
    report: HydeLivePairedRetrievalReport,
    *,
    expected_query_count_per_type: int = DEFAULT_EXPECTED_QUERY_COUNT_PER_TYPE,
    target_query_types: tuple[QueryType, ...] = TARGET_QUERY_TYPES,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.comparison_summary
    expected_query_count = expected_query_count_per_type * len(target_query_types)
    expected_no_answer_count = expected_query_count_per_type
    expected_generation_count = expected_query_count - expected_no_answer_count
    if report.work_id != WORK_ID:
        failures.append("work_id_mismatch")
    if report.report_version != HYDE_LARGER_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION:
        failures.append("report_version_mismatch")
    if summary.query_count != expected_query_count:
        failures.append("query_count_mismatch")
    if summary.hyde_generation_request_count != expected_generation_count:
        failures.append("hyde_generation_request_count_mismatch")
    if summary.no_answer_guard_query_count != expected_no_answer_count:
        failures.append("no_answer_guard_count_mismatch")
    if any(
        row.query_type == "no_answer" and row.hyde_generation_request_count
        for row in report.rows
    ):
        failures.append("no_answer_hyde_generation_executed")
    if any(row.query_type == "no_answer" and row.hyde_candidate_count for row in report.rows):
        failures.append("no_answer_hyde_retrieval_executed")
    if any(
        row.query_type != "no_answer" and row.hyde_generation_request_count != 1
        for row in report.rows
    ):
        failures.append("answerable_hyde_generation_missing")
    if summary.hard_cap_exceeded:
        failures.append("live_call_hard_cap_exceeded")
    if summary.solar_api_call_count > summary.live_call_hard_cap:
        failures.append("solar_api_call_count_exceeds_hard_cap")
    if set(row.query_type for row in report.rows) != set(target_query_types):
        failures.append("target_query_type_mismatch")
    return failures


def build_hyde_larger_live_comparison_doc(
    report: HydeLivePairedRetrievalReport,
) -> str:
    summary = report.comparison_summary
    query_type_rows = "\n".join(
        _format_query_type_delta_row(row) for row in report.query_type_deltas
    )
    pair_rows = "\n".join(_format_doc_pair_row(row) for row in report.rows)
    return f"""# HyDE Larger Live Paired Retrieval Comparison

## 결론

`HD-HYDE-001D`는 Solar Pro 3 HyDE larger dev live paired retrieval comparison이다.

이 문서는 최종 성능 개선 주장이 아니다. `HD-HYDE-001C`에서 고정한 dev 40개 query로 baseline route와 HyDE query expansion 후보를 같은 target judgment로 비교한 결과다.

raw query, raw answer, raw evidence, raw HyDE text, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| baseline_retrieval_run_count | {summary.baseline_retrieval_run_count} |
| hyde_retrieval_run_count | {summary.hyde_retrieval_run_count} |
| hyde_generation_request_count | {summary.hyde_generation_request_count} |
| no_answer_guard_query_count | {summary.no_answer_guard_query_count} |
| solar_api_call_count | {summary.solar_api_call_count} |
| live_call_hard_cap | {summary.live_call_hard_cap} |
| Recall@5 delta | {summary.recall_at_5_delta:.6f} |
| MRR delta | {summary.mrr_delta:.6f} |
| nDCG@5 delta | {summary.ndcg_at_5_delta:.6f} |
| latency_p95_ms delta | {summary.latency_p95_ms_delta:.6f} |
| adoption_decision | `{summary.adoption_decision}` |

## Candidate Summary

| candidate | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | {report.baseline_summary.recall_at_1:.6f} | {report.baseline_summary.recall_at_3:.6f} | {report.baseline_summary.recall_at_5:.6f} | {report.baseline_summary.mrr:.6f} | {report.baseline_summary.ndcg_at_5:.6f} | {report.baseline_summary.latency_p95_ms:.6f} |
| HyDE | {report.hyde_summary.recall_at_1:.6f} | {report.hyde_summary.recall_at_3:.6f} | {report.hyde_summary.recall_at_5:.6f} | {report.hyde_summary.mrr:.6f} | {report.hyde_summary.ndcg_at_5:.6f} | {report.hyde_summary.latency_p95_ms:.6f} |

## Query Type Delta

| query_type | query_count | baseline Recall@5 | HyDE Recall@5 | Recall@5 delta | baseline MRR | HyDE MRR | MRR delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

## Query Pair Rows

| query_id | query_type | baseline_rank | hyde_rank | baseline@5 | hyde@5 | no_answer_guard | hyde_call |
| --- | --- | ---: | ---: | --- | --- | --- | ---: |
{pair_rows}

## 실행 경계

| boundary | value |
| --- | --- |
| readiness_id | `{report.readiness_id}` |
| model | `{report.model_id}` |
| prompt_policy | `{report.prompt_policy_id}` |
| provider | `{report.provider}` |
| endpoint_alias | `{report.endpoint_alias}` |
| resolved_device | `{report.resolved_device}` |
| chunking baseline | `C0 parent-child` |
| final citation | source child chunk only |
| no-answer policy | HyDE generation blocked |
| claim boundary | larger-live-dev-only |

## Claim Boundary

| claim | allowed |
| --- | --- |
| HyDE larger live paired retrieval comparison을 dev 40개에서 실행했다 | yes |
| no-answer query 10개는 HyDE generation과 retrieval에서 차단했다 | yes |
| Solar Pro 3 HyDE generation request 수를 기록했다 | yes |
| HyDE를 production 기본 retrieval route로 채택했다 | no |
| locked test 개선을 입증했다 | no |
| no-answer hallucination 문제가 해결됐다 | no |
"""


def build_hyde_larger_live_comparison_markdown(
    report: HydeLivePairedRetrievalReport,
) -> str:
    summary = report.comparison_summary
    quality = report.output_quality
    query_type_rows = "\n".join(
        _format_query_type_delta_row(row) for row in report.query_type_deltas
    )
    pair_rows = "\n".join(_format_report_pair_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# HyDE Larger Live Paired Retrieval Comparison Report

## 목적

`HD-HYDE-001D`는 `HD-HYDE-001C` readiness에서 고정한 dev 40개 query subset으로 Solar Pro 3 HyDE query expansion이 retrieval metric을 개선하는지 paired 비교한다.

이 리포트는 최종 성능 개선 주장이 아니다. raw query, raw answer, raw evidence, raw HyDE text, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| work_id | `{report.work_id}` |
| readiness_id | `{report.readiness_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| result_path | `{report.result_path}` |
| provider | `{report.provider}` |
| provider_config_id | `{report.provider_config_id}` |
| endpoint_alias | `{report.endpoint_alias}` |
| model_id | `{report.model_id}` |
| prompt_policy_id | `{report.prompt_policy_id}` |
| packing_policy_id | `{report.packing_policy_id}` |
| top_k | {report.top_k} |
| resolved_device | `{report.resolved_device}` |
| source_fingerprint | `{report.source_fingerprint}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| baseline_retrieval_run_count | {summary.baseline_retrieval_run_count} |
| hyde_retrieval_run_count | {summary.hyde_retrieval_run_count} |
| hyde_generation_request_count | {summary.hyde_generation_request_count} |
| no_answer_guard_query_count | {summary.no_answer_guard_query_count} |
| solar_api_call_count | {summary.solar_api_call_count} |
| live_call_hard_cap | {summary.live_call_hard_cap} |
| hard_cap_exceeded | {str(summary.hard_cap_exceeded).lower()} |
| prompt_tokens | {summary.prompt_tokens} |
| completion_tokens | {summary.completion_tokens} |
| total_tokens | {summary.total_tokens} |
| estimated_cost | {summary.estimated_cost:.6f} |
| recall_at_1_delta | {summary.recall_at_1_delta:.6f} |
| recall_at_3_delta | {summary.recall_at_3_delta:.6f} |
| recall_at_5_delta | {summary.recall_at_5_delta:.6f} |
| mrr_delta | {summary.mrr_delta:.6f} |
| ndcg_at_5_delta | {summary.ndcg_at_5_delta:.6f} |
| latency_p95_ms_delta | {summary.latency_p95_ms_delta:.6f} |
| adoption_decision | `{summary.adoption_decision}` |

## Candidate Metrics

| candidate | query_count | retrieve_query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_with_candidate_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | {report.baseline_summary.query_count} | {report.baseline_summary.retrieve_query_count} | {report.baseline_summary.recall_at_1:.6f} | {report.baseline_summary.recall_at_3:.6f} | {report.baseline_summary.recall_at_5:.6f} | {report.baseline_summary.mrr:.6f} | {report.baseline_summary.ndcg_at_5:.6f} | {report.baseline_summary.latency_p95_ms:.6f} | {report.baseline_summary.no_answer_with_candidate_count} |
| HyDE | {report.hyde_summary.query_count} | {report.hyde_summary.retrieve_query_count} | {report.hyde_summary.recall_at_1:.6f} | {report.hyde_summary.recall_at_3:.6f} | {report.hyde_summary.recall_at_5:.6f} | {report.hyde_summary.mrr:.6f} | {report.hyde_summary.ndcg_at_5:.6f} | {report.hyde_summary.latency_p95_ms:.6f} | {report.hyde_summary.no_answer_with_candidate_count} |

## Query Type Delta

| query_type | query_count | baseline Recall@5 | HyDE Recall@5 | Recall@5 delta | baseline MRR | HyDE MRR | MRR delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

## Query Pair Rows

| query_id | query_type | baseline_route | hyde_route | baseline_rank | hyde_rank | baseline@5 | hyde@5 | hyde_hash | hyde_len | solar_api_call |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: | ---: |
{pair_rows}

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

HyDE는 larger dev subset에서만 비교했다. 이 결과는 locked test 또는 production 성능 개선 주장이 아니다.
"""


def build_hyde_larger_live_assessment(
    report: HydeLivePairedRetrievalReport,
    *,
    expected_query_count_per_type: int = DEFAULT_EXPECTED_QUERY_COUNT_PER_TYPE,
    target_query_types: tuple[QueryType, ...] = TARGET_QUERY_TYPES,
) -> dict[str, str]:
    failures = collect_hyde_larger_live_paired_retrieval_failures(
        report,
        expected_query_count_per_type=expected_query_count_per_type,
        target_query_types=target_query_types,
    )
    return {
        "scope": "HD-HYDE-001C에서 고정한 dev 40개 query subset만 비교했다.",
        "chunking_boundary": "C0 parent-child chunking을 고정하고 청킹 변수를 새로 열지 않았다.",
        "llm_call_boundary": "answerable query 30개만 Solar Pro 3 HyDE generation을 실행한다.",
        "no_answer_boundary": "no_answer query 10개는 HyDE generation과 retrieval을 모두 차단한다.",
        "retrieval_boundary": "baseline과 HyDE 모두 같은 chunk corpus, 같은 top_k, 같은 route family를 사용한다.",
        "latency_boundary": "HyDE latency는 generation latency와 retrieval latency를 합산한다.",
        "cuda_boundary": "retrieval embedding 경로는 사용 가능하면 CUDA를 사용하며 report에 resolved_device를 기록한다.",
        "data_mart_grain": "`fact_hyde_larger_live_pair` grain은 comparison_id + query_id + candidate_id다.",
        "security_boundary": "public artifact에는 raw query, raw HyDE text, prompt, evidence text를 남기지 않는다.",
        "external_audit": "5개 subset 후보성을 40개로 확대했지만 locked test 전 채택 주장은 금지한다.",
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def _format_doc_pair_row(row: HydePairRow) -> str:
    return (
        f"| `{row.query_id}` | `{row.query_type}` | "
        f"{_rank_text(row.baseline_relevant_rank)} | {_rank_text(row.hyde_relevant_rank)} | "
        f"{str(row.baseline_hit_at_5).lower()} | {str(row.hyde_hit_at_5).lower()} | "
        f"{str(row.no_answer_guard_applied).lower()} | {row.hyde_generation_request_count} |"
    )


def _rank_text(rank: int | None) -> str:
    return "0" if rank is None else str(rank)


def main() -> int:
    args = _parse_args()
    report = run_hyde_larger_live_paired_retrieval_comparison(
        dataset_path=args.dataset,
        chunks_path=args.chunks,
        env_file_path=args.env_file,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.results,
        target_query_types=tuple(args.query_type or TARGET_QUERY_TYPES),
        expected_query_count_per_type=args.expected_query_count_per_type,
        live_call_hard_cap=args.live_call_hard_cap,
        top_k=args.top_k,
    )
    return 0 if not collect_hyde_larger_live_paired_retrieval_failures(report) else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Solar Pro 3 HyDE larger live paired retrieval comparison.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--query-type", action="append", default=None)
    parser.add_argument(
        "--expected-query-count-per-type",
        type=int,
        default=DEFAULT_EXPECTED_QUERY_COUNT_PER_TYPE,
    )
    parser.add_argument(
        "--live-call-hard-cap",
        type=int,
        default=DEFAULT_LIVE_CALL_HARD_CAP,
    )
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
