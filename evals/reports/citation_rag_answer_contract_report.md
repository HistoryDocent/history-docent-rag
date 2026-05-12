# Citation RAG Answer Contract Report

## 목적

Solar Pro 3 generation을 붙이기 전에 citation RAG API 응답 계약을 고정한다.

이 문서는 답변 품질 개선 주장이 아니다. `answer`, `spoken_answer`, `citations`, `evidence_ids`, `place_ids`, `abstained`, `unsupported_claim_risk`가 public-safe 구조로 검증되는지 확인한다.

## 정량 리포트

| metric | value |
| --- | ---: |
| answer_count | 2 |
| answered_count | 1 |
| abstained_count | 1 |
| citation_count | 1 |
| evidence_id_count | 1 |
| citation_recoverability_rate | 1.000000 |
| answer_policy_count | 1 |
| unsupported_high_count | 0 |
| missing_citation_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 2 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `contract_scope`: citation RAG 응답 필드와 citation backtracking id 계약을 검증했다.
- `citation_boundary`: citation은 answer text가 아니라 child_id, parent_id, doc_id, source_block_ids, citation_block_ids로 추적한다.
- `abstain_policy`: no-answer 또는 evidence 없음 상태는 citations 없이 abstained=true로 반환한다.
- `provider_boundary`: Solar Pro 3 호출은 포함하지 않았다. provider 연결은 다음 단계에서 이 계약을 만족해야 한다.
- `public_policy`: public report와 result row에는 raw evidence text를 저장하지 않고 aggregate와 id만 남긴다.
- `gate_status`: PASS

## 해석

현재 단계는 LLM provider 구현이 아니라 응답 계약 고정이다.

다음 단계에서는 이 계약 위에 fake provider, Solar Pro 3 provider, generation evaluation harness를 순서대로 연결한다.
