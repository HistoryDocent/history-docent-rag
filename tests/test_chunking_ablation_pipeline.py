from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.chunking import ChildChunk, chunking_report_to_dict
from app.domain.retrieval import RetrievedCandidate, RetrievalEvalItem, RetrievalRunResult
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
)
from pipelines.build_parent_child_chunks import build_parent_child_chunks_from_files
from pipelines.run_chunking_ablation import (
    _validate_public_output_quality,
    compute_source_block_retrieval_metrics,
    run_chunking_ablation,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _block_payload(
    *,
    block_id: str,
    element_type: str,
    element_id: str,
    element_index: int,
    text_length: int,
    page: int = 1,
) -> dict[str, object]:
    return {
        "block_id": block_id,
        "doc_id": "doc-one",
        "doc_title": "doc-one",
        "parser_run_id": "upstage-parser-test",
        "element_type": element_type,
        "page_span": {
            "page_local_start": page,
            "page_local_end": page,
            "page_global_start": page,
            "page_global_end": page,
        },
        "element_refs": [
            {
                "element_id": element_id,
                "element_type": element_type,
                "element_index": element_index,
            }
        ],
        "text_hash": f"{element_index + 1}" * 64,
        "text_length": text_length,
        "provenance": {
            "source_file_name": "doc-one.pdf",
            "parser_artifact_path_alias": "PARSER_DIR/doc-one/document_analysis_results.json",
            "extraction_method": "upstage_parser",
        },
        "quality_flags": [],
        "public_allowed": False,
    }


def _eval_item_payload(
    *,
    query_id: str,
    query_type: str,
    query_text: str,
    expected_behavior: str,
    split: str = "dev",
    review_status: str | None = None,
) -> dict[str, object]:
    judgments: list[dict[str, object]] = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": ["parent-doc-one-00000-00-child-0000"],
                "relevant_parent_ids": ["parent-doc-one-00000-00"],
                "relevant_doc_ids": ["doc-one"],
                "relevance_grade": 3,
                "rationale_summary": "target ids only",
                "public_allowed": True,
            }
        )
    return {
        "dataset_version": "retrieval-eval-dataset/v2",
        "query": {
            "query_id": query_id,
            "query_type": query_type,
            "query_text": query_text,
            "language": "ko",
            "expected_behavior": expected_behavior,
            "user_context": None,
            "public_allowed": True,
        },
        "judgments": judgments,
        "metadata": {
            "split": split,
            "difficulty": "medium",
            "place_ids": ["gyeongbokgung"] if expected_behavior == "retrieve" else [],
            "requires_context": False,
            "answerability": "answerable"
            if expected_behavior == "retrieve"
            else "unanswerable",
            "review_status": review_status
            or ("reviewed" if split == "dev" else "locked"),
        },
    }


def _fixture_source_root(tmp_path: Path) -> Path:
    source_root = tmp_path / "History_Docent"
    doc_dir = source_root / "01_Data_Preprocessing" / "doc-one"
    (source_root / "00_PDF_history").mkdir(parents=True)
    (source_root / "00_PDF_history" / "doc-one.pdf").write_bytes(b"%PDF doc-one")
    _write_json(
        doc_dir / "document_analysis_results.json",
        {
            "page_elements": {
                "1": {
                    "text_elements": [
                        {
                            "id": "heading",
                            "category": "heading1",
                            "page": 1,
                            "content": {"text": "경복궁"},
                        },
                        {
                            "id": "body-one",
                            "category": "paragraph",
                            "page": 1,
                            "content": {"text": "경복궁 한양 정도전 " * 20},
                        },
                        {
                            "id": "body-two",
                            "category": "paragraph",
                            "page": 1,
                            "content": {"text": "궁궐 정치 공간 " * 24},
                        },
                        {
                            "id": "body-three",
                            "category": "paragraph",
                            "page": 1,
                            "content": {"text": "서울 관광 도슨트 " * 22},
                        },
                    ],
                    "table_elements": [],
                    "image_elements": [],
                }
            }
        },
    )
    return source_root


