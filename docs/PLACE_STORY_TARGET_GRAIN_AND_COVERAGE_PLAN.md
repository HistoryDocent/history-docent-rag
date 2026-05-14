# Place Story Target Grain 및 Top-rank Coverage 개선 계획

## 결론

지금은 청킹 비교 테스트로 바로 돌아가지 않는다.

`place_story` hard-case의 현재 증거는 전체 청킹 실패가 아니라 `target_grain_mismatch`와 낮은 top-rank coverage다. target doc은 검색됐지만 target child와 parent는 빠졌고, doc도 rank 5에 있었다. 따라서 다음 작업은 청킹 재실험이 아니라 `place_story` 평가 target grain을 명확히 하고, retrieval top-rank coverage를 개선할 후보를 분리해서 검증하는 것이다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | 청킹, retrieval, evidence packing, generation prompt를 한 번에 바꾸면 원인 추적이 불가능하다. 이번 단계는 retrieval 입력 품질을 먼저 고정한다. |
| Retrieval | 현재 문제는 target doc이 rank 5에만 들어온 상태다. child/parent coverage와 rank를 먼저 올려야 한다. |
| Evaluation | `place_story`는 서사형 질문이라 child-only 정답 기준이 과도하게 엄격할 수 있다. child, parent, doc grain을 분리해 기록해야 한다. |
| Data warehouse | query 단위 fact에 target grain별 coverage metric을 저장해야 이후 ablation 비교가 가능하다. |
| Security | public 문서에는 raw query, raw evidence, raw answer, private path를 남기지 않는다. |
| Portfolio | 실패 원인을 청킹 탓으로 단정하지 않고 평가 grain과 retrieval 품질을 분해한 과정을 보여주는 것이 더 설득력 있다. |

## 현재 근거

| 항목 | 값 |
| --- | ---: |
| 대상 query | `q-dev-place-story-001` |
| target_child_covered_count | 0 |
| target_parent_covered_count | 0 |
| target_doc_covered_count | 1 |
| target_min_retrieval_rank | 5 |
| target_min_pack_rank | 5 |
| citation_recoverability | 1.000000 |
| evidence_order_relevance_proxy | 0.200000 |
| generation_regression_count | 1 |
| root_cause_decision | `target_grain_mismatch` |

해석:

1. citation 복구성은 깨지지 않았다.
2. 문서 단위로는 관련 corpus에 닿았지만, generation에 직접 쓰기 좋은 child/parent evidence가 빠졌다.
3. v2 prompt repair를 먼저 하면 입력 evidence 품질 문제를 prompt 문제로 오판할 수 있다.

## Target Grain 정책

`place_story` query는 다음 세 grain을 동시에 기록한다.

| grain | 의미 | 평가상 사용 |
| --- | --- | --- |
| child | 답변 citation으로 바로 쓰기 좋은 최소 근거 | strict success |
| parent | 서사 맥락을 제공하는 상위 묶음 | context success |
| doc | 같은 원천 문서에 도달한 약한 신호 | weak success |

채택 기준:

- 최종 `Correct-with-Evidence` 개선 주장은 child 또는 parent coverage 개선이 있어야 한다.
- doc coverage만 개선된 경우 retrieval이 완전히 빗나가지 않았다는 보조 신호로만 사용한다.
- `place_story`는 child strict metric과 parent relaxed metric을 함께 공개하고, 둘 중 하나만 선택해서 성능 개선을 주장하지 않는다.

## 개선 후보

1. `place_story` deterministic rewrite v2
   - 장소 alias, 시대 단서, 서사형 의도 토큰을 query에 추가한다.
   - LLM 호출 없이 reproducible하게 만든다.
   - 측정: `target_child_recall@5`, `target_parent_recall@5`, `MRR`, `nDCG@5`, `latency_p95_ms`.

2. parent/doc context boost
   - parent title, doc title, place alias가 query와 맞는 child candidate에 제한적으로 boost를 준다.
   - target label을 scoring에 사용하지 않는다.
   - 측정: top-3 안에 child 또는 parent가 들어오는지 본다.

