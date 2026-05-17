# HyDE Larger Live Paired Retrieval Comparison Report

## 목적

`HD-HYDE-001D`는 `HD-HYDE-001C` readiness에서 고정한 dev 40개 query subset으로 Solar Pro 3 HyDE query expansion이 retrieval metric을 개선하는지 paired 비교한다.

이 리포트는 최종 성능 개선 주장이 아니다. raw query, raw answer, raw evidence, raw HyDE text, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `hyde-larger-live-paired-retrieval-comparison-report/v1` |
| comparison_id | `hyde-live-paired-q40-c30-3515845c6c21` |
| work_id | `HD-HYDE-001D` |
| readiness_id | `hyde-larger-dev-readiness-q40-c30-d01462ab869e` |
| generated_at_utc | `2026-05-17T07:02:43+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| result_path | `<private artifact: hyde_larger_live_paired_retrieval_comparison_rows.jsonl>` |
| provider | `solar_pro_3` |
| provider_config_id | `solar-pro-3-204eb9617a` |
| endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| model_id | `solar-pro3` |
| prompt_policy_id | `solar-pro3-hyde-query-expansion-v1` |
| packing_policy_id | `P0_rank_order` |
| top_k | 5 |
| resolved_device | `cuda` |
| source_fingerprint | `a71c5766bff8` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 40 |
| answerable_query_count | 30 |
| no_answer_query_count | 10 |
| baseline_retrieval_run_count | 40 |
| hyde_retrieval_run_count | 30 |
| hyde_generation_request_count | 30 |
| no_answer_guard_query_count | 10 |
| solar_api_call_count | 30 |
| live_call_hard_cap | 40 |
| hard_cap_exceeded | false |
| prompt_tokens | 11319 |
| completion_tokens | 3378 |
| total_tokens | 14697 |
| estimated_cost | 0.000000 |
| recall_at_1_delta | -0.066667 |
| recall_at_3_delta | -0.033333 |
| recall_at_5_delta | 0.033333 |
| mrr_delta | -0.035000 |
| ndcg_at_5_delta | -0.018384 |
| latency_p95_ms_delta | 1855.705900 |
| adoption_decision | `reject_hyde_for_now` |

## Candidate Metrics

| candidate | query_count | retrieve_query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_with_candidate_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 40 | 30 | 0.666667 | 0.800000 | 0.800000 | 0.727778 | 0.746426 | 23.188300 | 0 |
| HyDE | 40 | 30 | 0.600000 | 0.766667 | 0.833333 | 0.692778 | 0.728042 | 1878.894200 | 0 |

## Query Type Delta

| query_type | query_count | baseline Recall@5 | HyDE Recall@5 | Recall@5 delta | baseline MRR | HyDE MRR | MRR delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `no_answer` | 10 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| `overview` | 10 | 0.800000 | 0.900000 | 0.100000 | 0.750000 | 0.703333 | -0.046667 |
| `place_story` | 10 | 0.600000 | 0.800000 | 0.200000 | 0.600000 | 0.725000 | 0.125000 |
| `relationship` | 10 | 1.000000 | 0.800000 | -0.200000 | 0.833333 | 0.650000 | -0.183333 |

## Query Pair Rows

| query_id | query_type | baseline_route | hyde_route | baseline_rank | hyde_rank | baseline@5 | hyde@5 | hyde_hash | hyde_len | solar_api_call |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: | ---: |
| `q-dev-no-answer-001` | `no_answer` | `abstain_first_v1` | `abstain_first_v1` | 0 | 0 | false | false | `blocked` | 0 | 0 |
| `q-dev-no-answer-002` | `no_answer` | `abstain_first_v1` | `abstain_first_v1` | 0 | 0 | false | false | `blocked` | 0 | 0 |
| `q-dev-no-answer-003` | `no_answer` | `abstain_first_v1` | `abstain_first_v1` | 0 | 0 | false | false | `blocked` | 0 | 0 |
| `q-dev-no-answer-004` | `no_answer` | `abstain_first_v1` | `abstain_first_v1` | 0 | 0 | false | false | `blocked` | 0 | 0 |
| `q-dev-no-answer-005` | `no_answer` | `abstain_first_v1` | `abstain_first_v1` | 0 | 0 | false | false | `blocked` | 0 | 0 |
| `q-dev-no-answer-006` | `no_answer` | `abstain_first_v1` | `abstain_first_v1` | 0 | 0 | false | false | `blocked` | 0 | 0 |
| `q-dev-no-answer-007` | `no_answer` | `abstain_first_v1` | `abstain_first_v1` | 0 | 0 | false | false | `blocked` | 0 | 0 |
| `q-dev-no-answer-008` | `no_answer` | `abstain_first_v1` | `abstain_first_v1` | 0 | 0 | false | false | `blocked` | 0 | 0 |
| `q-dev-no-answer-009` | `no_answer` | `abstain_first_v1` | `abstain_first_v1` | 0 | 0 | false | false | `blocked` | 0 | 0 |
| `q-dev-no-answer-010` | `no_answer` | `abstain_first_v1` | `abstain_first_v1` | 0 | 0 | false | false | `blocked` | 0 | 0 |
| `q-dev-overview-001` | `overview` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 1 | true | true | `aaa7425992d0f36d` | 276 | 1 |
| `q-dev-overview-002` | `overview` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 1 | true | true | `d13c6b51fe2e2bdb` | 287 | 1 |
| `q-dev-overview-003` | `overview` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 3 | true | true | `a36e0d3bddd99055` | 241 | 1 |
| `q-dev-overview-004` | `overview` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 1 | true | true | `32050eb963fb463c` | 227 | 1 |
| `q-dev-overview-005` | `overview` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 0 | 0 | false | false | `e4ebdd7a9a0bbb3d` | 328 | 1 |
| `q-dev-overview-006` | `overview` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 1 | true | true | `6f6acc52540d51f8` | 283 | 1 |
| `q-dev-overview-007` | `overview` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 2 | true | true | `905f3372d34b1d30` | 190 | 1 |
| `q-dev-overview-008` | `overview` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 2 | 5 | true | true | `9ca87e142fe97453` | 301 | 1 |
| `q-dev-overview-009` | `overview` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 1 | true | true | `a70c26952e208864` | 258 | 1 |
| `q-dev-overview-010` | `overview` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 0 | 1 | false | true | `ce4bfc42652b7d2a` | 198 | 1 |
| `q-dev-place-story-001` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 0 | 0 | false | false | `ca322d82a0677728` | 227 | 1 |
| `q-dev-place-story-002` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 1 | true | true | `84a3f34698e34f58` | 251 | 1 |
| `q-dev-place-story-003` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 1 | true | true | `2a89a47d5098370d` | 271 | 1 |
| `q-dev-place-story-004` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 1 | true | true | `7d3f37126fa33885` | 193 | 1 |
| `q-dev-place-story-005` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 0 | 4 | false | true | `b9610cc313b25b24` | 170 | 1 |
| `q-dev-place-story-006` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 1 | true | true | `bf78115af820a970` | 216 | 1 |
| `q-dev-place-story-007` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 1 | true | true | `940cbcae277d5ba8` | 241 | 1 |
| `q-dev-place-story-008` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 0 | 0 | false | false | `3ff2565a15580ce1` | 249 | 1 |
| `q-dev-place-story-009` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 0 | 1 | false | true | `68f3fe06307f261c` | 289 | 1 |
| `q-dev-place-story-010` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 1 | 1 | true | true | `ba5a7b93955ba649` | 287 | 1 |
| `q-dev-relationship-001` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted_e5_small_alpha_0_5` | 3 | 2 | true | true | `426384fac95767b1` | 250 | 1 |
| `q-dev-relationship-002` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted_e5_small_alpha_0_5` | 1 | 1 | true | true | `d91fa38c30e5ead7` | 211 | 1 |
| `q-dev-relationship-003` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted_e5_small_alpha_0_5` | 1 | 1 | true | true | `0ff049d316ecd233` | 274 | 1 |
| `q-dev-relationship-004` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted_e5_small_alpha_0_5` | 2 | 2 | true | true | `477dbf4315ff40af` | 253 | 1 |
| `q-dev-relationship-005` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted_e5_small_alpha_0_5` | 1 | 2 | true | true | `edaaa76c2a50c85b` | 197 | 1 |
| `q-dev-relationship-006` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted_e5_small_alpha_0_5` | 1 | 1 | true | true | `ade9a78cbaa18c86` | 221 | 1 |
| `q-dev-relationship-007` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted_e5_small_alpha_0_5` | 1 | 1 | true | true | `12e52aafaa12c4b7` | 201 | 1 |
| `q-dev-relationship-008` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted_e5_small_alpha_0_5` | 1 | 0 | true | false | `460be68618471d41` | 226 | 1 |
| `q-dev-relationship-009` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted_e5_small_alpha_0_5` | 2 | 0 | true | false | `e638d57bd3469ba2` | 176 | 1 |
| `q-dev-relationship-010` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted_e5_small_alpha_0_5` | 1 | 1 | true | true | `8aee692f6f90791f` | 272 | 1 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 47 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `scope`: HD-HYDE-001C에서 고정한 dev 40개 query subset만 비교했다.
- `chunking_boundary`: C0 parent-child chunking을 고정하고 청킹 변수를 새로 열지 않았다.
- `llm_call_boundary`: answerable query 30개만 Solar Pro 3 HyDE generation을 실행한다.
- `no_answer_boundary`: no_answer query 10개는 HyDE generation과 retrieval을 모두 차단한다.
- `retrieval_boundary`: baseline과 HyDE 모두 같은 chunk corpus, 같은 top_k, 같은 route family를 사용한다.
- `latency_boundary`: HyDE latency는 generation latency와 retrieval latency를 합산한다.
- `cuda_boundary`: retrieval embedding 경로는 사용 가능하면 CUDA를 사용하며 report에 resolved_device를 기록한다.
- `data_mart_grain`: `fact_hyde_larger_live_pair` grain은 comparison_id + query_id + candidate_id다.
- `security_boundary`: public artifact에는 raw query, raw HyDE text, prompt, evidence text를 남기지 않는다.
- `external_audit`: 5개 subset 후보성을 40개로 확대했지만 locked test 전 채택 주장은 금지한다.
- `gate_status`: PASS

## 해석

HyDE는 larger dev subset에서만 비교했다. 이 결과는 locked test 또는 production 성능 개선 주장이 아니다.
