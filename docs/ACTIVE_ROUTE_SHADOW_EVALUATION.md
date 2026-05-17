# Active Route Shadow Evaluation

## 결론

`HD-API-ROUTER-004`는 active route를 실제로 켠 작업이 아니다.

dev reviewed query set에서 current baseline route와 `relationship_hybrid_weighted_e5_v1` shadow route를 paired 비교했다. active route 적용 여부는 `ready_for_active_route_dry_run_contract`로 기록한다.

이 문서는 public-safe 결과 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 핵심 수치

| metric | value |
| --- | ---: |
| query_count | 70 |
| answerable_query_count | 60 |
| no_answer_query_count | 10 |
| routed_candidate_query_count | 10 |
| false_hybrid_route_count | 0 |
| no_answer_candidate_route_count | 0 |
| active_route_applied_count | 0 |
| live_solar_call_count | 0 |
| Recall@5 delta | 0.033333 |
| MRR delta | 0.013888 |
| nDCG@5 delta | 0.009544 |
| latency_p95_ms delta | 5.035485 |
| relationship Recall@5 delta | 0.200000 |

## 판단

- active route는 아직 production route가 아니다.

- `relationship` hybrid route만 다음 API flag dry-run 후보가 될 수 있다.

- no-answer query는 candidate route에서 차단됐다.

- locked test 실행은 별도 승인 전까지 금지한다.