3. story-aware evidence packing
   - retrieval 결과가 같은 doc에 낮은 rank로만 닿는 경우 같은 parent/doc의 상위 sibling evidence를 보강 후보로 둔다.
   - citation은 여전히 child 기준으로만 생성한다.
   - 측정: citation recoverability와 duplicate parent rate를 함께 본다.

4. judgment target grain review
   - private 평가셋에서 `place_story` target이 child로 너무 좁게 잡힌 항목을 점검한다.
   - target을 느슨하게 바꾸는 작업이 아니라 child/parent/doc label을 분리해 평가 해석을 정교화하는 작업이다.

## 실험 순서

| 순서 | 작업 | 통과 기준 |
| --- | --- | --- |
| 1 | `place_story` 전체 dev query의 target grain coverage 진단 | 완료. child/parent/doc coverage와 min rank가 query별로 기록됨 |
| 2 | hard-case subset 정의 | child+parent miss 또는 target rank 4 이상 query를 분리 |
| 3 | deterministic rewrite v2 비교 | hard subset에서 child 또는 parent `Recall@5` 개선 |
| 4 | parent/doc context boost 비교 | top-rank 지표가 좋아지고 latency 악화가 제한적임 |
| 5 | story-aware packing 비교 | citation recoverability 유지, duplicate parent rate 악화 없음 |
| 6 | Solar Pro 3 v2 prompt repair 재검토 | retrieval 입력 품질 개선 후에만 live paired comparison 수행 |

## HD-PLACE-STORY-006 실행 결과

`place_story` 전체 dev query 10개를 대상으로 target grain coverage diagnostic runner를 실행했다.

| metric | value |
| --- | ---: |
| analyzed_query_count | 10 |
| target_child_recall_at_5 | 0.600000 |
| target_parent_recall_at_5 | 0.600000 |
| target_doc_recall_at_5 | 0.900000 |
| child_or_parent_recall_at_5 | 0.600000 |
| hard_case_count | 4 |
| doc_only_covered_count | 3 |
| full_grain_miss_count | 1 |
| MRR | 0.770000 |
| nDCG@5 | 0.616818 |
| latency_p95_ms | 54.415800 |
| citation_recoverability_avg | 1.000000 |
| recommended_decision | `repair_top_rank_retrieval_coverage` |

정성 판단:

- 청킹 재실험을 즉시 재개하지 않는다.
- doc-level coverage는 높지만 child/parent coverage가 낮아 generation에 직접 쓰기 좋은 근거가 부족하다.
- 다음 작업은 hard subset을 고정하고 deterministic rewrite v2 또는 parent/doc context boost를 비교하는 것이다.

## HD-PLACE-STORY-007 실행 결과

`place_story` hard subset 4개를 고정하고 baseline, deterministic rewrite v2, parent/doc context boost를 비교했다.

| strategy_id | child_or_parent@5 | child@5 | parent@5 | doc@5 | doc_only | full_miss | hard_case | MRR | nDCG@5 | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline_dense_e5_voice_rewrite` | 0.000000 | 0.000000 | 0.000000 | 0.750000 | 3 | 1 | 4 | 0.425000 | 0.288679 | 16.814800 |
| `place_story_rewrite_v2` | 0.000000 | 0.000000 | 0.000000 | 0.750000 | 3 | 1 | 4 | 0.550000 | 0.202381 | 18.885900 |
| `parent_doc_context_boost` | 0.250000 | 0.250000 | 0.250000 | 0.500000 | 1 | 2 | 3 | 0.208333 | 0.207605 | 15.864400 |

판단:

- `parent_doc_context_boost`는 hard subset에서 child/parent 직접 근거 coverage를 개선해 채택 후보로 둔다.
- `place_story_rewrite_v2`는 MRR은 올렸지만 child/parent coverage를 개선하지 못해 단독 후보로 채택하지 않는다.
- `parent_doc_context_boost`는 doc coverage, MRR, nDCG@5를 악화시켰으므로 production 기본값으로 즉시 고정하지 않는다.
- 다음 단계는 full `place_story` dev query에서 같은 후보를 재검증하고, generation 입력 품질에 미치는 영향을 확인하는 것이다.

## HD-PLACE-STORY-008 실행 결과

`parent_doc_context_boost`를 full `place_story` dev query 10개에서 baseline과 비교했다. 실행 device는 `cuda`다.

| strategy_id | child_or_parent@5 | input_ready | child@5 | parent@5 | doc@5 | doc_only | full_miss | hard_case | MRR | nDCG@5 | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline_dense_e5_voice_rewrite` | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.900000 | 3 | 1 | 4 | 0.770000 | 0.616818 | 10.233600 |
| `parent_doc_context_boost` | 0.700000 | 0.700000 | 0.700000 | 0.700000 | 0.800000 | 1 | 2 | 3 | 0.616667 | 0.544546 | 8.235900 |

