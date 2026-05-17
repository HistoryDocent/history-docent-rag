# History Docent RAG

서울을 방문한 한국인과 외국인에게 한양의 역사 맥락을 설명하는 역사 관광 도슨트 서비스의 RAG 백엔드 프로젝트.

원본 데이터는 `벌거벗은 한국사` 등 한국사 도서의 Upstage Parser 결과를 기반으로 한다.

## 포트폴리오 결과 요약

현재 공개 가능한 결론은 “production 성능 개선 완료”가 아니라 “평가 기반 RAG 의사결정 구조를 구현했다”이다.

| 항목 | 현재 결정 |
| --- | --- |
| 현재 stack | `C0 parent-child chunking + dense_multilingual_e5_small_voice_rewrite + P0_rank_order + Solar Pro 3 generation v1` |
| query type classifier/router | classifier baseline accuracy 0.957143, router는 `relationship` hybrid route, `no_answer` abstain-first, 나머지 dense voice rewrite, API는 dry-run만 적용, relationship guard는 dev-only |
| 채택한 핵심 | parent-child chunking, E5-small voice rewrite, P0 evidence packing, citation answer contract |
| 보류한 핵심 | BGE-M3 dense, BGE reranker, HyDE |
| 기각한 핵심 | GraphRAG-lite 기본값, RAPTOR-lite 기본값, Solar Pro 3 repaired v2 기본값, place_story guarded boost production route |
| 공개 경계 | 원본 PDF, 전체 parser JSON, 전체 chunk text, vector index, raw eval payload, secret은 public repo에 포함하지 않음 |

핵심 수치:

| stage | candidate | scope | metric | value | decision |
| --- | --- | --- | --- | ---: | --- |
| chunking | `C0 current parent-child` | dev 70 | Recall@5 | 0.566667 | adopt |
| dense retrieval | `dense_multilingual_e5_small` | dev 70 | Recall@5 | 0.733333 | base candidate |
| hybrid | `hybrid_weighted_e5_small_alpha_0_5` | dev 70 | Recall@5 | 0.783333 | route candidate |
| reranker | `bge-reranker-v2-m3 top20` | dev 70 | latency_p95_ms | 13140.690300 | reject default |
| query rewrite | `dense_multilingual_e5_small_voice_rewrite` | dev 70 | Recall@5 | 0.850000 | adopt candidate |
| evidence packing | `P0_rank_order` | dev 70 | citation_recoverability | 1.000000 | adopt |
| GraphRAG-lite | `entity_path_v1` | relationship dev 10 | nDCG@5 delta | -0.002056 | reject default |
| RAPTOR-lite | `summary_node_v1` | overview/place_story dev 20 | nDCG@5 delta | -0.029969 | reject default |
| router skeleton | `query_type_router_v1` | contract-only | route_policy_count | 3 | implemented |
| query type classifier | `deterministic_query_type_classifier_v1` | dev 70 | macro_f1 | 0.956818 | implemented baseline |
| classifier failure analysis | `deterministic_query_type_classifier_v1` | dev 70 | route_risk_failure_count | 2 | dry-run before active route |
| classifier/router dry-run | `chat-classifier-router-dry-run-v1` | API contract + fixture retrieval | active_route_applied_count | 0 | implemented dry-run |
| relationship route guard | `relationship-route-guard-v1` | dev 70 | false_hybrid_route_count | 2 -> 0 | implemented guard |

금지 claim:

- production 성능 검증 완료
- locked test에서 최종 개선 입증
- GraphRAG로 성능 개선
- RAPTOR로 성능 개선
- 음성 관광 앱 완성
- 전체 도서 데이터 공개

상세 요약은 [Portfolio Result Summary](docs/PORTFOLIO_RESULT_SUMMARY.md)와 [Portfolio Result Summary Report](evals/reports/portfolio_result_summary_report.md)를 기준으로 한다.

## 프로젝트 정체성

이 저장소는 일반 챗봇 데모가 아니다.

목표는 다음이다.

- 서울 주요 관광지를 한양 역사 맥락과 연결한다.
- 한국사 도서 parser 결과를 정규화한다.
- 문서 구조와 citation provenance를 보존한다.
- 장소, 인물, 사건, 제도 중심으로 근거를 검색한다.
- 관광객에게 짧고 재미있게 설명할 수 있는 답변을 생성한다.
- 근거 기반 답변 품질을 고정 평가셋으로 검증한다.

## 포트폴리오 기준 역할

지원 직무:

- AI 백엔드
- RAG 엔지니어
- 데이터 기반 LLM 애플리케이션 개발

본인 역할:

- Upstage Parser 결과 정규화
- 서울/한양 장소 catalog 설계
- parent-child chunking 재설계
- BM25 baseline 구현과 Dense/Hybrid retrieval 비교 실험
- citation RAG answer contract 설계
- 단계별 evaluation gate 구축

핵심 기술:

- Python
- FastAPI
- Pydantic
- Upstage Parser
- Solar Pro 3
- BM25
- Dense Retrieval
- Hybrid Retrieval
- Jupyter Notebook
- pytest

## 1차 범위

포함:

- Upstage Parser 결과 정규화
- 서울/한양 장소 catalog 설계
- 구조 보존 parent/child chunking
- BM25 baseline retrieval
- dense retrieval 및 hybrid retrieval 실험 설계
- 장소명, 지시어, 짧은 음성형 질문을 위한 query rewrite
- Solar Pro 3 기반 citation RAG 답변 생성 계약
- retrieval/generation 평가 harness
- 실패 분석과 ablation report

1차 공개 버전에서 제외:

- 원본 PDF
- 전체 parser JSON
- 전체 chunk text
- 전체 vector database
- 전체 raw evaluation CSV
- frontend service
- voice UI
- 기본 pipeline으로서의 GraphRAG
- 기본 pipeline으로서의 RAPTOR/RAPTOR-lite

## 목표 Pipeline과 현재 구현 범위

현재 구현 및 검증 완료:

```text
PDF
-> Upstage Parser 결과
-> canonical element schema
-> parser 품질 검사
-> 서울/한양 장소 catalog
-> parent/child chunks
-> BM25 baseline
-> dense retrieval / hybrid retrieval / reranker 비교
-> deterministic query rewrite
-> evidence packing
-> citation RAG answer contract
-> Solar Pro 3 provider contract
-> FastAPI /api/v1/chat contract
-> retrieval-backed smoke
-> query type classifier baseline eval
-> query type classifier failure analysis
-> classifier/router dry-run API field
-> relationship route guard eval
-> query type router skeleton
-> retrieval evaluation harness
-> public-safe aggregate reports
```

후속 구현 대상:

```text
guarded route dry-run API field
-> HyDE subset 비교
-> failure analysis 10개 정리
-> locked test 기반 최종 개선 주장 검증
-> frontend/voice UI
```

## RAG 전략

현재 검증 중인 기본 후보:

```text
Place-aware Retrieval + Query Rewrite + Parent-Child Chunking + Citation RAG
```

검색 method는 실험 결과에 따라 고정한다. dev 기준 현재 non-rerank 기본 후보는 `dense_multilingual_e5_small_voice_rewrite`이고, `relationship` query type에는 `hybrid_weighted_e5_small_alpha_0_5`를 제한적 route 후보로 둔다.

GraphRAG-lite는 relationship input-only 비교에서 기본값으로 승격하지 않았다. RAPTOR-lite도 overview/place_story input-only 비교에서 기본값으로 승격하지 않았다.

