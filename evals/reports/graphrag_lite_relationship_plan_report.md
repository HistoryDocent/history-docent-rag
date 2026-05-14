# GraphRAG-lite Relationship Plan Report

## 결론

GraphRAG-lite는 기본 RAG pipeline이 아니라 `relationship` 질문 전용 input-only 실험군으로 제한한다.

이번 단계는 계획과 runner skeleton 검증이다. GraphRAG-lite 실행 결과, 성능 개선, production 채택 주장이 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `graphrag-lite-relationship-plan-report/v1` |
| plan_id | `graphrag-lite-relationship-plan-s3-de2b2606` |
| generated_at_utc | `2026-05-14T13:09:57+00:00` |
| decision | `ready_for_graphrag_lite_input_only_approval` |

## 정량 리포트

| metric | value |
| --- | ---: |
| planned_query_type_count | 1 |
| planned_dev_query_count | 10 |
| planned_test_query_count | 5 |
| strategy_count | 3 |
| baseline_count | 1 |
| candidate_count | 2 |
| planned_solar_call_count | 0 |
| planned_raw_text_public_count | 0 |
| planned_private_path_public_count | 0 |
| min_required_citation_recoverability | 0.990000 |
| target_recall_at_5_delta | 0.030000 |
| target_mrr_delta | 0.030000 |
| target_ndcg_at_5_delta | 0.030000 |
| max_latency_p95_ms | 2500.000000 |

## Strategy Rows

| strategy_id | role | query_type | stage | graph_component | final_citation_source | solar_call_count | risk_tag |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| `hybrid_weighted_e5_small_alpha_0_5_reference` | baseline | relationship | reference | none | source_child_chunk | 0 | already_measured_reference |
| `graphrag_lite_entity_path_v1` | candidate | relationship | input_only | entity_path | source_child_chunk | 0 | entity_canonicalization_error |
| `graphrag_lite_community_hint_v1` | candidate | relationship | input_only | community_hint | source_child_chunk | 0 | summary_as_citation_forbidden |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 4 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `scope`: relationship query type 전용 GraphRAG-lite input-only 실험 계획이다.
- `baseline_boundary`: 기존 hybrid/dense reference를 비교 floor로 두고 청킹 재실험은 열지 않는다.
- `candidate_boundary`: entity path와 community hint는 retrieval 후보 보조 정보이며 최종 citation이 아니다.
- `citation_boundary`: 최종 citation은 source child chunk에서만 허용한다.
- `llm_call_boundary`: 계획 단계와 다음 input-only 단계 모두 Solar Pro 3 호출 0을 유지한다.
- `data_mart_grain`: `fact_graphrag_lite_relationship_eval`의 grain은 plan_id-strategy_id-query_type-metric_family다.
- `security_boundary`: public artifact에 raw query, raw evidence, chunk text, private path, secret을 기록하지 않는다.
- `external_audit`: 청킹이 아니라 relationship 관계 검색 실패 유형만 분리해 변수 폭발을 막았다.
- `gate_status`: PASS

## 다음 구현 조건

다음 단계에서만 실제 input-only 비교를 실행한다.

- `relationship` dev 10개만 사용한다.
- baseline은 기존 hybrid/dense 계열 최상위 reference를 사용한다.
- candidate는 entity path와 community hint를 source child chunk 후보로 되돌린다.
- graph summary나 community summary는 citation으로 쓰지 않는다.
- Solar Pro 3 호출은 0으로 유지한다.
- public report에는 raw query, raw answer, raw evidence, chunk text, private path, secret을 기록하지 않는다.
