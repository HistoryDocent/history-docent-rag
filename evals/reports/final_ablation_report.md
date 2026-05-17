# Final Ablation Report

## 목적

`HD-FINAL-ABLATION-001`은 현재까지의 RAG 실험 결과를 public-safe 최종 ablation 판단으로 고정한다.

이 리포트는 성능 개선 주장 문서가 아니다. dev-only, live-dev-subset, locked-retrieval-only 결과를 구분하고, 최종 제출용 claim boundary를 고정한다.

raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `final-ablation-report/v1` |
| work_id | `HD-FINAL-ABLATION-001` |
| source_decision_ledger | `docs/RAG_DECISION_LEDGER.md` |
| source_portfolio_summary | `docs/PORTFOLIO_RESULT_SUMMARY.md` |
| source_locked_report | `evals/reports/locked_retrieval_paired_comparison_report.md` |
| solar_call_count_for_this_report | 0 |
| cuda_required_for_this_report | false |

## 정량 리포트

| metric | value |
| --- | ---: |
| summarized_stage_count | 31 |
| selected_default_stack_count | 4 |
| rejected_default_count | 8 |
| shadow_only_candidate_count | 3 |
| locked_retrieval_query_count | 35 |
| locked_paired_query_count | 5 |
| locked_primary_metric_delta | -0.100000 |
| locked_primary_metric_ci_low | -0.300000 |
| locked_primary_metric_ci_high | 0.000000 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Final Stack

| layer | selected | status |
| --- | --- | --- |
| chunking | `C0 current parent-child` | adopted |
| retrieval | `dense_multilingual_e5_small_voice_rewrite` | adopted dev candidate |
| evidence packing | `P0_rank_order` | adopted |
| generation | `solar-generation-baseline-v1` | maintained |
| relationship route | `relationship_hybrid_weighted_e5_v1` | shadow only |
| active routing | none | default disabled |
| GraphRAG-lite | none | rejected default |
| RAPTOR-lite | none | rejected default |
| HyDE | none | rejected default |

## Key Decisions

| candidate | decision | 근거 |
| --- | --- | --- |
| `C0 current parent-child` | adopt | C1-C6이 C0를 넘지 못하거나 gate 실패 |
| `dense_multilingual_e5_small_voice_rewrite` | adopt candidate | dev Recall@5=0.850000, nDCG@5=0.615293 |
| `P0_rank_order` | adopt | citation_recoverability=1.000000 |
| `solar-generation-baseline-v1` | maintain | repaired v2는 citation recall 하락 |
| `bge-reranker-v2-m3 top20` | reject default | latency_p95_ms=13140.690300 |
| GraphRAG-lite | reject default | relationship input-only nDCG@5 개선 없음 |
| RAPTOR-lite | reject default | overview/place_story input-only 개선 없음 |
| HyDE | reject default | larger live MRR delta=-0.035000 |
| relationship active route | reject default enable | locked MRR delta=-0.100000 |

## 정성 리포트

- `architecture`: 최종 stack은 단순하지만 평가 근거가 가장 명확한 조합으로 고정한다.
- `retrieval`: E5-small voice rewrite는 관광 도슨트의 짧은 발화와 지시어 처리에 가장 실용적이다.
- `advanced_rag`: GraphRAG-lite와 RAPTOR-lite는 특정 질문군에서 실험했으나 기본값 승격 근거가 없다.
- `generation`: Solar Pro 3 v1을 유지하고 v2 repaired는 citation recall 하락 때문에 기본값에서 제외한다.
- `routing`: relationship route는 shadow 후보로 유지하되 active route 기본 활성화는 금지한다.
- `evaluation`: locked 결과는 tuning에 사용하지 않고 개선 주장 경계로만 사용한다.
- `portfolio`: "성능 개선 성공"보다 "평가로 채택과 기각을 판단했다"가 제출용 핵심 메시지다.
- `security`: public artifact에는 저작권 원문과 private eval payload를 포함하지 않는다.

## Claim Boundary

허용:

- final ablation report를 작성했다.
- 현재 기본 stack을 평가 결과에 따라 고정했다.
- locked retrieval paired comparison 결과 relationship hybrid 개선 주장을 보류했다.

금지:

- production 성능 검증 완료
- locked test 개선 입증
- GraphRAG, RAPTOR, HyDE 적용으로 최종 성능 개선
- active route 기본 활성화 완료
- 음성 앱 완성

## Public Output Gate

| metric | value |
| --- | ---: |
| report_row_count | 31 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- 대부분의 검색 비교는 dev split 또는 live-dev-subset 기준이다.
- locked paired relationship query는 5개라 통계적 해석 범위가 제한적이다.
- retrieval metric은 generation 품질 개선을 자동으로 의미하지 않는다.
- active route 기본 활성화는 별도 gate가 필요하다.

`HD-API-SAMPLE-001`과 `HD-PORTFOLIO-QA-001`은 완료됐다. 다음 gate는 `HD-COLBERT-001`이다.