Baseline delta:

| metric | delta |
| --- | ---: |
| child_or_parent@5 | 0.100000 |
| generation_input_ready_rate | 0.100000 |
| doc@5 | -0.100000 |
| doc_only_covered_count | -2 |
| full_grain_miss_count | 1 |
| hard_case_count | -1 |
| MRR | -0.153333 |
| nDCG@5 | -0.072272 |
| direct_evidence_improved_query_count | 1 |
| direct_evidence_regressed_query_count | 0 |

판단:

- `parent_doc_context_boost`는 full dev에서도 child/parent 직접 근거 coverage를 개선해 generation 입력 평가 후보로 승격한다.
- direct evidence regression은 0건이라 hard subset 한정 효과는 아니다.
- 그러나 MRR, nDCG@5, doc@5가 악화됐으므로 production 기본값 또는 최종 개선 주장으로 확정하지 않는다.
- 다음 단계는 Solar Pro 3 live 호출 전에 같은 query set에서 generation input-only 품질을 검토하는 것이다.

## HD-PLACE-STORY-009 실행 결과

`parent_doc_context_boost`를 full `place_story` dev query 10개에서 baseline과 비교하되, Solar Pro 3는 호출하지 않았다. dummy draft와 citation assembler만 사용해 generation 입력 evidence가 citation 평가에 어떤 영향을 주는지 확인했다. 실행 device는 `cuda`다.