비교 실험의 순서와 후보군은 [Retrieval Ablation Plan](docs/RETRIEVAL_ABLATION_PLAN.md)에 고정한다.
이 계획은 chunking, embedding, hybrid retrieval, reranker, query rewrite, evidence packing, Solar Pro 3 generation, RAPTOR-lite, GraphRAG-lite를 한 번에 섞지 않고 단계별로 검증하기 위한 문서다.

## 제품 목표

최종 서비스는 서울 관광 중 사용할 수 있는 역사 도슨트다.

예상 사용자는 다음이다.

- 서울을 여행하는 한국인
- 서울을 방문한 외국인
- 경복궁, 광화문, 북촌, 종로, 한양도성 등에서 역사적 맥락을 알고 싶은 사용자

답변 스타일은 다음을 지향한다.

- 짧다.
- 현장에서 듣기 쉽다.
- 장소와 역사 사건을 연결한다.
- 과장된 이야기가 아니라 근거 있는 설명을 제공한다.
- 화면에는 citation을 표시하고, 음성 답변에는 자연스럽게 축약한다.

## 공개 저장소 데이터 정책

이 public repository에는 저작권이 있는 원문 텍스트를 대량으로 포함하지 않는다.

허용:

- 코드
- 설정 파일
- 집계 metric
- 소량의 익명화 sample
- 문서

금지:

- 원본 도서 또는 PDF
- 전체 parser output
- 전체 OCR text
- 전체 chunk file
- 전체 vector index
- secret 또는 API key

## 문서 언어 정책

공개 README와 docs 하위 문서는 한글로 작성한다.

코드, API field, config key, metric 이름은 영어를 유지한다.

## 현재 상태

프로젝트 재시작 계획과 평가 gate 정리 완료.

canonical source를 `History_Docent`로 고정했고, 원본 PDF와 Upstage Parser 산출물의 `source_inventory` gate를 통과했다.

`data_manifest`와 `normalized_blocks` schema를 고정했고, parser normalization pipeline과 parser quality report도 통과했다.

parent-child chunking 전략과 gate를 문서로 고정했고, 실제 chunking pipeline도 통과했다.

BM25 baseline retrieval input contract와 seed 평가셋을 고정했다.

BM25 baseline retriever를 구현했고, seed 평가셋 기준 정량/정성 리포트를 생성했다.

현재 BM25 baseline 결과는 `Recall@5=0.250000`, `MRR=0.152778`, `nDCG@5=0.120124`다. 이 수치는 성능 개선 주장이 아니라 Dense/Hybrid/query rewrite 비교를 위한 기준선이다.

서울/한양 장소 catalog seed를 공개 가능한 형태로 작성했고, alias/relation/public leakage gate를 통과했다.

retrieval evaluation harness를 공통화했고, BM25 baseline을 새 harness에서 재현했다.

실서비스 기준의 RAG ablation 비교 실험 계획을 문서화했다.

retrieval 평가셋 v2 metadata contract와 dev/test split readiness gate를 추가했다. 현재 seed-only 상태라 contract gate는 통과하고 split readiness gate는 실패 상태다.

retrieval judgment target resolvability gate를 추가해 seed 평가셋의 child/parent/doc target이 실제 검색 corpus에 매핑되는지 검증했다.

retrieval 평가셋 확장 리포트를 추가했다. public seed 기준 현재 `contract_status=PASS`, `review_readiness_status=PASS`, `expansion_readiness_status=INCOMPLETE`, `target_query_count=105`, `current_query_count=14`, `overall_shortfall_count=91`, `dev_test_shortfall_count=105`다.

105개 full benchmark는 public repository에 직접 올리지 않고 local private storage에서 관리한다. public에는 seed/sample과 집계 report만 남긴다.

private dev 평가셋 70개를 작성하고 review rubric 기준으로 `reviewed` 승격했다. public-safe 집계 리포트 기준 `review_gate_status=PASS`, `target_resolvability_status=PASS`, `missing_child_target_count=0`, `public_raw_text_leakage_count=0`이다. private dev 원본 JSONL은 public repository에 commit하지 않는다.

private test 평가셋 35개를 작성하고 `locked` 상태로 고정했다. public-safe 집계 리포트 기준 `test_lock_gate_status=PASS`, `target_resolvability_status=PASS`, `benchmark_readiness_status=PASS`, `missing_child_target_count=0`, `public_raw_text_leakage_count=0`이다. private test 원본 JSONL은 public repository에 commit하지 않는다.

BM25 기준 chunking ablation runner를 v2로 확장했고, private dev split 70개에서 C0-C6을 비교했다. smaller/larger child, micro-parent merge, overlap 0/2, fixed-size block baseline 모두 C0를 넘지 못해 `selected_variant_id=C0`으로 유지했다. C4/C6은 `short_standalone_child` gate를 통과하지 못했다. locked test split은 사용하지 않았다.

Dense retrieval baseline v1을 구현했고, private dev split 70개에서 BM25와 `sklearn-tfidf-svd-v1` dense를 비교했다. Dense v1은 `Recall@5=0.350000`, `MRR=0.261111`, `nDCG@5=0.220955`로 BM25보다 낮아 개선 후보로 채택하지 않는다. 이 결과는 BGE-M3 또는 multilingual-E5 같은 neural embedding 결과가 아니다.

BM25-Dense 보완성 분석을 추가했다. Dense D0는 단독 성능은 낮지만 BM25가 놓친 query 2개를 맞춰 oracle union `Recall@5=0.600000`, BM25 대비 `+0.033333`을 기록했다. 이는 실제 Hybrid 성능 개선이 아니라 Hybrid RRF/Weighted 실험을 진행할 근거다.

Hybrid RRF/Weighted retrieval을 구현했고, private dev split 70개에서 BM25, Dense D0, H1 RRF, H2/H3/H4 Weighted alpha를 같은 harness로 비교했다. `hybrid_weighted_alpha_0_3`은 `Recall@1=0.416667`, `MRR=0.479722`, `nDCG@5=0.347259`로 BM25보다 top-rank 지표가 아주 소폭 높았지만 `Recall@5=0.566667`로 동일하고 `latency_p95_ms=23.038700`으로 BM25 대비 크게 느려 선택 gate를 통과하지 못했다. 따라서 D0 기반 Hybrid는 production 후보로 채택하지 않는다.

Neural embedding 비교 실험을 추가했고, private dev split 70개에서 BM25, Dense D0, BGE-M3, multilingual-E5-small, multilingual-MiniLM을 비교했다. `dense_multilingual_e5_small`은 `Recall@5=0.733333`, `MRR=0.675556`, `nDCG@5=0.533797`, `latency_p95_ms=15.717100`으로 BM25보다 높은 dev 지표를 보였다. `dense_bge_m3`는 `Recall@5=0.800000`, `nDCG@5=0.567476`으로 가장 높았지만 `latency_p95_ms=57.088400`으로 느렸다. 이 결과는 locked test와 generation 평가 전의 dev-only 후보 선별 결과이며, 최종 개선 주장으로 쓰지 않는다.

Neural dense 기반 Hybrid 비교 실험을 추가했고, private dev split 70개에서 E5-small/BGE-M3 dense leg와 RRF/Weighted fusion을 비교했다. `hybrid_weighted_e5_small_alpha_0_5`는 `Recall@5=0.783333`으로 E5-small dense 단독보다 높았지만 `MRR=0.655278`, `nDCG@5=0.509310`, `latency_p95_ms=27.547000`으로 E5-small dense 단독보다 top-rank 품질과 latency가 불리했다. 따라서 현재 기본 검색 후보는 `dense_multilingual_e5_small`이고, `hybrid_weighted_e5_small_alpha_0_5`는 reranker 비교에 투입할 recall-oriented 후보로 둔다.

