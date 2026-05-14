# Solar Pro 3 Generation v2 Prompt Repair Plan Report

## 목적

HD-SOLAR-024의 Solar Pro 3 generation v2 prompt repair 계획이 기존 v1/v2 live comparison, trade-off analysis, guarded boost locked readiness 결과를 근거로 정량/정성 gate와 public-safe boundary를 충족하는지 검토한다.

이 리포트는 문서 판단 리포트다. Solar Pro 3 호출, retrieval 재실행, generation 재평가는 수행하지 않았다.

## 정량 리포트

| metric | value |
| --- | ---: |
| reviewed_source_report_count | 3 |
| prompt_repair_candidate_count | 3 |
| query_type_policy_count | 7 |
| planned_validator_stage_count | 1 |
| planned_dry_run_stage_count | 1 |
| planned_live_comparison_stage_count | 1 |
| current_stage_solar_call_count | 0 |
| planned_immediate_solar_call_count | 0 |
| v2_precision_gain_count | 3 |
| v2_precision_regression_count | 2 |
| v2_recall_regression_count | 2 |
| v2_correctness_regression_count | 1 |
| v2_unsupported_regression_count | 1 |
| v2_adoption_blocker_count | 1 |
| guarded_locked_selected_candidate_count | 0 |
| guarded_locked_candidate_live_call_count | 0 |
| target_resolvability_fail_count | 0 |
| citation_recoverability_min | 1.000000 |
| public_raw_text_field_count | 0 |
| raw_prompt_field_count | 0 |
| private_path_field_count | 0 |
| secret_field_count | 0 |

## 판단 결과

| option | decision | reason |
| --- | --- | --- |
| restart chunking ablation | reject_now | target resolvability와 citation recoverability가 정상이다. |
| adopt v2 contract as default | reject | correctness와 unsupported claim regression이 있다. |
| discard v2 permanently | reject | citation precision과 latency 개선 가능성은 있다. |
| run live Solar Pro 3 immediately | reject_now | prompt repair policy와 validator gate가 아직 없다. |
| write prompt repair plan | accept | 실패 원인에 맞는 다음 실험 단위다. |
| implement repaired v2 validator next | accept_next | live call 없이 prompt policy와 evidence floor를 검증할 수 있다. |

## 정성 리포트

- `scope`: selected evidence v2 prompt repair 계획과 다음 validator/dry-run/live 단계의 gate를 정의했다.
- `execution_boundary`: 이번 단계는 문서화이며 새 retrieval/generation 실행은 없다.
- `llm_call_boundary`: Solar Pro 3 추가 호출은 0회다.
- `prompt_boundary`: public 문서에는 raw prompt가 아니라 prompt policy id와 검증 규칙만 기록한다.
- `metric_boundary`: v2 live 7건 결과는 dev-only adoption 판단이며 최종 개선 주장이 아니다.
- `data_boundary`: data mart grain은 `repair_id + query_type + prompt_policy_id + eval_stage + metric_family`로 고정했다.
- `security_boundary`: raw query, raw answer, raw evidence, chunk text, private path, secret을 public artifact에 기록하지 않는다.
- `next_action`: repaired v2 prompt policy validator 구현이다.

## Public Output Gate

| metric | value |
| --- | ---: |
| public_raw_text_leakage_count | 0 |
| raw_prompt_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_claim_count | 0 |
| live_solar_call_count | 0 |

## 외부 감사 결론

| 감사 항목 | 결과 |
| --- | --- |
| 근거 연결 | PASS |
| 정량 gate | PASS |
| 정성 gate | PASS |
| data mart grain | PASS |
| public-safe boundary | PASS |
| cost boundary | PASS |
| claim boundary | PASS |

## 결정

HD-SOLAR-024는 문서 gate를 통과한다.

청킹 비교 테스트는 계속 보류한다. 다음 작업은 Solar Pro 3 live 호출 없이 `HD-SOLAR-025 repaired v2 prompt policy validator`를 구현하는 것이다.
