# HyDE Live Paired Retrieval Comparison Report

## 목적

`HD-HYDE-001B`는 `HD-HYDE-001A` readiness에서 고정한 5개 query subset으로 Solar Pro 3 HyDE query expansion이 retrieval metric을 개선하는지 paired 비교한다.

이 리포트는 최종 성능 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `hyde-live-paired-retrieval-comparison-report/v1` |
| comparison_id | `hyde-live-paired-q5-c4-0d3952fda9dc` |
| work_id | `HD-HYDE-001B` |
| readiness_id | `hyde-subset-readiness-q5-c4-b74ec047069e` |
| generated_at_utc | `2026-05-17T06:27:38+00:00` |
| dataset_path | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| chunks_path | `<private parent_child_chunks report>` |
| result_path | `<private artifact: hyde_live_paired_retrieval_comparison_rows.jsonl>` |
| provider | `solar_pro_3` |
| provider_config_id | `solar-pro-3-204eb9617a` |
| endpoint_alias | `api.upstage.ai/v1/chat/completions` |
| model_id | `solar-pro3` |
| prompt_policy_id | `solar-pro3-hyde-query-expansion-v1` |
| packing_policy_id | `P0_rank_order` |
| top_k | 5 |
| resolved_device | `cuda` |
| source_fingerprint | `a99def648032` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | 5 |
| answerable_query_count | 4 |
| no_answer_query_count | 1 |
| baseline_retrieval_run_count | 5 |
| hyde_retrieval_run_count | 4 |
| hyde_generation_request_count | 4 |
| no_answer_guard_query_count | 1 |
| solar_api_call_count | 4 |
| live_call_hard_cap | 10 |
| hard_cap_exceeded | false |
| prompt_tokens | 1491 |
| completion_tokens | 407 |
| total_tokens | 1898 |
| estimated_cost | 0.000000 |
| recall_at_1_delta | -0.250000 |
| recall_at_3_delta | 0.000000 |
| recall_at_5_delta | 0.250000 |
| mrr_delta | -0.062500 |
| ndcg_at_5_delta | 0.015402 |
| latency_p95_ms_delta | 1499.894500 |
| adoption_decision | `keep_hyde_candidate_for_larger_eval` |

## Candidate Metrics

| candidate | query_count | retrieve_query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_with_candidate_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 5 | 4 | 0.250000 | 0.250000 | 0.250000 | 0.250000 | 0.250000 | 297.450600 | 0 |
| HyDE | 5 | 4 | 0.000000 | 0.250000 | 0.500000 | 0.187500 | 0.265402 | 1797.345100 | 0 |

## Query Type Delta

| query_type | query_count | baseline Recall@5 | HyDE Recall@5 | Recall@5 delta | baseline MRR | HyDE MRR | MRR delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `no_answer` | 1 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| `overview` | 1 | 0.000000 | 1.000000 | 1.000000 | 0.000000 | 0.500000 | 0.500000 |
| `place_story` | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| `relationship` | 1 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 0.250000 | -0.750000 |

## Query Pair Rows

| query_id | query_type | baseline_route | hyde_route | baseline_rank | hyde_rank | baseline@5 | hyde@5 | hyde_hash | hyde_len | solar_api_call |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: | ---: |
| `q-dev-place-story-001` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 0 | 0 | false | false | `ae9d835034e2cdaf` | 263 | 1 |
| `q-dev-place-story-008` | `place_story` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 0 | 0 | false | false | `7d96e455e514bcca` | 272 | 1 |
| `q-dev-relationship-008` | `relationship` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted_e5_small_alpha_0_5` | 1 | 4 | true | true | `1bec8dfa20560b5b` | 174 | 1 |
| `q-dev-overview-010` | `overview` | `dense_multilingual_e5_small_voice_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | 0 | 2 | false | true | `230e46a03f160d9b` | 213 | 1 |
| `q-dev-no-answer-001` | `no_answer` | `abstain_first_v1` | `abstain_first_v1` | 0 | 0 | false | false | `blocked` | 0 | 0 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 8 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `scope`: HD-HYDE-001A에서 고정한 5개 query subset만 비교했다.
- `llm_call_boundary`: answerable query 4개만 Solar Pro 3 HyDE generation을 실행한다.
- `no_answer_boundary`: no_answer query는 HyDE generation과 retrieval을 모두 차단한다.
- `retrieval_boundary`: baseline과 HyDE 모두 같은 chunk corpus, 같은 top_k, 같은 route family를 사용한다.
- `latency_boundary`: HyDE latency는 generation latency와 retrieval latency를 합산한다.
- `cuda_boundary`: retrieval embedding 경로는 사용 가능하면 CUDA를 사용하며 report에 resolved_device를 기록한다.
- `data_mart_grain`: `fact_hyde_live_pair` grain은 comparison_id + query_id + candidate_id다.
- `security_boundary`: public artifact에는 raw query, raw HyDE text, prompt, evidence text를 남기지 않는다.
- `external_audit`: subset이 작아 개선이 보이더라도 larger dev/locked test 전 채택 주장은 금지한다.
- `gate_status`: PASS

## 해석

HyDE는 live-dev-subset에서만 비교했다. 이 결과는 locked test 또는 production 성능 개선 주장이 아니다.
