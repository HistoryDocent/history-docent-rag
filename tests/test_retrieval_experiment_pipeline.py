from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core import project_paths
from app.domain.retrieval_experiment import collect_public_retrieval_artifact_failures
import app.infrastructure.index.dense as dense_module
import app.infrastructure.index.reranker as reranker_module
import pipelines.run_retrieval_experiment as retrieval_pipeline
from pipelines.run_retrieval_experiment import run_retrieval_experiment


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _child_payload(
    *,
    child_id: str,
    parent_id: str,
    doc_id: str,
    text: str,
) -> dict[str, object]:
    return {
        "child_id": child_id,
        "parent_id": parent_id,
        "doc_id": doc_id,
        "doc_title": doc_id,
        "parser_run_id": "parser-run",
        "source_block_ids": [f"block-{child_id}"],
        "context_block_ids": [],
        "page_span": {
            "page_local_start": 1,
            "page_local_end": 1,
            "page_global_start": 1,
            "page_global_end": 1,
        },
        "text_hash": "a" * 64,
        "text_length": len(text),
        "element_type_mix": {"paragraph": 1},
        "citation_refs": [
            {
                "block_id": f"block-{child_id}",
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
                        "element_index": 1,
                    }
                ],
                "source_file_name": f"{doc_id}.pdf",
                "text_hash": "b" * 64,
                "text_length": len(text),
                "quality_flags": [],
            }
        ],
        "quality_flags": [],
        "public_allowed": False,
        "text": text,
        "context_text": None,
    }


def _eval_item_payload(
    *,
    query_id: str,
    query_type: str,
    query_text: str,
    expected_behavior: str,
    child_id: str | None = None,
    parent_id: str | None = None,
    doc_id: str | None = None,
    split: str = "dev",
    review_status: str = "reviewed",
    user_context: str | None = None,
    place_ids: list[str] | None = None,
) -> dict[str, object]:
    judgments: list[dict[str, object]] = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": [child_id],
                "relevant_parent_ids": [parent_id],
                "relevant_doc_ids": [doc_id],
                "relevance_grade": 3,
                "rationale_summary": "test judgment ids only",
                "public_allowed": True,
            }
        )
    answerability = "unanswerable" if expected_behavior == "abstain" else "answerable"
    return {
        "dataset_version": "retrieval-eval-dataset/v2",
        "query": {
            "query_id": query_id,
            "query_type": query_type,
            "query_text": query_text,
            "language": "ko",
            "expected_behavior": expected_behavior,
            "user_context": user_context,
            "public_allowed": True,
        },
        "judgments": judgments,
        "metadata": {
            "split": split,
            "difficulty": "hard" if query_type in {"relationship", "route_context"} else "medium",
            "place_ids": place_ids
            if place_ids is not None
            else ["gyeongbokgung"]
            if expected_behavior == "retrieve"
            else [],
            "requires_context": query_type in {"route_context", "voice_followup"},
            "answerability": answerability,
            "review_status": review_status,
        },
    }


