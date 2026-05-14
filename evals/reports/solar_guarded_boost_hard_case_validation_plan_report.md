# Solar Pro 3 Guarded Boost Hard-case Validation Plan Report

## 목적

HD-SOLAR-018 문서 작업이 다음 실험을 실행하기 전에 정량/정성 gate, public-safe boundary, data mart grain을 충분히 고정했는지 검토한다.

이 리포트는 계획 검토 리포트다. Solar Pro 3 추가 호출, retrieval 재실행, generation 재평가는 수행하지 않았다.

## 정량 리포트

| metric | value |
| --- | ---: |
| reviewed_source_report_count | 2 |
| planned_hard_case_bucket_count | 6 |
| planned_public_safe_fact_count | 1 |
| planned_dimension_count | 6 |
| planned_next_implementation_units | 2 |
| planned_solar_call_count | 0 |
| planned_locked_test_usage | 0 |
| planned_public_raw_text_fields | 0 |
| planned_private_path_fields | 0 |
| planned_secret_fields | 0 |

기준으로 사용한 기존 metric:

| metric | value |
| --- | ---: |
| live_eval_count | 10 |
| live_candidate_selected_count | 1 |
| live_guardrail_block_count | 9 |
| live_correct_with_evidence_delta | 0.000000 |
| live_citation_precision_delta | 0.000000 |
| live_citation_recall_delta | 0.028572 |
| live_unsupported_claim_delta | 0.000000 |
| live_latency_p95_ms_delta | 388.989500 |

## 정성 리포트

- `scope`: guarded boost next gate 이후 추가 dev hard-case 검증 계획을 문서화했다.
- `execution_boundary`: 새 실험 실행은 없고, 기존 HD-SOLAR-016 결과를 바탕으로 다음 runner의 gate를 설계했다.
- `claim_boundary`: 최종 성능 개선, production 채택, locked test 통과, 통계적 유의성은 주장하지 않는다.
- `security_boundary`: public artifact에는 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다.
- `data_grain`: hard-case validation fact grain을 `validation_id + query_id + hard_case_bucket + strategy_id + router_policy_id + answer_policy_id`로 고정했다.
- `next_action`: HD-SOLAR-019에서 Solar call 0 조건의 hard-case validation runner와 public-safe report를 구현한다.

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
| 계획 완결성 | PASS |
| 정량 gate | PASS |
| 정성 tag | PASS |
| data mart grain | PASS |
| public-safe boundary | PASS |
| claim boundary | PASS |

## 결정

HD-SOLAR-018은 문서 gate를 통과했다.

다음 작업은 HD-SOLAR-019 guarded boost hard-case validation runner 구현이다. 이 작업도 기본 조건은 Solar Pro 3 추가 호출 0회다.
