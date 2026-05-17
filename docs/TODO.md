# TODO

## Now

- [x] 현업형 RAG ablation 비교 실험 계획 문서화
- [ ] `notebooks/` numbered skeleton 확인
- [x] `docs/PRD.md` 기준으로 README 첫 화면 재정리
- [x] `data_manifest` schema 설계
- [x] `normalized_blocks` schema 설계
- [x] schema unit test 작성
- [x] public sample leakage test 작성

## Next

- [x] `document_analysis_results.json` shape 분석
- [x] parser normalization pipeline 구현
- [x] global page recovery 구현
- [x] parser quality flags 구현
- [x] parser quality report 생성
- [ ] `01_data_manifest_audit.ipynb` 작성
- [x] `02_parser_quality_check.ipynb` 작성
- [x] `03_normalized_blocks_validation.ipynb` 작성
- [x] parent-child chunking 설계 문서 작성
- [x] chunking gate 문서 작성
- [x] 기본 chunking config 작성
- [x] `ChunkSourceRef`, `ParentChunk`, `ChildChunk`, `ChunkingQualityReport` schema 구현
- [x] parent-child chunking 구현
- [x] chunking quality report 생성
- [x] `04_chunking_quality_analysis.ipynb` 작성
- [x] place catalog seed 작성
- [x] place catalog validation report 생성
- [x] `05_place_catalog_validation.ipynb` 작성
- [x] BM25 retrieval input contract 정의
- [x] retrieval seed 평가셋 작성
- [x] `06_bm25_baseline_evaluation.ipynb` 평가 계약 셀 작성
- [x] BM25 baseline 구현
- [x] BM25 baseline 정량/정성 평가 리포트 작성
- [x] retrieval evaluation harness 구현
- [x] `07_dense_hybrid_retrieval_comparison.ipynb` 공통 harness 셀 작성

## Later

