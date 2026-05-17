# Chunking Decision Review Report

## 목적

`HD-CHUNK-DECISION-REVIEW-001`은 현재 청킹 기준선인 `C0 current parent-child`를 유지할지, 지금 청킹 비교를 다시 열지 판단하기 위한 public-safe 리뷰다.

이 리포트는 새 retrieval 실행 결과가 아니다. 기존 `chunking-ablation-report/v2`와 청킹 전략 문서를 근거로 한 의사결정 보고서다.

raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `chunking-decision-review-report/v1` |
| review_id | `HD-CHUNK-DECISION-REVIEW-001` |
| generated_at_utc | `2026-05-17T01:28:50Z` |
| source_report | `evals/reports/chunking_ablation_v2_report.md` |
| decision_doc | `docs/CHUNKING_DECISION_REVIEW.md` |
| selected_variant_id | `C0` |
| selected_strategy | `structure-aware hierarchical parent-child` |
| solar_call_count | 0 |
| cuda_required | false |

## 정량 리포트

| metric | value |
| --- | ---: |
| compared_variant_count | 7 |
| pass_gate_variant_count | 5 |
| failed_gate_variant_count | 2 |
| selected_variant_recall_at_5 | 0.566667 |
| selected_variant_mrr | 0.471389 |
| selected_variant_ndcg_at_5 | 0.344203 |
| selected_variant_latency_p95_ms | 7.504000 |
| selected_variant_citation_recoverability | 1.000000 |
| selected_variant_retrievable_coverage | 1.000000 |
| selected_variant_overlap_blocks | 1 |
| fixed_size_baseline_recall_at_5 | 0.316667 |
| fixed_size_baseline_gate_pass | 0 |
| semantic_chunking_executed | 0 |
| sentence_window_executed | 0 |
| active_pipeline_changed | 0 |

## Variant 판단

| variant | 판단 | 근거 |
| --- | --- | --- |
| `C0` | adopt | gate PASS, Recall@5/MRR/nDCG@5 기준 최종 선택 |
| `C1` | reject | smaller child에서 Recall@5 급락 |
| `C2` | reject | C0 대비 Recall@5와 nDCG@5 낮음 |
| `C3` | reject | micro-parent merge가 C0를 넘지 못함 |
| `C4` | reject | `short_standalone_child` gate 실패 |
| `C5` | reject | overlap 2가 C0를 넘지 못하고 latency 증가 |
| `C6` | reject | fixed-size block baseline, gate 실패 및 낮은 Recall@5 |

## 방식별 적용 상태

| 방식 | 적용 상태 | 리뷰 판단 |
| --- | --- | --- |
| Character | 미적용 | citation provenance와 구조 보존 때문에 기본 후보 아님 |
| Sentence | 미실험 | parser block 기반 구조가 이미 존재해 후순위 |
| Semantic | 미실험 | boundary failure 증거가 있을 때만 targeted experiment로 연다 |
| Sentence Window | 미실험 | parent-child context expansion과 역할이 겹침 |
| Fixed-size | C6로 근사 비교 | gate 실패로 제외 |
| Structure-aware | C0-C5 | C0 채택 |
| Hierarchical/Hybrid | C0 | 현재 기준선 |

## Public Output Gate

| metric | value |
| --- | ---: |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_claim_count | 0 |
| active_pipeline_changed | 0 |

## 정성 리포트

- `decision`: 청킹 재비교를 지금 다시 열지 않고 C0를 유지한다.
- `reason`: C0-C6 비교가 이미 있으며 C0가 gate와 retrieval metric을 동시에 가장 잘 만족했다.
- `limitation`: semantic chunking, sentence window, pure sentence chunking은 아직 실제 비교하지 않았다.
- `risk`: "모든 청킹 최적화 완료"라고 표현하면 과장이다.
- `next_gate`: failure analysis에서 chunk boundary 문제가 반복될 때만 targeted chunk audit을 연다.
- `security_boundary`: 공개 산출물에는 집계 수치와 방식명만 남긴다.
- `execution_boundary`: 문서 리뷰 작업이므로 Solar Pro 3 호출과 CUDA 연산을 사용하지 않는다.
- `external_audit`: C0 유지 판단은 타당하나 locked test 성능 또는 production 성능 주장으로 확장하면 안 된다.

## 결론

현재 단계에서는 청킹을 새로 비교하지 않는다.

다음 작업은 `/chat` dry-run field에 guarded route 후보를 노출하는 `HD-API-ROUTER-002`가 더 우선이다. 청킹은 후속 failure analysis에서 boundary 손실이 확인될 때만 targeted experiment로 다시 연다.
