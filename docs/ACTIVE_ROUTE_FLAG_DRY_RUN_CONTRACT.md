# Active Route Flag Dry-run Contract

## 결론

`HD-API-ROUTER-005`는 완료됐다.

`/api/v1/chat`에 `active_route_mode`를 추가했지만 기본값은 `disabled`다. `shadow`로 요청해도 실제 retrieval route는 바꾸지 않고, 응답에는 candidate route, guard 결과, fallback reason, 적용 여부만 public-safe field로 노출한다.

이 문서는 성능 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## API 계약

| field | 위치 | 값 |
| --- | --- | --- |
| `active_route_mode` | request | `disabled`, `shadow` |
| `classifier_router_dry_run.active_route_flag_dry_run.flag_policy_id` | response | `chat-active-route-flag-dry-run-v1` |
| `enabled` | response | `active_route_mode=shadow`일 때만 true |
| `default_enabled` | response | 항상 false |
| `selected_route_policy_id` | response | guard 적용 후 shadow candidate route |
| `fallback_reason_tag` | response | `feature_flag_disabled`, `shadow_only_candidate_route` 등 |
| `active_route_applied` | response | 항상 false |

## 정량 리포트

| metric | Chat API contract | Retrieval integration |
| --- | ---: | ---: |
| request_count | 6 | 3 |
| success_count | 4 | 3 |
| active_route_flag_dry_run_count | 4 | 3 |
| active_route_flag_enabled_count | 1 | 1 |
| active_route_flag_shadow_mode_count | 1 | 1 |
| active_route_flag_default_enabled_count | 0 | 0 |
| active_route_flag_applied_count | 0 | 0 |
| live_solar_call_count | 0 | 0 |
| public_raw_text_leakage_count | 0 | 0 |
| private_path_leakage_count | 0 | 0 |
| secret_like_leakage_count | 0 | 0 |

근거:

- `evals/reports/chat_api_contract_report.md`
- `evals/reports/chat_retrieval_integration_report.md`

## 정성 리포트

- `active_route_mode=disabled`는 기존 API 동작을 유지한다.
- `active_route_mode=shadow`는 route 후보를 관찰하지만 `usage.route_policy_id`를 바꾸지 않는다.
- `relationship_hybrid_weighted_e5_v1`은 active 적용이 아니라 shadow candidate로만 노출된다.
- `no_answer`와 guard가 우선이며, fallback reason은 원문 없이 tag만 남긴다.
- Solar Pro 3 live generation은 호출하지 않는다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | shadow evaluation 결과를 바로 production route로 연결하지 않고 API flag 경계를 먼저 고정한 것은 타당하다. |
| Backend | request/response contract만 확장했고 retrieval backend route 선택은 기존 `query_type` 기준으로 유지했다. |
| Evaluation | contract smoke와 retrieval integration smoke가 모두 `active_route_applied_count=0`을 확인했다. |
| Data warehouse | public row에는 route label, flag state, reason tag만 남기고 raw text 계열은 제외했다. |
| Security | secret, private path, 원문 chunk, raw answer는 report row에 없다. |
| 외부 감사 | 실제 성능 개선 claim 없이 rollback 가능한 dry-run field로 제한한 점이 적절하다. |

## 다음 Gate

다음 작업은 `HD-LOCKED-RETRIEVAL-001` locked retrieval 검증 승인 계획이다.

locked test 실행 전 금지:

- active route default enable
- relationship route production 적용 주장
- locked 성능 개선 주장
- Solar Pro 3 live generation 재실행