class _FakeSentenceTransformerModel:
    def encode(
        self,
        texts: list[str],
        *,
        batch_size: int,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> object:
        del batch_size, convert_to_numpy, normalize_embeddings, show_progress_bar
        import numpy as np

        vectors = []
        for text in texts:
            if "경복궁" in text or "정도전" in text:
                vectors.append([1.0, 0.0, 0.0])
            elif "시장" in text:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return np.asarray(vectors, dtype=np.float32)


class _FakeCrossEncoderModel:
    def predict(
        self,
        pairs: list[tuple[str, str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> object:
        del batch_size, show_progress_bar
        import numpy as np

        scores = [
            10.0 if "궁궐 정치" in passage or "시장 상업" in passage else 1.0
            for _query, passage in pairs
        ]
        return np.asarray(scores, dtype=np.float32)


def test_run_retrieval_experiment_writes_bm25_results_and_report(tmp_path: Path) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_seed.jsonl"
    results_dir = tmp_path / "results"
    report_path = tmp_path / "retrieval_harness_report.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="private source text 경복궁 한양 천도 정도전",
                ),
                _child_payload(
                    child_id="child-modern",
                    parent_id="parent-modern",
                    doc_id="doc-modern",
                    text="private source text 지하철 카페 막차",
                ),
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-one",
                query_type="relationship",
                query_text="경복궁 한양 천도 정도전",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
            ),
            _eval_item_payload(
                query_id="q-no-answer",
                query_type="no_answer",
                query_text="오늘 지하철 막차 시간",
                expected_behavior="abstain",
            ),
        ],
    )

    report = run_retrieval_experiment(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_dir=results_dir,
        report_path=report_path,
        methods=["bm25"],
        top_k=2,
    )

    result_path = results_dir / "retrieval_experiment_bm25_results.jsonl"
    result_text = result_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")

    assert report.baseline_method == "bm25"
    assert report.method_runs[0].method == "bm25"
    assert report.method_runs[0].metric_summary.query_count == 2
    assert report.method_runs[0].metric_summary.missing_result_count == 0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert collect_public_retrieval_artifact_failures(report.output_quality) == []
    assert result_path.exists()
    assert report_path.exists()
    assert "private source text" not in result_text
    assert "private source text" not in report_text


def test_run_retrieval_experiment_writes_dense_results_cache_and_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    results_dir = tmp_path / "private_data" / "evals" / "results"
    embedding_cache_dir = tmp_path / "private_data" / "embeddings"
    report_path = tmp_path / "dense_retrieval_baseline_report.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="private source text 경복궁 한양 천도 정도전 궁궐 정치",
                ),
                _child_payload(
                    child_id="child-market",
                    parent_id="parent-market",
                    doc_id="doc-market",
                    text="private source text 시장 상업 도시 사람 물건",
                ),
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-one",
                query_type="place_fact",
                query_text="경복궁 한양 정도전",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                review_status="reviewed",
            ),
            _eval_item_payload(
                query_id="q-no-answer",
                query_type="no_answer",
                query_text="실시간 주차 예약",
                expected_behavior="abstain",
                review_status="reviewed",
            ),
        ],
    )

    report = run_retrieval_experiment(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_dir=results_dir,
        report_path=report_path,
        methods=["bm25", "dense"],
        top_k=2,
        embedding_cache_dir=embedding_cache_dir,
    )
    report_text = report_path.read_text(encoding="utf-8")

    assert [run.method for run in report.method_runs] == ["bm25", "dense"]
    assert report.dataset_path == "<private retrieval eval dataset: retrieval_eval_dev.jsonl>"
    assert report.method_runs[1].method_config_summary["encoder_id"] == "sklearn-tfidf-svd-v1"
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert collect_public_retrieval_artifact_failures(report.output_quality) == []
    assert (results_dir / "retrieval_experiment_dense_results.jsonl").exists()
    assert list(embedding_cache_dir.glob("dense-*.npz"))
    manifest_paths = list(embedding_cache_dir.glob("dense-*.manifest.json"))
    assert manifest_paths
    manifest_text = manifest_paths[0].read_text(encoding="utf-8")
    assert str(tmp_path) not in manifest_text
    assert "private source text" not in manifest_text
    assert "vector_path_alias" in manifest_text
    assert "<private dense embedding cache:" in manifest_text
    assert "private source text" not in report_text
    assert str(dataset_path) not in report_text
    assert "<private artifact: retrieval_experiment_dense_results.jsonl>" in report_text
    assert "sklearn-tfidf-svd-v1" in report_text


def test_dense_retrieval_rejects_locked_test_split(tmp_path: Path) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_test.jsonl"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-test",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                split="test",
                review_status="locked",
            )
        ],
    )

    with pytest.raises(ValueError, match="locked/test split"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=tmp_path / "private_data" / "evals" / "results",
            report_path=tmp_path / "report.md",
            methods=["bm25", "dense"],
            embedding_cache_dir=tmp_path / "private_data" / "embeddings",
        )