Reranker comparison v1을 추가했고, private dev split 70개에서 `dense_multilingual_e5_small_rerank_bge_m3_top20`을 실제 `BAAI/bge-reranker-v2-m3` CrossEncoder로 비교했다. 이 후보는 `Recall@5=0.833333`, `MRR=0.761667`, `nDCG@5=0.635787`로 가장 높았지만 `latency_p95_ms=13140.690300`으로 CPU 실서비스 기본 후보로는 부적합하다. 따라서 현재 선택은 `dense_multilingual_e5_small`을 기본 검색 후보로 유지하고, reranker는 품질 상한과 오프라인/고비용 옵션으로만 둔다.

Query rewrite comparison v1을 추가했고, private dev split 70개에서 `dense_multilingual_e5_small`, 전체 place rewrite, voice-only rewrite를 비교했다. 전체 place rewrite는 `Recall@5=0.833333`으로 올랐지만 `place_fact`, `place_story`, `route_context`의 top-rank 품질이 일부 악화됐다. `dense_multilingual_e5_small_voice_rewrite`는 `Recall@5=0.850000`, `MRR=0.758056`, `nDCG@5=0.615293`, `latency_p95_ms=19.560200`을 기록했고 `voice_followup Recall@5`를 0.300000에서 1.000000으로 올렸다. 이 결과는 dev-only 후보 선별이며 locked test와 generation 평가 전의 최종 개선 주장이 아니다.

Evidence packing comparison v1을 추가했고, private dev split 70개에서 `dense_multilingual_e5_small_voice_rewrite` 검색 결과를 고정한 뒤 P0-P4 packing 정책을 비교했다. `P0_rank_order`와 `P3_mmr_diversity`가 `target_child_covered=0.850000`, `target_parent_covered=0.866667`, `target_doc_covered=0.950000`, `citation_recoverability=1.000000`으로 가장 높았다. `P3`의 개선은 duplicate parent rate를 0.127857에서 0.124286으로 낮춘 수준이라 generation 전 기본 교체 근거가 부족하다. 따라서 citation RAG generation v1 기본값은 `P0_rank_order`로 유지하고, `P3`는 diversity 후보로 둔다.

Citation RAG answer contract v1을 추가했다. `answer`, `spoken_answer`, `citations`, `evidence_ids`, `place_ids`, `abstained`, `unsupported_claim_risk`를 `citation-rag-answer/v1` 계약으로 고정했고, citation은 `child_id`, `parent_id`, `doc_id`, `source_block_ids`, `citation_block_ids`로 역추적한다. Solar Pro 3 호출은 아직 포함하지 않았고, public-safe 계약 리포트 기준 `citation_recoverability_rate=1.000000`, `missing_citation_count=0`, `private_path_leakage_count=0`, `secret_like_leakage_count=0`이다.

Generation evaluation harness v1을 추가했다. `CitationRagAnswer`를 `Correct-with-Evidence`, `citation_precision`, `citation_recall`, `place_relevance`, `docent_usefulness`, `spoken_answer_naturalness`, `unsupported_claim_rate`, `abstention_accuracy`, `latency_p95_ms`, `solar_call_count`, `estimated_cost`로 평가하는 구조를 고정했다. 현재 리포트는 contract-only smoke run이며 Solar Pro 3 품질 주장이 아니다. public-safe gate 기준 원문 answer/chunk text, private path, secret 누출은 0이다.

GraphRAG-lite relationship input-only 비교를 실행했다. `relationship` dev 10개에서 기존 `hybrid_weighted_e5_small_alpha_0_5_reference`가 `Recall@5=1.000000`, `MRR=0.833333`, `nDCG@5=0.709355`로 가장 적합했다. `entity_path`와 `community_hint` 후보는 citation recoverability는 1.000000이었지만 nDCG@5 개선이 없어 기본 RAG pipeline으로 승격하지 않는다. 이 결과는 dev input-only 비교이며 locked test 또는 production 개선 주장이 아니다.

RAPTOR-lite overview/place_story input-only 비교를 실행했다. private dev 20개에서 `dense_multilingual_e5_small_voice_rewrite_reference`와 `raptor_lite_parent_summary_v1`, `raptor_lite_summary_node_v1`를 비교했고, 최고 후보도 `Recall@5 delta=0.000000`, `MRR delta=0.000000`, `nDCG@5 delta=-0.029969`로 기준선을 넘지 못했다. Solar Pro 3 호출 수는 0이고 public-safe gate는 모두 0이다. 결론은 `reject_raptor_lite_default`다.

RAG 실험 decision ledger와 final ablation status report를 추가했다. 현재 기준선은 `C0 parent-child chunking + dense_multilingual_e5_small_voice_rewrite + P0_rank_order + Solar Pro 3 generation v1`로 둔다. 청킹 재비교는 지금 열지 않는다. 이 판단 역시 locked test 전의 public-safe 상태 요약이며 production 성능 주장이 아니다.

Query type router decision을 추가했다. 기본 answerable query는 `dense_multilingual_e5_small_voice_rewrite`를 유지하고, `relationship`은 `hybrid_weighted_e5_small_alpha_0_5`를 제한적 route 후보로 둔다. `place_story_guarded_boost_v1`은 locked readiness에서 candidate 선택 0건이므로 production route로 채택하지 않는다. 이번 산출물은 decision report이며 runtime router 구현 또는 locked 성능 개선 주장이 아니다.

Deterministic query type router skeleton을 추가했다. `relationship`은 hybrid weighted E5 route, `no_answer`는 abstain-first route, 나머지 answerable query type은 dense voice rewrite 기본 route로 분기한다. public-safe skeleton report 기준 `query_type_count=7`, `route_policy_count=3`, `relationship_hybrid_count=1`, `abstain_first_count=1`, `live_solar_call_count=0`이다. 이후 deterministic query type classifier baseline을 추가했고, private dev 70개에서 `accuracy=0.957143`, `macro_f1=0.956818`, `route_policy_accuracy=0.971429`, `fallback_count=0`으로 gate를 통과했다. classifier failure analysis에서는 `failure_count=3`, `route_risk_failure_count=2`, `false_hybrid_route_count=2`, `no_answer_failure_count=0`을 기록했다. `/api/v1/chat`에는 classifier/router dry-run field를 연결했고 contract/integration report 합산 기준 `classifier_dry_run_count=5`, `classifier_active_route_applied_count=0`이다. relationship route guard 평가에서는 dev 70 기준 `false_hybrid_route_count`가 2건에서 0건으로 줄고 `guarded_route_policy_accuracy=1.000000`을 기록했다. 이 결과는 production routing 또는 locked 성능 개선 주장이 아니다.

Solar Pro 3 provider contract v1을 추가했다. Upstage Chat Completions API의 `solar-pro3` 모델과 `response_format=json_schema`를 사용해 `CitationRagDraft`를 생성하는 provider를 구현했다. 현재 contract report는 mock transport 검증이며 live API 호출은 수행하지 않았다. API key는 환경변수에서만 읽고 public report/result row에는 저장하지 않는다.

FastAPI `/api/v1/chat` contract v1을 추가했다. 현재 API는 contract-only service로 `answer`, `spoken_answer`, `citations`, `evidence_ids`, `abstained`, `usage`, `classifier_router_dry_run`을 반환한다. blank query는 422 error envelope로 검증하고, `provider_mode=solar_pro_3` 요청은 live 호출 없이 503 `provider_unavailable`로 차단한다. public-safe contract report 기준 `request_count=4`, `success_count=2`, `validation_error_count=1`, `provider_unavailable_count=1`, `classifier_dry_run_count=2`, `classifier_active_route_applied_count=0`, `live_solar_call_count=0`, leakage gate는 0이다.

