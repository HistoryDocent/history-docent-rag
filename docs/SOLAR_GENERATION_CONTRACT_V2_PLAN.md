# Solar Pro 3 Generation Contract v2 비교 계획

## 결론

다음 작업은 청킹 재실험이 아니라 `Solar Pro 3 generation contract v2` 설계와 paired comparison이다.

단순 prompt-only 개선은 우선순위가 낮다. 현재 v1 구조에서는 Solar Pro 3 draft가 실제 사용한 evidence를 지정하지 않고, assembler가 packed evidence 전체를 citation으로 붙인다. 따라서 citation_precision을 올리려면 prompt 문구만 바꾸는 것보다 `used_evidence` 선택을 answer contract에 포함해야 한다.

이 문서는 실행 계획이다. live API 재호출 결과나 성능 개선 주장이 아니다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | v2는 prompt-only가 아니라 schema + assembler contract 변경이어야 한다. |
| Retrieval | `place_story`는 retrieval hard-case로 분리한다. generation v2 성공/실패 판단에 섞지 않는다. |
| Generation | Solar Pro 3가 답변에 실제 사용한 evidence rank를 구조화해서 반환해야 한다. |
| 평가 | v1과 v2는 같은 7개 query_id, 같은 retrieval label, 같은 packing policy에서 paired comparison한다. |
| 데이터 | 결과 grain은 query 단위 fact와 query_type summary를 분리한다. raw text는 fact에 넣지 않는다. |
| 보안 | public report에는 raw query, raw answer, chunk text, private path, secret 값을 기록하지 않는다. |
| 포트폴리오 | “citation precision 하락 원인 발견 -> contract 변경 -> paired comparison” 흐름으로 설명한다. |

## 현재 v1 한계

| 항목 | v1 상태 | 영향 |
| --- | --- | --- |
| draft schema | `answer`, `spoken_answer`, `unsupported_claim_risk`만 반환 | 답변이 어떤 evidence를 사용했는지 알 수 없다. |
| citation assembly | packed evidence 전체를 citation으로 변환 | 답변에 쓰지 않은 evidence도 citation으로 잡혀 precision이 낮아질 수 있다. |
| prompt rule | evidence 안에서 답하라고 지시 | citation 선택을 기계적으로 검증할 구조가 없다. |
| failure pattern | `place_fact`, `overview`는 target evidence가 들어왔지만 citation metric이 낮다 | 검색보다 citation selection contract 문제가 우선이다. |

## v2 계약 후보

`CitationRagDraftV2` 후보 필드:

| field | type | 목적 | public 저장 |
| --- | --- | --- | --- |
| `answer` | string | 화면 표시용 답변 | public row에는 fingerprint와 length만 저장 |
| `spoken_answer` | string | 음성 출력용 짧은 답변 | public row에는 length만 저장 |
| `used_evidence_pack_ranks` | list[int] | 답변에 실제 사용한 packed evidence rank | 집계 count와 validation result만 저장 |
| `coverage_intent` | enum | `focused`, `multi_evidence`, `abstain` 중 하나 | 가능 |
| `unsupported_claim_risk` | enum | `low`, `medium`, `high` | 가능 |

최소 규칙:

- `used_evidence_pack_ranks`는 evidence pack 안의 rank만 허용한다.
- answerable query에서 `used_evidence_pack_ranks`는 비어 있으면 안 된다.
- `place_fact`는 핵심 근거 1-3개를 선택한다.
- `overview`, `route_context`는 여러 근거가 필요한 경우 2개 이상을 선택할 수 있다.
- `spoken_answer`에는 citation marker, URL, bracket 문자를 넣지 않는다.
- evidence 밖 추론이 있으면 `unsupported_claim_risk`를 `medium` 이상으로 둔다.
- 선택한 evidence가 없거나 근거가 부족하면 abstain path로 보내야 한다.

## assembler v2 정책

| 단계 | 정책 |
| --- | --- |
| validate ranks | Solar가 반환한 rank가 evidence pack 안에 존재하는지 확인한다. |
| filter citations | 전체 packed evidence가 아니라 `used_evidence_pack_ranks`에 해당하는 evidence만 citation으로 변환한다. |
| fallback | rank가 비었거나 invalid하면 v2 gate에서 실패 처리한다. 임의로 전체 citation을 붙이지 않는다. |
| no-answer | 기존 abstain contract를 유지한다. Solar Pro 3를 호출하지 않는 path는 그대로 둔다. |
| place_story | retrieval hard-case tag를 유지하고 v2 generation 개선 성공 판단에서 분리한다. |

## 비교 실험 설계

| 항목 | v1 baseline | v2 candidate |
| --- | --- | --- |
| query set | baseline과 같은 7개 query_id | 동일 |
| retrieval label | `dense_multilingual_e5_small_voice_rewrite` | 동일 |
| packing policy | `P0_rank_order` | 동일 |
| model | `solar-pro3` | 동일 |
| answer policy | `solar-generation-baseline-v1` | `solar-generation-contract-v2` |
| output report | `solar_generation_baseline_report.md` | `solar_generation_contract_v2_comparison_report.md` |
| private row path | private results only | private results only |

query별 처리:

| query_type | v2 비교 사용 | 판단 |
| --- | --- | --- |
| `place_fact` | yes | citation precision과 latency를 핵심으로 본다. |
| `overview` | yes | citation recall과 multi-evidence coverage를 핵심으로 본다. |
| `place_story` | monitor only | retrieval hard-case라 generation 개선 성공률 계산에서 분리한다. |
| `relationship` | regression | 기존 1.0/1.0 citation 성능이 깨지지 않아야 한다. |
| `route_context` | monitor | recall 0.5에서 하락하면 실패로 본다. |
| `voice_followup` | regression | spoken answer naturalness와 citation 성능을 유지해야 한다. |
| `no_answer` | regression | abstention accuracy가 1.0을 유지해야 한다. |

## 정량 평가 기준

primary metric:

- `citation_precision`
- `citation_recall`
- `Correct-with-Evidence`
- `unsupported_claim_rate`

secondary metric:

- `spoken_answer_naturalness`
- `place_relevance`
- `docent_usefulness`
- `latency_p95_ms`
- `solar_call_count`
- `total_tokens`

v2 후보 통과 기준:

| gate | 기준 |
| --- | --- |
| public safety | raw answer, raw query, chunk text, private path, secret-like value 0 |
| schema validity | `used_evidence_pack_ranks` invalid count 0 |
| no-answer regression | `abstention_accuracy` 1.0 유지 |
| unsupported claim | `unsupported_claim_rate` 0.0 유지 |
| relationship regression | `relationship` citation_precision/recall 1.0 유지 |
| target cases | `place_fact` 또는 `overview` 중 1개 이상 citation metric 개선 |
| latency | `latency_p95_ms` 악화 시 원인 기록 |
| claim boundary | 7건 결과를 통계적 성능 개선으로 표현하지 않음 |

## 정성 평가 기준

| 항목 | 확인 질문 |
| --- | --- |
| evidence discipline | 답변이 선택한 evidence 범위를 벗어나지 않는가 |
| citation minimality | 답변에 쓰지 않은 evidence를 citation으로 붙이지 않는가 |
| coverage | overview 답변에서 필요한 근거를 하나만 쓰고 지나치게 단순화하지 않는가 |
| spoken answer | 음성 출력용 답변이 짧고 현장 도슨트 톤을 유지하는가 |
| abstain behavior | 근거 부족 시 무리해서 답하지 않는가 |

정성 평가는 public report에 원문을 싣지 않는다. 필요한 경우 private review note에는 sanitized summary만 저장한다.

## 구현 단위

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| `HD-GEN-V2-001` | baseline, failure analysis | v2 draft schema와 prompt policy 문서화 | public-safe docs, TODO 링크 | low | 문서 revert |
| `HD-GEN-V2-002` | `HD-GEN-V2-001` | `CitationRagDraftV2` schema와 provider mock test | schema unit test, provider contract test | medium | v2 schema 파일 revert |
| `HD-GEN-V2-003` | `HD-GEN-V2-002` | assembler가 selected evidence만 citation으로 변환 | citation filtering test, regression test | medium | assembler v2 path revert |
| `HD-GEN-V2-004` | `HD-GEN-V2-003` | v1/v2 paired comparison runner | fake provider test, public-safe report test | medium | runner/report revert |
| `HD-GEN-V2-005` | `HD-GEN-V2-004` | 승인 후 Solar Pro 3 live paired comparison 실행 | live report, public gate 0 | medium | private result 삭제, public report revert |

## 보고서 형식

`solar_generation_contract_v2_comparison_report.md`에는 다음만 기록한다.

- run metadata alias
- query_type별 v1/v2 metric
- paired delta
- failure tag
- public output gate
- qualitative summary
- claim boundary

기록하지 않는 것:

- raw query text
- raw answer
- raw evidence/context
- chunk text
- private file path
- API key 또는 credential

## 외부 감사 체크

| 감사 항목 | 기대 결과 |
| --- | --- |
| 실험 공정성 | v1/v2 query set, retrieval label, packing policy 동일 |
| 데이터 보안 | public report leakage count 0 |
| metric grain | query fact와 query_type summary를 섞지 않음 |
| 실패 분리 | `place_story`를 generation 실패로 과잉 해석하지 않음 |
| 주장 경계 | live 7건 결과를 최종 성능 개선으로 주장하지 않음 |

## 다음 액션

1. `CitationRagDraftV2` schema를 코드에 추가한다.
2. Solar Pro 3 provider prompt를 v2 전용으로 분리한다.
3. assembler v2에서 selected evidence만 citation으로 변환한다.
4. fake provider 기반 paired comparison report test를 먼저 만든다.
5. 별도 승인 후 live Solar Pro 3 paired comparison을 실행한다.

## 진행 상태

- `HD-GEN-V2-002`: 완료. `CitationRagDraftV2` schema와 provider mock response 계약을 검증했다.
- `HD-GEN-V2-003`: 완료. assembler가 v2 selected evidence rank만 citation으로 변환한다.
- `HD-GEN-V2-004`: 완료. fake provider 기반 v1/v2 paired comparison runner와 public-safe report를 추가했다.
- `HD-GEN-V2-005`: 미진행. live Solar Pro 3 paired comparison은 별도 승인 후 실행한다.
