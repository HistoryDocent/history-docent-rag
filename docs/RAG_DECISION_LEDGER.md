# RAG Decision Ledger

## 결론

청킹 비교 테스트는 지금 다시 열지 않는다.

현재 기준선은 `C0 current parent-child`로 고정한다. 실패 사례 10개 중 `place_story` 1건은 targeted chunk audit으로 확인했고, target child/parent가 chunk artifact에 존재해 전역 재청킹 근거가 아니라고 판단했다. HyDE subset readiness, live paired retrieval comparison, larger dev subset readiness, larger live paired retrieval comparison도 완료됐다. HyDE는 40개 확대 live 비교에서 Recall@5는 소폭 상승했지만 MRR, nDCG@5, latency가 악화되어 기본 retrieval route로 채택하지 않는다. active routing은 바로 적용하지 않는다. `relationship_hybrid_weighted_e5_v1`는 dev shadow에서는 좋아 보였지만 locked paired comparison에서 MRR delta=-0.100000, nDCG@5 delta=-0.073814라 개선 주장을 보류한다.

ColBERT-style late interaction은 dev hard subset에서 top50 MRR만 소폭 상승했지만 nDCG@5와 latency가 악화되어 기본 route로 채택하지 않는다. 이후 voice UI MVP 계획, frontend skeleton, frontend/backend contract smoke, real browser visual QA, portfolio demo runbook, public repository audit refresh, portfolio submission rehearsal을 완료했다. 다만 STT/TTS 품질 검증, live Solar Pro 3 voice demo, production 배포는 아직 수행하지 않았다.

이 문서는 public-safe 의사결정 장부다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | 청킹은 C0로 고정하고 retrieval, packing, generation, router 판단을 이어간다. |
| Retrieval | 전체 기본 후보는 `dense_multilingual_e5_small_voice_rewrite`가 가장 설득력 있다. |
| Generation | Solar Pro 3 v2 repaired는 citation recall 저하 때문에 기본값으로 채택하지 않는다. |
| Evaluation | locked test를 실행했지만 relationship hybrid 개선 주장은 통과하지 못했다. 최종 개선 표현은 여전히 금지한다. |
| Data warehouse | fact grain은 `decision_id + stage_id + candidate_id + metric_family + claim_boundary`로 둔다. |
| Security | public report에는 식별자와 집계 metric만 남긴다. 원문 계열 필드는 금지한다. |
| Portfolio | “많은 기법을 붙였다”보다 “실험으로 기각할 것은 기각했다”를 핵심 메시지로 둔다. |
| 외부 감사 | 지금 청킹을 다시 열면 이후 실험 전체가 비교 불가능해진다. 실패 query 기반 audit만 허용한다. |

## 현재 채택 기준선

| layer | current decision | 근거 |
| --- | --- | --- |
| source normalization | 유지 | parser quality와 normalized block gate 통과 |
| chunking | `C0 current parent-child` 유지 | C1-C6가 selection gate와 개선 조건을 동시에 충족하지 못함 |
| base retrieval | `dense_multilingual_e5_small_voice_rewrite` 후보 유지 | dev 70개 기준 Recall@5, MRR, nDCG@5가 non-rerank 후보 중 가장 강함 |
| relationship retrieval option | `hybrid_weighted_e5_small_alpha_0_5`는 shadow 후보로 보류 | dev shadow에서는 좋았지만 locked relationship 5개에서 MRR/nDCG가 하락 |
| reranker | 기본값 보류 | 품질은 최고지만 CPU p95 latency가 실서비스 기본값으로 부적합 |
| late interaction | 기본값 기각 | ColBERT-style top50은 MRR만 상승했고 nDCG@5와 latency가 악화됨 |
| evidence packing | `P0_rank_order` 유지 | P3 개선폭이 작고 generation 품질 개선으로 아직 연결되지 않음 |
| generation policy | v1 baseline 유지 | repaired v2는 precision 개선에도 citation recall 하락 |
| place_story boost | guarded router 후보 유지 | live-dev-subset에서 citation recall은 소폭 개선, 최종 채택은 locked gate 전 보류 |
| GraphRAG-lite | 기본값 기각 | relationship input-only에서 nDCG@5 개선 없음 |
| RAPTOR-lite | 기본값 기각 | overview/place_story input-only에서 Recall/MRR 개선 없음, nDCG@5 하락 |

## Decision Ledger

