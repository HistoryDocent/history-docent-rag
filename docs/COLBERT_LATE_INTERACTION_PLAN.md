# ColBERT-style Late Interaction Plan

## 결론

`HD-COLBERT-001A`는 ColBERT-style late interaction을 실제 실행하기 전의 계획과 readiness gate다.

이번 단계에서는 retrieval 비교를 실행하지 않는다. 목적은 BGE cross-encoder reranker가 dev 기준 품질 상한은 높지만 latency가 커서 기본 route로 부적합했던 문제를, hard subset에서 더 작은 late interaction 후보로 검토할 가치가 있는지 판단하는 것이다.

이 문서는 public-safe 계획만 기록한다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 왜 지금 ColBERT-style인가

현재 기본 후보는 `dense_multilingual_e5_small_voice_rewrite + P0_rank_order`다.

기존 BGE reranker top20은 `Recall@5=0.833333`, `MRR=0.761667`, `nDCG@5=0.635787`로 dev 기준 품질이 높았지만 `latency_p95_ms=13140.690300`으로 API 기본값에 부적합했다. ColBERT-style late interaction은 dense 검색과 cross-encoder reranker 사이의 latency/quality trade-off 후보로만 검토한다.

따라서 이번 claim은 "ColBERT로 개선"이 아니다. 정확한 claim은 "reranker latency 대안 후보를 hard subset에서 검토할 계획을 수립했다"이다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | 전체 기본 검색 route는 바꾸지 않는다. late interaction은 hard subset 보조 후보로만 둔다. |
| Retrieval | `place_story`, `relationship`, `route_context` hard subset에서만 top-rank 회복 가능성을 본다. |
| Evaluation | locked test는 사용하지 않는다. dev hard subset plan-only gate 이후 별도 승인으로 실행한다. |
| ML/Ops | CUDA는 사용 가능하지만 이번 단계에서는 model load, index build, retrieval execution을 하지 않는다. |
| Data warehouse | fact grain은 `experiment_id + query_bucket + candidate_id + metric_family + claim_boundary`로 둔다. |
| Security | public report에는 bucket count와 metric plan만 기록하고 raw payload를 남기지 않는다. |
| Portfolio | ColBERT를 붙였다는 말보다 reranker latency 대안을 통제된 실험으로 검토했다는 흐름이 더 방어 가능하다. |
| 외부 감사 | final ablation 기준선을 흔들지 않도록 `HD-COLBERT-001A`를 plan-only로 닫고, 실행은 별도 work_id로 분리한다. |

## 실험 범위

| 항목 | 결정 |
| --- | --- |
| work id | `HD-COLBERT-001A` |
| 현재 단계 | plan-only readiness |
| 실행 여부 | retrieval execution 없음 |
| Solar Pro 3 호출 | 0 |
| locked test 사용 | 0 |
| CUDA 상태 | 사용 가능 |
| hard subset 후보 | `place_story`, `relationship`, `route_context` |
| 제외 query type | `no_answer`, `voice_followup`, 단순 `place_fact`, 일반 `overview` |
| 공개 범위 | bucket count, candidate id, metric plan, gate 결과만 공개 |

## 비교 후보

| candidate_id | 역할 | 설명 |
| --- | --- | --- |
| `baseline_dense_e5_voice_rewrite` | baseline | 현재 non-rerank 기본 후보 |
| `bge_cross_encoder_rerank_top20_reference` | quality ceiling reference | 이미 실행된 고비용 reranker 기준선 |
| `colbert_style_late_interaction_top20_cuda` | planned candidate | retrieve top20 후보를 late interaction 방식으로 재정렬하는 계획 후보 |
| `colbert_style_late_interaction_top50_cuda` | planned candidate | recall-oriented 후보를 더 넓게 받아 재정렬하는 계획 후보 |

이번 단계에서는 planned candidate를 실행하지 않는다. 다음 gate에서 model, tokenizer, index artifact, memory budget, candidate_k를 다시 고정한다.

## Metric Gate

| metric | 기준 |
| --- | --- |
| `Recall@5` | baseline 이상이어야 함 |
| `MRR` | baseline 대비 하락하면 채택 금지 |
| `nDCG@5` | top-rank 품질 판단의 1차 metric |
| `latency_p95_ms` | BGE cross-encoder reference보다 명확히 낮아야 함 |
| `cuda_memory_peak_mb` | 4080 SUPER local budget 안에서 기록 |
| `candidate_empty_result_count` | 0이어야 함 |
| `public_raw_payload_leakage_count` | 0이어야 함 |

개선 주장은 이 단계에서 금지한다. 다음 실행 gate에서도 dev hard subset 개선만 주장할 수 있고, locked test 또는 production claim은 별도 승인 없이는 금지한다.

## Stop Condition

- CUDA를 사용할 수 없으면 실행 후보를 열지 않는다.
- hard subset target resolvability가 1건이라도 실패하면 실행하지 않는다.
- late interaction 후보가 BGE reference보다 latency가 낮지 않으면 기본 route 후보로 올리지 않는다.
- `MRR` 또는 `nDCG@5`가 baseline보다 낮으면 채택하지 않는다.
- public artifact에 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret이 발견되면 실패로 처리한다.

## 다음 실행 Gate

다음 작업은 `HD-COLBERT-001B`다.

`HD-COLBERT-001B`는 바로 locked test를 실행하지 않는다. 먼저 dev hard subset에서 다음을 고정해야 한다.

- 실제 model/provider 선택
- CUDA memory budget
- candidate_k
- index build 방식
- latency measurement 방식
- public-safe report schema
- 실행 중단 조건

## Claim Boundary

허용:

- ColBERT-style late interaction을 BGE reranker latency 대안 후보로 검토할 계획을 수립했다.
- CUDA 사용 가능성을 확인하고, 실행 전 gate와 metric을 고정했다.
- locked test와 Solar Pro 3 호출 없이 plan-only readiness를 완료했다.

금지:

- ColBERT로 retrieval 성능 개선
- ColBERT로 reranker latency 문제 해결 완료
- locked test에서 ColBERT 개선 입증
- production route에 ColBERT 적용
- 음성 관광 앱 완성
- 전체 도서 데이터 공개
