from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.retrieval import QueryType, RetrievalEvalItem
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
)


EVIDENCE_PACKING_REPORT_VERSION = "evidence-packing-report/v1"
DEFAULT_PACKING_CONTEXT_BUDGET_CHARS = 4200
VOICE_PACKING_CONTEXT_BUDGET_CHARS = 2600
DEFAULT_MAX_EVIDENCE_ITEMS = 5
PARENT_EXPANSION_MAX_EVIDENCE_ITEMS = 7
VOICE_MAX_EVIDENCE_ITEMS = 3

EvidencePackingPolicyId = Literal[
    "P0_rank_order",
    "P1_parent_expansion",
    "P2_best_first_with_parent",
    "P3_mmr_diversity",
    "P4_voice_compact",
]


class EvidencePackingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidencePackingConfig(EvidencePackingModel):
    context_budget_chars: int = Field(default=DEFAULT_PACKING_CONTEXT_BUDGET_CHARS, ge=1)
    voice_context_budget_chars: int = Field(
        default=VOICE_PACKING_CONTEXT_BUDGET_CHARS,
        ge=1,
    )
    max_evidence_items: int = Field(default=DEFAULT_MAX_EVIDENCE_ITEMS, ge=1)
    parent_expansion_max_evidence_items: int = Field(
        default=PARENT_EXPANSION_MAX_EVIDENCE_ITEMS,
        ge=1,
    )
    voice_max_evidence_items: int = Field(default=VOICE_MAX_EVIDENCE_ITEMS, ge=1)
    parent_expansion_sibling_window: int = Field(default=1, ge=0)
    duplicate_parent_penalty: float = Field(default=0.25, ge=0.0)
    duplicate_doc_penalty: float = Field(default=0.10, ge=0.0)


class EvidenceCandidate(EvidencePackingModel):
    source_rank: int = Field(ge=1)
    retrieval_doc_id: str = Field(min_length=1)
    child_id: str = Field(min_length=1)
    parent_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    score: float
    text_length: int = Field(ge=0)
    source_block_ids: tuple[str, ...] = Field(default_factory=tuple)
    citation_block_ids: tuple[str, ...] = Field(default_factory=tuple)
    quality_flags: tuple[str, ...] = Field(default_factory=tuple)

    @property
    def citation_recoverable(self) -> bool:
        if not self.source_block_ids or not self.citation_block_ids:
            return False
        return set(self.source_block_ids).issubset(set(self.citation_block_ids))


class PackedEvidence(EvidencePackingModel):
    pack_rank: int = Field(ge=1)
    source_rank: int = Field(ge=1)
    retrieval_doc_id: str = Field(min_length=1)
    child_id: str = Field(min_length=1)
    parent_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    score: float
    estimated_chars: int = Field(ge=0)
    source_block_ids: tuple[str, ...] = Field(default_factory=tuple)
    citation_block_ids: tuple[str, ...] = Field(default_factory=tuple)
    citation_recoverable: bool
    clipped: bool = False
    packing_reason: str = Field(min_length=1)


