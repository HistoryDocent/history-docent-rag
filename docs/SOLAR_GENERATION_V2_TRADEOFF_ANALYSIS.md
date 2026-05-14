# Solar Pro 3 Generation v2 Trade-off 원인 분석

## 결론

`CitationRagDraftV2` selected evidence contract는 현재 기본 generation contract로 채택하지 않는다.

이유는 단순하다. v2는 citation 수를 줄여 일부 query의 `citation_precision`을 개선했지만, `place_story`에서 `Correct-with-Evidence`와 `unsupported_claim_rate`가 동시에 악화됐다. 취업 포트폴리오 관점에서도 이 결과는 실패가 아니라 좋은 판단 근거다. 기법을 추가한 뒤 지표로 채택 보류를 결정했기 때문이다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | v2는 전체 폐기가 아니라 query-type별 selected evidence rule 보정 대상이다. |
| Retrieval | `place_story`는 retrieval hard-case 영향이 있으므로 generation prompt 실패와 분리해야 한다. |
| Generation | evidence rank를 적게 고르는 방향이 precision은 올렸지만 coverage와 unsupported claim guard를 약화했다. |
| 평가 | 7건 dev subset 결과를 최종 개선 주장으로 쓰면 안 된다. adoption gate로만 사용한다. |
| 데이터 | query grain diagnostic fact는 metric/tag만 저장한다. raw text는 저장하지 않는다. |
| 보안 | public report에는 raw query, raw answer, evidence text, chunk text, private path, secret을 남기지 않는다. |
| 포트폴리오 | "무조건 GraphRAG/RAPTOR 적용"보다 "실험 결과로 채택/보류 판단"을 강조한다. |

## 입력과 산출물

입력:

- source: `<private solar_generation_contract_v2_live_comparison_results.jsonl>`
- grain: query-level paired metric row
- 추가 Solar Pro 3 호출: 0

산출물:

- public report: `evals/reports/solar_generation_v2_tradeoff_analysis_report.md`
- private diagnostic rows: `private_data/evals/results/solar_generation_v2_tradeoff_analysis_rows.jsonl`

## 정량 결과

| metric | value |
| --- | ---: |
| row_count | 7 |
| answerable_row_count | 6 |
| precision_gain_count | 3 |
| precision_regression_count | 2 |
| recall_regression_count | 2 |
| correctness_regression_count | 1 |
| unsupported_regression_count | 1 |
| citation_count_reduction_count | 6 |
| adoption_blocker_count | 1 |
| mean_citation_count_delta | -3.166667 |
| mean_latency_ms_delta | -2558.989700 |
| adoption_decision | `reject_default_contract` |

## query별 진단

| query_type | 판단 |
| --- | --- |
| `place_fact` | positive case. citation count를 5에서 1로 줄였고 precision을 개선했다. |
| `overview` | positive case. citation count를 줄였지만 correctness와 recall은 유지했다. |
| `place_story` | blocker case. correctness, precision, recall, unsupported claim이 모두 악화됐다. |
| `relationship` | citation selection risk. correctness는 유지했지만 recall이 하락했다. |
| `route_context` | precision은 개선됐지만 latency가 악화된 monitor case다. |
| `voice_followup` | citation selection regression. precision이 하락했다. |
| `no_answer` | abstain path 유지. provider 호출 없이 regression 없음. |

## 원인 가설

가장 가능성이 높은 원인은 청킹이 아니다.

현재 증거는 v2가 evidence를 적게 선택하면서 다음 trade-off를 만든다는 쪽에 가깝다.

- 답변에 필요한 근거를 너무 적게 선택한다.
- `place_story`처럼 서사와 맥락이 필요한 질문에서 단일 evidence 선택이 부족하다.
- `used_evidence_pack_ranks`는 precision을 올릴 수 있지만, coverage guard가 없으면 recall과 correctness를 낮춘다.
- prompt가 "적게 고르기"에는 성공했지만 "충분히 고르기"에는 실패했다.

## 채택 판단

현재 production 후보:

```text
v1 CitationRagDraft + P0_rank_order citation assembly 유지
```

보류 후보:

```text
v2 selected evidence contract
```

v2를 다시 실험하려면 다음 조건이 필요하다.

- `place_story`, `overview`, `relationship`에서 multi-evidence 최소 선택 규칙을 둔다.
- `coverage_intent=multi_evidence`일 때 evidence rank 2개 이상을 요구한다.
- selected evidence가 1개일 때 unsupported claim risk를 더 보수적으로 둔다.
- raw answer/evidence private review로 `place_story`가 retrieval 실패인지 prompt 실패인지 분리한다.

## 다음 작업

1. `place_story` retrieval hard-case 원인 분석
2. v2 prompt repair 후보 문서화
3. 필요 시 승인 후 소규모 live 재실험

청킹 비교는 이 다음이다. 현재 병목은 chunk boundary보다 generation contract와 selected evidence coverage에 있다.

## HD-SOLAR-024 Prompt Repair 계획

v2 prompt repair 후보를 [Solar Pro 3 Generation v2 Prompt Repair 계획](SOLAR_GENERATION_V2_PROMPT_REPAIR_PLAN.md)에 고정했다.

결정:

- 청킹 비교는 계속 보류한다.
- repaired v2를 production 기본값으로 채택하지 않는다.
- Solar Pro 3 live 재호출은 보류한다.
- `HD-SOLAR-025` validator는 live 호출 0회, fail 0건으로 통과했다.
- 다음 구현 후보는 live 호출 없이 `repaired v2 dry-run/readiness runner`를 만드는 것이다.