| stage_id | candidate_id | split/scope | key_metric | decision | claim_boundary | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `chunking` | `C0 current parent-child` | dev 70, BM25 fixed | Recall@5=0.566667, MRR=0.471389, nDCG@5=0.344203 | adopt | dev-only | `evals/reports/chunking_ablation_v2_report.md` |
| `chunking` | `C1 smaller child` | dev 70, BM25 fixed | Recall@5=0.083333 | reject | dev-only | same report |
| `chunking` | `C2 larger child` | dev 70, BM25 fixed | Recall@5=0.533333 | reject | dev-only | same report |
| `chunking` | `C3 micro-parent merge` | dev 70, BM25 fixed | Recall@5=0.533333 | reject | dev-only | same report |
| `chunking` | `C4 overlap 0` | dev 70, BM25 fixed | gate=FAIL | reject | dev-only | same report |
| `chunking` | `C5 overlap 2` | dev 70, BM25 fixed | Recall@5=0.533333 | reject | dev-only | same report |
| `chunking` | `C6 fixed-size block baseline` | dev 70, BM25 fixed | gate=FAIL | reject | dev-only | same report |
| `embedding` | `dense_bge_m3` | dev 70 | Recall@5=0.800000, nDCG@5=0.567476, p95=57.088400ms | candidate_quality_ceiling | dev-only | `evals/reports/neural_embedding_retrieval_comparison_report.md` |
| `embedding` | `dense_multilingual_e5_small` | dev 70 | Recall@5=0.733333, MRR=0.675556, p95=15.717100ms | adopt_base_candidate | dev-only | same report |
| `hybrid` | `hybrid_weighted_e5_small_alpha_0_5` | dev 70 | Recall@5=0.783333, MRR=0.655278, p95=27.547000ms | route_candidate | dev-only | `evals/reports/neural_dense_hybrid_retrieval_comparison_report.md` |
| `reranker` | `dense_multilingual_e5_small_rerank_bge_m3_top20` | dev 70 | Recall@5=0.833333, MRR=0.761667, p95=13140.690300ms | reject_default_keep_quality_ceiling | dev-only | `evals/reports/reranker_retrieval_comparison_report.md` |
| `query_rewrite` | `dense_multilingual_e5_small_voice_rewrite` | dev 70 | Recall@5=0.850000, MRR=0.758056, nDCG@5=0.615293 | adopt_retrieval_candidate | dev-only | `evals/reports/query_rewrite_retrieval_comparison_report.md` |
| `evidence_packing` | `P0_rank_order` | dev 70, fixed retrieval | target_child_covered=0.850000, citation_recoverability=1.000000 | adopt | dev-input-only | `evals/reports/evidence_packing_comparison_report.md` |
| `evidence_packing` | `P3_mmr_diversity` | dev 70, fixed retrieval | duplicate_parent_delta=-0.003571 | reject_default_keep_candidate | dev-input-only | same report |
| `generation` | `solar-generation-v2-repaired` | live dev subset 7 | citation_precision delta=+0.216666, citation_recall delta=-0.027778 | reject_default | live-dev-subset | `evals/reports/solar_generation_v2_repaired_live_comparison_report.md` |
| `place_story_router` | `parent_doc_context_boost_guarded` | live dev subset 10 | citation_recall delta=+0.028571, Correct delta=0.000000 | keep_router_candidate | live-dev-subset | `evals/reports/solar_guarded_boost_live_comparison_report.md` |
| `query_type_router` | `query_type_router_v1` | `HD-ROUTER-001`, dev 70, relationship dev 10, place_story locked readiness 5 | relationship route Recall@5=1.000000, place_story locked selected_candidate_count=0 | adopt_relationship_route_candidate | mixed-boundary | `evals/reports/query_type_router_decision_report.md` |
| `query_type_router_skeleton` | `query_type_router_v1` | deterministic branch contract | query_type_count=7, route_policy_count=3, live_solar_call_count=0 | implemented | contract-only | `evals/reports/query_type_router_skeleton_report.md` |
| `query_type_classifier` | `deterministic_query_type_classifier_v1` | dev 70 | accuracy=0.957143, macro_f1=0.956818, route_policy_accuracy=0.971429 | implemented_baseline | dev-only | `evals/reports/query_type_classifier_eval_report.md` |
| `query_type_classifier_failure_analysis` | `deterministic_query_type_classifier_v1` | dev 70 failures | failure_count=3, route_risk_failure_count=2, false_hybrid_route_count=2 | analyzed | dev-only | `evals/reports/query_type_classifier_failure_analysis_report.md` |
| `chat_classifier_router_dry_run` | `chat-classifier-router-dry-run-v1` | API contract + fixture retrieval | classifier_dry_run_count=6, classifier_active_route_applied_count=0 | implemented_dry_run | contract-only | `evals/reports/chat_api_contract_report.md`, `evals/reports/chat_retrieval_integration_report.md` |
| `relationship_route_guard` | `relationship-route-guard-v1` | dev 70 | false_hybrid_route_count 2 -> 0, route_policy_accuracy 0.971429 -> 1.000000 | implemented_guard | dev-only | `evals/reports/relationship_route_guard_eval_report.md` |
| `chat_guarded_route_dry_run` | `guarded_route_candidate` | API contract + fixture retrieval | guarded_route_candidate_count=6, guard_applied_count=1, active_route_applied_count=0 | implemented_dry_run | contract-only | `evals/reports/chat_api_contract_report.md`, `evals/reports/chat_retrieval_integration_report.md` |
| `portfolio_summary` | `HD-PORTFOLIO-001` | public README/docs summary | summarized_stage_count=28, leakage_count=0 | implemented | public-safe-summary | `evals/reports/portfolio_result_summary_report.md` |
| `portfolio_failure_analysis` | `HD-PORTFOLIO-002` | public-safe failure cases | case_count=10, chunk_boundary_audit_candidate_count=1, reopen_global_chunking_count=0 | implemented | public-safe-summary | `evals/reports/portfolio_failure_analysis_report.md` |
| `place_story_targeted_chunk_audit` | `HD-CHUNK-AUDIT-001` | dev-only single failure case | target_child_exists_rate=1.000000, chunk_boundary_defect_count=0, reopen_global_chunking_count=0 | do_not_reopen_global_chunking | dev-only | `evals/reports/place_story_targeted_chunk_audit_report.md` |
| `hyde_subset_readiness` | `HD-HYDE-001A` | dev-readiness-only, 5 queries | expected_hyde_generation_live_call_count=4, no_answer_guard_query_count=1, solar_call_count=0 | ready_for_hyde_live_approval | dev-readiness-only | `evals/reports/hyde_subset_readiness_report.md` |
| `hyde_live_paired_retrieval` | `HD-HYDE-001B` | live-dev-subset, 5 queries | Recall@5 delta=0.250000, MRR delta=-0.062500, nDCG@5 delta=0.015402, solar_api_call_count=4 | keep_hyde_candidate_for_larger_eval | live-dev-subset | `evals/reports/hyde_live_paired_retrieval_comparison_report.md` |
| `hyde_larger_dev_readiness` | `HD-HYDE-001C` | dev-readiness-only, 40 queries | expected_hyde_generation_live_call_count=30, no_answer_guard_query_count=10, solar_call_count=0 | ready_for_hyde_larger_live_approval | larger-dev-readiness-only | `evals/reports/hyde_larger_dev_subset_readiness_report.md` |
| `hyde_larger_live_paired_retrieval` | `HD-HYDE-001D` | live-dev-subset, 40 queries | Recall@5 delta=0.033333, MRR delta=-0.035000, nDCG@5 delta=-0.018384, solar_api_call_count=30 | reject_hyde_for_now | larger-live-dev-only | `evals/reports/hyde_larger_live_paired_retrieval_comparison_report.md` |
| `active_routing_decision` | `HD-API-ROUTER-003` | plan-only, public-safe aggregate reports | active_route_applied_count=0, planned_shadow_candidate_count=1, live_solar_call_count=0 | defer_active_route_shadow_next | plan-only | `evals/reports/active_routing_decision_plan_report.md` |
| `active_route_shadow_evaluation` | `HD-API-ROUTER-004` | dev 70, paired route shadow | MRR delta=0.013888, relationship Recall@5 delta=0.200000, false_hybrid_route_count=0, no_answer_candidate_route_count=0 | ready_for_active_route_dry_run_contract | dev-shadow-only | `evals/reports/active_route_shadow_evaluation_report.md` |
| `active_route_flag_dry_run_contract` | `HD-API-ROUTER-005` | API contract + fixture retrieval | active_route_flag_enabled_count=1, active_route_flag_applied_count=0, live_solar_call_count=0 | implemented_dry_run_contract | contract-only | `docs/ACTIVE_ROUTE_FLAG_DRY_RUN_CONTRACT.md`, `evals/reports/chat_api_contract_report.md`, `evals/reports/chat_retrieval_integration_report.md` |
| `locked_retrieval_validation_plan` | `HD-LOCKED-RETRIEVAL-001` | plan-only | planned_locked_query_count=35, locked_test_execution_count=0, solar_call_count=0 | ready_for_locked_retrieval_readiness_dry_run | plan-only | `docs/LOCKED_RETRIEVAL_VALIDATION_PLAN.md`, `evals/reports/locked_retrieval_validation_plan_report.md` |
| `locked_retrieval_readiness` | `HD-LOCKED-RETRIEVAL-002` | readiness-only | target_resolvability_fail_count=0, no_answer_candidate_route_count=0, retrieval_execution_count=0, resolved_device=cuda | ready_for_locked_execution_approval | readiness-only | `docs/LOCKED_RETRIEVAL_READINESS.md`, `evals/reports/locked_retrieval_readiness_report.md` |
| `locked_retrieval_execution_approval` | `HD-LOCKED-RETRIEVAL-003` | approval-only | planned_bootstrap_iteration_count=10000, confidence_interval_percent=95, retrieval_execution_count=0, solar_call_count=0 | ready_for_user_execution_approval | approval-only | `docs/LOCKED_RETRIEVAL_EXECUTION_APPROVAL.md`, `evals/reports/locked_retrieval_execution_approval_report.md` |
| `locked_retrieval_paired_comparison` | `HD-LOCKED-RETRIEVAL-004` | locked test 35, relationship paired 5 | MRR delta=-0.100000, nDCG@5 delta=-0.073814, 95% CI=[-0.300000, 0.000000] | keep_shadow_without_locked_improvement_claim | locked-retrieval-only | `docs/LOCKED_RETRIEVAL_PAIRED_COMPARISON.md`, `evals/reports/locked_retrieval_paired_comparison_report.md` |
| `colbert_late_interaction_plan` | `HD-COLBERT-001A` | plan-only | retrieval_execution_count=0, locked_test_execution_count=0, solar_call_count=0 | ready_for_dev_hard_subset_approval | plan-only | `docs/COLBERT_LATE_INTERACTION_PLAN.md`, `evals/reports/colbert_late_interaction_plan_report.md` |
| `colbert_late_interaction_execution_approval` | `HD-COLBERT-001B` | approval-only | actual_retrieval_execution_count=0, locked_test_execution_count=0, solar_call_count=0 | ready_for_dev_hard_subset_execution | approval-only | `docs/COLBERT_LATE_INTERACTION_EXECUTION_APPROVAL.md`, `evals/reports/colbert_late_interaction_execution_approval_report.md` |
| `colbert_late_interaction_hard_subset` | `colbert_style_late_interaction_top20_cuda` | dev hard subset 21 | Recall@5 delta=-0.047619, MRR delta=-0.037302, nDCG@5 delta=-0.060589, p95=117.263100ms | reject_default | dev-hard-subset-only | `docs/COLBERT_LATE_INTERACTION_HARD_SUBSET.md`, `evals/reports/colbert_late_interaction_hard_subset_report.md` |
| `colbert_late_interaction_hard_subset` | `colbert_style_late_interaction_top50_cuda` | dev hard subset 21 | Recall@5 delta=0.000000, MRR delta=+0.022222, nDCG@5 delta=-0.021670, p95=164.956000ms | reject_default_keep_as_experiment_result | dev-hard-subset-only | `docs/COLBERT_LATE_INTERACTION_HARD_SUBSET.md`, `evals/reports/colbert_late_interaction_hard_subset_report.md` |
| `voice_ui_mvp_plan` | `HD-VOICE-UI-001` | plan-only | planned_user_journey_count=3, required_api_field_mapping_count=12, frontend_implementation_count=0, live_solar_call_count=0 | ready_for_frontend_skeleton | plan-only | `docs/VOICE_UI_MVP_PLAN.md`, `docs/VOICE_UI_API_CONTRACT.md`, `evals/reports/voice_ui_mvp_plan_report.md` |
| `voice_ui_skeleton` | `HD-VOICE-UI-002` | frontend fixture UI | ui_state_test_count=5, implemented_frontend_package_count=1, backend_endpoint_added_count=0, live_solar_call_count=0 | ready_for_contract_smoke | frontend-fixture-only | `docs/VOICE_UI_SKELETON.md`, `evals/reports/voice_ui_skeleton_report.md` |
| `voice_ui_contract_smoke` | `HD-VOICE-UI-003` | frontend/backend contract | frontend_backend_mode_unit_test_count=4, backend_contract_smoke_request_count=2, live_solar_call_count=0, retrieval_execution_count=0 | ready_for_visual_qa | local-contract-only | `docs/VOICE_UI_CONTRACT_SMOKE.md`, `evals/reports/voice_ui_contract_smoke_report.md` |
| `voice_ui_visual_qa` | `HD-VOICE-UI-004` | browser local fixture UI | visual_qa_scenario_count=3, screenshot_artifact_count=3, live_solar_call_count=0, retrieval_execution_count=0 | visual_qa_completed | browser-local-fixture-only | `docs/VOICE_UI_VISUAL_QA.md`, `evals/reports/voice_ui_visual_qa_report.md` |
| `portfolio_demo_runbook` | `HD-PORTFOLIO-DEMO-001` | public-safe local demo | demo_step_count=6, runbook_command_block_count=8, private_corpus_required_count=0 | demo_path_documented | public-safe-demo-only | `docs/PORTFOLIO_DEMO_RUNBOOK.md`, `evals/reports/portfolio_demo_runbook_report.md` |
| `submission_refresh_audit` | `HD-SUBMISSION-REFRESH-001` | public repository audit | required_readme_link_count=2, required_demo_artifact_count=3, public_secret_like_leakage_count=0 | submission_refresh_passed | public-safe-summary | `docs/SUBMISSION_REFRESH_AUDIT.md`, `evals/reports/submission_refresh_audit_report.md` |
| `portfolio_rehearsal` | `HD-PORTFOLIO-REHEARSAL-001` | submission explanation | interview_answer_count=12, rejected_candidate_explained_count=8, forbidden_claim_count=8 | required_portfolio_gates_completed | public-safe-summary | `docs/PORTFOLIO_REHEARSAL.md`, `evals/reports/portfolio_rehearsal_report.md` |
| `graphrag_lite` | `graphrag_lite_entity_path_v1` | relationship dev 10 | Recall@5 delta=0.000000, nDCG@5 delta=-0.002056 | reject_default | dev-input-only | `evals/reports/graphrag_lite_relationship_input_only_report.md` |
| `graphrag_lite` | `graphrag_lite_community_hint_v1` | relationship dev 10 | Recall@5 delta=0.000000, nDCG@5 delta=-0.030337 | reject_default | dev-input-only | same report |
| `raptor_lite` | `raptor_lite_parent_summary_v1` | overview/place_story dev 20 | Recall@5 delta=0.000000, nDCG@5 delta=-0.074957 | reject_default | dev-input-only | `evals/reports/raptor_lite_input_only_report.md` |
| `raptor_lite` | `raptor_lite_summary_node_v1` | overview/place_story dev 20 | Recall@5 delta=0.000000, nDCG@5 delta=-0.029969 | reject_default | dev-input-only | same report |

