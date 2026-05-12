from __future__ import annotations

import argparse
from pathlib import Path

import httpx

from app.domain.generation import CitationRagDraft
from app.domain.retrieval_experiment import (
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
)
from app.providers.llm.base import CitationDraftRequest
from app.providers.llm.solar_pro_3 import (
    DEFAULT_UPSTAGE_BASE_URL,
    SolarPro3CitationDraftProvider,
    SolarPro3ProviderConfig,
    build_solar_provider_public_rows,
)


SOLAR_PROVIDER_CONTRACT_REPORT_VERSION = "solar-pro-3-provider-contract-report/v1"
DEFAULT_REPORT_PATH = Path("evals/reports/solar_pro_3_provider_contract_report.md")


def build_solar_provider_contract_report(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> str:
    config = SolarPro3ProviderConfig(
        credential="mock-provider-key",
        base_url=DEFAULT_UPSTAGE_BASE_URL,
        model_id="solar-pro3",
        timeout_seconds=30.0,
        max_retries=2,
        max_tokens=700,
    )
    provider = SolarPro3CitationDraftProvider(
        config=config,
        client=httpx.Client(transport=httpx.MockTransport(_mock_solar_response)),
    )
    result = provider.generate_draft(_draft_request())
    rows = build_solar_provider_public_rows(config=config, result=result)
    provisional_markdown = build_solar_provider_contract_report_markdown(
        config=config,
        result=result,
        output_quality=None,
    )
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_PROVIDER_CONTRACT_REPORT_VERSION,
        run_id=result.provider_config_id,
        result_rows=rows,
        report_text=provisional_markdown,
    )
    markdown = build_solar_provider_contract_report_markdown(
        config=config,
        result=result,
        output_quality=output_quality,
    )
    failures = collect_public_retrieval_artifact_failures(output_quality)
    if failures:
        raise ValueError(f"solar provider contract report gate failed: {failures}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    return markdown


def build_solar_provider_contract_report_markdown(
    *,
    config: SolarPro3ProviderConfig,
    result,
    output_quality,
) -> str:
    quality_rows = (
        "| result_row_count | 0 |\n"
        "| public_raw_text_leakage_count | 0 |\n"
        "| private_path_leakage_count | 0 |\n"
        "| secret_like_leakage_count | 0 |\n"
        "| forbidden_result_field_count | 0 |"
        if output_quality is None
        else (
            f"| result_row_count | {output_quality.result_row_count} |\n"
            f"| public_raw_text_leakage_count | {output_quality.public_raw_text_leakage_count} |\n"
            f"| private_path_leakage_count | {output_quality.private_path_leakage_count} |\n"
            f"| secret_like_leakage_count | {output_quality.secret_like_leakage_count} |\n"
            f"| forbidden_result_field_count | {output_quality.forbidden_result_field_count} |"
        )
    )
    return f"""# Solar Pro 3 Provider Contract Report

## 목적

Solar Pro 3 provider가 Upstage Chat Completions API 계약과 citation RAG draft schema를 만족하는지 mock transport로 검증한다.

이 문서는 live API 품질 결과가 아니다. API key를 사용하지 않고, 실제 Solar Pro 3 호출도 수행하지 않는다.

## 정량 리포트

| metric | value |
| --- | ---: |
| provider | solar_pro_3 |
| model_id | {result.model_id} |
| provider_config_id | {result.provider_config_id} |
| endpoint_alias | {config.endpoint.replace("https://", "").replace("http://", "")} |
| structured_output | 1 |
| mock_call_count | {result.usage.api_call_count} |
| live_call_count | 0 |
| draft_schema_valid_count | 1 |
| draft_schema_invalid_count | 0 |
| prompt_tokens | {result.usage.prompt_tokens} |
| completion_tokens | {result.usage.completion_tokens} |
| total_tokens | {result.usage.total_tokens} |
| estimated_cost | {result.usage.estimated_cost:.6f} |

## Public Output Gate

| metric | value |
| --- | ---: |
{quality_rows}

## 정성 리포트

- `api_boundary`: `POST /chat/completions`와 `response_format=json_schema`를 사용한다.
- `secret_boundary`: API key는 환경변수에서만 읽고 report와 result row에 저장하지 않는다.
- `citation_boundary`: provider는 `CitationRagDraft`만 생성하고 citation 결합은 `CitationRagAnswerAssembler`가 담당한다.
- `live_boundary`: 현재 리포트는 mock transport 결과이며 live 품질 또는 비용 주장이 아니다.
- `gate_status`: PASS
"""


def _draft_request() -> CitationDraftRequest:
    return CitationDraftRequest(
        query_id="q-solar-contract",
        query_type="place_story",
        query_text="경복궁은 왜 중요한 장소야?",
        evidence_context="공개 가능한 테스트 evidence placeholder.",
        place_ids=("gyeongbokgung",),
        language="ko",
    )


def _mock_solar_response(request: httpx.Request) -> httpx.Response:
    if request.headers.get("Authorization") != "Bearer mock-provider-key":
        return httpx.Response(status_code=401, json={"error": "unauthorized"})
    draft = CitationRagDraft(
        answer="경복궁은 조선의 시작과 한양의 중심을 설명하기 좋은 장소입니다.",
        spoken_answer="경복궁은 조선의 시작과 한양의 중심을 함께 보여주는 장소입니다.",
        unsupported_claim_risk="low",
    )
    return httpx.Response(
        status_code=200,
        json={
            "id": "mock-solar-response",
            "object": "chat.completion",
            "created": 0,
            "model": "solar-pro3",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": draft.model_dump_json(),
                    },
                    "finish_reason": "stop",
                },
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 40,
                "total_tokens": 140,
            },
        },
    )


def main() -> int:
    args = _parse_args()
    build_solar_provider_contract_report(report_path=args.report)
    print("solar_provider_contract status=PASS live_call_count=0 failures=0")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build public-safe Solar Pro 3 provider contract report.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
