# ColBERT-style Late Interaction Execution Approval

## 결론

`HD-COLBERT-001B`는 ColBERT-style late interaction을 dev hard subset에서 실행할지 결정하기 위한 실행 승인 기준이다.

이번 단계에서는 실제 retrieval 비교를 실행하지 않는다. 실행 전 hard subset, CUDA budget, candidate, metric, stop condition, public-safe report schema를 고정한다.

이 문서는 public-safe 승인 기준만 기록한다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 전 판단

실행 후보는 유지한다. 단, 기본 route 후보로 올리지 않고 `dev-hard-subset-only` 실험으로 제한한다.

이유는 다음과 같다.

- 기존 BGE cross-encoder reranker는 품질 상한은 높지만 latency가 커서 기본값에서 제외됐다.
- ColBERT-style late interaction은 cross-encoder보다 낮은 latency 가능성을 볼 수 있는 후보지만, 아직 이 프로젝트 corpus에서 검증되지 않았다.
- locked retrieval paired comparison에서 relationship hybrid 개선 주장이 실패했으므로, 새 reranking 후보를 바로 locked test나 active route에 연결하면 claim boundary가 깨진다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | 현재 기본 stack은 유지한다. late interaction은 hard subset 실험 후보로만 둔다. |
| Retrieval | `place_story`, `relationship`, `route_context`에서 top-rank 회복 가능성만 본다. |
| Evaluation | 이번 문서는 실행 승인이며, 실행 자체는 별도 다음 단계로 분리한다. locked test는 금지한다. |
| ML/Ops | CUDA는 사용 가능하다. 이후 실행 시 memory peak와 latency를 함께 기록해야 한다. |
| Data warehouse | fact grain은 `experiment_id + execution_scope + query_bucket + candidate_id + metric_family + claim_boundary`로 둔다. |
| Security | public report에는 raw payload 없이 bucket, count, metric, decision만 기록한다. |
| Portfolio | 제출 포트폴리오의 핵심 claim은 이미 충분하다. ColBERT는 추가 고도화 실험으로만 둔다. |
| 외부 감사 | 실행 전 approval gate를 별도 문서로 만든 것은 타당하다. 실험 결과가 나오기 전 개선 표현은 금지한다. |

## 실행 Scope

| 항목 | 결정 |
| --- | --- |
| work id | `HD-COLBERT-001B` |
| expected_retrieval_execution_scope | `dev-hard-subset-only` |
| actual_retrieval_execution_count | 0 |
| locked_test_execution_count | 0 |
| solar_call_count | 0 |
| CUDA device | `NVIDIA GeForce RTX 4080 SUPER` |
| CUDA availability | available |
| candidate_k | `20`, `50` |
| query bucket | `place_story`, `relationship`, `route_context` |
| baseline candidate | `baseline_dense_e5_voice_rewrite` |
| planned candidate | `colbert_style_late_interaction_top20_cuda`, `colbert_style_late_interaction_top50_cuda` |

## 실행 전 Acceptance Gate

| gate | 기준 |
| --- | --- |
| CUDA | `torch.cuda.is_available()`가 true |
| hard subset | target resolvability fail count 0 |
| candidate | candidate_k 20, 50만 허용 |
| metric | `Recall@5`, `MRR`, `nDCG@5`, `latency_p95_ms`, `cuda_memory_peak_mb` 기록 |
| public report | raw query, raw answer, raw evidence, prompt, chunk text, private path, secret 미기록 |
| locked split | 사용 금지 |
| Solar Pro 3 | 호출 금지 |
| claim | dev hard subset 외 개선 주장 금지 |

## Stop Condition

- CUDA unavailable이면 실행하지 않는다.
- target resolvability fail count가 1 이상이면 실행하지 않는다.
- candidate empty result count가 1 이상이면 실패로 처리한다.
- latency p95가 BGE cross-encoder reference 대비 명확히 낮지 않으면 기본 route 후보로 올리지 않는다.
- MRR 또는 nDCG@5가 baseline보다 낮으면 채택하지 않는다.
- public report에서 raw payload 또는 secret-like leakage가 감지되면 실패로 처리한다.

## 다음 작업

다음 작업 후보는 `HD-COLBERT-001C`다.

`HD-COLBERT-001C`는 실제 dev hard subset 실행이다. 실행 전에는 다음을 다시 확인해야 한다.

- 사용할 ColBERT-style model/provider
- local artifact 저장 위치가 gitignore/public boundary 안에 있는지
- query bucket별 sample count
- CUDA memory cap
- timeout cap
- public-safe aggregate report format

## Claim Boundary

허용:

- ColBERT-style late interaction 실행 승인 기준을 고정했다.
- CUDA 사용 가능성과 dev hard subset-only 실행 범위를 확인했다.
- locked test와 Solar Pro 3 호출 없이 실행 전 gate를 문서화했다.

금지:

- ColBERT로 retrieval 성능 개선
- ColBERT로 reranker latency 문제 해결 완료
- ColBERT를 production route에 적용
- locked test에서 ColBERT 개선 입증
- Solar Pro 3 기반 ColBERT 성능 개선
- 음성 관광 앱 완성