| strategy_id | context_build | direct_ready | Correct-with-Evidence | citation_precision | citation_recall | citation_recoverability | evidence_order | avg_context_chars | input_latency_p95_ms | solar_calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline_dense_e5_voice_rewrite` | 1.000000 | 0.600000 | 0.900000 | 0.580000 | 0.481309 | 1.000000 | 0.770000 | 4317.000000 | 11.764400 | 0 |
| `parent_doc_context_boost` | 1.000000 | 0.700000 | 0.800000 | 0.550000 | 0.565953 | 1.000000 | 0.616667 | 4309.600000 | 8.362300 | 0 |

Baseline delta:

| metric | delta |
| --- | ---: |
| direct_ready | 0.100000 |
| Correct-with-Evidence | -0.100000 |
| citation_precision | -0.030000 |
| citation_recall | 0.084644 |
| evidence_order | -0.153333 |
| avg_context_chars | -7.400000 |
| input_latency_p95_ms | -3.402100 |

판단:

- `parent_doc_context_boost`는 direct evidence와 citation recall을 개선했다.
- 그러나 Correct-with-Evidence, citation precision, evidence order가 하락했다.
- Solar Pro 3 호출 수는 0이고 public-safe gate는 모두 0이다.
- 결론은 `keep_as_tradeoff_candidate`다. production 기본값 또는 live generation 개선 주장으로 확정하지 않는다.
- 다음 단계는 raw text를 공개하지 않는 방식으로 query별 input regression 원인을 분류한 뒤, v2 prompt repair 또는 reranking guardrail을 결정하는 것이다.

## HD-PLACE-STORY-010 실행 결과

HD-009의 trade-off를 query 단위로 분해했다. Solar Pro 3는 호출하지 않았고, 공개 리포트에는 raw query, raw evidence, prompt, answer text를 기록하지 않았다. 실행 device는 `cuda`다.

| metric | value |
| --- | ---: |
| query_count | 10 |
| direct_ready_gain_count | 1 |
| direct_ready_loss_count | 0 |
| correct_with_evidence_regression_count | 1 |
| citation_precision_regression_count | 3 |
| citation_recall_gain_count | 3 |
| evidence_order_regression_count | 3 |
| mixed_tradeoff_count | 1 |
| guardrail_required_count | 1 |
| input_latency_improved_count | 5 |
| solar_call_count | 0 |

Tag distribution:

| tag | count |
| --- | ---: |
| `citation_precision_regression` | 3 |
| `citation_recall_gain` | 3 |
| `citation_recall_regression` | 1 |
| `correctness_regression` | 1 |
| `direct_ready_gain` | 1 |
| `evidence_order_regression` | 3 |
| `guardrail_required` | 1 |
| `latency_improved` | 5 |
| `mixed_tradeoff` | 1 |
| `no_material_change` | 2 |

판단:

- candidate가 실제로 도움이 된 query는 존재한다. `direct_ready_gain_count=1`이다.
- 그러나 correctness regression 1건과 precision regression 3건이 있어 전체 기본값으로 승격할 수 없다.
- evidence order regression 3건은 parent/doc boost가 관련 근거를 찾더라도 generation에 넣는 순서를 흐릴 수 있음을 의미한다.
- 결론은 `require_guardrail_before_live_generation`이다.
- 다음 단계는 Solar Pro 3 live 호출이 아니라 `parent_doc_context_boost` 적용 조건을 제한하는 router 또는 reranking guardrail 계획이다.

## HD-PLACE-STORY-011 계획 결과

별도 문서 [Place Story Guardrail/Router Plan](PLACE_STORY_GUARDRAIL_ROUTER_PLAN.md)에 `parent_doc_context_boost` 적용 조건과 차단 조건을 고정했다.

핵심 결정:

- `parent_doc_context_boost`는 전체 기본값으로 채택하지 않는다.
- Router는 `place_story` query에만 적용한다.
- baseline과 candidate를 모두 계산한 뒤 guardrail 조건을 통과할 때만 candidate를 선택한다.
- `Correct-with-Evidence` proxy regression, precision/order regression, doc coverage loss가 있으면 baseline을 유지한다.
- 다음 실험은 `baseline`, `always_boost`, `guarded_boost` 3-way input-only 비교다.

## HD-PLACE-STORY-012 실행 결과

`baseline`, `always_boost`, `guarded_boost`를 full `place_story` dev query 10개에서 비교했다. Solar Pro 3는 호출하지 않았고, 실행 device는 `cuda`다.

| strategy_id | selected_candidate | blocked | direct_ready | Correct-with-Evidence | citation_precision | citation_recall | doc_coverage | evidence_order | duplicate_parent | latency_p95_ms | solar_calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline_dense_e5_voice_rewrite` | 0 | 0 | 0.600000 | 0.900000 | 0.580000 | 0.481309 | 0.900000 | 0.770000 | 0.140000 | 11.343300 | 0 |
| `parent_doc_context_boost_always` | 10 | 0 | 0.700000 | 0.800000 | 0.550000 | 0.565953 | 0.800000 | 0.616667 | 0.145000 | 7.980800 | 0 |
| `parent_doc_context_boost_guarded` | 1 | 9 | 0.600000 | 0.900000 | 0.580000 | 0.509881 | 0.900000 | 0.770000 | 0.140000 | 11.343300 | 0 |

정량 판단:

- `always_boost`는 citation recall을 올렸지만 correctness, precision, doc coverage, evidence order를 악화시켰다.
- `guarded_boost`는 baseline의 safety metric을 유지하면서 citation recall만 `+0.028572` 개선했다.
- public-safe gate는 raw text/private path/secret leakage 모두 0이다.

정성 판단:

- guardrail은 candidate를 대부분 차단했지만, candidate가 안전하게 이득을 주는 query 1건은 선택했다.
- `manual_review_required`가 2건 있으므로 즉시 live generation 기본값으로 확정하지 않는다.
- 다음 단계는 Solar Pro 3 live paired comparison 실행이 아니라 그 계획과 승인 gate를 먼저 작성하는 것이다.

## HD-SOLAR-013 계획 결과

`parent_doc_context_boost_guarded` 기반 Solar Pro 3 live paired comparison 계획을 작성했다.

| 항목 | 값 |
| --- | --- |
| 계획 문서 | [Solar Pro 3 Guarded Boost Live Comparison Plan](SOLAR_GUARDED_BOOST_LIVE_COMPARISON_PLAN.md) |
| query scope | private `place_story` dev 10개 |
| baseline strategy | `baseline_dense_e5_voice_rewrite` |
| candidate strategy | `parent_doc_context_boost_guarded` |
| router policy | `place_story_guarded_boost_v1` |
| expected live call count | 11 |
| live call hard cap | 20 |
| duplicate policy | identical input fingerprint 재사용 |
| live call executed | 0 |

판단:

- 청킹 비교 테스트는 계속 보류한다.
- live 품질 개선을 주장하지 않는다.
- 다음 단계는 live 호출이 아니라 dry-run runner로 input fingerprint와 예상 call count를 검증하는 것이다.

## HD-SOLAR-014 실행 결과

Solar Pro 3 guarded boost live comparison dry-run runner를 실행했다. Solar Pro 3 실제 호출은 수행하지 않았다.

| metric | value |
| --- | ---: |
| query_count | 10 |
| baseline_live_call_count | 10 |
| candidate_live_call_count | 1 |
| expected_total_live_call_count | 11 |
| live_call_hard_cap | 20 |
| reused_candidate_count | 9 |
| changed_candidate_input_count | 1 |
| solar_call_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

판단:

- live call budget은 계획 범위 안이다.
- guarded input이 baseline과 달라지는 query는 1건이다.
- 다음 단계는 live call 실행이 아니라 live paired comparison runner 구현과 실행 전 재승인이다.

## HD-SOLAR-015 실행 결과

Solar Pro 3 guarded boost live paired comparison readiness runner를 구현했다. 기본 실행은 dry-run 재검증과 call cap 확인만 수행하며, 실제 Solar Pro 3 호출은 차단한다. 실행 device는 `cuda`다.

| metric | value |
| --- | ---: |
| readiness_decision | `ready_for_live_execution_approval` |
| expected_total_live_call_count | 11 |
| candidate_live_call_count | 1 |
| reused_candidate_count | 9 |
| live_call_hard_cap | 20 |
| dry_run_gate_passed | True |
| call_cap_passed | True |
| public_safety_passed | True |
| live_call_executed | False |
| solar_call_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

판단:

- 청킹 비교 테스트는 계속 보류한다.
- `guarded_boost`는 live 실행 준비성 gate까지 통과했지만 live 답변 품질은 아직 검증하지 않았다.
- 다음 단계는 HD-SOLAR-016 live paired comparison 실행 승인 여부 결정이다.

## HD-SOLAR-016 실행 결과

Solar Pro 3 guarded boost live paired comparison을 private `place_story` dev 10개에서 실행했다.

| metric | baseline | guarded candidate | delta |
| --- | ---: | ---: | ---: |
| Correct-with-Evidence | 0.900000 | 0.900000 | 0.000000 |
| citation_precision | 0.580000 | 0.580000 | 0.000000 |
| citation_recall | 0.481309 | 0.509881 | 0.028572 |
| unsupported_claim_rate | 0.100000 | 0.100000 | 0.000000 |
| latency_p95_ms | 5066.690100 | 5455.679600 | 388.989500 |

| gate | value |
| --- | ---: |
| actual_solar_call_count | 11 |
| live_call_hard_cap | 20 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

판단:

- 청킹 비교 테스트는 계속 보류한다.
- 현재 이득은 청킹 변경이 아니라 guarded router가 안전한 candidate 1건만 통과시킨 결과다.
- `adoption_decision=promote_guarded_candidate_for_next_gate`지만, dev 10건 결과라 최종 개선 주장으로 쓰지 않는다.
- 다음 단계는 next gate 판단 문서화와 추가 검증 범위 결정이다.

## 정량 Gate

최소 기록 metric:

- `target_child_recall@1/3/5`
- `target_parent_recall@1/3/5`
- `target_doc_recall@1/3/5`
- `MRR`
- `nDCG@5`
- `latency_p95_ms`
- `citation_recoverability`
- `duplicate_parent_rate`
- `public_raw_text_leakage_count`
- `private_path_leakage_count`
- `secret_like_leakage_count`

개선 주장 gate:

- 같은 private dev split, 같은 query set, 같은 chunk corpus에서 paired comparison을 수행한다.
- locked test split은 후보 선택 후 1회만 사용한다.
- child 또는 parent `Recall@5`가 개선되어야 한다.
- doc-only 개선은 최종 개선 주장으로 쓰지 않는다.
- latency/cost 악화가 있으면 포트폴리오 문서에 trade-off로 명시한다.

## 정성 Gate

각 hard-case는 다음을 수기로 분류한다.

- `target_too_narrow`: target child가 서사형 질문에 과도하게 좁음
- `retrieval_semantic_miss`: 같은 장소/사건 표현을 semantic retriever가 놓침
- `lexical_alias_miss`: 별칭, 지시어, 음성형 표현 때문에 놓침
- `evidence_rank_too_low`: 관련 근거가 있지만 rank가 낮음
- `packing_order_bad`: 검색은 됐지만 answer context 앞쪽에 배치되지 않음

정성 판단에는 raw text를 public 문서에 기록하지 않는다. public에는 label과 aggregate count만 남긴다.

## 분석용 Grain 설계

`fact_place_story_coverage`의 grain은 query-run-strategy 단위다.

| 필드 | 설명 |
| --- | --- |
| `run_id` | 실험 실행 id |
| `query_id` | 평가 query id |
| `strategy_id` | retrieval 또는 packing 전략 |
| `query_type` | `place_story` |
| `target_child_covered` | child hit 여부 |
| `target_parent_covered` | parent hit 여부 |
| `target_doc_covered` | doc hit 여부 |
| `target_child_min_rank` | child 최소 rank |
| `target_parent_min_rank` | parent 최소 rank |
| `target_doc_min_rank` | doc 최소 rank |
| `latency_ms` | query 단위 latency |
| `failure_tag` | hard-case 정성 label |

dimension 후보:

- `dim_retrieval_strategy`
- `dim_query_type`
- `dim_target_grain`
- `dim_eval_split`
- `dim_run`

## Non-goal

- 이번 단계에서 전체 청킹 ablation을 다시 실행하지 않는다.
- 이번 단계에서 Solar Pro 3 live call을 추가하지 않는다.
- 이번 단계에서 v2 contract를 기본값으로 채택하지 않는다.
- 이번 단계에서 GraphRAG/RAPTOR-lite를 시작하지 않는다.
- raw query, raw answer, raw evidence text를 public artifact에 기록하지 않는다.