FastAPI `/api/v1/chat` retrieval-backed integration v1을 추가했다. `retrieval_mode=retrieval_backed` 요청은 retrieval outcome, `P0_rank_order` evidence packing, citation answer assembler를 거쳐 동일한 ChatResponse로 반환된다. public fixture integration report 기준 `retrieval_backed_request_count=2`, `retrieval_success_count=1`, `citation_count=2`, `classifier_dry_run_count=3`, `classifier_active_route_applied_count=0`, leakage gate는 0이다. local private smoke에서는 `dense_multilingual_e5_small_voice_rewrite` backend가 실제 private corpus에서 `retrieval_candidate_count=5`, `citation_count=5`, `live_solar_call_count=0`을 기록했다. 이 결과는 API 연결 smoke이며, Solar Pro 3 답변 품질 주장이 아니다.

Solar Pro 3 live generation smoke를 private dev subset 2건으로 실행했다. `solar_call_count=1`, `Correct-with-Evidence=1.000000`, `citation_precision=0.200000`, `citation_recall=0.500000`, `abstention_accuracy=1.000000`, `unsupported_claim_rate=0.000000`, `latency_p95_ms=13524.912600`을 기록했고 public-safe gate는 모두 0으로 통과했다. 이 결과는 live provider 연결 smoke이며, 작은 subset 결과라 답변 품질 개선 주장으로 사용하지 않는다.

Solar Pro 3 generation baseline을 private dev stratified subset 7건으로 실행했다. query type별 1건씩 `place_fact`, `place_story`, `relationship`, `overview`, `route_context`, `voice_followup`, `no_answer`를 평가했고 `solar_call_count=6`, `Correct-with-Evidence=1.000000`, `citation_precision=0.566667`, `citation_recall=0.509722`, `spoken_answer_naturalness=1.000000`, `unsupported_claim_rate=0.000000`, `abstention_accuracy=1.000000`, `latency_p95_ms=13144.776600`을 기록했다. 실패 태그는 `overview=low_citation_recall`, `place_fact=low_citation_precision, latency_slo_exceeded`, `place_story=low_citation_precision, low_citation_recall`이다. 이 결과도 작은 dev subset baseline이며, 개선 주장이 아니라 다음 prompt/contract 개선의 기준선이다.

Solar Pro 3 generation contract v2의 schema와 assembler filtering을 추가했다. v2 draft는 `used_evidence_pack_ranks`로 답변에 실제 사용한 evidence rank를 반환하고, assembler는 해당 rank만 citation으로 변환한다. 현재 검증은 unit/mock contract 수준이며 live Solar Pro 3 paired comparison 또는 성능 개선 주장이 아니다.

Solar Pro 3 generation contract v2 paired comparison runner를 추가했다. 현재 리포트는 fake provider 기반으로 v1/v2 query set, retrieval label, packing policy가 동일한지 검증하고 query grain paired delta를 기록한다. live Solar Pro 3 호출 수는 0이며, 결과는 runner 검증이지 실제 품질 개선 주장이 아니다.

Solar Pro 3 generation contract v2 live paired comparison을 private dev stratified subset 7건으로 실행했다. 같은 query set, 같은 retrieval label `dense_multilingual_e5_small_voice_rewrite`, 같은 packing policy `P0_rank_order`에서 v1/v2를 비교했고 live call은 v1 6회, v2 6회, no-answer 0회다. v2는 `citation_precision=0.750000`으로 v1 `0.566667`보다 높았지만 `Correct-with-Evidence`는 `1.000000`에서 `0.833333`으로 낮아졌고 `unsupported_claim_rate`는 `0.000000`에서 `0.142857`로 악화됐다. 따라서 v2는 현재 기본 contract로 채택하지 않고, `place_story`와 selected evidence prompt 실패 원인을 다음 분석 대상으로 둔다. public-safe gate는 raw text/private path/secret leakage 모두 0이다.

Solar Pro 3 generation v2 trade-off 원인 분석을 추가했다. 기존 live paired comparison의 private metric rows를 분석했고 추가 Solar Pro 3 호출은 수행하지 않았다. query 단위 진단 결과 `precision_gain_count=3`, `precision_regression_count=2`, `recall_regression_count=2`, `correctness_regression_count=1`, `unsupported_regression_count=1`, `adoption_decision=reject_default_contract`로 기록했다. 결론은 청킹 재실험보다 `place_story` retrieval hard-case와 v2 selected evidence prompt repair를 먼저 분리하는 것이다.

`place_story` hard-case 원인 진단을 추가했다. `q-dev-place-story-001`은 target doc은 retrieval/evidence pack에 들어왔지만 target child와 target parent는 빠졌고, target doc도 retrieval rank 5, pack rank 5에 위치했다. 동시에 v2 generation correctness와 unsupported claim regression이 발생했다. 따라서 현재 root cause는 `target_grain_mismatch`로 기록하며, 전체 청킹 재실험보다 `place_story` judgment target grain과 top-rank retrieval coverage를 먼저 점검한다.

`place_story` target grain 및 top-rank coverage 개선 계획을 추가했다. 현재 결정은 청킹 재실험 보류다. 먼저 `place_story` 전체 dev query에서 child, parent, doc grain별 coverage와 min rank를 진단하고, hard subset을 정의한 뒤 deterministic rewrite 또는 parent/doc context boost를 비교한다. Solar Pro 3 v2 prompt repair는 retrieval 입력 품질을 개선한 뒤 재검토한다.

`place_story` 전체 dev query 10개에 대한 target grain coverage 진단을 실행했다. `target_child_recall_at_5=0.600000`, `target_parent_recall_at_5=0.600000`, `target_doc_recall_at_5=0.900000`, `hard_case_count=4`, `doc_only_covered_count=3`, `full_grain_miss_count=1`, `recommended_decision=repair_top_rank_retrieval_coverage`다. 따라서 다음 작업은 청킹 재실험이 아니라 hard subset을 기준으로 deterministic rewrite v2 또는 parent/doc context boost를 비교하는 것이다. Solar Pro 3 추가 호출은 없었다.

`place_story` hard subset 4개에서 top-rank coverage repair 후보를 비교했다. `parent_doc_context_boost`는 baseline 대비 `child_or_parent_recall_at_5`를 `0.000000`에서 `0.250000`으로 올렸고 `doc_only_covered_count`를 3에서 1로 줄였다. 다만 `target_doc_recall_at_5`, `MRR`, `nDCG@5`는 악화되어 최종 기본 검색 전략으로 즉시 채택하지 않는다. 이 결과는 retrieval repair 후보 선별이며 locked test 또는 Solar Pro 3 generation 품질 개선 주장이 아니다.

`parent_doc_context_boost`를 full `place_story` dev query 10개에서 재검증했다. CUDA 실행 기준 `child_or_parent_recall_at_5`와 `generation_input_ready_rate`가 각각 `0.600000`에서 `0.700000`으로 개선됐고 direct evidence regression은 0건이었다. 다만 `MRR=0.770000 -> 0.616667`, `nDCG@5=0.616818 -> 0.544546`, `target_doc_recall_at_5=0.900000 -> 0.800000`으로 악화되어 최종 검색 기본값으로 확정하지 않는다. 이 결과는 Solar Pro 3 호출 전 generation 입력 후보 선별이다.

`parent_doc_context_boost`의 Solar Pro 3 호출 전 generation input-only 평가를 추가했다. CUDA 실행 기준 full `place_story` dev 10개에서 `direct_ready=0.600000 -> 0.700000`, `citation_recall=0.481309 -> 0.565953`로 개선됐지만 `Correct-with-Evidence=0.900000 -> 0.800000`, `citation_precision=0.580000 -> 0.550000`, `evidence_order=0.770000 -> 0.616667`로 하락했다. Solar Pro 3 호출 수는 0이고 public-safe gate는 모두 0이다. 결론은 즉시 채택이 아니라 `keep_as_tradeoff_candidate`이며, live generation 전에 query별 input regression을 점검해야 한다.

