from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

import app.core.project_paths as project_paths
import app.infrastructure.index.dense as dense_module
from app.infrastructure.index.late_interaction import (
    LateInteractionConfig,
    LateInteractionScoreBatch,
)
from pipelines.run_colbert_late_interaction_hard_subset import (
    WORK_ID,
    count_target_resolvability_failures,
    run_colbert_late_interaction_hard_subset,
    select_colbert_hard_subset,
)


def test_colbert_hard_subset_public_artifacts_record_actual_decision() -> None:
    report = Path("evals/reports/colbert_late_interaction_hard_subset_report.md")
    doc = Path("docs/COLBERT_LATE_INTERACTION_HARD_SUBSET.md")

    report_text = report.read_text(encoding="utf-8")
    doc_text = doc.read_text(encoding="utf-8")

    assert "`HD-COLBERT-001C`" in report_text
    assert "selected_query_count | 21" in report_text
    assert "target_resolvability_fail_count | 0" in report_text
    assert "locked_test_execution_count | 0" in report_text
    assert "solar_call_count | 0" in report_text
    assert "colbert_style_late_interaction_top50_cuda | 0.809524" in report_text
    assert "0.022222" in report_text
    assert "-0.021670" in report_text
    assert "reject_default_keep_as_experiment_result" in doc_text
    assert "private file path" in report_text
    assert not _contains_private_leakage(report_text + doc_text)


def test_select_colbert_hard_subset_uses_reviewed_dev_hard_target_types(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload("q-place", "place_story", "hard", "child-place"),
            _eval_item_payload("q-route", "route_context", "hard", "child-route"),
            _eval_item_payload("q-overview", "overview", "hard", "child-overview"),
            _eval_item_payload("q-medium", "place_story", "medium", "child-medium"),
        ],
    )

    from app.domain.retrieval import load_retrieval_eval_jsonl

    selected = select_colbert_hard_subset(load_retrieval_eval_jsonl(dataset_path))

    assert [item.query.query_id for item in selected] == ["q-place", "q-route"]


def test_count_target_resolvability_failures_detects_missing_targets() -> None:
    from app.domain.retrieval import RetrievalDocument, load_retrieval_eval_jsonl
    from app.domain.data_contracts import PageSpan

    items_path = Path("evals/datasets/retrieval_eval_seed.jsonl")
    items = load_retrieval_eval_jsonl(items_path)[:1]
    documents = [
        RetrievalDocument(
            retrieval_doc_id="not-target",
            child_id="not-target",
            parent_id="not-target-parent",
            doc_id="not-target-doc",
            doc_title="doc",
            page_span=PageSpan(
                page_local_start=1,
                page_local_end=1,
                page_global_start=1,
                page_global_end=1,
            ),
            source_block_ids=["block-a"],
            text_hash="a" * 32,
            text_length=10,
            element_type_mix={"paragraph": 1},
            citation_block_ids=["block-a"],
        )
    ]

    assert count_target_resolvability_failures(items=items, documents=documents) == 1


def test_run_colbert_late_interaction_hard_subset_writes_public_safe_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(
        dense_module,
        "_load_sentence_transformer_model",
        lambda config: _FakeSentenceTransformerModel(),
    )
    chunks_path = tmp_path / "private_data" / "reports" / "parent_child_chunks.json"
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    results_dir = tmp_path / "private_data" / "evals" / "results"
    embedding_cache_dir = tmp_path / "private_data" / "embeddings"
    report_path = tmp_path / "evals" / "reports" / "colbert_report.md"
    doc_path = tmp_path / "docs" / "colbert_doc.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload("child-place", "parent-place", "doc-place", "palace story"),
                _child_payload(
                    "child-relationship",
                    "parent-relationship",
                    "doc-relationship",
                    "king minister relation",
                ),
                _child_payload("child-route", "parent-route", "doc-route", "route wall"),
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload("q-place", "place_story", "hard", "child-place"),
            _eval_item_payload(
                "q-relationship",
                "relationship",
                "hard",
                "child-relationship",
            ),
            _eval_item_payload("q-route", "route_context", "hard", "child-route"),
        ],
    )

    report = run_colbert_late_interaction_hard_subset(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_dir=results_dir,
        report_path=report_path,
        doc_path=doc_path,
        embedding_cache_dir=embedding_cache_dir,
        place_catalog_path=Path.cwd() / "data_samples" / "place_catalog_seed.json",
        top_k=2,
        candidate_ks=(2,),
        scorer_factory=lambda config: _FakeLateInteractionScorer(config),
    )

    report_text = report_path.read_text(encoding="utf-8")
    doc_text = doc_path.read_text(encoding="utf-8")
    rows_text = (results_dir / "colbert_hard_subset_rows.jsonl").read_text(
        encoding="utf-8",
    )
    assert report.work_id == WORK_ID
    assert len(report.selected_items) == 3
    assert report.target_resolvability_fail_count == 0
    assert "baseline_dense_e5_voice_rewrite" in report_text
    assert "colbert_style_late_interaction_top2_cuda" in report_text
    assert "private source text" not in report_text
    assert "palace story" not in report_text
    assert "raw query" in report_text
    assert "chunk text" in report_text
    assert "ColBERT-style Late Interaction Hard Subset" in doc_text
    assert "colbert_style_late_interaction_top2_cuda" in rows_text
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert report.output_quality.public_raw_text_leakage_count == 0