def test_run_retrieval_experiment_writes_hybrid_variant_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_seed.jsonl"
    results_dir = tmp_path / "results"
    embedding_cache_dir = tmp_path / "private_data" / "embeddings"
    report_path = tmp_path / "hybrid_retrieval_comparison_report.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="private source text 경복궁 한양 천도 정도전 궁궐 정치",
                ),
                _child_payload(
                    child_id="child-market",
                    parent_id="parent-market",
                    doc_id="doc-market",
                    text="private source text 시장 상업 도시 사람 물건",
                ),
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-one",
                query_type="place_fact",
                query_text="경복궁 한양 정도전",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                split="seed",
                review_status="reviewed",
            ),
            _eval_item_payload(
                query_id="q-no-answer",
                query_type="no_answer",
                query_text="실시간 주차 예약",
                expected_behavior="abstain",
                split="seed",
                review_status="reviewed",
            ),
        ],
    )

    report = run_retrieval_experiment(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_dir=results_dir,
        report_path=report_path,
        methods=[
            "bm25",
            "dense",
            "hybrid_rrf",
            "hybrid_weighted_alpha_0_3",
            "hybrid_weighted_alpha_0_7",
        ],
        top_k=2,
        embedding_cache_dir=embedding_cache_dir,
    )
    report_text = report_path.read_text(encoding="utf-8")

    assert [run.run_label for run in report.method_runs] == [
        "bm25",
        "dense",
        "hybrid_rrf",
        "hybrid_weighted_alpha_0_3",
        "hybrid_weighted_alpha_0_7",
    ]
    assert [run.method for run in report.method_runs] == [
        "bm25",
        "dense",
        "hybrid_rrf",
        "hybrid_weighted",
        "hybrid_weighted",
    ]
    assert (
        results_dir / "retrieval_experiment_hybrid_weighted_alpha_0_3_results.jsonl"
    ).exists()
    assert (
        results_dir / "retrieval_experiment_hybrid_weighted_alpha_0_7_results.jsonl"
    ).exists()
    assert "run_label | method | config" in report_text
    assert "hybrid_weighted_alpha_0_3" in report_text
    assert "dense_weight_alpha=0.3" in report_text
    assert "private source text" not in report_text
    assert report.output_quality.public_raw_text_leakage_count == 0