`parent_doc_context_boost`의 query별 input regression 분석을 추가했다. full `place_story` dev 10개에서 `direct_ready_gain_count=1`, `correct_with_evidence_regression_count=1`, `citation_precision_regression_count=3`, `citation_recall_gain_count=3`, `evidence_order_regression_count=3`, `mixed_tradeoff_count=1`, `guardrail_required_count=1`로 기록됐다. Solar Pro 3 호출 수는 0이고 public-safe gate는 모두 0이다. 결론은 `require_guardrail_before_live_generation`이며, candidate는 전체 기본값이 아니라 hard-case router 또는 reranking guardrail 후보로 제한한다.

`parent_doc_context_boost` guardrail/router 계획을 추가했다. candidate를 전역 적용하지 않고 `place_story` query에서 baseline과 candidate를 함께 계산한 뒤, direct evidence gain, doc coverage 유지, evidence order, citation precision/correctness proxy 조건을 통과할 때만 candidate를 선택한다. 다음 구현은 `baseline`, `always_boost`, `guarded_boost` 3-way input-only 비교다.

`place_story` guarded boost 3-way input-only 비교를 실행했다. CUDA 실행 기준 `parent_doc_context_boost_guarded`는 10개 query 중 candidate 1건만 선택하고 9건을 차단했다. baseline 대비 `Correct-with-Evidence=0.900000`, `citation_precision=0.580000`, `doc_coverage=0.900000`, `evidence_order=0.770000`을 유지하면서 `citation_recall`은 `0.481309`에서 `0.509881`로 소폭 개선됐다. Solar Pro 3 호출 수는 0이고 public-safe gate는 모두 0이다. 결론은 live 품질 개선 주장이 아니라 `promote_guarded_to_live_plan_review`다.

`parent_doc_context_boost_guarded` 기반 Solar Pro 3 live paired comparison 계획을 추가했다. 비교 범위는 private `place_story` dev 10개로 제한하고, baseline과 guarded 입력 fingerprint가 동일한 query는 baseline generation 결과를 재사용하도록 계획했다. 예상 live call은 11회, hard cap은 20회다. 이 문서는 실행 계획이며 Solar Pro 3 추가 호출 또는 품질 개선 주장이 아니다.

Solar Pro 3 guarded boost live comparison dry-run runner를 추가했다. CUDA 실행 기준 private `place_story` dev 10개에서 baseline live call 10회, candidate live call 1회, baseline 결과 재사용 9건으로 계산됐고 expected total live call은 11회로 hard cap 20회 안에 있다. Solar Pro 3 실제 호출 수는 0이고 public-safe gate는 모두 0이다. 이 결과는 live 품질 개선 주장이 아니라 live 실행 전 input fingerprint와 call budget 검증이다.

Solar Pro 3 guarded boost live paired comparison readiness runner를 추가했다. 기본 실행은 dry-run 재검증, call cap 확인, public-safe readiness report 생성까지만 수행하며 실제 Solar Pro 3 호출은 차단한다. readiness 기준 `expected_total_live_call_count=11`, `candidate_live_call_count=1`, `reused_candidate_count=9`, `live_call_executed=False`, `solar_call_count=0`, `readiness_decision=ready_for_live_execution_approval`이다. 다음 단계의 실제 live paired comparison은 별도 승인 후에만 실행한다.

Solar Pro 3 guarded boost live paired comparison을 private `place_story` dev 10개에서 실행했다. 실제 Solar Pro 3 호출은 baseline 10회, candidate 추가 1회로 총 11회였고, candidate 9건은 동일 input fingerprint라 baseline 결과를 재사용했다. 결과는 `Correct-with-Evidence=0.900000 -> 0.900000`, `citation_precision=0.580000 -> 0.580000`, `citation_recall=0.481309 -> 0.509881`, `unsupported_claim_rate=0.100000 -> 0.100000`, `latency_p95_ms=5066.690100 -> 5455.679600`이다. public-safe gate는 모두 0이고, 결정은 `promote_guarded_candidate_for_next_gate`다. 이 결과는 locked test 또는 최종 성능 개선 주장이 아니라 다음 gate로 승격할 dev-only 근거다.

Solar Pro 3 guarded boost next gate 판단 문서를 추가했다. 결론은 `parent_doc_context_boost_guarded`를 next gate로 승격하되 production 기본값 채택은 보류하는 것이다. 청킹 비교는 계속 보류하고, 다음 작업은 추가 Solar Pro 3 호출 없이 query-level paired delta와 route decision을 기준으로 추가 dev hard-case 검증 범위를 정하는 것이다.

Solar Pro 3 guarded boost 추가 dev hard-case 검증 계획을 추가했다. 결론은 청킹 비교 재개가 아니라 HD-SOLAR-016의 route decision을 `candidate_direct_gain`, `correctness_guardrail`, `doc_guardrail`, `precision_guardrail`, `manual_review_required`, `no_candidate_gain_control` bucket으로 나눠 검증하는 것이다. 이번 문서 작업은 새 retrieval/generation 실행이나 Solar Pro 3 추가 호출을 하지 않았고, 다음 구현 후보는 Solar call 0 조건의 hard-case validation runner다.

Solar Pro 3 guarded boost hard-case validation runner를 추가했다. CUDA 실행 기준 private `place_story` dev 10개가 6개 bucket에 모두 매핑됐고, `selected_candidate_count=1`, `guardrail_block_count=9`, `manual_review_count=2`, `route_decision_mismatch_count=0`, `citation_recoverability_min=1.000000`, `solar_call_count=0`, `validation_decision=keep_guarded_router_for_next_runner`를 기록했다. public-safe gate는 모두 0이다. 이 결과는 router safety 검증이며 production 기본값 채택이나 최종 성능 개선 주장이 아니다.

Solar Pro 3 guarded boost router threshold 판단 문서를 추가했다. 결론은 `place_story_guarded_boost_v1` threshold를 유지하는 것이다. threshold 완화는 manual review 2건의 evidence order regression 때문에 기각했고, threshold 강화는 유일한 safe direct gain 1건을 잃을 수 있어 기각했다. 이 판단은 추가 Solar Pro 3 호출 없이 수행했고, production 기본값 채택은 계속 보류한다.

Solar Pro 3 guarded boost locked test 승인 계획을 추가했다. 결론은 locked test를 즉시 실행하지 않고, 먼저 Solar Pro 3 호출 0회의 readiness dry-run으로 split, route decision, expected live call budget, public-safe gate를 확인하는 것이다. future live paired comparison은 `place_story` locked subset으로 제한하고 별도 명시 승인 후에만 실행한다.

Solar Pro 3 guarded boost locked test readiness dry-run runner를 추가했다. CUDA 실행 기준 locked `place_story` test subset 5건에서 `selected_candidate_count=0`, `candidate_live_call_count=0`, `expected_total_live_call_count=5`, `target_resolvability_fail_count=0`, `solar_call_count=0`, `readiness_decision=ready_without_candidate_live_call`을 기록했다. readiness gate는 통과했지만 candidate live call 대상이 없으므로 locked live paired comparison은 보류한다.

Solar Pro 3 guarded boost locked readiness next gate 판단 문서를 추가했다. 결론은 `place_story_guarded_boost_v1`을 production 기본값으로 채택하지 않는 것이다. locked 결과를 보고 threshold를 완화하지 않고, 청킹 비교도 재개하지 않는다. `guarded_boost`는 dev-only limited generalization 사례로 보관하고 다음 작업은 Solar Pro 3 generation v2 prompt repair 계획으로 돌린다.