## 다음 작업 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-PLACE-STORY-006 | `PLACE_STORY_HARD_CASE_ANALYSIS` | `place_story` 전체 dev query의 child/parent/doc coverage diagnostic runner 구현 | 완료. pytest 통과, public-safe report 생성, leakage count 0 | Medium | runner와 report만 revert |
| HD-PLACE-STORY-007 | HD-PLACE-STORY-006 | hard subset 기준 rewrite/boost 후보 비교 | 완료. paired comparison report 생성, latency 기록, leakage count 0 | Medium | strategy flag 비활성화 |
| HD-PLACE-STORY-008 | HD-PLACE-STORY-007 | `parent_doc_context_boost` full `place_story` dev 재검증 및 generation 입력 영향 분석 | 완료. full place_story report 생성, target grain metric 기록, leakage count 0 | Medium | 후보 strategy 비활성화 |
| HD-PLACE-STORY-009 | HD-PLACE-STORY-008 | `parent_doc_context_boost` 적용 후 Solar Pro 3 호출 전 generation input-only 평가 | 완료. input-only report 생성, Solar call 0, leakage count 0 | Medium | report/runner revert |
| HD-PLACE-STORY-010 | HD-PLACE-STORY-009 | `parent_doc_context_boost` query별 input regression 원인 점검 | 완료. regression tag report 생성, Solar call 0, leakage count 0 | Medium | report/runner revert |
| HD-PLACE-STORY-011 | HD-PLACE-STORY-010 | `parent_doc_context_boost` 적용 조건 제한 guardrail/router 계획 | 완료. 적용 조건, 차단 조건, 3-way 비교 설계 문서화 | Low | 문서 revert |
| HD-PLACE-STORY-012 | HD-PLACE-STORY-011 | guarded boost 3-way 비교 runner 구현 | 완료. baseline/always/guarded report 생성, Solar call 0, leakage count 0 | Medium | runner/report revert |
| HD-SOLAR-013 | HD-PLACE-STORY-012 | `parent_doc_context_boost_guarded` 기반 Solar Pro 3 live paired comparison 계획 | 완료. live call 전 query set, cost, pass/fail gate 문서화 | Medium | 문서 revert |
| HD-SOLAR-014 | HD-SOLAR-013 | Solar Pro 3 guarded boost live comparison dry-run runner | 완료. input fingerprint, 예상 call count, public-safe dry-run report | High | runner/report revert |
| HD-SOLAR-015 | HD-SOLAR-014 | Solar Pro 3 guarded boost live paired comparison runner | 완료. readiness mode, dry-run 재검증, call cap 확인, Solar call 0 | High | runner/report revert |
| HD-SOLAR-016 | HD-SOLAR-015 승인 | Solar Pro 3 guarded boost live paired comparison 실행 | 완료. actual Solar call 11, public leakage 0, paired metric report | High | candidate 미채택, public report revert |
| HD-SOLAR-017 | HD-SOLAR-016 | guarded boost next gate 판단 문서화 | 완료. next gate 승격, production 채택 보류, 청킹 재개 보류 | Low | 문서 revert |
| HD-SOLAR-018 | HD-SOLAR-017 | guarded boost 추가 dev hard-case 검증 계획 | 완료. route decision bucket, gate, data mart grain 문서화 | Low | 문서 revert |
| HD-SOLAR-019 | HD-SOLAR-018 | guarded boost hard-case validation runner 구현 | 완료. bucket coverage 10/10, route mismatch 0, Solar call 0 | Medium | runner/report revert |
| HD-SOLAR-020 | HD-SOLAR-019 | guarded boost router threshold 유지/수정 판단 | 완료. threshold 유지, 완화/강화 기각, locked test 전 claim boundary 유지 | Low | 문서 revert |
| HD-SOLAR-021 | HD-SOLAR-020 | guarded boost locked test 실행 전 승인 계획 | 완료. locked test 즉시 실행 보류, readiness dry-run 우선, future live call 별도 승인 | Medium | 문서 revert |
| HD-SOLAR-022 | HD-SOLAR-021 | guarded boost locked test readiness dry-run runner | 완료. locked place_story 5건에서 candidate live call 0, Solar call 0, readiness gate PASS | Medium | runner/report revert |
| HD-SOLAR-023 | HD-SOLAR-022 | guarded boost locked readiness 결과 기반 next gate 판단 | 완료. 청킹 재개 보류, locked live 보류, production 채택 기각 | Medium | 문서 revert |

## 결정

다음 결정 우선순위는 `HD-SOLAR-024` Solar Pro 3 generation v2 prompt repair 계획 작성이다.

청킹 비교 테스트는 계속 보류한다. `guarded_boost`는 input-only 기준, dry-run call budget gate, readiness gate, dev-only live comparison을 통과했다. 다만 locked test와 bootstrap confidence interval 전에는 최종 성능 개선 주장으로 쓰지 않는다.