class _FakeSentenceTransformerModel:
    def encode(
        self,
        texts: list[str],
        batch_size: int,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray:
        del batch_size, convert_to_numpy, normalize_embeddings, show_progress_bar
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    1.0 if "place" in lowered or "palace" in lowered else 0.0,
                    1.0 if "relationship" in lowered or "relation" in lowered else 0.0,
                    1.0 if "route" in lowered else 0.0,
                ]
            )
        return np.asarray(vectors, dtype=np.float32)


class _FakeLateInteractionScorer:
    def __init__(self, config: LateInteractionConfig) -> None:
        self.config = config

    def score(self, query_text, documents):  # noqa: ANN001, ANN201
        del query_text
        return LateInteractionScoreBatch(
            scores=[float(index + 1) for index, _document in enumerate(documents)],
            cuda_memory_peak_mb=42.0,
        )


def _child_payload(
    child_id: str,
    parent_id: str,
    doc_id: str,
    text: str,
) -> dict[str, object]:
    block_id = f"block-{child_id}"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "child_id": child_id,
        "parent_id": parent_id,
        "doc_id": doc_id,
        "doc_title": f"title-{doc_id}",
        "parser_run_id": "parser-test",
        "source_block_ids": [block_id],
        "context_block_ids": [],
        "page_span": {
            "page_local_start": 1,
            "page_local_end": 1,
            "page_global_start": 1,
            "page_global_end": 1,
        },
        "text_hash": digest,
        "text_length": len(text),
        "element_type_mix": {"paragraph": 1},
        "citation_refs": [
            {
                "block_id": block_id,
                "doc_id": doc_id,
                "element_type": "paragraph",
                "page_span": {
                    "page_local_start": 1,
                    "page_local_end": 1,
                    "page_global_start": 1,
                    "page_global_end": 1,
                },
                "element_refs": [
                    {
                        "element_id": f"element-{child_id}",
                        "element_type": "paragraph",
                        "element_index": 0,
                    }
                ],
                "source_file_name": "source.pdf",
                "text_hash": digest,
                "text_length": len(text),
                "quality_flags": [],
            }
        ],
        "quality_flags": [],
        "public_allowed": False,
        "text": f"private source text {text}",
        "context_text": None,
    }


def _eval_item_payload(
    query_id: str,
    query_type: str,
    difficulty: str,
    child_id: str,
) -> dict[str, object]:
    parent_id = child_id.replace("child", "parent")
    doc_id = child_id.replace("child", "doc")
    return {
        "dataset_version": "retrieval-eval-dataset/v2",
        "query": {
            "query_id": query_id,
            "query_type": query_type,
            "query_text": f"{query_type} question",
            "language": "ko",
            "expected_behavior": "retrieve",
            "user_context": None,
            "public_allowed": True,
        },
        "judgments": [
            {
                "query_id": query_id,
                "relevant_child_ids": [child_id],
                "relevant_parent_ids": [parent_id],
                "relevant_doc_ids": [doc_id],
                "relevance_grade": 3,
                "rationale_summary": "target summary",
                "public_allowed": True,
            }
        ],
        "metadata": {
            "split": "dev",
            "difficulty": difficulty,
            "place_ids": [],
            "requires_context": False,
            "answerability": "answerable",
            "review_status": "reviewed",
        },
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _contains_private_leakage(text: str) -> bool:
    secret_marker = "UPSTAGE" + "_API" + "_KEY="
    private_marker = "private" + "_data/"
    return any(marker in text for marker in (secret_marker, "sk-", private_marker))
