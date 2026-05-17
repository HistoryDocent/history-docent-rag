# HyDE Larger Dev Subset Readiness Report

## 목적

`HD-HYDE-001C`는 HyDE live-dev-subset 5개 결과를 확대 검증하기 전 범위, call budget, no-answer guard를 고정한다.

이 리포트는 성능 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `hyde-larger-dev-subset-readiness-report/v1` |
| readiness_id | `hyde-larger-dev-readiness-q40-c30-d01462ab869e` |
| work_id | `HD-HYDE-001C` |
| generated_at_utc | `2026-05-17T06:47:52+00:00` |
| model_id | `solar-pro3` |
| prompt_policy_id | `solar-pro3-hyde-query-expansion-v1` |
| selection_strategy_id | `hyde_larger_dev_subset_v1_q10_per_type` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| result_path | `<private artifact: hyde_larger_dev_subset_readiness_rows.jsonl>` |
| source_fingerprint | `5fcccb6ee6a6` |
| resolved_device | `cuda` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 40 |
| query_type_count | 4 |
| target_query_type_count | 4 |
| expected_query_count_per_type | 10 |
| answerable_query_count | 30 |
| no_answer_query_count | 10 |
| hyde_candidate_query_count | 30 |
| no_answer_guard_query_count | 10 |
| baseline_retrieval_run_count | 40 |
| hyde_retrieval_run_count | 30 |
| expected_hyde_generation_live_call_count | 30 |
| live_call_hard_cap | 40 |
| hard_cap_exceeded | false |
| live_execution_requested | false |
| live_execution_confirmed | false |
| solar_call_count | 0 |
| cuda_required | false |
| readiness_decision | `ready_for_hyde_larger_live_approval` |

## Query Type Breakdown

| query_type | query_count | answerable | no_answer | expected_live_call | no_answer_guard | baseline | hyde_candidate |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `overview` | 10 | 10 | 0 | 10 | 0 | `dense_multilingual_e5_small_voice_rewrite_reference` | `solar_pro3_hyde_v1` |
| `place_story` | 10 | 10 | 0 | 10 | 0 | `dense_multilingual_e5_small_voice_rewrite_reference` | `solar_pro3_hyde_v1` |
| `relationship` | 10 | 10 | 0 | 10 | 0 | `hybrid_weighted_e5_small_alpha_0_5_reference` | `solar_pro3_hyde_v1` |
| `no_answer` | 10 | 0 | 10 | 0 | 10 | `abstain_first_v1` | `blocked_for_no_answer_guard` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 45 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `scope`: dev 70 중 overview, place_story, relationship, no_answer 40개만 확대한다.
- `chunking_boundary`: 청킹 비교는 다시 열지 않고 C0 parent-child 기준선을 유지한다.
- `llm_call_boundary`: readiness 단계에서 Solar Pro 3 live 호출은 수행하지 않는다.
- `no_answer_boundary`: no_answer query 10개는 HyDE generation과 retrieval 후보에서 차단한다.
- `retrieval_boundary`: answerable 30개만 HyDE retrieval paired comparison 대상으로 둔다.
- `citation_boundary`: HyDE 가설은 citation이 아니며 최종 citation은 source child chunk만 허용한다.
- `cuda_boundary`: readiness는 실행 계획 검증이지만 CUDA 사용 가능 여부를 resolved_device로 기록한다.
- `data_mart_grain`: `fact_hyde_larger_readiness` grain은 readiness_id + query_id + candidate_id다.
- `security_boundary`: public artifact에는 query id, type, count, boolean, decision만 남긴다.
- `external_audit`: 5개 subset 결과를 바로 채택하지 않고 40개 readiness로 확대한 판단은 타당하다.
- `gate_status`: PASS

## 해석

readiness gate는 통과했다. 다음 단계는 별도 승인 후 `HD-HYDE-001D` live paired retrieval comparison이다.
