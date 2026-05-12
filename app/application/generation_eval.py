from __future__ import annotations

from app.domain.generation import CitationRagAnswer
from app.domain.generation_eval import (
    GenerationEvalInput,
    GenerationEvalReport,
    GenerationEvalUsage,
    build_generation_eval_report,
)
from app.domain.retrieval import RetrievalEvalItem


class GenerationEvaluationHarness:
    def evaluate(
        self,
        *,
        items_by_query_id: dict[str, RetrievalEvalItem],
        answers: list[CitationRagAnswer],
        packing_policy_id: str,
        retrieval_run_label: str,
        provider_config_id: str,
        usage_by_query_id: dict[str, GenerationEvalUsage] | None = None,
        report_text: str = "",
    ) -> GenerationEvalReport:
        usage_by_query_id = usage_by_query_id or {}
        missing_query_ids = [
            answer.query_id
            for answer in answers
            if answer.query_id not in items_by_query_id
        ]
        if missing_query_ids:
            raise ValueError(
                "generation eval requires RetrievalEvalItem for every answer: "
                f"{missing_query_ids[:5]}",
            )
        inputs = [
            GenerationEvalInput(
                item=items_by_query_id[answer.query_id],
                answer=answer,
                packing_policy_id=packing_policy_id,
                retrieval_run_label=retrieval_run_label,
                provider_config_id=provider_config_id,
                usage=usage_by_query_id.get(
                    answer.query_id,
                    GenerationEvalUsage(),
                ),
            )
            for answer in answers
        ]
        return build_generation_eval_report(inputs=inputs, report_text=report_text)