def _normalized_blocks_path(tmp_path: Path) -> Path:
    path = tmp_path / "normalized_blocks.json"
    _write_json(
        path,
        {
            "normalized_blocks": [
                _block_payload(
                    block_id="block-heading",
                    element_type="heading1",
                    element_id="heading",
                    element_index=0,
                    text_length=3,
                ),
                _block_payload(
                    block_id="block-body-one",
                    element_type="paragraph",
                    element_id="body-one",
                    element_index=1,
                    text_length=220,
                ),
                _block_payload(
                    block_id="block-body-two",
                    element_type="paragraph",
                    element_id="body-two",
                    element_index=2,
                    text_length=210,
                ),
                _block_payload(
                    block_id="block-body-three",
                    element_type="paragraph",
                    element_id="body-three",
                    element_index=3,
                    text_length=220,
                ),
            ]
        },
    )
    return path


def _baseline_chunks_path(tmp_path: Path, normalized_blocks_path: Path, source_root: Path) -> Path:
    result = build_parent_child_chunks_from_files(
        normalized_blocks_path=normalized_blocks_path,
        source_root=source_root,
    )
    path = tmp_path / "parent_child_chunks.json"
    _write_json(path, chunking_report_to_dict(result=result, include_text=True))
    return path


def _load_children(path: Path) -> list[ChildChunk]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [ChildChunk.model_validate(child) for child in payload["children"]]


def test_run_chunking_ablation_writes_public_safe_report(tmp_path: Path) -> None:
    source_root = _fixture_source_root(tmp_path)
    normalized_blocks_path = _normalized_blocks_path(tmp_path)
    baseline_chunks_path = _baseline_chunks_path(
        tmp_path,
        normalized_blocks_path,
        source_root,
    )
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    report_path = tmp_path / "chunking_ablation_report.md"
    experiment_dir = tmp_path / "private_experiment"
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-dev-place_fact-001",
                query_type="place_fact",
                query_text="경복궁 한양 정도전",
                expected_behavior="retrieve",
            ),
            _eval_item_payload(
                query_id="q-dev-no_answer-001",
                query_type="no_answer",
                query_text="오늘 실시간 예약 가능 좌석",
                expected_behavior="abstain",
            ),
        ],
    )

    report = run_chunking_ablation(
        normalized_blocks_path=normalized_blocks_path,
        baseline_chunks_path=baseline_chunks_path,
        dataset_path=dataset_path,
        source_root=source_root,
        experiment_dir=experiment_dir,
        report_path=report_path,
        variants=["C0", "C1"],
        top_k=2,
    )
    report_text = report_path.read_text(encoding="utf-8")

    assert report.method == "bm25"
    assert report.split == "dev"
    assert report.dataset_query_count == 2
    assert [variant.variant_id for variant in report.variants] == ["C0", "C1"]
    assert report.variants[0].metric_summary.query_count == 2
    assert report.variants[0].metric_summary.recall_at_1 == 1.0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert collect_public_retrieval_artifact_failures(report.output_quality) == []
    assert (experiment_dir / "C0_parent_child_chunks.json").exists()
    assert (experiment_dir / "C1_parent_child_chunks.json").exists()
    assert "private source text" not in report_text
    assert "경복궁 한양 정도전 " * 3 not in report_text
    assert str(source_root) not in report_text
    assert str(experiment_dir).replace("\\", "/") not in report_text
    assert "locked test split은 사용하지 않는다" in report_text
    assert "source_block_ids 전체를 포함해야 relevant hit" in report_text


def test_chunking_ablation_rejects_test_split(tmp_path: Path) -> None:
    source_root = _fixture_source_root(tmp_path)
    normalized_blocks_path = _normalized_blocks_path(tmp_path)
    baseline_chunks_path = _baseline_chunks_path(
        tmp_path,
        normalized_blocks_path,
        source_root,
    )
    dataset_path = tmp_path / "retrieval_eval_test.jsonl"
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-test-place_fact-001",
                query_type="place_fact",
                query_text="경복궁 한양 정도전",
                expected_behavior="retrieve",
                split="test",
            )
        ],
    )

    with pytest.raises(ValueError, match="dev split only"):
        run_chunking_ablation(
            normalized_blocks_path=normalized_blocks_path,
            baseline_chunks_path=baseline_chunks_path,
            dataset_path=dataset_path,
            source_root=source_root,
            experiment_dir=tmp_path / "private_experiment",
            report_path=tmp_path / "report.md",
            variants=["C0"],
        )