- [x] retrieval 평가셋 105개 확장 workflow와 부족분 리포트 추가
- [x] benchmark public/private 경계 고정
- [x] private retrieval 평가셋 dev 후보 35개 1차 draft 작성
- [x] private retrieval 평가셋 dev 1차 35개 review rubric 고정 및 reviewed 승격
- [x] private retrieval 평가셋 dev 2차 35개 작성 및 reviewed 승격
- [x] private retrieval 평가셋 dev 70개 reviewed 완성
- [x] private retrieval 평가셋 test 후보 35개 locked 작성
- [x] retrieval dev/test split contract 고정
- [x] retrieval judgment target 검증 gate 추가
- [x] chunking ablation runner 구현
- [x] chunking ablation v2 C0-C6 비교 리포트 작성
- [x] 청킹 결정 리뷰와 재실험 기준 정리
- [x] Dense retrieval baseline v1 구현
- [x] BM25-Dense 보완성 분석
- [x] Hybrid retrieval 구현
- [x] neural embedding model 비교
- [x] neural dense 기반 Hybrid 비교
- [x] neural dense 기반 Reranker 비교 v1
- [x] reranker comparison 구현
- [x] place-aware query rewrite 구현
- [ ] reranker top30/top50 장시간 실험
- [ ] smaller reranker 후보 비교
- [x] evidence packing 비교 구현
- [x] citation RAG answer contract 구현
- [x] generation evaluation harness 구현
- [x] Solar Pro 3 provider 구현
- [x] FastAPI `/chat` contract 구현
- [x] FastAPI `/chat` retrieval-backed integration 구현
- [x] private dense retrieval smoke report 생성
- [x] Solar Pro 3 live generation smoke runner 구현
- [x] `UPSTAGE_API_KEY` 주입 후 Solar Pro 3 live generation smoke report 생성
- [x] Solar Pro 3 generation baseline runner 구현
- [x] query type별 Solar Pro 3 generation baseline report 생성
- [x] Solar Pro 3 generation 실패 원인 진단 문서 작성
- [x] generation prompt/answer contract v2 비교 계획 작성
- [x] `CitationRagDraftV2` schema와 provider mock test 구현
- [x] `CitationRagDraftV2` schema 검증 리포트 작성
- [x] assembler v2 selected evidence citation filtering 구현
- [x] Solar Pro 3 generation v1/v2 paired comparison runner 구현
- [x] Solar Pro 3 generation 개선 전후 paired comparison
- [x] Solar Pro 3 generation v2 trade-off 원인 분석
- [x] Solar Pro 3 generation v2 prompt repair 계획 작성
- [x] Solar Pro 3 generation v2 repaired prompt policy validator 구현
- [x] Solar Pro 3 generation v2 repaired dry-run/readiness runner 구현
- [x] Solar Pro 3 generation v2 repaired live paired comparison 실행 승인 여부 결정
- [x] Solar Pro 3 generation v2 repaired live paired comparison 실행 및 기본값 승격 보류 판단
- [x] `place_story` retrieval hard-case 원인 분석
- [x] `place_story` target grain 및 top-rank coverage 개선 계획 작성
- [x] `place_story` 전체 dev query target grain coverage diagnostic runner 구현
- [x] `place_story` top-rank retrieval coverage 개선 후보 비교 실험
- [x] `parent_doc_context_boost` full place_story/dev 재검증 및 generation 입력 영향 분석
- [x] `parent_doc_context_boost` 적용 후 Solar Pro 3 호출 전 generation input-only 평가
- [x] `parent_doc_context_boost` query별 input regression 원인 점검
- [x] `parent_doc_context_boost` 적용 조건 제한 guardrail/router 계획 작성
- [x] `parent_doc_context_boost` guarded 3-way 비교 runner 구현
- [x] `parent_doc_context_boost_guarded` 기반 Solar Pro 3 live paired comparison 계획 작성
- [x] Solar Pro 3 guarded boost live comparison dry-run runner 구현
- [x] Solar Pro 3 guarded boost live paired comparison runner 구현
- [x] Solar Pro 3 live paired comparison 실행 승인 여부 결정
- [x] Solar Pro 3 guarded boost next gate 판단 문서 작성
- [x] Solar Pro 3 guarded boost 추가 dev hard-case 검증 계획 작성
- [x] Solar Pro 3 guarded boost 추가 dev hard-case validation runner 구현
- [x] Solar Pro 3 guarded boost router threshold 유지/수정 판단 문서 작성
- [x] Solar Pro 3 guarded boost locked test 실행 전 승인 계획 작성
- [x] Solar Pro 3 guarded boost locked test readiness dry-run runner 구현
- [x] Solar Pro 3 guarded boost locked readiness 결과 기반 next gate 판단 문서 작성

## Experiments

- [x] RAPTOR-lite overview/place_story input-only 비교
- [x] GraphRAG-lite relationship 계획 및 runner skeleton 작성
- [x] GraphRAG-lite relationship input-only 비교
- [x] RAG decision ledger 및 final ablation status report 작성
- [x] query-type router decision report 작성
- [x] query-type router 채택 여부 판단
- [x] deterministic query-type router skeleton 구현
- [x] deterministic query-type classifier baseline 평가
- [x] query-type classifier 오분류 failure analysis
- [x] FastAPI `/chat` classifier/router dry-run field 연결
- [x] relationship route guard 설계
- [x] FastAPI `/chat` guarded route 후보 dry-run field 연결
- [x] HyDE subset readiness dry-run
- [x] HyDE live paired retrieval comparison
- [x] HyDE larger dev subset readiness
- [x] HyDE larger dev live paired retrieval comparison
- [x] `place_story` targeted chunk audit
- [x] active routing 적용 여부 판단 계획
- [x] active route shadow evaluation runner
- [x] API active route flag dry-run contract
- [x] locked retrieval 검증 승인 계획
- [x] locked retrieval readiness dry-run runner
- [x] locked retrieval paired comparison 실행 여부 승인
- [x] locked retrieval paired comparison runner 실행
- [ ] ColBERT style late interaction hard subset 검토
- [x] final ablation report 작성

## Portfolio

- [x] README 결과 표 실제 수치로 갱신
- [x] failure analysis 10개 작성
- [ ] API response sample 작성
- [ ] 이력서 한 줄 설명 작성
- [ ] 면접 예상 질문 답변 작성
