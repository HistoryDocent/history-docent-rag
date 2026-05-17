# HyDE Subset Readiness Report

## 목적

`HD-HYDE-001A`는 Solar Pro 3 기반 HyDE live 비교를 실행하기 전 subset, call budget, no-answer guard, public-safe gate를 고정한다.

이 리포트는 HyDE 성능 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `hyde-subset-readiness-report/v1` |
| readiness_id | `hyde-subset-readiness-q5-c4-b74ec047069e` |
| work_id | `HD-HYDE-001A` |
| generated_at_utc | `2026-05-17T06:11:16+00:00` |
| model_id | `solar-pro3` |
| prompt_policy_id | `solar-pro3-hyde-query-expansion-v1` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| result_path | `<private artifact: hyde_subset_readiness_rows.jsonl>` |
| source_fingerprint | `f7b52e7519a6` |
| resolved_device | `cuda` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 5 |
| query_type_count | 4 |
| answerable_query_count | 4 |
| no_answer_query_count | 1 |
| hyde_candidate_query_count | 4 |
| no_answer_guard_query_count | 1 |
| baseline_retrieval_run_count | 5 |
| hyde_retrieval_run_count | 4 |
| expected_hyde_generation_live_call_count | 4 |
| live_call_hard_cap | 10 |
| hard_cap_exceeded | false |
| live_execution_requested | false |
| live_execution_confirmed | false |
| solar_call_count | 0 |
| cuda_required | false |
| readiness_decision | `ready_for_hyde_live_approval` |

## Query Type Breakdown

| query_type | query_count | expected_hyde_generation_live_call_count | no_answer_guard_query_count |
| --- | ---: | ---: | ---: |
| `no_answer` | 1 | 0 | 1 |
| `overview` | 1 | 1 | 0 |
| `place_story` | 2 | 2 | 0 |
| `relationship` | 1 | 1 | 0 |

## Query Readiness Rows

| query_id | query_type | expected_behavior | subset_reason | baseline | hyde_candidate | expected_live_call | guard | status |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `q-dev-place-story-001` | `place_story` | `retrieve` | `place_story_targeted_audit_followup` | `dense_multilingual_e5_small_voice_rewrite_reference` | `solar_pro3_hyde_v1` | 1 | false | `ready_for_live_approval` |
| `q-dev-place-story-008` | `place_story` | `retrieve` | `place_story_retrieval_miss` | `dense_multilingual_e5_small_voice_rewrite_reference` | `solar_pro3_hyde_v1` | 1 | false | `ready_for_live_approval` |
| `q-dev-relationship-008` | `relationship` | `retrieve` | `relationship_retrieval_miss` | `hybrid_weighted_e5_small_alpha_0_5_reference` | `solar_pro3_hyde_v1` | 1 | false | `ready_for_live_approval` |
| `q-dev-overview-010` | `overview` | `retrieve` | `overview_retrieval_miss` | `dense_multilingual_e5_small_voice_rewrite_reference` | `solar_pro3_hyde_v1` | 1 | false | `ready_for_live_approval` |
| `q-dev-no-answer-001` | `no_answer` | `abstain` | `no_answer_hallucination_guard` | `abstain_first_v1` | `blocked_for_no_answer_guard` | 0 | true | `blocked_by_no_answer_guard` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 6 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `scope`: HyDE live 비교 전 subset과 call budget만 검증한다.
- `chunking_boundary`: 청킹 비교는 다시 열지 않고 C0 parent-child 기준선을 유지한다.
- `llm_call_boundary`: readiness 단계에서 Solar Pro 3 live 호출은 수행하지 않는다.
- `no_answer_boundary`: no_answer query는 HyDE generation 후보에서 차단한다.
- `retrieval_boundary`: answerable query만 baseline retrieval과 HyDE retrieval을 paired 비교 대상으로 둔다.
- `citation_boundary`: HyDE로 생성한 가설은 citation이 아니며 최종 citation은 source child chunk만 허용한다.
- `cuda_boundary`: 이번 readiness는 LLM call budget 검증이라 CUDA 연산이 필요하지 않다.
- `data_mart_grain`: `fact_hyde_subset_readiness` grain은 readiness_id + query_id + candidate_id다.
- `security_boundary`: public artifact에는 id, count, boolean, decision만 남긴다.
- `external_audit`: live 실행 전에 no-answer guard와 call cap을 고정한 판단은 타당하다.
- `gate_status`: PASS

## 해석

readiness gate는 통과했고, 후속 `HD-HYDE-001B` live paired retrieval comparison은 별도 보고서에서 실행했다.
