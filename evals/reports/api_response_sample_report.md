# API Response Sample Report

## 목적

`HD-API-SAMPLE-001`은 `/api/v1/chat`의 public-safe response sample 문서가 포트폴리오 제출용 API 계약을 설명하는지 검증한다.

이 리포트는 답변 품질, 검색 성능, Solar Pro 3 live generation, production route enable 주장이 아니다. raw query, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `api-response-sample-report/v1` |
| work_id | `HD-API-SAMPLE-001` |
| source_api_contract_report | `evals/reports/chat_api_contract_report.md` |
| source_retrieval_integration_report | `evals/reports/chat_retrieval_integration_report.md` |
| source_sample_doc | `docs/API_RESPONSE_SAMPLE.md` |
| solar_call_count_for_this_report | 0 |
| cuda_required_for_this_report | false |

## 정량 리포트

| metric | value |
| --- | ---: |
| json_sample_block_count | 5 |
| answerable_response_sample_count | 1 |
| no_answer_response_sample_count | 1 |
| error_envelope_sample_count | 2 |
| public_report_row_sample_count | 1 |
| required_top_level_field_count | 18 |
| required_usage_field_count | 18 |
| required_router_field_count | 19 |
| sample_solar_call_count | 0 |
| active_route_applied_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

## 정성 리포트

- `api_contract`: answerable, no-answer, validation error, provider unavailable, public report row를 분리했다.
- `citation_boundary`: answerable sample은 citation trace를 포함하고 no-answer sample은 citation을 비운다.
- `voice_boundary`: `answer`와 `spoken_answer`를 분리해 화면/음성 응답 계약을 보여준다.
- `routing_boundary`: classifier/router, guarded route, active route flag는 dry-run 관찰 필드로만 노출한다.
- `provider_boundary`: Solar Pro 3 live call은 sample/report 모두 0으로 둔다.
- `data_boundary`: sample은 fixture/synthetic 값만 사용하며 원문, private query, chunk body를 포함하지 않는다.
- `warehouse_grain`: public report row grain은 API smoke case 1건이며 free-text answer body는 저장하지 않는다.
- `gate_status`: PASS

## Public Output Gate

| metric | value |
| --- | ---: |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| live_solar_call_count | 0 |
| active_route_applied_count | 0 |

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- sample은 synthetic fixture이며 실제 production 응답 품질이 아니다.
- API sample은 schema와 public boundary 설명용이며, locked 성능 개선 근거가 아니다.
- active route는 여전히 기본 활성화하지 않는다.

다음 gate는 `HD-PORTFOLIO-QA-001`이다.