class EvidencePack(EvidencePackingModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    policy_id: EvidencePackingPolicyId
    context_budget_chars: int = Field(ge=1)
    total_estimated_chars: int = Field(ge=0)
    context_budget_violation: bool = False
    evidence: tuple[PackedEvidence, ...] = Field(default_factory=tuple)
    target_child_covered: bool = False
    target_parent_covered: bool = False
    target_doc_covered: bool = False
    evidence_order_relevance_proxy: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_pack_ranks(self) -> "EvidencePack":
        ranks = [item.pack_rank for item in self.evidence]
        if len(ranks) != len(set(ranks)):
            raise ValueError("packed evidence ranks must be unique")
        if ranks and sorted(ranks) != list(range(1, len(ranks) + 1)):
            raise ValueError("packed evidence ranks must be contiguous from 1")
        return self

    @property
    def citation_recoverability(self) -> float:
        if not self.evidence:
            return 1.0
        recoverable_count = sum(1 for item in self.evidence if item.citation_recoverable)
        return _safe_ratio(recoverable_count, len(self.evidence))

    @property
    def duplicate_parent_rate(self) -> float:
        return _duplicate_rate([item.parent_id for item in self.evidence])

    @property
    def duplicate_doc_rate(self) -> float:
        return _duplicate_rate([item.doc_id for item in self.evidence])


class EvidencePackingPolicySummary(EvidencePackingModel):
    policy_id: EvidencePackingPolicyId
    query_count: int = Field(ge=0)
    retrieve_query_count: int = Field(ge=0)
    abstain_query_count: int = Field(ge=0)
    packed_query_count: int = Field(ge=0)
    avg_packed_evidence_count: float = Field(ge=0.0)
    avg_unique_parent_count: float = Field(ge=0.0)
    avg_unique_doc_count: float = Field(ge=0.0)
    estimated_context_chars_p50: int = Field(ge=0)
    estimated_context_chars_p95: int = Field(ge=0)
    context_budget_violation_count: int = Field(ge=0)
    citation_recoverability_rate: float = Field(ge=0.0, le=1.0)
    target_child_covered_rate: float = Field(ge=0.0, le=1.0)
    target_parent_covered_rate: float = Field(ge=0.0, le=1.0)
    target_doc_covered_rate: float = Field(ge=0.0, le=1.0)
    duplicate_parent_rate: float = Field(ge=0.0, le=1.0)
    duplicate_doc_rate: float = Field(ge=0.0, le=1.0)
    evidence_order_relevance_proxy: float = Field(ge=0.0, le=1.0)
    abstain_with_evidence_count: int = Field(ge=0)


class EvidencePackingQueryTypeSummary(EvidencePackingModel):
    policy_id: EvidencePackingPolicyId
    query_type: QueryType
    query_count: int = Field(ge=0)
    target_child_covered_rate: float = Field(ge=0.0, le=1.0)
    target_parent_covered_rate: float = Field(ge=0.0, le=1.0)
    target_doc_covered_rate: float = Field(ge=0.0, le=1.0)
    estimated_context_chars_p95: int = Field(ge=0)
    duplicate_parent_rate: float = Field(ge=0.0, le=1.0)
    evidence_order_relevance_proxy: float = Field(ge=0.0, le=1.0)


class EvidencePackingComparisonDelta(EvidencePackingModel):
    baseline_policy_id: EvidencePackingPolicyId
    compared_policy_id: EvidencePackingPolicyId
    target_child_covered_rate_delta: float
    target_parent_covered_rate_delta: float
    target_doc_covered_rate_delta: float
    citation_recoverability_rate_delta: float
    duplicate_parent_rate_delta: float
    evidence_order_relevance_proxy_delta: float
    estimated_context_chars_p95_delta: int


class EvidencePackingComparisonReport(EvidencePackingModel):
    report_version: str = EVIDENCE_PACKING_REPORT_VERSION
    comparison_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path: str = Field(min_length=1)
    retrieval_result_path: str = Field(min_length=1)
    chunks_path_alias: str = "<private parent_child_chunks report>"
    dataset_fingerprint: str = Field(min_length=8)
    retrieval_result_fingerprint: str = Field(min_length=8)
    corpus_fingerprint: str = Field(min_length=8)
    baseline_policy_id: EvidencePackingPolicyId
    policy_summaries: tuple[EvidencePackingPolicySummary, ...] = Field(min_length=1)
    query_type_breakdown: tuple[EvidencePackingQueryTypeSummary, ...]
    policy_deltas: tuple[EvidencePackingComparisonDelta, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


@dataclass(frozen=True)
class EvidenceCorpus:
    children_by_id: dict[str, EvidenceCandidate]
    child_ids_by_parent: dict[str, tuple[str, ...]]
    corpus_fingerprint: str


class EvidencePacker:
    def __init__(
        self,
        *,
        corpus: EvidenceCorpus,
        config: EvidencePackingConfig | None = None,
    ) -> None:
        self.corpus = corpus
        self.config = config or EvidencePackingConfig()

    def pack(
        self,
        *,
        item: RetrievalEvalItem,
        candidates: list[EvidenceCandidate],
        policy_id: EvidencePackingPolicyId,
    ) -> EvidencePack:
        if item.query.expected_behavior == "abstain":
            return _empty_pack(item=item, policy_id=policy_id, config=self.config)
        ordered = self._ordered_candidates(policy_id=policy_id, candidates=candidates)
        if policy_id == "P1_parent_expansion":
            ordered = self._with_parent_expansion(ordered)
        elif policy_id == "P2_best_first_with_parent":
            ordered = self._best_first_parent_groups(ordered)
        elif policy_id == "P4_voice_compact" and item.query.query_type == "voice_followup":
            ordered = _dedupe_by_parent(ordered)
        evidence = self._pack_with_budget(
            item=item,
            candidates=ordered,
            policy_id=policy_id,
        )
        target_child = _target_child_covered(item, evidence)
        target_parent = _target_parent_covered(item, evidence)
        target_doc = _target_doc_covered(item, evidence)
        total_chars = sum(item.estimated_chars for item in evidence)
        budget = _budget_for_policy(
            config=self.config,
            policy_id=policy_id,
            query_type=item.query.query_type,
        )
        return EvidencePack(
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            policy_id=policy_id,
            context_budget_chars=budget,
            total_estimated_chars=total_chars,
            context_budget_violation=total_chars > budget,
            evidence=tuple(evidence),
            target_child_covered=target_child,
            target_parent_covered=target_parent,
            target_doc_covered=target_doc,
            evidence_order_relevance_proxy=_evidence_order_relevance_proxy(
                item=item,
                evidence=evidence,
            ),
        )

    def _ordered_candidates(
        self,
        *,
        policy_id: EvidencePackingPolicyId,
        candidates: list[EvidenceCandidate],
    ) -> list[EvidenceCandidate]:
        if policy_id in {
            "P0_rank_order",
            "P1_parent_expansion",
            "P2_best_first_with_parent",
            "P4_voice_compact",
        }:
            return sorted(candidates, key=lambda item: item.source_rank)
        if policy_id == "P3_mmr_diversity":
            return self._mmr_diverse_order(candidates)
        raise ValueError(f"unsupported evidence packing policy: {policy_id}")

    def _with_parent_expansion(
        self,
        candidates: list[EvidenceCandidate],
    ) -> list[EvidenceCandidate]:
        ordered: list[EvidenceCandidate] = []
        seen: set[str] = set()
        for candidate in candidates:
            for expanded in self._candidate_with_siblings(candidate):
                if expanded.child_id in seen:
                    continue
                ordered.append(expanded)
                seen.add(expanded.child_id)
        return ordered

    def _candidate_with_siblings(
        self,
        candidate: EvidenceCandidate,
    ) -> list[EvidenceCandidate]:
        child_ids = self.corpus.child_ids_by_parent.get(candidate.parent_id, ())
        if candidate.child_id not in child_ids:
            return [candidate]
        index = child_ids.index(candidate.child_id)
        lower = max(0, index - self.config.parent_expansion_sibling_window)
        upper = min(len(child_ids), index + self.config.parent_expansion_sibling_window + 1)
        expanded_ids = child_ids[lower:upper]
        expanded: list[EvidenceCandidate] = []
        for child_id in expanded_ids:
            child = self.corpus.children_by_id.get(child_id)
            if child is None:
                continue
            expanded.append(
                child.model_copy(
                    update={
                        "source_rank": candidate.source_rank,
                        "score": candidate.score,
                    },
                ),
            )
        return expanded

    def _best_first_parent_groups(
        self,
        candidates: list[EvidenceCandidate],
    ) -> list[EvidenceCandidate]:
        by_parent: dict[str, list[EvidenceCandidate]] = defaultdict(list)
        for candidate in candidates:
            by_parent[candidate.parent_id].append(candidate)
        parent_groups = sorted(
            by_parent.values(),
            key=lambda group: (
                -max(item.score for item in group),
                min(item.source_rank for item in group),
            ),
        )
        ordered: list[EvidenceCandidate] = []
        for group in parent_groups:
            head = min(group, key=lambda item: item.source_rank)
            ordered.extend(self._candidate_with_siblings(head))
        return _dedupe_by_child(ordered)

    def _mmr_diverse_order(
        self,
        candidates: list[EvidenceCandidate],
    ) -> list[EvidenceCandidate]:
        remaining = list(candidates)
        selected: list[EvidenceCandidate] = []
        max_score = max((item.score for item in remaining), default=1.0)
        min_score = min((item.score for item in remaining), default=0.0)
        score_range = max(max_score - min_score, 1e-9)
        while remaining:
            seen_parents = {item.parent_id for item in selected}
            seen_docs = {item.doc_id for item in selected}
            best = max(
                remaining,
                key=lambda item: (
                    ((item.score - min_score) / score_range)
                    - self.config.duplicate_parent_penalty * int(item.parent_id in seen_parents)
                    - self.config.duplicate_doc_penalty * int(item.doc_id in seen_docs),
                    -item.source_rank,
                ),
            )
            selected.append(best)
            remaining.remove(best)
        return selected

    def _pack_with_budget(
        self,
        *,
        item: RetrievalEvalItem,
        candidates: list[EvidenceCandidate],
        policy_id: EvidencePackingPolicyId,
    ) -> list[PackedEvidence]:
        budget = _budget_for_policy(
            config=self.config,
            policy_id=policy_id,
            query_type=item.query.query_type,
        )
        max_items = _max_items_for_policy(
            config=self.config,
            policy_id=policy_id,
            query_type=item.query.query_type,
        )
        packed: list[PackedEvidence] = []
        used_chars = 0
        seen_children: set[str] = set()
        for candidate in candidates:
            if candidate.child_id in seen_children:
                continue
            if len(packed) >= max_items:
                break
            next_chars = used_chars + candidate.text_length
            if packed and next_chars > budget:
                continue
            packed.append(
                _packed_evidence_from_candidate(
                    candidate=candidate,
                    pack_rank=len(packed) + 1,
                    clipped=next_chars > budget,
                    packing_reason=_packing_reason(policy_id),
                ),
            )
            used_chars += candidate.text_length
            seen_children.add(candidate.child_id)
        return packed


def build_evidence_corpus_from_chunks_payload(payload: dict[str, Any]) -> EvidenceCorpus:
    children_payload = payload.get("children")
    parents_payload = payload.get("parents")
    if not isinstance(children_payload, list):
        raise ValueError("parent_child_chunks payload must include children list")
    if not isinstance(parents_payload, list):
        raise ValueError("parent_child_chunks payload must include parents list")
    children_by_id: dict[str, EvidenceCandidate] = {}
    for child in children_payload:
        if not isinstance(child, dict):
            continue
        child_id = _required_str(child, "child_id")
        source_block_ids = tuple(_string_list(child.get("source_block_ids", [])))
        citation_refs = child.get("citation_refs", [])
        citation_block_id_values: list[str] = []
        if isinstance(citation_refs, list):
            for ref in citation_refs:
                if not isinstance(ref, dict):
                    continue
                block_id = ref.get("block_id")
                if isinstance(block_id, str):
                    citation_block_id_values.append(block_id)
        citation_block_ids = tuple(citation_block_id_values)
        children_by_id[child_id] = EvidenceCandidate(
            source_rank=1,
            retrieval_doc_id=child_id,
            child_id=child_id,
            parent_id=_required_str(child, "parent_id"),
            doc_id=_required_str(child, "doc_id"),
            score=0.0,
            text_length=int(child.get("text_length", 0)),
            source_block_ids=source_block_ids,
            citation_block_ids=citation_block_ids,
            quality_flags=tuple(_string_list(child.get("quality_flags", []))),
        )
    child_ids_by_parent: dict[str, tuple[str, ...]] = {}
    for parent in parents_payload:
        if not isinstance(parent, dict):
            continue
        parent_id = parent.get("parent_id")
        child_ids = parent.get("child_ids")
        if isinstance(parent_id, str) and isinstance(child_ids, list):
            child_ids_by_parent[parent_id] = tuple(
                child_id for child_id in child_ids if isinstance(child_id, str)
            )
    payload_for_fingerprint = {
        "children": [
            {
                "child_id": child.child_id,
                "parent_id": child.parent_id,
                "doc_id": child.doc_id,
                "text_length": child.text_length,
                "source_block_ids": child.source_block_ids,
                "citation_block_ids": child.citation_block_ids,
            }
            for child in sorted(children_by_id.values(), key=lambda item: item.child_id)
        ],
        "parents": {
            parent_id: child_ids for parent_id, child_ids in sorted(child_ids_by_parent.items())
        },
    }
    return EvidenceCorpus(
        children_by_id=children_by_id,
        child_ids_by_parent=child_ids_by_parent,
        corpus_fingerprint=_stable_digest(payload_for_fingerprint),
    )


def build_candidates_by_query_id(
    *,
    result_rows: list[dict[str, Any]],
    corpus: EvidenceCorpus,
) -> dict[str, list[EvidenceCandidate]]:
    candidates_by_query_id: dict[str, list[EvidenceCandidate]] = defaultdict(list)
    for row in result_rows:
        child_id = row.get("child_id")
        rank = row.get("rank")
        if not isinstance(child_id, str) or not isinstance(rank, int):
            continue
        child = corpus.children_by_id.get(child_id)
        if child is None:
            continue
        query_id = row.get("query_id")
        if not isinstance(query_id, str):
            continue
        score = row.get("score")
        candidates_by_query_id[query_id].append(
            child.model_copy(
                update={
                    "source_rank": rank,
                    "retrieval_doc_id": str(row.get("retrieval_doc_id") or child_id),
                    "score": float(score) if isinstance(score, int | float) else 0.0,
                },
            ),
        )
    return {
        query_id: sorted(candidates, key=lambda item: item.source_rank)
        for query_id, candidates in candidates_by_query_id.items()
    }


def build_evidence_packs(
    *,
    items: list[RetrievalEvalItem],
    candidates_by_query_id: dict[str, list[EvidenceCandidate]],
    corpus: EvidenceCorpus,
    policy_ids: list[EvidencePackingPolicyId] | None = None,
    config: EvidencePackingConfig | None = None,
) -> list[EvidencePack]:
    policies = policy_ids or [
        "P0_rank_order",
        "P1_parent_expansion",
        "P2_best_first_with_parent",
        "P3_mmr_diversity",
        "P4_voice_compact",
    ]
    packer = EvidencePacker(corpus=corpus, config=config)
    packs: list[EvidencePack] = []
    for policy_id in policies:
        for item in items:
            packs.append(
                packer.pack(
                    item=item,
                    candidates=candidates_by_query_id.get(item.query.query_id, []),
                    policy_id=policy_id,
                ),
            )
    return packs


def build_evidence_packing_comparison_report(
    *,
    items: list[RetrievalEvalItem],
    packs: list[EvidencePack],
    dataset_path: Path,
    retrieval_result_path: Path,
    result_rows: list[dict[str, Any]],
    corpus: EvidenceCorpus,
    report_text_for_quality: str = "",
) -> EvidencePackingComparisonReport:
    if not packs:
        raise ValueError("evidence packing comparison requires at least one pack")
    policy_summaries = tuple(summarize_packs_by_policy(items=items, packs=packs))
    baseline_policy_id = "P0_rank_order"
    if baseline_policy_id not in {summary.policy_id for summary in policy_summaries}:
        baseline_policy_id = policy_summaries[0].policy_id
    report = EvidencePackingComparisonReport(
        comparison_id=build_evidence_packing_comparison_id(
            policy_summaries=policy_summaries,
            packs=packs,
        ),
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path=public_path_alias(dataset_path),
        retrieval_result_path=public_path_alias(retrieval_result_path),
        dataset_fingerprint=_dataset_fingerprint(items),
        retrieval_result_fingerprint=_stable_digest(result_rows),
        corpus_fingerprint=corpus.corpus_fingerprint,
        baseline_policy_id=baseline_policy_id,
        policy_summaries=policy_summaries,
        query_type_breakdown=tuple(summarize_packs_by_query_type(packs)),
        policy_deltas=tuple(
            build_policy_deltas(
                summaries=policy_summaries,
                baseline_policy_id=baseline_policy_id,
            ),
        ),
        output_quality=measure_public_retrieval_artifact_quality(
            report_version=EVIDENCE_PACKING_REPORT_VERSION,
            run_id="pending",
            result_rows=result_rows,
            report_text=report_text_for_quality,
        ),
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_evidence_packing_qualitative_assessment(
                report,
            ),
        },
    )


def summarize_packs_by_policy(
    *,
    items: list[RetrievalEvalItem],
    packs: list[EvidencePack],
) -> list[EvidencePackingPolicySummary]:
    item_by_query_id = {item.query.query_id: item for item in items}
    summaries: list[EvidencePackingPolicySummary] = []
    for policy_id in sorted({pack.policy_id for pack in packs}):
        policy_packs = [pack for pack in packs if pack.policy_id == policy_id]
        retrieve_packs = [
            pack
            for pack in policy_packs
            if item_by_query_id[pack.query_id].query.expected_behavior == "retrieve"
        ]
        abstain_packs = [
            pack
            for pack in policy_packs
            if item_by_query_id[pack.query_id].query.expected_behavior == "abstain"
        ]
        summaries.append(
            EvidencePackingPolicySummary(
                policy_id=policy_id,
                query_count=len(policy_packs),
                retrieve_query_count=len(retrieve_packs),
                abstain_query_count=len(abstain_packs),
                packed_query_count=sum(1 for pack in policy_packs if pack.evidence),
                avg_packed_evidence_count=_mean(
                    [float(len(pack.evidence)) for pack in policy_packs],
                ),
                avg_unique_parent_count=_mean(
                    [
                        float(len({item.parent_id for item in pack.evidence}))
                        for pack in policy_packs
                    ],
                ),
                avg_unique_doc_count=_mean(
                    [float(len({item.doc_id for item in pack.evidence})) for pack in policy_packs],
                ),
                estimated_context_chars_p50=_percentile_int(
                    [pack.total_estimated_chars for pack in policy_packs],
                    0.5,
                ),
                estimated_context_chars_p95=_percentile_int(
                    [pack.total_estimated_chars for pack in policy_packs],
                    0.95,
                ),
                context_budget_violation_count=sum(
                    1 for pack in policy_packs if pack.context_budget_violation
                ),
                citation_recoverability_rate=_mean(
                    [pack.citation_recoverability for pack in policy_packs],
                ),
                target_child_covered_rate=_coverage_rate(
                    retrieve_packs,
                    "target_child_covered",
                ),
                target_parent_covered_rate=_coverage_rate(
                    retrieve_packs,
                    "target_parent_covered",
                ),
                target_doc_covered_rate=_coverage_rate(
                    retrieve_packs,
                    "target_doc_covered",
                ),
                duplicate_parent_rate=_mean(
                    [pack.duplicate_parent_rate for pack in policy_packs],
                ),
                duplicate_doc_rate=_mean(
                    [pack.duplicate_doc_rate for pack in policy_packs],
                ),
                evidence_order_relevance_proxy=_mean(
                    [pack.evidence_order_relevance_proxy for pack in retrieve_packs],
                ),
                abstain_with_evidence_count=sum(1 for pack in abstain_packs if pack.evidence),
            ),
        )
    return summaries


def summarize_packs_by_query_type(
    packs: list[EvidencePack],
) -> list[EvidencePackingQueryTypeSummary]:
    rows: list[EvidencePackingQueryTypeSummary] = []
    keys = sorted({(pack.policy_id, pack.query_type) for pack in packs})
    for policy_id, query_type in keys:
        subset = [
            pack for pack in packs if pack.policy_id == policy_id and pack.query_type == query_type
        ]
        rows.append(
            EvidencePackingQueryTypeSummary(
                policy_id=policy_id,
                query_type=query_type,
                query_count=len(subset),
                target_child_covered_rate=_coverage_rate(subset, "target_child_covered"),
                target_parent_covered_rate=_coverage_rate(subset, "target_parent_covered"),
                target_doc_covered_rate=_coverage_rate(subset, "target_doc_covered"),
                estimated_context_chars_p95=_percentile_int(
                    [pack.total_estimated_chars for pack in subset],
                    0.95,
                ),
                duplicate_parent_rate=_mean(
                    [pack.duplicate_parent_rate for pack in subset],
                ),
                evidence_order_relevance_proxy=_mean(
                    [pack.evidence_order_relevance_proxy for pack in subset],
                ),
            ),
        )
    return rows


def build_policy_deltas(
    *,
    summaries: tuple[EvidencePackingPolicySummary, ...],
    baseline_policy_id: EvidencePackingPolicyId,
) -> list[EvidencePackingComparisonDelta]:
    baseline = next(summary for summary in summaries if summary.policy_id == baseline_policy_id)
    deltas: list[EvidencePackingComparisonDelta] = []
    for summary in summaries:
        deltas.append(
            EvidencePackingComparisonDelta(
                baseline_policy_id=baseline_policy_id,
                compared_policy_id=summary.policy_id,
                target_child_covered_rate_delta=round(
                    summary.target_child_covered_rate - baseline.target_child_covered_rate,
                    6,
                ),
                target_parent_covered_rate_delta=round(
                    summary.target_parent_covered_rate - baseline.target_parent_covered_rate,
                    6,
                ),
                target_doc_covered_rate_delta=round(
                    summary.target_doc_covered_rate - baseline.target_doc_covered_rate,
                    6,
                ),
                citation_recoverability_rate_delta=round(
                    summary.citation_recoverability_rate - baseline.citation_recoverability_rate,
                    6,
                ),
                duplicate_parent_rate_delta=round(
                    summary.duplicate_parent_rate - baseline.duplicate_parent_rate,
                    6,
                ),
                evidence_order_relevance_proxy_delta=round(
                    summary.evidence_order_relevance_proxy
                    - baseline.evidence_order_relevance_proxy,
                    6,
                ),
                estimated_context_chars_p95_delta=(
                    summary.estimated_context_chars_p95 - baseline.estimated_context_chars_p95
                ),
            ),
        )
    return deltas


def build_public_evidence_packing_rows(
    *,
    comparison_id: str,
    packs: list[EvidencePack],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pack in packs:
        if not pack.evidence:
            rows.append(
                {
                    "comparison_id": comparison_id,
                    "policy_id": pack.policy_id,
                    "query_id": pack.query_id,
                    "query_type": pack.query_type,
                    "pack_rank": None,
                    "source_rank": None,
                    "child_id": None,
                    "parent_id": None,
                    "doc_id": None,
                    "estimated_chars": 0,
                    "citation_recoverable": True,
                    "target_child_covered": pack.target_child_covered,
                    "target_parent_covered": pack.target_parent_covered,
                    "target_doc_covered": pack.target_doc_covered,
                },
            )
            continue
        for evidence in pack.evidence:
            rows.append(
                {
                    "comparison_id": comparison_id,
                    "policy_id": pack.policy_id,
                    "query_id": pack.query_id,
                    "query_type": pack.query_type,
                    "pack_rank": evidence.pack_rank,
                    "source_rank": evidence.source_rank,
                    "child_id": evidence.child_id,
                    "parent_id": evidence.parent_id,
                    "doc_id": evidence.doc_id,
                    "estimated_chars": evidence.estimated_chars,
                    "citation_recoverable": evidence.citation_recoverable,
                    "target_child_covered": pack.target_child_covered,
                    "target_parent_covered": pack.target_parent_covered,
                    "target_doc_covered": pack.target_doc_covered,
                },
            )
    return rows


def build_evidence_packing_report_markdown(
    report: EvidencePackingComparisonReport,
) -> str:
    summary_rows = "\n".join(
        _format_policy_summary_row(summary) for summary in report.policy_summaries
    )
    breakdown_rows = "\n".join(
        _format_query_type_summary_row(row) for row in report.query_type_breakdown
    )
    delta_rows = "\n".join(_format_policy_delta_row(delta) for delta in report.policy_deltas)
    quality = report.output_quality
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Evidence Packing Comparison Report

## 목적

검색된 evidence를 Solar Pro 3 generation 전에 어떤 순서와 범위로 묶을지 비교한다.

이 문서는 답변 생성 품질 주장이 아니다. LLM 호출 없이 retrieval 결과와 chunk metadata만 사용해 context budget, citation recoverability, target coverage, duplicate rate를 비교한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| baseline_policy_id | `{report.baseline_policy_id}` |
| dataset_path | `{report.dataset_path}` |
| retrieval_result_path | `{report.retrieval_result_path}` |
| chunks_path_alias | `{report.chunks_path_alias}` |
| dataset_fingerprint | `{report.dataset_fingerprint}` |
| retrieval_result_fingerprint | `{report.retrieval_result_fingerprint}` |
| corpus_fingerprint | `{report.corpus_fingerprint}` |

## 정량 리포트

| policy_id | query_count | retrieve_query_count | abstain_query_count | packed_query_count | avg_packed_evidence_count | avg_unique_parent_count | avg_unique_doc_count | context_chars_p50 | context_chars_p95 | budget_violation | citation_recoverability | target_child_covered | target_parent_covered | target_doc_covered | duplicate_parent_rate | duplicate_doc_rate | order_relevance_proxy | abstain_with_evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{summary_rows}

## Query Type Breakdown

| policy_id | query_type | query_count | target_child_covered | target_parent_covered | target_doc_covered | context_chars_p95 | duplicate_parent_rate | order_relevance_proxy |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{breakdown_rows}

## Baseline Delta

| baseline_policy_id | compared_policy_id | target_child_delta | target_parent_delta | target_doc_delta | citation_recoverability_delta | duplicate_parent_delta | order_relevance_delta | context_chars_p95_delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{delta_rows}

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

현재 결과는 dev retrieval 결과 위에서 evidence 구성 정책만 비교한 것이다.

다음 단계에서는 선택된 packing 후보를 citation RAG answer contract와 generation evaluation harness에 연결한다. `Correct-with-Evidence`, `citation_precision`, `unsupported_claim_rate`는 Solar Pro 3 generation 단계에서 별도로 측정한다.
"""


def build_evidence_packing_qualitative_assessment(
    report: EvidencePackingComparisonReport,
) -> dict[str, str]:
    baseline = next(
        summary
        for summary in report.policy_summaries
        if summary.policy_id == report.baseline_policy_id
    )
    best_coverage = max(
        report.policy_summaries,
        key=lambda summary: (
            summary.target_parent_covered_rate,
            summary.target_child_covered_rate,
            summary.evidence_order_relevance_proxy,
        ),
    )
    least_duplicate = min(
        report.policy_summaries,
        key=lambda summary: (
            summary.duplicate_parent_rate,
            summary.estimated_context_chars_p95,
        ),
    )
    default_text = _build_default_policy_candidate_text(
        baseline=baseline,
        best_coverage=best_coverage,
    )
    return {
        "comparison_scope": (
            "검색 결과를 새로 만들지 않고 고정된 retrieval result 위에서 evidence packing만 비교했다."
        ),
        "default_policy_candidate": default_text,
        "coverage_candidate": _build_coverage_candidate_text(
            baseline=baseline,
            best_coverage=best_coverage,
        ),
        "diversity_candidate": (
            f"`{least_duplicate.policy_id}`가 duplicate parent 억제 수치는 가장 낮지만 "
            "target coverage 손실이 있으면 기본 정책으로 채택하지 않는다."
        ),
        "citation_boundary": (
            "모든 evidence는 child chunk와 source block id 기준으로만 pack하며 요약 node를 citation으로 쓰지 않는다."
        ),
        "no_answer_policy": (
            "abstain query에는 evidence를 pack하지 않아 generation 단계의 corpus 밖 질문 환각 위험을 낮춘다."
        ),
        "claim_boundary": (
            "이 결과는 generation 품질 개선 주장이 아니다. LLM 답변 평가는 다음 단계에서 분리한다."
        ),
    }


def _build_default_policy_candidate_text(
    *,
    baseline: EvidencePackingPolicySummary,
    best_coverage: EvidencePackingPolicySummary,
) -> str:
    same_coverage = (
        best_coverage.target_child_covered_rate == baseline.target_child_covered_rate
        and best_coverage.target_parent_covered_rate == baseline.target_parent_covered_rate
        and best_coverage.target_doc_covered_rate == baseline.target_doc_covered_rate
    )
    small_order_gain = (
        best_coverage.evidence_order_relevance_proxy - baseline.evidence_order_relevance_proxy
        < 0.01
    )
    if same_coverage and small_order_gain:
        return (
            f"`{baseline.policy_id}`를 v1 기본값으로 유지한다. "
            f"`{best_coverage.policy_id}`의 개선은 동률에 가까워 generation 전 기본 교체 근거가 부족하다."
        )
    return f"`{best_coverage.policy_id}`를 generation 단계 후보로 우선 검증한다."


def _build_coverage_candidate_text(
    *,
    baseline: EvidencePackingPolicySummary,
    best_coverage: EvidencePackingPolicySummary,
) -> str:
    if best_coverage.policy_id == baseline.policy_id:
        return f"`{baseline.policy_id}`가 coverage 관점의 우선 후보이다."
    return (
        f"`{best_coverage.policy_id}`가 coverage 관점의 최고 후보이나 "
        f"`{baseline.policy_id}` 대비 차이가 generation 품질로 이어지는지는 아직 미검증이다."
    )


def build_evidence_packing_comparison_id(
    *,
    policy_summaries: tuple[EvidencePackingPolicySummary, ...],
    packs: list[EvidencePack],
) -> str:
    payload = {
        "policy_ids": [summary.policy_id for summary in policy_summaries],
        "query_ids": sorted({pack.query_id for pack in packs}),
        "summary": [summary.model_dump(mode="json") for summary in policy_summaries],
    }
    digest = _stable_digest(payload)[:8]
    return f"evidence-packing-p{len(policy_summaries)}-q{len({pack.query_id for pack in packs})}-{digest}"


def _empty_pack(
    *,
    item: RetrievalEvalItem,
    policy_id: EvidencePackingPolicyId,
    config: EvidencePackingConfig,
) -> EvidencePack:
    return EvidencePack(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        policy_id=policy_id,
        context_budget_chars=_budget_for_policy(
            config=config,
            policy_id=policy_id,
            query_type=item.query.query_type,
        ),
        total_estimated_chars=0,
        evidence=(),
        target_child_covered=False,
        target_parent_covered=False,
        target_doc_covered=False,
        evidence_order_relevance_proxy=0.0,
    )


def _packed_evidence_from_candidate(
    *,
    candidate: EvidenceCandidate,
    pack_rank: int,
    clipped: bool,
    packing_reason: str,
) -> PackedEvidence:
    return PackedEvidence(
        pack_rank=pack_rank,
        source_rank=candidate.source_rank,
        retrieval_doc_id=candidate.retrieval_doc_id,
        child_id=candidate.child_id,
        parent_id=candidate.parent_id,
        doc_id=candidate.doc_id,
        score=candidate.score,
        estimated_chars=candidate.text_length,
        source_block_ids=candidate.source_block_ids,
        citation_block_ids=candidate.citation_block_ids,
        citation_recoverable=candidate.citation_recoverable,
        clipped=clipped,
        packing_reason=packing_reason,
    )


def _budget_for_policy(
    *,
    config: EvidencePackingConfig,
    policy_id: EvidencePackingPolicyId,
    query_type: QueryType,
) -> int:
    if policy_id == "P4_voice_compact" and query_type == "voice_followup":
        return config.voice_context_budget_chars
    return config.context_budget_chars


def _max_items_for_policy(
    *,
    config: EvidencePackingConfig,
    policy_id: EvidencePackingPolicyId,
    query_type: QueryType,
) -> int:
    if policy_id == "P1_parent_expansion":
        return config.parent_expansion_max_evidence_items
    if policy_id == "P4_voice_compact" and query_type == "voice_followup":
        return config.voice_max_evidence_items
    return config.max_evidence_items


def _packing_reason(policy_id: EvidencePackingPolicyId) -> str:
    return {
        "P0_rank_order": "retrieval_rank_order",
        "P1_parent_expansion": "parent_sibling_expansion",
        "P2_best_first_with_parent": "best_parent_group_first",
        "P3_mmr_diversity": "metadata_diversity_order",
        "P4_voice_compact": "voice_compact_context",
    }[policy_id]


def _target_child_covered(
    item: RetrievalEvalItem,
    evidence: list[PackedEvidence],
) -> bool:
    evidence_child_ids = {row.child_id for row in evidence}
    return any(
        child_id in evidence_child_ids
        for judgment in item.judgments
        for child_id in judgment.relevant_child_ids
    )


def _target_parent_covered(
    item: RetrievalEvalItem,
    evidence: list[PackedEvidence],
) -> bool:
    evidence_parent_ids = {row.parent_id for row in evidence}
    return any(
        parent_id in evidence_parent_ids
        for judgment in item.judgments
        for parent_id in judgment.relevant_parent_ids
    )


def _target_doc_covered(
    item: RetrievalEvalItem,
    evidence: list[PackedEvidence],
) -> bool:
    evidence_doc_ids = {row.doc_id for row in evidence}
    return any(
        doc_id in evidence_doc_ids
        for judgment in item.judgments
        for doc_id in judgment.relevant_doc_ids
    )


def _evidence_order_relevance_proxy(
    *,
    item: RetrievalEvalItem,
    evidence: list[PackedEvidence],
) -> float:
    for row in evidence:
        if _packed_evidence_is_relevant(item=item, row=row):
            return round(1 / row.pack_rank, 6)
    return 0.0


def _packed_evidence_is_relevant(
    *,
    item: RetrievalEvalItem,
    row: PackedEvidence,
) -> bool:
    return any(
        row.child_id in judgment.relevant_child_ids
        or row.parent_id in judgment.relevant_parent_ids
        or row.doc_id in judgment.relevant_doc_ids
        for judgment in item.judgments
    )


def _dedupe_by_parent(candidates: list[EvidenceCandidate]) -> list[EvidenceCandidate]:
    seen: set[str] = set()
    deduped: list[EvidenceCandidate] = []
    for candidate in candidates:
        if candidate.parent_id in seen:
            continue
        deduped.append(candidate)
        seen.add(candidate.parent_id)
    return deduped


def _dedupe_by_child(candidates: list[EvidenceCandidate]) -> list[EvidenceCandidate]:
    seen: set[str] = set()
    deduped: list[EvidenceCandidate] = []
    for candidate in candidates:
        if candidate.child_id in seen:
            continue
        deduped.append(candidate)
        seen.add(candidate.child_id)
    return deduped


def _coverage_rate(packs: list[EvidencePack], field_name: str) -> float:
    if not packs:
        return 0.0
    return _safe_ratio(
        sum(1 for pack in packs if bool(getattr(pack, field_name))),
        len(packs),
    )


def _duplicate_rate(values: list[str]) -> float:
    if not values:
        return 0.0
    return round((len(values) - len(set(values))) / len(values), 6)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def _percentile_int(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percentile)
    return int(sorted_values[index])


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"chunk child must include string field: {key}")
    return value


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _dataset_fingerprint(items: list[RetrievalEvalItem]) -> str:
    payload = [
        item.model_dump(mode="json") for item in sorted(items, key=lambda item: item.query.query_id)
    ]
    return _stable_digest(payload)


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def _format_policy_summary_row(summary: EvidencePackingPolicySummary) -> str:
    return (
        f"| {summary.policy_id} | {summary.query_count} | "
        f"{summary.retrieve_query_count} | {summary.abstain_query_count} | "
        f"{summary.packed_query_count} | {summary.avg_packed_evidence_count:.6f} | "
        f"{summary.avg_unique_parent_count:.6f} | {summary.avg_unique_doc_count:.6f} | "
        f"{summary.estimated_context_chars_p50} | {summary.estimated_context_chars_p95} | "
        f"{summary.context_budget_violation_count} | "
        f"{summary.citation_recoverability_rate:.6f} | "
        f"{summary.target_child_covered_rate:.6f} | "
        f"{summary.target_parent_covered_rate:.6f} | "
        f"{summary.target_doc_covered_rate:.6f} | "
        f"{summary.duplicate_parent_rate:.6f} | "
        f"{summary.duplicate_doc_rate:.6f} | "
        f"{summary.evidence_order_relevance_proxy:.6f} | "
        f"{summary.abstain_with_evidence_count} |"
    )


def _format_query_type_summary_row(row: EvidencePackingQueryTypeSummary) -> str:
    return (
        f"| {row.policy_id} | {row.query_type} | {row.query_count} | "
        f"{row.target_child_covered_rate:.6f} | "
        f"{row.target_parent_covered_rate:.6f} | "
        f"{row.target_doc_covered_rate:.6f} | "
        f"{row.estimated_context_chars_p95} | "
        f"{row.duplicate_parent_rate:.6f} | "
        f"{row.evidence_order_relevance_proxy:.6f} |"
    )


def _format_policy_delta_row(delta: EvidencePackingComparisonDelta) -> str:
    return (
        f"| {delta.baseline_policy_id} | {delta.compared_policy_id} | "
        f"{delta.target_child_covered_rate_delta:.6f} | "
        f"{delta.target_parent_covered_rate_delta:.6f} | "
        f"{delta.target_doc_covered_rate_delta:.6f} | "
        f"{delta.citation_recoverability_rate_delta:.6f} | "
        f"{delta.duplicate_parent_rate_delta:.6f} | "
        f"{delta.evidence_order_relevance_proxy_delta:.6f} | "
        f"{delta.estimated_context_chars_p95_delta} |"
    )