def test_chunking_ablation_rejects_locked_review_status_in_dev_split(
    tmp_path: Path,
) -> None:
    source_root = _fixture_source_root(tmp_path)
    normalized_blocks_path = _normalized_blocks_path(tmp_path)
    baseline_chunks_path = _baseline_chunks_path(
        tmp_path,
        normalized_blocks_path,
        source_root,
    )
    dataset_path = tmp_path / "retrieval_eval_dev_locked.jsonl"
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-dev-place_fact-001",
                query_type="place_fact",
                query_text="경복궁 한양 정도전",
                expected_behavior="retrieve",
                split="dev",
                review_status="locked",
            )
        ],
    )

    with pytest.raises(ValueError, match="reviewed dev rows only"):
        run_chunking_ablation(
            normalized_blocks_path=normalized_blocks_path,
            baseline_chunks_path=baseline_chunks_path,
            dataset_path=dataset_path,
            source_root=source_root,
            experiment_dir=tmp_path / "private_experiment",
            report_path=tmp_path / "report.md",
            variants=["C0"],
        )


def test_chunking_ablation_rejects_variant_without_c0(tmp_path: Path) -> None:
    source_root = _fixture_source_root(tmp_path)
    normalized_blocks_path = _normalized_blocks_path(tmp_path)
    baseline_chunks_path = _baseline_chunks_path(
        tmp_path,
        normalized_blocks_path,
        source_root,
    )
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-dev-place_fact-001",
                query_type="place_fact",
                query_text="경복궁 한양 정도전",
                expected_behavior="retrieve",
            )
        ],
    )

    with pytest.raises(ValueError, match="C0 baseline variant is required"):
        run_chunking_ablation(
            normalized_blocks_path=normalized_blocks_path,
            baseline_chunks_path=baseline_chunks_path,
            dataset_path=dataset_path,
            source_root=source_root,
            experiment_dir=tmp_path / "private_experiment",
            report_path=tmp_path / "report.md",
            variants=["C1"],
        )


def test_source_block_metrics_require_full_child_source_block_match(
    tmp_path: Path,
) -> None:
    source_root = _fixture_source_root(tmp_path)
    normalized_blocks_path = _normalized_blocks_path(tmp_path)
    baseline_chunks_path = _baseline_chunks_path(
        tmp_path,
        normalized_blocks_path,
        source_root,
    )
    baseline_children = _load_children(baseline_chunks_path)
    baseline_child = next(
        child for child in baseline_children if len(child.source_block_ids) > 1
    )
    target_payload = _eval_item_payload(
        query_id="q-dev-place_fact-001",
        query_type="place_fact",
        query_text="경복궁 한양 정도전",
        expected_behavior="retrieve",
    )
    target_payload["judgments"][0]["relevant_child_ids"] = [baseline_child.child_id]
    item = RetrievalEvalItem.model_validate(target_payload)
    partial_source_block_ids = [baseline_child.source_block_ids[0]]
    partial_candidate = baseline_child.model_copy(
        update={
            "child_id": "variant-partial-child",
            "source_block_ids": partial_source_block_ids,
            "citation_refs": [
                ref
                for ref in baseline_child.citation_refs
                if ref.block_id in set(partial_source_block_ids)
            ],
        }
    )
    partial_result = RetrievalRunResult(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        method="bm25",
        latency_ms=1.0,
        candidates=[
            RetrievedCandidate(
                rank=1,
                retrieval_doc_id=partial_candidate.child_id,
                child_id=partial_candidate.child_id,
                parent_id=partial_candidate.parent_id,
                doc_id=partial_candidate.doc_id,
                score=1.0,
            )
        ],
    )
    partial_metric = compute_source_block_retrieval_metrics(
        items=[item],
        results=[partial_result],
        candidate_child_by_id={partial_candidate.child_id: partial_candidate},
        baseline_child_by_id={baseline_child.child_id: baseline_child},
        baseline_children_by_parent_id={baseline_child.parent_id: [baseline_child]},
        baseline_children_by_doc_id={baseline_child.doc_id: [baseline_child]},
    )

    assert partial_metric.recall_at_1 == 0.0
    assert partial_metric.mrr == 0.0

    full_candidate = baseline_child.model_copy(update={"child_id": "variant-full-child"})
    full_result = partial_result.model_copy(
        update={
            "candidates": [
                RetrievedCandidate(
                    rank=1,
                    retrieval_doc_id=full_candidate.child_id,
                    child_id=full_candidate.child_id,
                    parent_id=full_candidate.parent_id,
                    doc_id=full_candidate.doc_id,
                    score=1.0,
                )
            ]
        }
    )
    full_metric = compute_source_block_retrieval_metrics(
        items=[item],
        results=[full_result],
        candidate_child_by_id={full_candidate.child_id: full_candidate},
        baseline_child_by_id={baseline_child.child_id: baseline_child},
        baseline_children_by_parent_id={baseline_child.parent_id: [baseline_child]},
        baseline_children_by_doc_id={baseline_child.doc_id: [baseline_child]},
    )

    assert full_metric.recall_at_1 == 1.0
    assert full_metric.mrr == 1.0