def test_run_retrieval_experiment_writes_neural_dense_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(
        dense_module,
        "_load_sentence_transformer_model",
        lambda config: _FakeSentenceTransformerModel(),
    )
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    results_dir = tmp_path / "private_data" / "evals" / "results"
    embedding_cache_dir = tmp_path / "private_data" / "embeddings"
    report_path = tmp_path / "neural_embedding_retrieval_comparison_report.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="private source text 경복궁 한양 천도 정도전 궁궐 정치",
                ),
                _child_payload(
                    child_id="child-market",
                    parent_id="parent-market",
                    doc_id="doc-market",
                    text="private source text 시장 상업 도시 사람 물건",
                ),
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-one",
                query_type="place_fact",
                query_text="경복궁 한양 정도전",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                review_status="reviewed",
            ),
            _eval_item_payload(
                query_id="q-no-answer",
                query_type="no_answer",
                query_text="실시간 주차 예약",
                expected_behavior="abstain",
                review_status="reviewed",
            ),
        ],
    )

    report = run_retrieval_experiment(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_dir=results_dir,
        report_path=report_path,
        methods=[
            "bm25",
            "dense_multilingual_e5_small",
            "dense_paraphrase_multilingual_minilm",
        ],
        top_k=2,
        embedding_cache_dir=embedding_cache_dir,
    )
    report_text = report_path.read_text(encoding="utf-8")

    assert [run.run_label for run in report.method_runs] == [
        "bm25",
        "dense_multilingual_e5_small",
        "dense_paraphrase_multilingual_minilm",
    ]
    assert report.method_runs[1].method_config_summary["encoder_backend"] == (
        "sentence_transformers"
    )
    assert report.method_runs[1].method_config_summary["query_prefix_enabled"] is True
    assert report.method_runs[2].method_config_summary["model_name"] == (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    assert (
        results_dir / "retrieval_experiment_dense_multilingual_e5_small_results.jsonl"
    ).exists()
    assert list(embedding_cache_dir.glob("dense-*.manifest.json"))
    assert "Dense neural encoder" in report_text
    assert "private source text" not in report_text
    assert str(dataset_path) not in report_text
    assert collect_public_retrieval_artifact_failures(report.output_quality) == []


def test_run_retrieval_experiment_writes_neural_hybrid_results_with_shared_dense_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    load_counts: dict[str, int] = {}

    def fake_loader(config: object) -> _FakeSentenceTransformerModel:
        encoder_id = getattr(config, "encoder_id")
        load_counts[encoder_id] = load_counts.get(encoder_id, 0) + 1
        return _FakeSentenceTransformerModel()

    monkeypatch.setattr(dense_module, "_load_sentence_transformer_model", fake_loader)
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    results_dir = tmp_path / "private_data" / "evals" / "results"
    embedding_cache_dir = tmp_path / "private_data" / "embeddings"
    report_path = tmp_path / "neural_dense_hybrid_retrieval_comparison_report.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="private source text 경복궁 한양 천도 정도전 궁궐 정치",
                ),
                _child_payload(
                    child_id="child-market",
                    parent_id="parent-market",
                    doc_id="doc-market",
                    text="private source text 시장 상업 도시 사람 물건",
                ),
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-one",
                query_type="place_fact",
                query_text="경복궁 한양 정도전",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                review_status="reviewed",
            ),
            _eval_item_payload(
                query_id="q-no-answer",
                query_type="no_answer",
                query_text="실시간 주차 예약",
                expected_behavior="abstain",
                review_status="reviewed",
            ),
        ],
    )

    report = run_retrieval_experiment(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_dir=results_dir,
        report_path=report_path,
        methods=[
            "bm25",
            "dense_multilingual_e5_small",
            "hybrid_rrf_e5_small",
            "hybrid_weighted_e5_small_alpha_0_3",
            "hybrid_weighted_e5_small_alpha_0_5",
            "hybrid_rrf_bge_m3",
            "hybrid_weighted_bge_m3_alpha_0_3",
        ],
        top_k=2,
        embedding_cache_dir=embedding_cache_dir,
    )
    report_text = report_path.read_text(encoding="utf-8")

    assert [run.run_label for run in report.method_runs] == [
        "bm25",
        "dense_multilingual_e5_small",
        "hybrid_rrf_e5_small",
        "hybrid_weighted_e5_small_alpha_0_3",
        "hybrid_weighted_e5_small_alpha_0_5",
        "hybrid_rrf_bge_m3",
        "hybrid_weighted_bge_m3_alpha_0_3",
    ]
    assert [run.method for run in report.method_runs] == [
        "bm25",
        "dense",
        "hybrid_rrf",
        "hybrid_weighted",
        "hybrid_weighted",
        "hybrid_rrf",
        "hybrid_weighted",
    ]
    assert load_counts["multilingual-e5-small"] == 1
    assert load_counts["bge-m3"] == 1
    assert (
        results_dir / "retrieval_experiment_hybrid_rrf_e5_small_results.jsonl"
    ).exists()
    assert (
        results_dir
        / "retrieval_experiment_hybrid_weighted_bge_m3_alpha_0_3_results.jsonl"
    ).exists()
    assert "dense_encoder_backend=sentence_transformers" in report_text
    assert "dense_model_name=intfloat/multilingual-e5-small" in report_text
    assert "private source text" not in report_text
    assert str(dataset_path) not in report_text
    assert collect_public_retrieval_artifact_failures(report.output_quality) == []


