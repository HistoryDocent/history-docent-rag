# Solar Pro 3 Provider Contract Report

## 목적

Solar Pro 3 provider가 Upstage Chat Completions API 계약과 citation RAG draft schema를 만족하는지 mock transport로 검증한다.

이 문서는 live API 품질 결과가 아니다. API key를 사용하지 않고, 실제 Solar Pro 3 호출도 수행하지 않는다.

## 정량 리포트

| metric | value |
| --- | ---: |
| provider | solar_pro_3 |
| model_id | solar-pro3 |
| provider_config_id | solar-pro-3-2b17971612 |
| endpoint_alias | api.upstage.ai/v1/chat/completions |
| structured_output | 1 |
| mock_call_count | 1 |
| live_call_count | 0 |
| draft_schema_valid_count | 1 |
| draft_schema_invalid_count | 0 |
| prompt_tokens | 100 |
| completion_tokens | 40 |
| total_tokens | 140 |
| estimated_cost | 0.000000 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 1 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `api_boundary`: `POST /chat/completions`와 `response_format=json_schema`를 사용한다.
- `secret_boundary`: API key는 환경변수에서만 읽고 report와 result row에 저장하지 않는다.
- `citation_boundary`: provider는 `CitationRagDraft`만 생성하고 citation 결합은 `CitationRagAnswerAssembler`가 담당한다.
- `live_boundary`: 현재 리포트는 mock transport 결과이며 live 품질 또는 비용 주장이 아니다.
- `gate_status`: PASS
