# Solar Pro 3 Generation Contract v2 Schema Report

## 목적

`CitationRagDraftV2` schema와 Solar Pro 3 v2 mock response 계약이 selected evidence 기반 generation 비교 실험의 선행 조건을 만족하는지 검증한다.

이 문서는 live Solar Pro 3 품질 결과가 아니다. 실제 API 호출은 수행하지 않았고, raw answer, raw query, evidence context, chunk text, private path, secret 값은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-generation-contract-v2-schema-report/v1` |
| contract_candidate | `CitationRagDraftV2` |
| answer_policy_candidate | `solar-generation-contract-v2` |
| provider | `solar_pro_3` |
| model_id | `solar-pro3` |
| live_call_count | 0 |
| mock_response_count | 1 |

## 정량 리포트

| metric | value |
| --- | ---: |
| v1_compatibility_test_count | 8 |
| v2_valid_schema_case_count | 1 |
| v2_invalid_rank_case_count | 5 |
| v2_public_text_safety_case_count | 2 |
| provider_v2_mock_schema_case_count | 1 |
| required_v2_field_count | 5 |
| used_evidence_rank_minimum | 1 |
| used_evidence_rank_max_items | 10 |
| used_evidence_rank_unique_required | 1 |
| live_solar_call_count | 0 |

## Public Output Gate

| metric | value |
| --- | ---: |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `schema_boundary`: v2 draft는 v1 `answer`, `spoken_answer`, `unsupported_claim_risk`를 유지하면서 `used_evidence_pack_ranks`, `coverage_intent`를 추가한다.
- `selected_evidence_policy`: `used_evidence_pack_ranks`는 1 이상의 정수, 비어 있지 않은 목록, 중복 없는 목록이어야 한다.
- `provider_boundary`: 기존 Solar Pro 3 provider live path는 v1 schema를 유지한다. v2는 mock response schema 계약만 먼저 검증했다.
- `security_boundary`: 공개 리포트에는 raw answer, raw query, evidence context, chunk text, private path, secret 값을 저장하지 않는다.
- `next_step`: assembler v2에서 selected evidence만 citation으로 변환하는 filtering path를 구현한다.
- `gate_status`: PASS

## 해석

`CitationRagDraftV2` schema는 다음 단계인 assembler v2 selected evidence citation filtering을 구현할 수 있는 최소 계약을 제공한다.

아직 generation 품질 개선은 주장하지 않는다. v2 schema, assembler filtering, paired comparison runner가 모두 구현된 뒤 같은 7개 query set으로 비교해야 한다.
