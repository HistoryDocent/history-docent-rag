# Solar Pro 3 Generation Contract v2 Assembler Report

## 목적

`CitationRagDraftV2.used_evidence_pack_ranks`가 citation assembly 단계에서 실제 citation filtering으로 연결되는지 검증한다.

이 문서는 live Solar Pro 3 품질 결과가 아니다. 실제 API 호출은 수행하지 않았고, raw answer, raw query, evidence context, chunk text, private path, secret 값은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `solar-generation-contract-v2-assembler-report/v1` |
| contract_candidate | `CitationRagDraftV2` |
| answer_policy_candidate | `solar-generation-contract-v2` |
| implementation_unit | `HD-GEN-V2-003` |
| provider | `contract_only/mock` |
| live_call_count | 0 |

## 정량 리포트

| metric | value |
| --- | ---: |
| targeted_contract_test_count | 16 |
| v1_full_citation_regression_case_count | 1 |
| v2_selected_rank_filtering_case_count | 1 |
| v2_invalid_rank_failure_case_count | 1 |
| selected_citation_count_in_v2_case | 2 |
| excluded_unused_evidence_count_in_v2_case | 1 |
| live_solar_call_count | 0 |

## Public Output Gate

| metric | value |
| --- | ---: |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `v1_regression_boundary`: v1 `CitationRagDraft`는 기존처럼 packed evidence 전체를 citation으로 변환한다.
- `v2_filtering_policy`: v2 `CitationRagDraftV2`는 `used_evidence_pack_ranks`에 포함된 evidence만 citation으로 변환한다.
- `invalid_rank_policy`: v2 draft가 evidence pack에 없는 rank를 반환하면 assembler가 실패 처리한다. 임의로 전체 citation fallback을 붙이지 않는다.
- `citation_boundary`: citation은 여전히 child, parent, doc, source block, citation block id로만 역추적한다.
- `security_boundary`: 공개 리포트에는 raw answer, raw query, evidence context, chunk text, private path, secret 값을 저장하지 않는다.
- `next_step`: 같은 7개 query set에서 v1/v2 paired comparison runner를 구현한다.
- `gate_status`: PASS

## 해석

v2 selected evidence 계약이 schema 단계에서 assembler 단계까지 연결됐다.

아직 generation 품질 개선은 주장하지 않는다. 다음 단계에서 같은 retrieval label, 같은 packing policy, 같은 query set으로 v1/v2 paired comparison을 실행해야 한다.
