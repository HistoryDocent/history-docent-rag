from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.chunking import ChildChunk
from app.domain.data_contracts import PageSpan


RETRIEVAL_CONTRACT_VERSION = "retrieval-contract/v1"
RETRIEVAL_EVAL_DATASET_VERSION = "retrieval-eval-dataset/v2"
RETRIEVAL_EVAL_MIN_QUERIES_PER_TYPE = 2
RETRIEVAL_EVAL_TARGET_DEV_PER_QUERY_TYPE = 10
RETRIEVAL_EVAL_TARGET_TEST_PER_QUERY_TYPE = 5
MAX_PUBLIC_EVAL_TEXT_VALUE_LENGTH = 600
SECRET_VALUE_MARKERS = (
    "sk-",
    "api_" + "key=",
    "api" + "key=",
    "ghp_",
    "github_pat_",
    "hf_",
    "xoxb-",
    "bearer ",
    "pass" + "word=",
    "to" + "ken=",
    "sec" + "ret=",
)

QueryType = Literal[
    "place_fact",
    "place_story",
    "relationship",
    "overview",
    "route_context",
    "voice_followup",
    "no_answer",
]
LanguageCode = Literal["ko", "en", "mixed"]
ExpectedBehavior = Literal["retrieve", "abstain"]
RetrievalMethod = Literal["bm25", "dense", "hybrid_weighted", "hybrid_rrf"]
RetrievalEvalSplit = Literal["seed", "dev", "test"]
RetrievalQueryDifficulty = Literal["easy", "medium", "hard"]
RetrievalAnswerability = Literal["answerable", "unanswerable"]
RetrievalReviewStatus = Literal["draft", "reviewed", "locked"]

REQUIRED_QUERY_TYPES: tuple[QueryType, ...] = (
    "place_fact",
    "place_story",
    "relationship",
    "overview",
    "route_context",
    "voice_followup",
    "no_answer",
)
FORBIDDEN_PUBLIC_EVAL_FIELDS: frozenset[str] = frozenset(
    {
        "answer",
        "answer_text",
        "context_text",
        "content",
        "html",
        "markdown",
        "raw_text",
        "search_text",
        "source_text",
        "text",
    }
)
_PRIVATE_PATH_PATTERN = re.compile(r"([A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+)")
_POSIX_PRIVATE_PATH_PATTERN = re.compile(
    r"(^|\s)/(home|users|mnt|var|tmp|private|runner|workspace|root)/",
    re.IGNORECASE,
)


class RetrievalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RetrievalDocument(RetrievalModel):
    contract_version: str = RETRIEVAL_CONTRACT_VERSION
    retrieval_doc_id: str = Field(min_length=1)
    child_id: str = Field(min_length=1)
    parent_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    doc_title: str = Field(min_length=1)
    page_span: PageSpan
    source_block_ids: list[str] = Field(min_length=1)
    context_block_ids: list[str] = Field(default_factory=list)
    text_hash: str = Field(min_length=32)
    text_length: int = Field(ge=0)
    element_type_mix: dict[str, int]
    citation_block_ids: list[str] = Field(min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    public_allowed: bool = False
    search_text: str | None = None
    context_text: str | None = None

    @model_validator(mode="after")
    def validate_public_redaction(self) -> "RetrievalDocument":
        if self.public_allowed and (self.search_text or self.context_text):
            raise ValueError("public RetrievalDocument must not include private text")
        return self


class RetrievalQuery(RetrievalModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    query_text: str = Field(min_length=1)
    language: LanguageCode
    expected_behavior: ExpectedBehavior
    user_context: str | None = None
    public_allowed: bool = True

    @model_validator(mode="after")
    def validate_query_type_behavior(self) -> "RetrievalQuery":
        if self.query_type == "no_answer" and self.expected_behavior != "abstain":
            raise ValueError("no_answer query must use expected_behavior='abstain'")
        if self.query_type != "no_answer" and self.expected_behavior != "retrieve":
            raise ValueError("non no_answer query must use expected_behavior='retrieve'")
        return self


class RetrievalJudgment(RetrievalModel):
    query_id: str = Field(min_length=1)
    relevant_child_ids: list[str] = Field(default_factory=list)
    relevant_parent_ids: list[str] = Field(default_factory=list)
    relevant_doc_ids: list[str] = Field(default_factory=list)
    relevance_grade: int = Field(default=2, ge=1, le=3)
    rationale_summary: str = Field(min_length=1)
    public_allowed: bool = True

    def has_expected_target(self) -> bool:
        return bool(
            self.relevant_child_ids or self.relevant_parent_ids or self.relevant_doc_ids
        )


class RetrievalEvalMetadata(RetrievalModel):
    split: RetrievalEvalSplit
    difficulty: RetrievalQueryDifficulty
    place_ids: list[str] = Field(default_factory=list)
    requires_context: bool = False
    answerability: RetrievalAnswerability
    review_status: RetrievalReviewStatus


class RetrievalEvalItem(RetrievalModel):
    dataset_version: str = RETRIEVAL_EVAL_DATASET_VERSION
    query: RetrievalQuery
    judgments: list[RetrievalJudgment] = Field(default_factory=list)
    metadata: RetrievalEvalMetadata

    @model_validator(mode="after")
    def validate_judgments(self) -> "RetrievalEvalItem":
        if self.dataset_version != RETRIEVAL_EVAL_DATASET_VERSION:
            raise ValueError(
                f"retrieval eval dataset_version must be {RETRIEVAL_EVAL_DATASET_VERSION}"
            )
        mismatched = [
            judgment.query_id
            for judgment in self.judgments
            if judgment.query_id != self.query.query_id
        ]
        if mismatched:
            raise ValueError("judgment query_id must match item query_id")
        if self.query.expected_behavior == "abstain" and self.judgments:
            raise ValueError("abstain query must not include positive judgments")
        if self.query.expected_behavior == "retrieve":
            if not self.judgments:
                raise ValueError("retrieve query must include at least one judgment")
            if not any(judgment.has_expected_target() for judgment in self.judgments):
                raise ValueError("retrieve query must include at least one expected target")
        if (
            self.metadata.answerability == "unanswerable"
            and self.query.expected_behavior != "abstain"
        ):
            raise ValueError("unanswerable metadata must use expected_behavior='abstain'")
        if (
            self.metadata.answerability == "answerable"
            and self.query.expected_behavior != "retrieve"
        ):
            raise ValueError("answerable metadata must use expected_behavior='retrieve'")
        if self.query.query_type == "voice_followup" and not self.metadata.requires_context:
            raise ValueError("voice_followup metadata must use requires_context=true")
        return self


class RetrievedCandidate(RetrievalModel):
    rank: int = Field(ge=1)
    retrieval_doc_id: str = Field(min_length=1)
    child_id: str = Field(min_length=1)
    parent_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    score: float


class RetrievalRunResult(RetrievalModel):
    contract_version: str = RETRIEVAL_CONTRACT_VERSION
    query_id: str = Field(min_length=1)
    query_type: QueryType
    method: RetrievalMethod
    candidates: list[RetrievedCandidate] = Field(default_factory=list)
    latency_ms: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_candidate_ranks(self) -> "RetrievalRunResult":
        ranks = [candidate.rank for candidate in self.candidates]
        if len(ranks) != len(set(ranks)):
            raise ValueError("candidate ranks must be unique")
        if ranks and sorted(ranks) != list(range(1, len(ranks) + 1)):
            raise ValueError("candidate ranks must be contiguous from 1")
        return self


class RetrievalEvalDatasetSummary(RetrievalModel):
    dataset_version: str
    query_count: int = Field(ge=0)
    query_type_distribution: dict[str, int]
    split_distribution: dict[str, int]
    query_type_by_split: dict[str, dict[str, int]]
    difficulty_distribution: dict[str, int]
    answerability_distribution: dict[str, int]
    review_status_distribution: dict[str, int]
    judgment_count: int = Field(ge=0)
    retrieve_query_count: int = Field(ge=0)
    abstain_query_count: int = Field(ge=0)
    dataset_version_mismatch_count: int = Field(ge=0)
    query_type_min_shortfall_count: int = Field(ge=0)
    dev_query_count: int = Field(ge=0)
    test_query_count: int = Field(ge=0)
    dev_target_shortfall_count: int = Field(ge=0)
    test_target_shortfall_count: int = Field(ge=0)
    duplicate_query_id_count: int = Field(ge=0)
    missing_metadata_count: int = Field(ge=0)
    answerability_mismatch_count: int = Field(ge=0)
    voice_followup_context_missing_count: int = Field(ge=0)
    requires_context_count: int = Field(ge=0)
    place_id_count: int = Field(ge=0)
    missing_required_query_type_count: int = Field(ge=0)
    missing_expected_target_count: int = Field(ge=0)
    judgment_query_mismatch_count: int = Field(ge=0)
    public_raw_text_leakage_count: int = Field(ge=0)
    private_path_leakage_count: int = Field(ge=0)


class RetrievalTargetInventory(RetrievalModel):
    child_ids: frozenset[str] = Field(default_factory=frozenset)
    parent_ids: frozenset[str] = Field(default_factory=frozenset)
    doc_ids: frozenset[str] = Field(default_factory=frozenset)


class RetrievalEvalTargetResolvabilitySummary(RetrievalModel):
    query_count: int = Field(ge=0)
    judgment_count: int = Field(ge=0)
    answerable_query_count: int = Field(ge=0)
    no_answer_query_count: int = Field(ge=0)
    searchable_child_count: int = Field(ge=0)
    searchable_parent_count: int = Field(ge=0)
    searchable_doc_count: int = Field(ge=0)
    judgment_target_count: int = Field(ge=0)
    child_target_count: int = Field(ge=0)
    resolved_child_target_count: int = Field(ge=0)
    missing_child_target_count: int = Field(ge=0)
    parent_target_count: int = Field(ge=0)
    resolved_parent_target_count: int = Field(ge=0)
    missing_parent_target_count: int = Field(ge=0)
    doc_target_count: int = Field(ge=0)
    resolved_doc_target_count: int = Field(ge=0)
    missing_doc_target_count: int = Field(ge=0)
    answerable_without_child_or_parent_target_count: int = Field(ge=0)
    no_answer_with_positive_target_count: int = Field(ge=0)
    public_raw_text_leakage_count: int = Field(ge=0)
    private_path_leakage_count: int = Field(ge=0)
    secret_like_leakage_count: int = Field(ge=0)


class RetrievalEvalExpansionTypeRow(RetrievalModel):
    query_type: QueryType
    seed_query_count: int = Field(ge=0)
    dev_query_count: int = Field(ge=0)
    test_query_count: int = Field(ge=0)
    target_dev_query_count: int = Field(ge=0)
    target_test_query_count: int = Field(ge=0)
    target_total_query_count: int = Field(ge=0)
    current_total_query_count: int = Field(ge=0)
    dev_shortfall_count: int = Field(ge=0)
    test_shortfall_count: int = Field(ge=0)
    total_shortfall_count: int = Field(ge=0)


class RetrievalEvalExpansionSummary(RetrievalModel):
    dataset_version: str
    target_query_count: int = Field(ge=0)
    current_query_count: int = Field(ge=0)
    overall_shortfall_count: int = Field(ge=0)
    seed_query_count: int = Field(ge=0)
    dev_query_count: int = Field(ge=0)
    test_query_count: int = Field(ge=0)
    dev_test_target_query_count: int = Field(ge=0)
    dev_test_current_query_count: int = Field(ge=0)
    dev_test_shortfall_count: int = Field(ge=0)
    draft_query_count: int = Field(ge=0)
    reviewed_query_count: int = Field(ge=0)
    locked_query_count: int = Field(ge=0)
    review_status_distribution: dict[str, int]
    query_type_rows: dict[str, RetrievalEvalExpansionTypeRow]
    public_raw_text_leakage_count: int = Field(ge=0)
    private_path_leakage_count: int = Field(ge=0)
    secret_like_leakage_count: int = Field(ge=0)


class RetrievalMetricSummary(RetrievalModel):
    method: RetrievalMethod
    query_count: int = Field(ge=0)
    retrieve_query_count: int = Field(ge=0)
    abstain_query_count: int = Field(ge=0)
    result_count: int = Field(ge=0)
    missing_result_count: int = Field(ge=0)
    recall_at_1: float = Field(ge=0.0, le=1.0)
    recall_at_3: float = Field(ge=0.0, le=1.0)
    recall_at_5: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    latency_p50_ms: float = Field(ge=0.0)
    latency_p95_ms: float = Field(ge=0.0)
    abstain_with_candidate_count: int = Field(ge=0)


def build_retrieval_document_from_child(
    child: ChildChunk,
    *,
    include_private_text: bool = False,
) -> RetrievalDocument:
    return RetrievalDocument(
        retrieval_doc_id=child.child_id,
        child_id=child.child_id,
        parent_id=child.parent_id,
        doc_id=child.doc_id,
        doc_title=child.doc_title,
        page_span=child.page_span,
        source_block_ids=child.source_block_ids,
        context_block_ids=child.context_block_ids,
        text_hash=child.text_hash,
        text_length=child.text_length,
        element_type_mix=child.element_type_mix,
        citation_block_ids=[ref.block_id for ref in child.citation_refs],
        quality_flags=child.quality_flags,
        public_allowed=False,
        search_text=child.text if include_private_text else None,
        context_text=child.context_text if include_private_text else None,
    )


def build_retrieval_target_inventory(
    children: list[ChildChunk],
) -> RetrievalTargetInventory:
    searchable_children = [child for child in children if child.text]
    return RetrievalTargetInventory(
        child_ids=frozenset(child.child_id for child in searchable_children),
        parent_ids=frozenset(child.parent_id for child in searchable_children),
        doc_ids=frozenset(child.doc_id for child in searchable_children),
    )


def load_retrieval_eval_jsonl(path: Path) -> list[RetrievalEvalItem]:
    items: list[RetrievalEvalItem] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            items.append(RetrievalEvalItem.model_validate_json(line))
        except ValueError as exc:
            raise ValueError(f"invalid retrieval eval item at line {line_number}") from exc
    return items


def summarize_retrieval_eval_dataset(
    items: list[RetrievalEvalItem],
) -> RetrievalEvalDatasetSummary:
    query_types = Counter(item.query.query_type for item in items)
    query_ids = [item.query.query_id for item in items]
    split_distribution = Counter(
        item.metadata.split for item in items if item.metadata is not None
    )
    difficulty_distribution = Counter(
        item.metadata.difficulty for item in items if item.metadata is not None
    )
    answerability_distribution = Counter(
        item.metadata.answerability for item in items if item.metadata is not None
    )
    review_status_distribution = Counter(
        item.metadata.review_status for item in items if item.metadata is not None
    )
    payload = [item.model_dump(mode="json") for item in items]
    missing_expected_target_count = sum(
        1
        for item in items
        if item.query.expected_behavior == "retrieve"
        and not any(judgment.has_expected_target() for judgment in item.judgments)
    )
    judgment_query_mismatch_count = sum(
        1
        for item in items
        for judgment in item.judgments
        if judgment.query_id != item.query.query_id
    )
    answerability_mismatch_count = sum(
        1
        for item in items
        if item.metadata is not None
        and (
            (
                item.metadata.answerability == "answerable"
                and item.query.expected_behavior != "retrieve"
            )
            or (
                item.metadata.answerability == "unanswerable"
                and item.query.expected_behavior != "abstain"
            )
        )
    )
    voice_followup_context_missing_count = sum(
        1
        for item in items
        if item.query.query_type == "voice_followup"
        and not item.metadata.requires_context
    )
    dataset_versions = {item.dataset_version for item in items}
    dataset_version = (
        RETRIEVAL_EVAL_DATASET_VERSION
        if not dataset_versions
        else next(iter(dataset_versions))
        if len(dataset_versions) == 1
        else "mixed"
    )

    return RetrievalEvalDatasetSummary(
        dataset_version=dataset_version,
        query_count=len(items),
        query_type_distribution=dict(sorted(query_types.items())),
        split_distribution=dict(sorted(split_distribution.items())),
        query_type_by_split=_count_query_types_by_split(items),
        difficulty_distribution=dict(sorted(difficulty_distribution.items())),
        answerability_distribution=dict(sorted(answerability_distribution.items())),
        review_status_distribution=dict(sorted(review_status_distribution.items())),
        judgment_count=sum(len(item.judgments) for item in items),
        retrieve_query_count=sum(
            1 for item in items if item.query.expected_behavior == "retrieve"
        ),
        abstain_query_count=sum(
            1 for item in items if item.query.expected_behavior == "abstain"
        ),
        dataset_version_mismatch_count=sum(
            1
            for item in items
            if item.dataset_version != RETRIEVAL_EVAL_DATASET_VERSION
        ),
        query_type_min_shortfall_count=sum(
            max(0, RETRIEVAL_EVAL_MIN_QUERIES_PER_TYPE - query_types.get(query_type, 0))
            for query_type in REQUIRED_QUERY_TYPES
        ),
        dev_query_count=split_distribution.get("dev", 0),
        test_query_count=split_distribution.get("test", 0),
        dev_target_shortfall_count=_count_query_type_split_shortfall(
            items=items,
            split="dev",
            target_per_query_type=RETRIEVAL_EVAL_TARGET_DEV_PER_QUERY_TYPE,
        ),
        test_target_shortfall_count=_count_query_type_split_shortfall(
            items=items,
            split="test",
            target_per_query_type=RETRIEVAL_EVAL_TARGET_TEST_PER_QUERY_TYPE,
        ),
        duplicate_query_id_count=len(query_ids) - len(set(query_ids)),
        missing_metadata_count=0,
        answerability_mismatch_count=answerability_mismatch_count,
        voice_followup_context_missing_count=voice_followup_context_missing_count,
        requires_context_count=sum(1 for item in items if item.metadata.requires_context),
        place_id_count=len(
            {
                place_id
                for item in items
                for place_id in item.metadata.place_ids
            }
        ),
        missing_required_query_type_count=len(set(REQUIRED_QUERY_TYPES) - set(query_types)),
        missing_expected_target_count=missing_expected_target_count,
        judgment_query_mismatch_count=judgment_query_mismatch_count,
        public_raw_text_leakage_count=_count_public_raw_text_leakage(payload),
        private_path_leakage_count=_count_private_path_leakage(payload),
    )


def summarize_retrieval_eval_target_resolvability(
    *,
    items: list[RetrievalEvalItem],
    inventory: RetrievalTargetInventory,
) -> RetrievalEvalTargetResolvabilitySummary:
    child_targets = [
        target
        for item in items
        for judgment in item.judgments
        for target in judgment.relevant_child_ids
    ]
    parent_targets = [
        target
        for item in items
        for judgment in item.judgments
        for target in judgment.relevant_parent_ids
    ]
    doc_targets = [
        target
        for item in items
        for judgment in item.judgments
        for target in judgment.relevant_doc_ids
    ]
    payload = [item.model_dump(mode="json") for item in items]
    return RetrievalEvalTargetResolvabilitySummary(
        query_count=len(items),
        judgment_count=sum(len(item.judgments) for item in items),
        answerable_query_count=sum(
            1 for item in items if item.query.expected_behavior == "retrieve"
        ),
        no_answer_query_count=sum(
            1 for item in items if item.query.expected_behavior == "abstain"
        ),
        searchable_child_count=len(inventory.child_ids),
        searchable_parent_count=len(inventory.parent_ids),
        searchable_doc_count=len(inventory.doc_ids),
        judgment_target_count=len(child_targets) + len(parent_targets) + len(doc_targets),
        child_target_count=len(child_targets),
        resolved_child_target_count=sum(
            1 for target in child_targets if target in inventory.child_ids
        ),
        missing_child_target_count=sum(
            1 for target in child_targets if target not in inventory.child_ids
        ),
        parent_target_count=len(parent_targets),
        resolved_parent_target_count=sum(
            1 for target in parent_targets if target in inventory.parent_ids
        ),
        missing_parent_target_count=sum(
            1 for target in parent_targets if target not in inventory.parent_ids
        ),
        doc_target_count=len(doc_targets),
        resolved_doc_target_count=sum(
            1 for target in doc_targets if target in inventory.doc_ids
        ),
        missing_doc_target_count=sum(
            1 for target in doc_targets if target not in inventory.doc_ids
        ),
        answerable_without_child_or_parent_target_count=sum(
            1
            for item in items
            if item.query.expected_behavior == "retrieve"
            and not any(
                judgment.relevant_child_ids or judgment.relevant_parent_ids
                for judgment in item.judgments
            )
        ),
        no_answer_with_positive_target_count=sum(
            1
            for item in items
            if item.query.expected_behavior == "abstain"
            and any(judgment.has_expected_target() for judgment in item.judgments)
        ),
        public_raw_text_leakage_count=_count_public_raw_text_leakage(payload),
        private_path_leakage_count=_count_private_path_leakage(payload),
        secret_like_leakage_count=_count_secret_like_leakage(payload),
    )


def summarize_retrieval_eval_expansion(
    items: list[RetrievalEvalItem],
) -> RetrievalEvalExpansionSummary:
    dataset_summary = summarize_retrieval_eval_dataset(items)
    target_total_per_type = (
        RETRIEVAL_EVAL_TARGET_DEV_PER_QUERY_TYPE
        + RETRIEVAL_EVAL_TARGET_TEST_PER_QUERY_TYPE
    )
    query_type_rows: dict[str, RetrievalEvalExpansionTypeRow] = {}
    for query_type in REQUIRED_QUERY_TYPES:
        seed_count = dataset_summary.query_type_by_split.get("seed", {}).get(query_type, 0)
        dev_count = dataset_summary.query_type_by_split.get("dev", {}).get(query_type, 0)
        test_count = dataset_summary.query_type_by_split.get("test", {}).get(query_type, 0)
        current_total = seed_count + dev_count + test_count
        query_type_rows[query_type] = RetrievalEvalExpansionTypeRow(
            query_type=query_type,
            seed_query_count=seed_count,
            dev_query_count=dev_count,
            test_query_count=test_count,
            target_dev_query_count=RETRIEVAL_EVAL_TARGET_DEV_PER_QUERY_TYPE,
            target_test_query_count=RETRIEVAL_EVAL_TARGET_TEST_PER_QUERY_TYPE,
            target_total_query_count=target_total_per_type,
            current_total_query_count=current_total,
            dev_shortfall_count=max(
                0,
                RETRIEVAL_EVAL_TARGET_DEV_PER_QUERY_TYPE - dev_count,
            ),
            test_shortfall_count=max(
                0,
                RETRIEVAL_EVAL_TARGET_TEST_PER_QUERY_TYPE - test_count,
            ),
            total_shortfall_count=max(0, target_total_per_type - current_total),
        )

    payload = [item.model_dump(mode="json") for item in items]
    return RetrievalEvalExpansionSummary(
        dataset_version=dataset_summary.dataset_version,
        target_query_count=len(REQUIRED_QUERY_TYPES) * target_total_per_type,
        current_query_count=dataset_summary.query_count,
        overall_shortfall_count=sum(
            row.total_shortfall_count for row in query_type_rows.values()
        ),
        seed_query_count=dataset_summary.split_distribution.get("seed", 0),
        dev_query_count=dataset_summary.dev_query_count,
        test_query_count=dataset_summary.test_query_count,
        dev_test_target_query_count=len(REQUIRED_QUERY_TYPES) * target_total_per_type,
        dev_test_current_query_count=(
            dataset_summary.dev_query_count + dataset_summary.test_query_count
        ),
        dev_test_shortfall_count=(
            dataset_summary.dev_target_shortfall_count
            + dataset_summary.test_target_shortfall_count
        ),
        draft_query_count=dataset_summary.review_status_distribution.get("draft", 0),
        reviewed_query_count=dataset_summary.review_status_distribution.get(
            "reviewed",
            0,
        ),
        locked_query_count=dataset_summary.review_status_distribution.get("locked", 0),
        review_status_distribution=dataset_summary.review_status_distribution,
        query_type_rows=query_type_rows,
        public_raw_text_leakage_count=dataset_summary.public_raw_text_leakage_count,
        private_path_leakage_count=dataset_summary.private_path_leakage_count,
        secret_like_leakage_count=_count_secret_like_leakage(payload),
    )


def collect_retrieval_eval_dataset_failures(
    summary: RetrievalEvalDatasetSummary,
) -> list[str]:
    failures: list[str] = []
    if summary.query_count == 0:
        failures.append("empty_eval_dataset")
    if summary.missing_required_query_type_count:
        failures.append("missing_required_query_types")
    if summary.dataset_version_mismatch_count:
        failures.append("dataset_version_mismatch")
    if summary.query_type_min_shortfall_count:
        failures.append("query_type_min_shortfall")
    if summary.duplicate_query_id_count:
        failures.append("duplicate_query_ids")
    if summary.missing_metadata_count:
        failures.append("missing_eval_metadata")
    if summary.answerability_mismatch_count:
        failures.append("answerability_mismatch")
    if summary.voice_followup_context_missing_count:
        failures.append("voice_followup_context_missing")
    if summary.missing_expected_target_count:
        failures.append("missing_expected_targets")
    if summary.judgment_query_mismatch_count:
        failures.append("judgment_query_mismatch")
    if summary.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if summary.private_path_leakage_count:
        failures.append("private_path_leakage")
    return failures


def collect_retrieval_eval_expansion_readiness_failures(
    summary: RetrievalEvalExpansionSummary,
) -> list[str]:
    failures: list[str] = []
    if summary.overall_shortfall_count:
        failures.append("overall_query_target_shortfall")
    if summary.dev_query_count == 0:
        failures.append("missing_dev_split")
    if summary.test_query_count == 0:
        failures.append("missing_test_split")
    if any(row.dev_shortfall_count for row in summary.query_type_rows.values()):
        failures.append("dev_query_type_target_shortfall")
    if any(row.test_shortfall_count for row in summary.query_type_rows.values()):
        failures.append("test_query_type_target_shortfall")
    if summary.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if summary.private_path_leakage_count:
        failures.append("private_path_leakage")
    if summary.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    return failures


def collect_retrieval_eval_review_readiness_failures(
    summary: RetrievalEvalExpansionSummary,
) -> list[str]:
    failures: list[str] = []
    accepted_query_count = summary.reviewed_query_count + summary.locked_query_count
    if summary.current_query_count == 0:
        failures.append("empty_eval_dataset")
    if summary.draft_query_count:
        failures.append("draft_queries_remaining")
    if accepted_query_count != summary.current_query_count:
        failures.append("unreviewed_queries_remaining")
    if summary.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if summary.private_path_leakage_count:
        failures.append("private_path_leakage")
    if summary.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    return failures


def collect_retrieval_eval_target_resolvability_failures(
    summary: RetrievalEvalTargetResolvabilitySummary,
) -> list[str]:
    failures: list[str] = []
    if summary.missing_child_target_count:
        failures.append("missing_child_targets")
    if summary.missing_parent_target_count:
        failures.append("missing_parent_targets")
    if summary.missing_doc_target_count:
        failures.append("missing_doc_targets")
    if summary.answerable_without_child_or_parent_target_count:
        failures.append("answerable_without_child_or_parent_target")
    if summary.no_answer_with_positive_target_count:
        failures.append("no_answer_with_positive_target")
    if summary.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if summary.private_path_leakage_count:
        failures.append("private_path_leakage")
    if summary.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    return failures


def collect_retrieval_eval_split_readiness_failures(
    summary: RetrievalEvalDatasetSummary,
) -> list[str]:
    failures: list[str] = []
    if summary.split_distribution.get("dev", 0) == 0:
        failures.append("missing_dev_split")
    if summary.split_distribution.get("test", 0) == 0:
        failures.append("missing_test_split")
    if summary.dev_target_shortfall_count:
        failures.append("dev_query_type_target_shortfall")
    if summary.test_target_shortfall_count:
        failures.append("test_query_type_target_shortfall")
    return failures


def _count_query_types_by_split(
    items: list[RetrievalEvalItem],
) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = {}
    for item in items:
        if item.metadata is None:
            continue
        split_counts = counts.setdefault(item.metadata.split, Counter())
        split_counts[item.query.query_type] += 1
    return {
        split: dict(sorted(split_counts.items()))
        for split, split_counts in sorted(counts.items())
    }


def _count_query_type_split_shortfall(
    *,
    items: list[RetrievalEvalItem],
    split: RetrievalEvalSplit,
    target_per_query_type: int,
) -> int:
    type_counts = _count_query_types_by_split(items).get(split, {})
    return sum(
        max(0, target_per_query_type - type_counts.get(query_type, 0))
        for query_type in REQUIRED_QUERY_TYPES
    )


def compute_retrieval_metrics(
    *,
    items: list[RetrievalEvalItem],
    results: list[RetrievalRunResult],
    method: RetrievalMethod,
) -> RetrievalMetricSummary:
    method_results = [result for result in results if result.method == method]
    _validate_unique_run_results(method_results)
    results_by_query_id = {result.query_id: result for result in method_results}
    retrieve_items = [
        item for item in items if item.query.expected_behavior == "retrieve"
    ]
    abstain_items = [
        item for item in items if item.query.expected_behavior == "abstain"
    ]
    recall_at_1_values = [_recall_at_k(item, results_by_query_id.get(item.query.query_id), 1) for item in retrieve_items]
    recall_at_3_values = [_recall_at_k(item, results_by_query_id.get(item.query.query_id), 3) for item in retrieve_items]
    recall_at_5_values = [_recall_at_k(item, results_by_query_id.get(item.query.query_id), 5) for item in retrieve_items]
    mrr_values = [
        _reciprocal_rank(item, results_by_query_id.get(item.query.query_id))
        for item in retrieve_items
    ]
    ndcg_values = [
        _ndcg_at_k(item, results_by_query_id.get(item.query.query_id), 5)
        for item in retrieve_items
    ]
    latencies = [result.latency_ms for result in method_results]

    return RetrievalMetricSummary(
        method=method,
        query_count=len(items),
        retrieve_query_count=len(retrieve_items),
        abstain_query_count=len(abstain_items),
        result_count=len(method_results),
        missing_result_count=sum(
            1 for item in items if item.query.query_id not in results_by_query_id
        ),
        recall_at_1=_mean(recall_at_1_values),
        recall_at_3=_mean(recall_at_3_values),
        recall_at_5=_mean(recall_at_5_values),
        mrr=_mean(mrr_values),
        ndcg_at_5=_mean(ndcg_values),
        latency_p50_ms=_percentile(latencies, 0.5),
        latency_p95_ms=_percentile(latencies, 0.95),
        abstain_with_candidate_count=sum(
            1
            for item in abstain_items
            if results_by_query_id.get(item.query.query_id)
            and results_by_query_id[item.query.query_id].candidates
        ),
    )


def _recall_at_k(
    item: RetrievalEvalItem,
    result: RetrievalRunResult | None,
    k: int,
) -> float:
    if result is None:
        return 0.0
    return 1.0 if any(_candidate_is_relevant(item, candidate) for candidate in result.candidates[:k]) else 0.0


def _reciprocal_rank(item: RetrievalEvalItem, result: RetrievalRunResult | None) -> float:
    if result is None:
        return 0.0
    for candidate in result.candidates:
        if _candidate_is_relevant(item, candidate):
            return round(1 / candidate.rank, 6)
    return 0.0


def _ndcg_at_k(
    item: RetrievalEvalItem,
    result: RetrievalRunResult | None,
    k: int,
) -> float:
    if result is None:
        return 0.0
    relevance_by_identifier = _build_relevance_by_identifier(item)
    gains = [
        _candidate_relevance(candidate, relevance_by_identifier)
        for candidate in result.candidates[:k]
    ]
    dcg = _dcg(gains)
    ideal_gains = _ideal_relevance_gains(item, k)
    idcg = _dcg(ideal_gains)
    if idcg == 0:
        return 0.0
    return round(dcg / idcg, 6)


def _candidate_is_relevant(
    item: RetrievalEvalItem,
    candidate: RetrievedCandidate,
) -> bool:
    return _candidate_relevance(candidate, _build_relevance_by_identifier(item)) > 0


def _build_relevance_by_identifier(item: RetrievalEvalItem) -> dict[str, int]:
    relevance_by_identifier: dict[str, int] = {}
    for judgment in item.judgments:
        for identifier in _primary_relevance_targets(judgment):
            relevance_by_identifier[identifier] = max(
                relevance_by_identifier.get(identifier, 0),
                judgment.relevance_grade,
            )
    return relevance_by_identifier


def _ideal_relevance_gains(item: RetrievalEvalItem, k: int) -> list[int]:
    gains: list[int] = []
    for judgment in item.judgments:
        gains.extend(
            judgment.relevance_grade for _ in _primary_relevance_targets(judgment)
        )
    return sorted(gains, reverse=True)[:k]


def _primary_relevance_targets(judgment: RetrievalJudgment) -> list[str]:
    if judgment.relevant_child_ids:
        return judgment.relevant_child_ids
    if judgment.relevant_parent_ids:
        return judgment.relevant_parent_ids
    return judgment.relevant_doc_ids


def _candidate_relevance(
    candidate: RetrievedCandidate,
    relevance_by_identifier: dict[str, int],
) -> int:
    return max(
        relevance_by_identifier.get(candidate.child_id, 0),
        relevance_by_identifier.get(candidate.parent_id, 0),
        relevance_by_identifier.get(candidate.doc_id, 0),
    )


def _dcg(gains: list[int]) -> float:
    return sum(
        ((2**gain - 1) / math.log2(rank + 1))
        for rank, gain in enumerate(gains, start=1)
        if gain > 0
    )


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percentile)
    return round(sorted_values[index], 6)


def _validate_unique_run_results(results: list[RetrievalRunResult]) -> None:
    result_keys = [(result.method, result.query_id) for result in results]
    duplicate_count = len(result_keys) - len(set(result_keys))
    if duplicate_count:
        raise ValueError("retrieval results must be unique by method and query_id")


def _count_forbidden_public_eval_fields(payload: Any) -> int:
    if isinstance(payload, dict):
        count = sum(1 for key in payload if str(key) in FORBIDDEN_PUBLIC_EVAL_FIELDS)
        return count + sum(
            _count_forbidden_public_eval_fields(value) for value in payload.values()
        )
    if isinstance(payload, list | tuple):
        return sum(_count_forbidden_public_eval_fields(item) for item in payload)
    return 0


def _count_public_raw_text_leakage(payload: Any) -> int:
    return _count_forbidden_public_eval_fields(payload) + sum(
        1 for value in _iter_string_values(payload) if _is_source_text_like(value)
    )


def _count_private_path_leakage(payload: Any) -> int:
    return sum(
        1
        for value in _iter_string_values(payload)
        if _contains_private_path(value)
    )


def _count_secret_like_leakage(payload: Any) -> int:
    return sum(
        1
        for value in _iter_string_values(payload)
        if _contains_secret_like_value(value)
    )


def _is_source_text_like(value: str) -> bool:
    stripped = value.strip()
    return bool(
        ("\n" in stripped)
        or ("\r" in stripped)
        or len(stripped) > MAX_PUBLIC_EVAL_TEXT_VALUE_LENGTH
    )


def _contains_private_path(value: str) -> bool:
    return bool(
        _PRIVATE_PATH_PATTERN.search(value.replace("/", "\\"))
        or _POSIX_PRIVATE_PATH_PATTERN.search(value)
    )


def _contains_secret_like_value(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in SECRET_VALUE_MARKERS)


def _iter_string_values(payload: Any) -> list[str]:
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, dict):
        values: list[str] = []
        for key, value in payload.items():
            values.extend(_iter_string_values(str(key)))
            values.extend(_iter_string_values(value))
        return values
    if isinstance(payload, list | tuple | set):
        values = []
        for item in payload:
            values.extend(_iter_string_values(item))
        return values
    return []


def retrieval_eval_items_to_jsonl(items: list[RetrievalEvalItem]) -> str:
    return "\n".join(
        json.dumps(item.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        for item in items
    )