Solar Pro 3 generation v2 prompt repair 계획을 추가했다. v2 selected evidence contract는 citation precision을 올릴 가능성을 보였지만, evidence over-pruning 때문에 `Correct-with-Evidence`, `citation_recall`, `unsupported_claim_rate`가 악화된 blocker가 있었다. 따라서 청킹 비교는 계속 보류하고, 다음 작업은 Solar Pro 3 live 호출 없이 repaired v2 prompt policy validator를 구현하는 것이다. public 문서에는 raw prompt, raw answer, raw evidence, raw query, private path, secret을 기록하지 않는다.

Solar Pro 3 generation v2 repaired prompt policy validator를 추가했다. fake provider/validator 기준 7개 query type 정책을 검증했고 `pass_count=6`, `fallback_required_count=1`, `fail_count=0`, `live_solar_call_count=0`, `readiness_decision=ready_for_repaired_prompt_dry_run`을 기록했다. `place_story`는 v1 fallback monitor case로 분리했다. 다음 작업은 Solar Pro 3 live 호출 없이 repaired v2 dry-run/readiness runner를 구현하는 것이다.

Solar Pro 3 generation v2 repaired dry-run/readiness runner를 추가했다. 기존 7개 query type dev subset 구조에서 route와 call budget을 검증했고 `baseline_live_call_count=6`, `repaired_candidate_live_call_count=5`, `v1_fallback_route_count=1`, `expected_total_live_call_count=11`, `solar_call_count=0`, `readiness_decision=ready_for_repaired_v2_live_approval`을 기록했다. 이 결과는 live 품질 개선 주장이 아니라 별도 승인 전 readiness gate다.

Solar Pro 3 generation v2 repaired live paired comparison을 실행했다. 실제 Solar Pro 3 호출은 총 11회였고 `Correct-with-Evidence=1.000000 -> 1.000000`, `citation_precision=0.566667 -> 0.783333`, `citation_recall=0.509722 -> 0.481944`, `unsupported_claim_rate=0.000000 -> 0.000000`을 기록했다. gate는 통과했지만 recall 하락 때문에 `adoption_decision=reject_repaired_v2_default`로 기본값 승격을 보류했다.

GraphRAG-lite relationship 실험 계획과 runner skeleton을 추가했다. 범위는 `relationship` query type 전용 input-only 계획이며 `planned_dev_query_count=10`, `planned_test_query_count=5`, `strategy_count=3`, `candidate_count=2`, `planned_solar_call_count=0`, `decision=ready_for_graphrag_lite_input_only_approval`을 기록했다. 이 결과는 GraphRAG-lite 실행 성능이나 production 채택 주장이 아니다.

RAPTOR-lite overview/place_story input-only runner와 report를 추가했다. 범위는 `overview`, `place_story` dev 20개이며 `candidate_count=2`, `promoted_candidate_count=0`, `solar_call_count=0`, `decision=reject_raptor_lite_default`를 기록했다. 이 결과는 RAPTOR-lite production 채택 또는 generation 품질 개선 주장이 아니다.

## 실행 전략

단계별 구현 순서, 정량/정성 평가 기준, 포트폴리오 산출물 기준은 [실행 전략](docs/EXECUTION_STRATEGY.md)에 정리한다.

## 개발 문서

