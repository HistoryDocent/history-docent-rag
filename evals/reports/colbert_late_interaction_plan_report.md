# ColBERT-style Late Interaction Plan Report

## 결론

`HD-COLBERT-001A`는 PASS다.

이번 결과는 ColBERT-style late interaction 실행 결과가 아니다. CUDA 사용 가능성을 확인하고, hard subset, candidate, metric, stop condition, public-safe boundary를 실행 전 고정한 plan-only readiness 결과다.

## 정량 결과

| metric | value |
| --- | ---: |
| planned_candidate_count | 2 |
| baseline_candidate_count | 1 |
| reference_candidate_count | 1 |
| hard_subset_query_type_count | 3 |
| planned_metric_count | 7 |
| solar_call_count | 0 |
| retrieval_execution_count | 0 |
| locked_test_execution_count | 0 |
| cuda_available_flag | 1 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| forbidden_success_claim_count | 0 |

## 정성 결과

| gate | status | 판단 |
| --- | --- | --- |
| scope control | PASS | plan-only로 제한하고 실제 retrieval 실행을 하지 않았다. |
| baseline control | PASS | 현재 기본 후보를 `baseline_dense_e5_voice_rewrite`로 유지한다. |
| locked boundary | PASS | locked test는 사용하지 않는다. |
| CUDA readiness | PASS | local CUDA 사용 가능 상태를 확인했다. |
| metric readiness | PASS | Recall@5, MRR, nDCG@5, latency, CUDA memory, empty result, public leakage gate를 고정했다. |
| public safety | PASS | raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다. |
| claim boundary | PASS | 성능 개선 주장을 금지하고 plan-only readiness만 기록한다. |

## Candidate Summary

| candidate_id | role | execution_status |
| --- | --- | --- |
| `baseline_dense_e5_voice_rewrite` | baseline | previous artifact only |
| `bge_cross_encoder_rerank_top20_reference` | quality ceiling reference | previous artifact only |
| `colbert_style_late_interaction_top20_cuda` | planned candidate | not executed |
| `colbert_style_late_interaction_top50_cuda` | planned candidate | not executed |

## Data Mart Grain

`fact_colbert_late_interaction_plan`의 grain은 `experiment_id + query_bucket + candidate_id + metric_family + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `experiment_id` | `HD-COLBERT-001A` 같은 stable experiment id |
| `query_bucket` | place_story, relationship, route_context 등 hard subset bucket |
| `candidate_id` | baseline, reference, planned late interaction 후보 |
| `metric_family` | retrieval, latency, cuda_memory, public_safety |
| `claim_boundary` | plan-only, dev-hard-subset-only, locked-only |
| `execution_status` | not_executed, previous_artifact_only, executed |
| `evidence_artifact` | public-safe report path |

금지 필드:

- raw query
- raw answer
- raw evidence
- prompt
- chunk text
- private file path
- secret

## 외부 감사 의견

현재 단계에서 ColBERT-style 후보를 바로 실행하지 않은 판단은 타당하다.

이유는 기존 final ablation에서 relationship hybrid active route 개선 주장을 locked retrieval에서 보류했고, BGE reranker도 latency 때문에 기본값에서 제외했기 때문이다. 새 reranking 계열 후보는 제출 패키지 이후 별도 hard subset 실험으로 제한해야 한다.

## 다음 Gate

다음 gate는 `HD-COLBERT-001B`다.

실행 전 승인 조건:

- model/provider 후보 확정
- candidate_k 확정
- CUDA memory cap 확정
- dev hard subset target resolvability 확인
- public-safe report schema 확정
- locked test 사용 금지 재확인