def test_run_retrieval_experiment_writes_place_rewrite_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(
        dense_module,
        "_load_sentence_transformer_model",
        lambda config: _FakeSentenceTransformerModel(),
    )
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    results_dir = tmp_path / "private_data" / "evals" / "results"
    embedding_cache_dir = tmp_path / "private_data" / "embeddings"
    report_path = tmp_path / "query_rewrite_retrieval_comparison_report.md"
    place_catalog_path = tmp_path / "data_samples" / "place_catalog_seed.json"
    _write_json(
        place_catalog_path,
        {
            "catalog_version": "place-catalog/v1",
            "places": [
                {
                    "place_id": "gyeongbokgung",
                    "canonical_name": "경복궁",
                    "category": "palace",
                    "aliases": [
                        {
                            "alias": "경복궁",
                            "language": "ko",
                            "alias_type": "primary",
                        },
                        {
                            "alias": "Gyeongbokgung Palace",
                            "language": "en",
                            "alias_type": "tourism",
                        },
                    ],
                    "related_place_ids": [],
                    "relations": [],
                    "tour_context_tags": ["palace"],
                    "source_policy": "manual_public_seed",
                    "public_allowed": True,
                }
            ],
        },
    )
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="private source text 경복궁 한양 천도 정도전 궁궐 정치",
                ),
                _child_payload(
                    child_id="child-zmarket",
                    parent_id="parent-market",
                    doc_id="doc-market",
                    text="private source text 시장 상업 도시 사람 물건",
                ),
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-voice",
                query_type="voice_followup",
                query_text="여기는 왜 중요해?",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                user_context="현재 위치는 Gyeongbokgung Palace",
                place_ids=[],
                review_status="reviewed",
            ),
            _eval_item_payload(
                query_id="q-no-answer",
                query_type="no_answer",
                query_text="실시간 주차 예약",
                expected_behavior="abstain",
                review_status="reviewed",
            ),
        ],
    )

    report = run_retrieval_experiment(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_dir=results_dir,
        report_path=report_path,
        methods=[
            "bm25",
            "dense_multilingual_e5_small",
            "dense_multilingual_e5_small_place_rewrite",
            "dense_multilingual_e5_small_voice_rewrite",
        ],
        top_k=1,
        embedding_cache_dir=embedding_cache_dir,
        place_catalog_path=place_catalog_path,
    )
    report_text = report_path.read_text(encoding="utf-8")

    assert [run.run_label for run in report.method_runs] == [
        "bm25",
        "dense_multilingual_e5_small",
        "dense_multilingual_e5_small_place_rewrite",
        "dense_multilingual_e5_small_voice_rewrite",
    ]
    assert report.method_runs[1].metric_summary.recall_at_1 == 0.0
    assert report.method_runs[2].metric_summary.recall_at_1 == 1.0
    assert report.method_runs[3].metric_summary.recall_at_1 == 1.0
    rewrite_config = report.method_runs[2].method_config_summary
    assert rewrite_config["query_rewrite"] is True
    assert rewrite_config["query_rewrite_strategy"] == "place-aware-deterministic-v1"
    assert rewrite_config["query_rewrite_changed_count"] == 1
    assert rewrite_config["query_rewrite_invalid_json_count"] == 0
    assert rewrite_config["query_rewrite_solar_call_count"] == 0
    voice_rewrite_config = report.method_runs[3].method_config_summary
    assert voice_rewrite_config["query_rewrite"] is True
    assert voice_rewrite_config["query_rewrite_strategy"] == (
        "voice-followup-deterministic-v1"
    )
    assert voice_rewrite_config["query_rewrite_target_types"] == "voice_followup"
    assert (
        results_dir
        / "retrieval_experiment_dense_multilingual_e5_small_place_rewrite_results.jsonl"
    ).exists()
    assert (
        results_dir
        / "retrieval_experiment_dense_multilingual_e5_small_voice_rewrite_results.jsonl"
    ).exists()
    assert "query_rewrite_strategy=place-aware-deterministic-v1" in report_text
    assert "Query rewrite 최고 후보" in report_text
    assert "private source text" not in report_text
    assert str(dataset_path) not in report_text
    assert collect_public_retrieval_artifact_failures(report.output_quality) == []