| 문서 | 목적 |
| --- | --- |
| [PRD](docs/PRD.md) | 제품 목적, MVP, non-goal, 성공 기준 |
| [Data Policy](docs/DATA_POLICY.md) | public/private 데이터와 benchmark 공개 범위 정책 |
| [Source Data Decision](docs/SOURCE_DATA_DECISION.md) | canonical source 선정과 첫 번째 데이터 gate |
| [Data Contracts](docs/DATA_CONTRACTS.md) | data manifest와 normalized block 계약 |
| [Normalization](docs/NORMALIZATION.md) | parser 결과를 NormalizedBlock으로 변환하는 규칙과 gate |
| [Parser Quality Report](docs/PARSER_QUALITY_REPORT.md) | 청킹 전 parser/block 품질 지표와 해석 |
| [Chunking Strategy](docs/CHUNKING_STRATEGY.md) | parent-child chunking grain, boundary, filtering, citation 정책 |
| [Chunking Gates](docs/CHUNKING_GATES.md) | chunking 구현 후 통과해야 할 정량 gate |
| [Chunking Quality Report](docs/CHUNKING_QUALITY_REPORT.md) | parent-child chunking 결과의 정량/정성 평가 |
| [Place Catalog](docs/PLACE_CATALOG.md) | 서울/한양 장소 seed, alias, relation, 공개 정책 |
| [Place Catalog Validation Report](evals/reports/place_catalog_validation_report.md) | 장소 catalog seed의 정량/정성 gate 결과 |
| [BM25 Baseline Plan](docs/BM25_BASELINE_PLAN.md) | BM25 baseline 입력 계약, metric, 실패 분석 계획 |
| [Retrieval Eval Dataset](docs/RETRIEVAL_EVAL_DATASET.md) | retrieval seed 평가셋의 정량/정성 품질 보고서 |
| [Retrieval Eval Review Rubric](docs/RETRIEVAL_EVAL_REVIEW_RUBRIC.md) | retrieval dev/test 평가셋의 draft/reviewed/locked 승격 기준 |
| [Retrieval Eval Dataset Report](evals/reports/retrieval_eval_dataset_report.md) | retrieval 평가셋 v2 contract와 split gate 결과 |
| [Retrieval Eval Target Resolvability Report](evals/reports/retrieval_eval_target_resolvability_report.md) | retrieval judgment target의 corpus 매핑 검증 결과 |
| [Retrieval Eval Expansion Report](evals/reports/retrieval_eval_expansion_report.md) | retrieval dev/test 평가셋 확장 현황과 부족분 |
| [Private Dev Eval Expansion Report](evals/reports/retrieval_eval_private_dev_expansion_report.md) | private dev reviewed 70개 집계 현황과 test 부족분 |
| [Private Dev Eval Target Report](evals/reports/retrieval_eval_private_dev_target_report.md) | private dev reviewed 70개 target resolvability 검증 결과 |
| [Private Dev Eval Review Report](evals/reports/retrieval_eval_private_dev_review_report.md) | private dev 70개 review gate 결과 |
| [Private Test Eval Target Report](evals/reports/retrieval_eval_private_test_target_report.md) | private test locked 35개 target resolvability 검증 결과 |
| [Private Test Eval Lock Report](evals/reports/retrieval_eval_private_test_lock_report.md) | private test 35개 lock gate 결과 |
| [Private Benchmark Readiness Report](evals/reports/retrieval_eval_private_benchmark_readiness_report.md) | private dev 70개와 test 35개의 ablation benchmark readiness 결과 |
| [Retrieval Ablation Plan](docs/RETRIEVAL_ABLATION_PLAN.md) | 실서비스 기준 RAG 비교 실험 순서, 논문 매핑, 선택 기준 |
| [BM25 Baseline Report](evals/reports/bm25_baseline_report.md) | BM25 baseline 실행 결과와 query type별 실패 분석 |
| [Retrieval Harness Report](evals/reports/retrieval_harness_report.md) | BM25/Dense/Hybrid 공통 평가 harness와 BM25 재현 결과 |
| [Chunking Ablation Report](evals/reports/chunking_ablation_report.md) | BM25 dev-only C0/C1/C2 chunking 비교 결과 |
| [Chunking Ablation v2 Report](evals/reports/chunking_ablation_v2_report.md) | BM25 dev-only C0-C6 chunking 비교 결과 |
| [Dense Retrieval Baseline Report](evals/reports/dense_retrieval_baseline_report.md) | BM25 대비 Dense v1 baseline 비교 결과 |
| [Retrieval Overlap Analysis Report](evals/reports/retrieval_overlap_analysis_report.md) | BM25와 Dense D0의 query 단위 보완성 분석 결과 |
| [Hybrid Retrieval Comparison Report](evals/reports/hybrid_retrieval_comparison_report.md) | BM25, Dense D0, Hybrid RRF/Weighted alpha 비교 결과 |
| [Neural Embedding Retrieval Comparison Report](evals/reports/neural_embedding_retrieval_comparison_report.md) | BM25, D0, BGE-M3, multilingual-E5-small, multilingual-MiniLM 비교 결과 |
| [Neural Dense Hybrid Retrieval Comparison Report](evals/reports/neural_dense_hybrid_retrieval_comparison_report.md) | E5-small/BGE-M3 dense leg 기반 Hybrid RRF/Weighted 비교 결과 |
| [Reranker Retrieval Comparison Report](evals/reports/reranker_retrieval_comparison_report.md) | E5-small dense 후보와 BGE reranker top20 비교 결과 |
| [Query Rewrite Retrieval Comparison Report](evals/reports/query_rewrite_retrieval_comparison_report.md) | E5-small dense와 deterministic place/voice rewrite 비교 결과 |
| [Evidence Packing Comparison Report](evals/reports/evidence_packing_comparison_report.md) | 고정된 retrieval 결과 위에서 P0-P4 evidence packing 정책 비교 결과 |
| [Citation RAG Answer Contract Report](evals/reports/citation_rag_answer_contract_report.md) | Solar Pro 3 연결 전 citation RAG 응답 계약과 public-safe gate 결과 |
| [Generation Evaluation Harness Report](evals/reports/generation_eval_harness_report.md) | Solar Pro 3 연결 전 citation RAG 답변 평가 metric과 public-safe gate 결과 |
| [Solar Pro 3 Provider Contract Report](evals/reports/solar_pro_3_provider_contract_report.md) | Solar Pro 3 provider의 structured output, secret boundary, public-safe gate 결과 |
| [Solar Pro 3 Live Generation Smoke Report](evals/reports/solar_live_generation_smoke_report.md) | private dev subset 기반 Solar Pro 3 live 연결 smoke와 public-safe gate 결과 |
| [Solar Pro 3 Generation Baseline Report](evals/reports/solar_generation_baseline_report.md) | query type별 Solar Pro 3 generation baseline과 failure tag 결과 |
| [Solar Pro 3 Generation Failure Analysis](docs/GENERATION_FAILURE_ANALYSIS.md) | generation baseline 실패 원인 분해와 다음 실험 우선순위 |
| [Solar Pro 3 Generation Contract v2 Plan](docs/SOLAR_GENERATION_CONTRACT_V2_PLAN.md) | selected evidence 기반 v2 answer contract와 paired comparison 계획 |
| [Solar Pro 3 Generation Contract v2 Schema Report](evals/reports/solar_generation_contract_v2_schema_report.md) | `CitationRagDraftV2` schema와 provider v2 mock response 계약 검증 결과 |
| [Solar Pro 3 Generation Contract v2 Assembler Report](evals/reports/solar_generation_contract_v2_assembler_report.md) | `used_evidence_pack_ranks` 기반 selected citation filtering 검증 결과 |
| [Solar Pro 3 Generation Contract v2 Comparison Report](evals/reports/solar_generation_contract_v2_comparison_report.md) | fake provider 기반 v1/v2 paired comparison runner와 public-safe gate 결과 |
| [Solar Pro 3 Generation Contract v2 Live Comparison Report](evals/reports/solar_generation_contract_v2_live_comparison_report.md) | Solar Pro 3 실제 호출 기반 v1/v2 paired comparison과 trade-off 결과 |
| [Solar Pro 3 Generation v2 Trade-off Analysis](docs/SOLAR_GENERATION_V2_TRADEOFF_ANALYSIS.md) | v2 selected evidence contract의 채택 보류 판단과 다음 실험 방향 |
| [Solar Pro 3 Generation v2 Trade-off Analysis Report](evals/reports/solar_generation_v2_tradeoff_analysis_report.md) | 기존 live comparison metric rows 기반 query-level failure tag와 public-safe gate 결과 |
| [Place Story Hard-case Analysis](docs/PLACE_STORY_HARD_CASE_ANALYSIS.md) | `place_story` 실패 query의 retrieval, evidence pack, generation regression 경계 진단 |
| [Place Story Hard-case Analysis Report](evals/reports/place_story_hard_case_analysis_report.md) | `q-dev-place-story-001` target coverage, rank, failure tag, public-safe gate 결과 |
| [Place Story Target Grain and Coverage Plan](docs/PLACE_STORY_TARGET_GRAIN_AND_COVERAGE_PLAN.md) | `place_story` target grain 정책, top-rank coverage 개선 후보, 청킹 재실험 재개 조건 |
| [Place Story Target Grain Coverage Report](evals/reports/place_story_target_grain_coverage_report.md) | `place_story` dev 10개 target grain별 coverage, hard-case tag, public-safe gate 결과 |
| [Place Story Generation Input-only Eval Report](evals/reports/place_story_generation_input_only_eval_report.md) | `parent_doc_context_boost`의 Solar Pro 3 호출 전 evidence input 품질과 trade-off 결과 |
| [Place Story Generation Input Regression Analysis Report](evals/reports/place_story_generation_input_regression_analysis_report.md) | `parent_doc_context_boost` query별 input regression tag와 guardrail 필요성 |
| [Place Story Guardrail/Router Plan](docs/PLACE_STORY_GUARDRAIL_ROUTER_PLAN.md) | `parent_doc_context_boost` 적용 조건, 차단 조건, 3-way guarded comparison 설계 |
| [Place Story Guarded Boost Comparison Report](evals/reports/place_story_guarded_boost_comparison_report.md) | baseline, always boost, guarded boost 3-way input-only 비교와 route decision 결과 |
| [Solar Pro 3 Guarded Boost Live Comparison Plan](docs/SOLAR_GUARDED_BOOST_LIVE_COMPARISON_PLAN.md) | `parent_doc_context_boost_guarded`의 Solar Pro 3 live paired comparison 실행 전 계획, 비용, 중단 조건, 공개 경계 |
| [Solar Pro 3 Guarded Boost Live Dry-run Report](evals/reports/solar_guarded_boost_live_dry_run_report.md) | live 실행 전 input fingerprint, reuse 대상, 예상 live call count, public-safe gate 결과 |
| [Solar Pro 3 Guarded Boost Live Comparison Readiness Report](evals/reports/solar_guarded_boost_live_comparison_readiness_report.md) | live paired comparison 실행 전 dry-run 재검증, call cap, live 실행 차단 상태, public-safe gate 결과 |
| [Solar Pro 3 Guarded Boost Live Comparison Report](evals/reports/solar_guarded_boost_live_comparison_report.md) | private `place_story` dev 10개 Solar Pro 3 live paired comparison과 public-safe gate 결과 |
| [Solar Pro 3 Guarded Boost Next Gate Decision](docs/SOLAR_GUARDED_BOOST_NEXT_GATE_DECISION.md) | guarded boost next gate 승격 판단, 청킹 재개 조건, 포트폴리오 claim boundary |
| [Solar Pro 3 Guarded Boost Hard-case Validation Plan](docs/SOLAR_GUARDED_BOOST_HARD_CASE_VALIDATION_PLAN.md) | guarded boost 추가 dev hard-case bucket, 정량/정성 gate, data mart grain, 다음 runner 구현 지시서 |
| [Solar Pro 3 Guarded Boost Hard-case Validation Plan Report](evals/reports/solar_guarded_boost_hard_case_validation_plan_report.md) | HD-SOLAR-018 계획 문서의 정량/정성 검토와 public-safe gate 결과 |
| [Solar Pro 3 Guarded Boost Hard-case Validation Report](evals/reports/solar_guarded_boost_hard_case_validation_report.md) | HD-SOLAR-016 live metric row와 현재 input-only route decision 기반 hard-case bucket 검증 결과 |
| [Solar Pro 3 Guarded Boost Router Threshold Decision](docs/SOLAR_GUARDED_BOOST_ROUTER_THRESHOLD_DECISION.md) | guarded boost router threshold 유지/완화/강화 판단과 claim boundary |
| [Solar Pro 3 Guarded Boost Router Threshold Decision Report](evals/reports/solar_guarded_boost_router_threshold_decision_report.md) | HD-SOLAR-020 threshold 판단의 정량/정성 검토와 public-safe gate 결과 |
| [Solar Pro 3 Guarded Boost Locked Test Approval Plan](docs/SOLAR_GUARDED_BOOST_LOCKED_TEST_APPROVAL_PLAN.md) | guarded boost locked test 실행 전 승인 조건, call budget, stop condition, claim boundary |
| [Solar Pro 3 Guarded Boost Locked Test Approval Plan Report](evals/reports/solar_guarded_boost_locked_test_approval_plan_report.md) | HD-SOLAR-021 승인 계획의 정량/정성 검토와 public-safe gate 결과 |
| [Solar Pro 3 Guarded Boost Locked Test Readiness Report](evals/reports/solar_guarded_boost_locked_test_readiness_report.md) | HD-SOLAR-022 locked `place_story` readiness dry-run, call budget, public-safe gate 결과 |
| [Solar Pro 3 Guarded Boost Locked Readiness Next Gate Decision](docs/SOLAR_GUARDED_BOOST_LOCKED_READINESS_NEXT_GATE_DECISION.md) | HD-SOLAR-022 결과 기반 locked live 보류, production 채택 기각, 다음 gate 판단 |
| [Solar Pro 3 Guarded Boost Locked Readiness Next Gate Decision Report](evals/reports/solar_guarded_boost_locked_readiness_next_gate_decision_report.md) | HD-SOLAR-023 next gate 판단의 정량/정성 검토와 public-safe gate 결과 |
| [Solar Pro 3 Generation v2 Prompt Repair Plan](docs/SOLAR_GENERATION_V2_PROMPT_REPAIR_PLAN.md) | HD-SOLAR-024 selected evidence over-pruning 보정 계획, no-live-call gate, data mart grain |
| [Solar Pro 3 Generation v2 Prompt Repair Plan Report](evals/reports/solar_generation_v2_prompt_repair_plan_report.md) | HD-SOLAR-024 계획 문서의 정량/정성 검토와 public-safe gate 결과 |
| [Solar Pro 3 Generation v2 Prompt Policy Validator Report](evals/reports/solar_generation_v2_prompt_policy_validator_report.md) | HD-SOLAR-025 repaired v2 prompt policy validator의 정량/정성 검증과 public-safe gate 결과 |
| [Solar Pro 3 Generation v2 Repaired Dry-run Readiness Report](evals/reports/solar_generation_v2_repaired_dry_run_readiness_report.md) | HD-SOLAR-026 repaired v2 route, fallback, call budget, public-safe readiness 결과 |
| [Solar Pro 3 Generation v2 Repaired Live Comparison Report](evals/reports/solar_generation_v2_repaired_live_comparison_report.md) | HD-SOLAR-027 Solar Pro 3 실제 호출 기반 repaired v2 routed policy 비교와 기본값 승격 보류 판단 |
| [GraphRAG-lite Relationship Plan](docs/GRAPHRAG_LITE_RELATIONSHIP_PLAN.md) | HD-ADV-RAG-001 relationship 전용 GraphRAG-lite input-only 실험 계획과 gate |
| [GraphRAG-lite Relationship Plan Report](evals/reports/graphrag_lite_relationship_plan_report.md) | HD-ADV-RAG-001 계획 runner skeleton, 정량/정성 report, public-safe gate 결과 |
| [RAPTOR-lite Input-only Report](evals/reports/raptor_lite_input_only_report.md) | HD-RAPTOR-001 overview/place_story 전용 RAPTOR-lite input-only 비교와 기본값 기각 판단 |
| [Query Type Router Decision](docs/QUERY_TYPE_ROUTER_DECISION.md) | HD-ROUTER-001 query type별 route policy, 채택/보류/기각 판단, claim boundary |
| [Query Type Router Decision Report](evals/reports/query_type_router_decision_report.md) | HD-ROUTER-001 route policy 정량/정성 리포트와 public-safe gate 결과 |
| [Query Type Router Skeleton Report](evals/reports/query_type_router_skeleton_report.md) | HD-ROUTER-002 deterministic router skeleton, route table, public-safe gate 결과 |
| [Relationship Route Guard Eval Report](evals/reports/relationship_route_guard_eval_report.md) | HD-CLASSIFIER-005 false hybrid route guard 평가와 active route 미적용 gate 결과 |
| [Portfolio Result Summary](docs/PORTFOLIO_RESULT_SUMMARY.md) | HD-PORTFOLIO-001 제출용 현재 stack, 핵심 수치, 채택/기각 판단, claim boundary |
| [Portfolio Result Summary Report](evals/reports/portfolio_result_summary_report.md) | HD-PORTFOLIO-001 정량/정성 포트폴리오 요약과 public-safe gate 결과 |
| [Chat API Contract Report](evals/reports/chat_api_contract_report.md) | FastAPI `/api/v1/chat`의 response contract, classifier/router dry-run, error envelope, provider boundary, public-safe gate 결과 |
| [Chat Retrieval Integration Report](evals/reports/chat_retrieval_integration_report.md) | `/api/v1/chat` retrieval-backed mode의 API grain, evidence packing, classifier/router dry-run 연결, public-safe gate 결과 |
| [Chat Private Retrieval Smoke Report](evals/reports/chat_private_retrieval_smoke_report.md) | private corpus 기반 dense retrieval-backed smoke 결과와 공개 경계 검증 |
| [Solar Pro 3 Live Generation Smoke Runbook](docs/SOLAR_LIVE_GENERATION_SMOKE.md) | live provider smoke 실행 조건, 산출물, 통과 기준 |
| [WBS](docs/WBS.md) | 단계별 작업, 산출물, commit 단위 |
| [Checklist](docs/CHECKLIST.md) | 단계별 통과 기준과 공개 전 검수 |
| [TODO](docs/TODO.md) | 즉시 실행할 작업 목록 |
| [Notebook Guide](docs/NOTEBOOK_GUIDE.md) | numbered notebook 작성 규칙 |
| [Portfolio Strategy](docs/PORTFOLIO_STRATEGY.md) | README, 이력서, 면접 메시지 |
| [Eval Gates](docs/EVAL_GATES.md) | 정량/정성 평가와 개선 주장 규칙 |
| [Execution Strategy](docs/EXECUTION_STRATEGY.md) | 상세 실행 전략 |

## Notebook 체계

notebook은 분석과 검증 기록용이다. 핵심 구현은 Python module에 둔다.

경로:

```text
notebooks/
```

작성 규칙은 [Notebook Guide](docs/NOTEBOOK_GUIDE.md)를 따른다.
