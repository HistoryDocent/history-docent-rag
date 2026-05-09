from __future__ import annotations

import json
from pathlib import Path


def test_chunking_quality_doc_matches_public_sample() -> None:
    sample = json.loads(
        Path("data_samples/chunking_quality_sample.json").read_text(encoding="utf-8")
    )
    doc = Path("docs/CHUNKING_QUALITY_REPORT.md").read_text(encoding="utf-8")
    summary = sample["quality_summary"]

    expected_fragments = [
        f"parents={summary['parent_chunk_count']}",
        f"children={summary['child_chunk_count']}",
        f"filtered_parent_candidates={summary['filtered_parent_count']}",
        f"child_length_p50={summary['child_length_p50']}",
        f"child_length_p95={summary['child_length_p95']}",
        f"micro_parent_count={summary['micro_parent_count']}",
        f"replacement_char_child_rate={summary['replacement_char_child_rate']}",
        f"duplicate_child_text_hash_count={summary['duplicate_child_text_hash_count']}",
        f"`replacement_char_child_rate={summary['replacement_char_child_rate']}`",
        f"`micro_parent_count={summary['micro_parent_count']}`",
        f"`duplicate_child_text_hash_count={summary['duplicate_child_text_hash_count']}`",
    ]

    missing = [fragment for fragment in expected_fragments if fragment not in doc]

    assert missing == []