def test_run_retrieval_experiment_writes_reranker_results_with_shared_models(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    dense_load_counts: dict[str, int] = {}
    reranker_load_count = 0

    def fake_dense_loader(config: object) -> _FakeSentenceTransformerModel:
        encoder_id = getattr(config, "encoder_id")
        dense_load_counts[encoder_id] = dense_load_counts.get(encoder_id, 0) + 1
        return _FakeSentenceTransformerModel()

    def fake_reranker_loader(config: object) -> _FakeCrossEncoderModel:
        nonlocal reranker_load_count
        assert getattr(config, "model_name") == "BAAI/bge-reranker-v2-m3"
        reranker_load_count += 1
        return _FakeCrossEncoderModel()

    monkeypatch.setattr(dense_module, "_load_sentence_transformer_model", fake_dense_loader)
    monkeypatch.setattr(reranker_module, "_load_cross_encoder_model", fake_reranker_loader)
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    results_dir = tmp_path / "private_data" / "evals" / "results"
    embedding_cache_dir = tmp_path / "private_data" / "embeddings"
    report_path = tmp_path / "reranker_retrieval_comparison_report.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="private source text 경복궁 한양 천도 정도전 궁궐 정치",
                ),
                _child_payload(
                    child_id="child-market",
                    parent_id="parent-market",
                    doc_id="doc-market",
                    text="private source text 시장 상업 도시 사람 물건",
                ),
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-one",
                query_type="place_fact",
                query_text="경복궁 한양 정도전",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                review_status="reviewed",
            ),
            _eval_item_payload(
                query_id="q-no-answer",
                query_type="no_answer",
                query_text="실시간 주차 예약",
                expected_behavior="abstain",
                review_status="reviewed",
            ),
        ],
    )

    report = run_retrieval_experiment(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_dir=results_dir,
        report_path=report_path,
        methods=[
            "bm25",
            "dense_multilingual_e5_small",
            "hybrid_weighted_e5_small_alpha_0_5",
            "dense_multilingual_e5_small_rerank_bge_m3_top20",
            "dense_multilingual_e5_small_rerank_bge_m3_top30",
            "dense_multilingual_e5_small_rerank_bge_m3_top50",
            "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top20",
            "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top30",
            "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top50",
        ],
        top_k=2,
        embedding_cache_dir=embedding_cache_dir,
    )
    report_text = report_path.read_text(encoding="utf-8")

    assert [run.run_label for run in report.method_runs] == [
        "bm25",
        "dense_multilingual_e5_small",
        "hybrid_weighted_e5_small_alpha_0_5",
        "dense_multilingual_e5_small_rerank_bge_m3_top20",
        "dense_multilingual_e5_small_rerank_bge_m3_top30",
        "dense_multilingual_e5_small_rerank_bge_m3_top50",
        "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top20",
        "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top30",
        "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top50",
    ]
    assert [run.method for run in report.method_runs] == [
        "bm25",
        "dense",
        "hybrid_weighted",
        "dense",
        "dense",
        "dense",
        "hybrid_weighted",
        "hybrid_weighted",
        "hybrid_weighted",
    ]
    assert dense_load_counts["multilingual-e5-small"] == 1
    assert reranker_load_count == 1
    reranked_config = report.method_runs[3].method_config_summary
    assert reranked_config["reranking"] is True
    assert reranked_config["retrieval_candidate_k"] == 20
    assert reranked_config["base_run_label"] == "dense_multilingual_e5_small"
    assert (
        results_dir
        / "retrieval_experiment_dense_multilingual_e5_small_rerank_bge_m3_top20_results.jsonl"
    ).exists()
    assert "reranker_model_name=BAAI/bge-reranker-v2-m3" in report_text
    assert "Reranker 최고 top-rank 후보" in report_text
    assert "private source text" not in report_text
    assert str(dataset_path) not in report_text
    assert collect_public_retrieval_artifact_failures(report.output_quality) == []