def test_source_block_metrics_use_stable_parent_identifier(
    tmp_path: Path,
) -> None:
    source_root = _fixture_source_root(tmp_path)
    normalized_blocks_path = _normalized_blocks_path(tmp_path)
    baseline_chunks_path = _baseline_chunks_path(
        tmp_path,
        normalized_blocks_path,
        source_root,
    )
    baseline_child = _load_children(baseline_chunks_path)[0]
    target_payload = _eval_item_payload(
        query_id="q-dev-place_story-001",
        query_type="place_story",
        query_text="경복궁 이야기",
        expected_behavior="retrieve",
    )
    target_payload["judgments"][0]["relevant_child_ids"] = []
    target_payload["judgments"][0]["relevant_parent_ids"] = [baseline_child.parent_id]
    target_payload["judgments"][0]["relevant_doc_ids"] = []
    item = RetrievalEvalItem.model_validate(target_payload)
    wrong_parent_candidate = baseline_child.model_copy(
        update={"child_id": "wrong-parent-child", "parent_id": "other-parent"}
    )
    wrong_parent_result = RetrievalRunResult(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        method="bm25",
        latency_ms=1.0,
        candidates=[
            RetrievedCandidate(
                rank=1,
                retrieval_doc_id=wrong_parent_candidate.child_id,
                child_id=wrong_parent_candidate.child_id,
                parent_id=wrong_parent_candidate.parent_id,
                doc_id=wrong_parent_candidate.doc_id,
                score=1.0,
            )
        ],
    )

    wrong_parent_metric = compute_source_block_retrieval_metrics(
        items=[item],
        results=[wrong_parent_result],
        candidate_child_by_id={wrong_parent_candidate.child_id: wrong_parent_candidate},
        baseline_child_by_id={baseline_child.child_id: baseline_child},
        baseline_children_by_parent_id={baseline_child.parent_id: [baseline_child]},
        baseline_children_by_doc_id={baseline_child.doc_id: [baseline_child]},
    )

    assert wrong_parent_metric.recall_at_1 == 0.0

    partial_source_block_ids = [baseline_child.source_block_ids[0]]
    same_parent_candidate = baseline_child.model_copy(
        update={
            "child_id": "same-parent-partial-child",
            "source_block_ids": partial_source_block_ids,
            "citation_refs": [
                ref
                for ref in baseline_child.citation_refs
                if ref.block_id in set(partial_source_block_ids)
            ],
        }
    )
    same_parent_result = wrong_parent_result.model_copy(
        update={
            "candidates": [
                RetrievedCandidate(
                    rank=1,
                    retrieval_doc_id=same_parent_candidate.child_id,
                    child_id=same_parent_candidate.child_id,
                    parent_id=same_parent_candidate.parent_id,
                    doc_id=same_parent_candidate.doc_id,
                    score=1.0,
                )
            ]
        }
    )
    same_parent_metric = compute_source_block_retrieval_metrics(
        items=[item],
        results=[same_parent_result],
        candidate_child_by_id={same_parent_candidate.child_id: same_parent_candidate},
        baseline_child_by_id={baseline_child.child_id: baseline_child},
        baseline_children_by_parent_id={baseline_child.parent_id: [baseline_child]},
        baseline_children_by_doc_id={baseline_child.doc_id: [baseline_child]},
    )

    assert same_parent_metric.recall_at_1 == 1.0


