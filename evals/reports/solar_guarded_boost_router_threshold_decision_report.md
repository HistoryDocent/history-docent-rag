# Solar Pro 3 Guarded Boost Router Threshold Decision Report

## 목적

HD-SOLAR-020의 router threshold 판단이 HD-SOLAR-016, HD-SOLAR-019 결과를 근거로 정량/정성 gate와 public-safe boundary를 충족하는지 검토한다.

이 리포트는 문서 판단 리포트다. Solar Pro 3 추가 호출, retrieval 재실행, generation 재평가는 수행하지 않았다.

## 정량 리포트

| metric | value |
| --- | ---: |
| reviewed_source_report_count | 2 |
| threshold_option_count | 3 |
| selected_threshold_option_count | 1 |
| selected_candidate_count | 1 |
| guardrail_block_count | 9 |
| manual_review_count | 2 |
| route_decision_mismatch_count | 0 |
| selected_candidate_safety_passed | 1 |
| manual_review_block_passed | 1 |
| doc_guardrail_block_passed | 1 |
| citation_recoverability_min | 1.000000 |
| planned_solar_call_count | 0 |
| planned_locked_test_usage | 0 |
| public_raw_text_field_count | 0 |
| private_path_field_count | 0 |
| secret_field_count | 0 |

기준 metric:

| metric | value |
| --- | ---: |
| live_correct_with_evidence_delta | 0.000000 |
| live_citation_precision_delta | 0.000000 |
| live_citation_recall_delta | 0.028572 |
| live_unsupported_claim_delta | 0.000000 |
| live_latency_p95_ms_delta | 388.989500 |

## 판단 결과

| option | decision | reason |
| --- | --- | --- |
| relax_threshold | reject | manual review 2건의 evidence order regression이 커서 자동 선택 위험이 있다. |
| tighten_threshold | reject | 유일한 safe direct gain 1건의 recall gain을 잃을 수 있다. |
| keep_threshold | accept | route mismatch 0, selected candidate safety pass, manual review block pass를 만족한다. |

## 정성 리포트

- `scope`: `place_story_guarded_boost_v1` threshold 유지/수정 판단을 문서화했다.
- `execution_boundary`: 새 retrieval/generation 실행은 없다.
- `llm_call_boundary`: Solar Pro 3 추가 호출은 0회다.
- `claim_boundary`: dev-only router 판단이며 production 기본값 채택이나 최종 성능 개선 주장이 아니다.
- `security_boundary`: public artifact에는 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다.
- `data_grain`: threshold decision fact grain을 `decision_id + router_policy_id + validation_id + metric_family`로 고정했다.
- `next_action`: locked test 또는 expanded dev 검증 실행 전 승인 계획을 먼저 작성한다.

## Public Output Gate

| metric | value |
| --- | ---: |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_claim_count | 0 |

## 외부 감사 결론

| 감사 항목 | 결과 |
| --- | --- |
| 근거 연결 | PASS |
| 정량 gate | PASS |
| 정성 gate | PASS |
| data mart grain | PASS |
| public-safe boundary | PASS |
| claim boundary | PASS |

## 결정

HD-SOLAR-020은 문서 gate를 통과했다.

`place_story_guarded_boost_v1` threshold는 유지한다. 다음 작업은 HD-SOLAR-021 locked test 또는 expanded dev 검증 승인 계획 작성이다.