def test_dense_retrieval_rejects_unreviewed_dev_rows(tmp_path: Path) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-dev",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                split="dev",
                review_status="draft",
            )
        ],
    )

    with pytest.raises(ValueError, match="reviewed seed/dev rows only"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=tmp_path / "private_data" / "evals" / "results",
            report_path=tmp_path / "report.md",
            methods=["bm25", "dense"],
            embedding_cache_dir=tmp_path / "private_data" / "embeddings",
        )


def test_dense_retrieval_rejects_private_dataset_public_artifact_dirs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-dev",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                review_status="reviewed",
            )
        ],
    )

    with pytest.raises(ValueError, match="results must be written under private_data"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=tmp_path / "evals" / "results",
            report_path=tmp_path / "report.md",
            methods=["bm25", "dense"],
            embedding_cache_dir=tmp_path / "private_data" / "embeddings",
        )

    with pytest.raises(ValueError, match="embedding cache must be under private_data"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=tmp_path / "private_data" / "evals" / "results",
            report_path=tmp_path / "report.md",
            methods=["bm25", "dense"],
            embedding_cache_dir=tmp_path / "embeddings",
        )


def test_dense_retrieval_rejects_private_corpus_public_embedding_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    chunks_path = tmp_path / "private_data" / "reports" / "parent_child_chunks.json"
    dataset_path = tmp_path / "evals" / "datasets" / "retrieval_eval_seed.jsonl"
    public_embedding_cache_dir = tmp_path / "embeddings"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-seed",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                split="seed",
                review_status="reviewed",
            )
        ],
    )

    with pytest.raises(ValueError, match="embedding cache must be under private_data"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=tmp_path / "evals" / "results",
            report_path=tmp_path / "report.md",
            methods=["bm25", "dense"],
            embedding_cache_dir=public_embedding_cache_dir,
        )

    assert not public_embedding_cache_dir.exists()


def test_private_data_artifact_paths_must_stay_under_repository_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    external_root = tmp_path / "external"
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", repo_root)
    chunks_path = external_root / "private_data" / "reports" / "parent_child_chunks.json"
    dataset_path = repo_root / "evals" / "datasets" / "retrieval_eval_seed.jsonl"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-seed",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                split="seed",
                review_status="reviewed",
            )
        ],
    )

    with pytest.raises(ValueError, match="repository private_data"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=repo_root / "evals" / "results",
            report_path=repo_root / "report.md",
            methods=["bm25", "dense"],
            embedding_cache_dir=repo_root / "private_data" / "embeddings",
        )


def test_private_data_resolved_alias_must_stay_under_repository_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    external_root = tmp_path / "external"
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", repo_root)
    chunks_path = repo_root / "parent_child_chunks.json"
    dataset_path = repo_root / "aliases" / "retrieval_eval_dev.jsonl"
    external_resolved_dataset_path = (
        external_root / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    )
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-dev",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                split="dev",
                review_status="reviewed",
            )
        ],
    )
    original_resolve = Path.resolve

    def fake_resolve(self: Path, *args: object, **kwargs: object) -> Path:
        if self == dataset_path:
            return external_resolved_dataset_path
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    with pytest.raises(ValueError, match="repository private_data"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=repo_root / "private_data" / "evals" / "results",
            report_path=repo_root / "report.md",
            methods=["bm25", "dense"],
            embedding_cache_dir=repo_root / "private_data" / "embeddings",
        )


