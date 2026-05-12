# Chat Private Retrieval Smoke Report

## 목적

private `parent_child_chunks` artifact와 `multilingual-e5-small` dense retriever를 사용해 `/chat` retrieval-backed service가 실제 local corpus에서 evidence를 찾아 citation answer contract로 조립되는지 확인한다.

이 문서는 검색 성능 개선 주장이 아니다. 단일 smoke request이며, latency에는 model load와 cache load 비용이 포함될 수 있다.

## 정량 리포트

| metric | value |
| --- | ---: |
| request_count | 1 |
| success_count | 1 |
| answered_count | 1 |
| citation_count | 5 |
| evidence_id_count | 5 |
| retrieval_candidate_count | 5 |
| evidence_count | 5 |
| live_solar_call_count | 0 |
| latency_ms | 10277.503500 |
| retrieval_latency_ms | 68.224300 |

## 실행 경계

| field | value |
| --- | --- |
| retrieval_method | `dense_multilingual_e5_small_voice_rewrite` |
| private_corpus | `<private parent_child_chunks artifact>` |
| embedding_cache | `<private dense embedding cache>` |
| solar_live_generation | disabled |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 1 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `private_smoke_scope`: local private artifact를 사용해 retrieval-backed service path를 1회 smoke 검증했다.
- `evidence_boundary`: 응답과 report에는 evidence id와 citation id만 남기며 raw chunk text는 저장하지 않는다.
- `latency_boundary`: latency는 단일 local smoke 값이며 model load/cache load가 섞일 수 있어 SLO나 성능 주장으로 쓰지 않는다.
- `generation_boundary`: Solar Pro 3 live generation은 호출하지 않았고 contract draft만 사용했다.
- `gate_status`: PASS

## 해석

실제 private corpus에서 retrieval candidate와 citation-ready evidence가 반환됐다. 그러나 답변 본문은 아직 Solar Pro 3 live generation이 아니라 contract draft이므로, 역사 해설 품질이나 최종 RAG 성능으로 주장하지 않는다.