## 청킹 재비교 판단

지금은 청킹 재비교를 하지 않는다.

근거:

- C0-C6 비교가 이미 있고 C0가 selection gate를 통과했다.
- C1은 Recall@5가 0.083333으로 크게 낮았다.
- C2/C3/C5는 C0를 넘지 못했다.
- C4/C6은 chunking gate 자체가 실패했다.
- 청킹을 바꾸면 retrieval, evidence packing, generation, GraphRAG-lite 결과를 모두 재실행해야 한다.

허용되는 예외:

- 특정 failure query가 source block boundary 손실로 실패했다는 evidence가 있을 때만 targeted chunk audit을 연다.
- audit은 새 기본 청킹 후보가 아니라 failure analysis artifact로 둔다.

## 다음 작업 우선순위

| priority | work_id | 작업 | 이유 | 승인 필요 |
| ---: | --- | --- | --- | --- |
| 1 | `HD-VOICE-STT-TTS-PLAN-001` | optional voice STT/TTS planning | 필수 포트폴리오 제출 gate는 완료됐다. 후속 제품 개발을 이어갈 경우 실제 음성 입출력 범위, 비용, 개인정보 처리를 별도 계획으로 분리해야 한다. | 예 |

## Data Mart 설계

`fact_rag_decision_ledger`의 grain은 `decision_id + stage_id + candidate_id + metric_family + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `decision_id` | stable decision id |
| `stage_id` | chunking, embedding, hybrid, reranker, query_rewrite, packing, generation, router, graphrag_lite, raptor_lite |
| `candidate_id` | method, policy, router, prompt 후보 id |
| `split_scope` | seed, dev, live-dev-subset, locked-test 등 |
| `metric_family` | retrieval, latency, citation, safety, generation, cost |
| `primary_metric_value` | 대표 metric 값 |
| `decision` | adopt, reject, route_candidate, keep_router_candidate 등 |
| `claim_boundary` | dev-only, dev-input-only, live-dev-subset, locked-only |
| `evidence_artifact` | public-safe report path |

금지 필드:

- raw query
- raw answer
- raw evidence
- prompt
- chunk text
- private file path
- secret

## 포트폴리오 메시지

이 프로젝트의 강점은 최신 RAG 기법을 모두 붙인 것이 아니다.

강점은 다음이다.

- 도서 parser output에서 citation 가능한 RAG corpus를 재구성했다.
- 청킹, retrieval, reranker, query rewrite, evidence packing, generation을 분리해서 비교했다.
- 좋은 수치만 골라 채택하지 않고 latency, citation recall, unsupported claim risk 때문에 후보를 기각했다.
- GraphRAG-lite도 relationship 질문에 한정해 검증했고 개선이 없어 기본값에서 제외했다.
- RAPTOR-lite도 overview/place_story 질문에 한정해 검증했고 개선이 없어 기본값에서 제외했다.
- 실패 사례 10개를 원문 없이 분류했고 `place_story` 1건 targeted audit으로 전역 청킹 재실험을 열지 않는 근거를 확인했다.
- HyDE live 비교 전 subset, call budget, no-answer guard를 public-safe readiness gate로 고정했고, 40개 확대 live 비교에서는 기본 route 채택을 기각했다.
- active route shadow evaluation에서 relationship route 후보를 dev 70 paired metric으로 검증했고 active route는 여전히 적용하지 않았다.
- locked retrieval readiness에서 target resolvability와 route/candidate count를 확인했다.
- locked retrieval execution approval에서 bootstrap, confidence interval, stop condition, data mart grain을 실행 전 고정했다.
- locked retrieval paired comparison에서 relationship hybrid가 MRR/nDCG 개선을 입증하지 못해 active route 개선 주장을 보류했다.
- ColBERT-style execution approval gate에서 dev hard subset 실행 전 scope, CUDA, locked/Solar 금지 조건을 고정했다.
- ColBERT-style hard subset 비교에서 기본 route 채택을 기각했고, 결과를 dev-only 실험으로 보관했다.
- voice UI MVP plan에서 `/api/v1/chat`의 spoken answer, detailed answer, citation, abstain, unsupported claim risk 표시 단위를 매핑했다.
- voice UI skeleton에서 contract fixture 기반 관광 도슨트 화면, no-answer state, citation drawer, voice fallback control을 구현했다.
- voice UI contract smoke에서 frontend backend mode와 FastAPI contract-only answerable/no-answer 연결을 검증했다.
- voice UI visual QA에서 실제 browser desktop/mobile/error 상태와 screenshot artifact를 검증했다.
- portfolio demo runbook에서 backend/frontend local demo 순서와 금지 claim을 고정했다.
- public repository audit refresh에서 README 링크, screenshot artifact, 금지 claim, public-safe scan을 재검증했다.
- portfolio submission rehearsal에서 30초 요약, 3분 설명, 면접 답변, 기각 후보 설명, 금지 claim 회피를 고정했다.
- public repo에는 저작권 원문과 private eval payload를 올리지 않고 집계 metric만 공개했다.

## 최종 감사 의견

현재 흐름은 취업 포트폴리오 관점에서 타당하다.

README 결과 표와 포트폴리오 메시지 정리는 완료했다. query type classifier baseline, 오분류 failure analysis, `/chat` dry-run field 연결, relationship guard 평가, guarded route 후보 dry-run 노출, failure analysis 10개 정리, `place_story` targeted chunk audit, HyDE subset readiness, HyDE live paired retrieval comparison, HyDE larger dev subset readiness, HyDE larger live paired retrieval comparison, active routing 적용 판단 계획, active route shadow evaluation, API active route flag dry-run contract, locked retrieval 검증 승인 계획, locked retrieval readiness dry-run runner, locked retrieval execution approval, locked retrieval paired comparison, final ablation report, API response sample, portfolio QA, submission ready audit, ColBERT-style plan-only gate, execution approval gate, hard subset 비교, voice UI MVP plan, voice UI skeleton, voice UI contract smoke, real browser voice UI visual QA, portfolio demo runbook, public repository audit refresh, portfolio submission rehearsal까지 완료했다. 필수 포트폴리오 제출 gate는 여기서 완료이며, 다음에는 별도 승인 후 optional voice STT/TTS planning으로 넘어갈 수 있다.