def test_retrieval_harness_report_contains_quantitative_and_qualitative_sections(
    tmp_path: Path,
) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_seed.jsonl"
    report_path = tmp_path / "retrieval_harness_report.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-one",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
            )
        ],
    )

    run_retrieval_experiment(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_dir=tmp_path / "results",
        report_path=report_path,
        methods=["bm25"],
        top_k=1,
    )
    markdown = report_path.read_text(encoding="utf-8")

    assert "## 정량 리포트" in markdown
    assert "## Query Type Breakdown" in markdown
    assert "## Baseline Delta" in markdown
    assert "## Method Config" in markdown
    assert "## 정성 리포트" in markdown
    assert "성능 개선 주장이 아니다" in markdown


def test_retrieval_experiment_rejects_unimplemented_methods(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported retrieval methods"):
        run_retrieval_experiment(
            chunks_path=tmp_path / "missing.json",
            dataset_path=tmp_path / "missing.jsonl",
            results_dir=tmp_path / "results",
            report_path=tmp_path / "report.md",
            methods=["graph_rag"],
        )


def test_retrieval_experiment_rejects_locked_test_split_for_bm25(
    tmp_path: Path,
) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_test.jsonl"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-test",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                split="test",
                review_status="locked",
            )
        ],
    )

    with pytest.raises(ValueError, match="locked/test split"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=tmp_path / "results",
            report_path=tmp_path / "report.md",
            methods=["bm25"],
        )


def test_retrieval_experiment_rejects_unreviewed_seed_or_dev_rows_for_bm25(
    tmp_path: Path,
) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-dev-draft",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                split="dev",
                review_status="draft",
            )
        ],
    )

    with pytest.raises(ValueError, match="reviewed seed/dev rows only"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=tmp_path / "results",
            report_path=tmp_path / "report.md",
            methods=["bm25"],
        )


def test_retrieval_experiment_rejects_public_result_row_leakage_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_seed.jsonl"
    results_dir = tmp_path / "results"
    report_path = tmp_path / "retrieval_harness_report.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-one",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
            )
        ],
    )

    def unsafe_rows(*, run_id: str, results: object) -> list[dict[str, object]]:
        return [
            {
                "run_id": run_id,
                "method": "bm25",
                "query_id": "q-one",
                "text": "private source text must not be public",
            }
        ]

    monkeypatch.setattr(
        retrieval_pipeline,
        "build_public_retrieval_result_rows",
        unsafe_rows,
    )

    with pytest.raises(ValueError, match="retrieval public output gate failed"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=results_dir,
            report_path=report_path,
            methods=["bm25"],
            top_k=1,
        )

    assert not (results_dir / "retrieval_experiment_bm25_results.jsonl").exists()
    assert not report_path.exists()


def test_retrieval_experiment_rejects_public_report_leakage_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_seed.jsonl"
    results_dir = tmp_path / "results"
    report_path = tmp_path / "retrieval_harness_report.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-one",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
            )
        ],
    )

    def unsafe_markdown(report: object) -> str:
        return "F" + ":\\private_data\\raw\\source.pdf"

    monkeypatch.setattr(
        retrieval_pipeline,
        "build_retrieval_harness_report_markdown",
        unsafe_markdown,
    )

    with pytest.raises(ValueError, match="retrieval public output gate failed"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=results_dir,
            report_path=report_path,
            methods=["bm25"],
            top_k=1,
        )

    assert (results_dir / "retrieval_experiment_bm25_results.jsonl").exists()
    assert not report_path.exists()


def test_dense_private_artifact_policy_uses_resolved_private_dataset_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "aliases" / "retrieval_eval_dev.jsonl"
    resolved_private_dataset_path = (
        tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    )
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-dev",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                split="dev",
                review_status="reviewed",
            )
        ],
    )

    original_resolve = Path.resolve

    def fake_resolve(self: Path, *args: object, **kwargs: object) -> Path:
        if self == dataset_path:
            return resolved_private_dataset_path
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    with pytest.raises(ValueError, match="results must be written under private_data"):
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=tmp_path / "evals" / "results",
            report_path=tmp_path / "report.md",
            methods=["bm25", "dense"],
            embedding_cache_dir=tmp_path / "private_data" / "embeddings",
        )
