# Chat API Contract Report

## 목적

FastAPI `/api/v1/chat` 계약을 live Solar Pro 3 호출 없이 검증한다.

이 문서는 답변 품질 개선 주장이 아니다. 외부 입력 validation, 표준 error envelope, `answer`, `spoken_answer`, `citations`, `evidence_ids`, `abstained`, provider boundary가 public-safe 구조로 동작하는지 확인한다.

## 정량 리포트

| metric | value |
| --- | ---: |
| request_count | 5 |
| success_count | 3 |
| validation_error_count | 1 |
| provider_unavailable_count | 1 |
| answered_count | 2 |
| abstained_count | 1 |
| citation_count | 2 |
| evidence_id_count | 2 |
| classifier_dry_run_count | 3 |
| classifier_route_policy_changed_count | 2 |
| classifier_active_route_applied_count | 0 |
| classifier_fallback_count | 0 |
| classifier_guarded_route_candidate_count | 3 |
| classifier_guard_applied_count | 1 |
| classifier_guarded_route_policy_changed_count | 1 |
| live_solar_call_count | 0 |
| latency_p95_ms | 0.887400 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 5 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `api_scope`: `POST /api/v1/chat`는 contract-only answer path와 no-answer abstain path를 검증했다.
- `validation_boundary`: blank query는 422 error envelope로 반환하고 request body 원문을 report에 남기지 않는다.
- `provider_boundary`: provider_mode=solar_pro_3 요청은 503 provider_unavailable로 차단해 live 비용과 secret 노출을 방지한다.
- `citation_boundary`: answerable 응답은 recoverable citation과 evidence_id를 포함하고, no-answer 응답은 citation 없이 abstained=true를 반환한다.
- `classifier_router_boundary`: classifier/router 판단은 dry-run field로만 노출하고 active retrieval route에는 적용하지 않는다.
- `guarded_route_boundary`: relationship route guard 결과는 guarded_route_candidate로만 노출하며 active route에는 적용하지 않는다.
- `claim_boundary`: 이 리포트는 API 계약 검증이며 검색 또는 생성 품질 개선 주장이 아니다.
- `gate_status`: PASS

## 해석

현재 API는 contract-only service를 통해 citation RAG answer contract를 노출한다. Solar Pro 3 live 호출은 명시적으로 차단하며, provider 연결은 별도 승인 후 private dev subset에서 smoke test로 검증한다.