def test_source_block_metrics_use_stable_doc_identifier(tmp_path: Path) -> None:
    source_root = _fixture_source_root(tmp_path)
    normalized_blocks_path = _normalized_blocks_path(tmp_path)
    baseline_chunks_path = _baseline_chunks_path(
        tmp_path,
        normalized_blocks_path,
        source_root,
    )
    baseline_child = _load_children(baseline_chunks_path)[0]
    target_payload = _eval_item_payload(
        query_id="q-dev-overview-001",
        query_type="overview",
        query_text="문서 개요",
        expected_behavior="retrieve",
    )
    target_payload["judgments"][0]["relevant_child_ids"] = []
    target_payload["judgments"][0]["relevant_parent_ids"] = []
    target_payload["judgments"][0]["relevant_doc_ids"] = [baseline_child.doc_id]
    item = RetrievalEvalItem.model_validate(target_payload)
    wrong_doc_candidate = baseline_child.model_copy(
        update={"child_id": "wrong-doc-child", "doc_id": "other-doc"}
    )
    wrong_doc_result = RetrievalRunResult(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        method="bm25",
        latency_ms=1.0,
        candidates=[
            RetrievedCandidate(
                rank=1,
                retrieval_doc_id=wrong_doc_candidate.child_id,
                child_id=wrong_doc_candidate.child_id,
                parent_id=wrong_doc_candidate.parent_id,
                doc_id=wrong_doc_candidate.doc_id,
                score=1.0,
            )
        ],
    )

    wrong_doc_metric = compute_source_block_retrieval_metrics(
        items=[item],
        results=[wrong_doc_result],
        candidate_child_by_id={wrong_doc_candidate.child_id: wrong_doc_candidate},
        baseline_child_by_id={baseline_child.child_id: baseline_child},
        baseline_children_by_parent_id={baseline_child.parent_id: [baseline_child]},
        baseline_children_by_doc_id={baseline_child.doc_id: [baseline_child]},
    )

    assert wrong_doc_metric.recall_at_1 == 0.0

    partial_source_block_ids = [baseline_child.source_block_ids[0]]
    same_doc_candidate = baseline_child.model_copy(
        update={
            "child_id": "same-doc-partial-child",
            "source_block_ids": partial_source_block_ids,
            "citation_refs": [
                ref
                for ref in baseline_child.citation_refs
                if ref.block_id in set(partial_source_block_ids)
            ],
        }
    )
    same_doc_result = wrong_doc_result.model_copy(
        update={
            "candidates": [
                RetrievedCandidate(
                    rank=1,
                    retrieval_doc_id=same_doc_candidate.child_id,
                    child_id=same_doc_candidate.child_id,
                    parent_id=same_doc_candidate.parent_id,
                    doc_id=same_doc_candidate.doc_id,
                    score=1.0,
                )
            ]
        }
    )
    same_doc_metric = compute_source_block_retrieval_metrics(
        items=[item],
        results=[same_doc_result],
        candidate_child_by_id={same_doc_candidate.child_id: same_doc_candidate},
        baseline_child_by_id={baseline_child.child_id: baseline_child},
        baseline_children_by_parent_id={baseline_child.parent_id: [baseline_child]},
        baseline_children_by_doc_id={baseline_child.doc_id: [baseline_child]},
    )

    assert same_doc_metric.recall_at_1 == 1.0


@pytest.mark.parametrize(
    "field_name",
    [
        "public_raw_text_leakage_count",
        "private_path_leakage_count",
        "secret_like_leakage_count",
        "forbidden_result_field_count",
    ],
)
def test_chunking_ablation_public_output_gate_fails_closed(field_name: str) -> None:
    payload = {
        "result_row_count": 0,
        "report_version": "chunking-ablation-report/v1",
        "run_id": "test-run",
        "public_raw_text_leakage_count": 0,
        "private_path_leakage_count": 0,
        "secret_like_leakage_count": 0,
        "forbidden_result_field_count": 0,
    }
    payload[field_name] = 1

    with pytest.raises(ValueError, match="public output gate failed"):
        _validate_public_output_quality(
            PublicRetrievalArtifactQuality.model_validate(payload)
        )
