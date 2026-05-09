# TODO

## Now

- [ ] `notebooks/` numbered skeleton 확인
- [ ] `docs/PRD.md` 기준으로 README 첫 화면 재정리
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

## Later

- [ ] place catalog seed 작성
- [ ] `ChunkSourceRef`, `ParentChunk`, `ChildChunk`, `ChunkingQualityReport` schema 구현
- [ ] parent-child chunking 구현
- [ ] `04_chunking_quality_analysis.ipynb` 작성
- [ ] BM25 baseline 구현
- [ ] Dense/Hybrid retrieval 구현
- [ ] retrieval evaluation harness 구현
- [ ] place-aware query rewrite 구현
- [ ] citation RAG answer contract 구현
- [ ] Solar Pro 3 provider 구현
- [ ] FastAPI `/chat` contract 구현

## Experiments

- [ ] RAPTOR-lite overview/place_story 비교
- [ ] GraphRAG-lite relationship 비교
- [ ] query-type router 채택 여부 판단
- [ ] final ablation report 작성

## Portfolio

- [ ] README 결과 표 실제 수치로 갱신
- [ ] failure analysis 10개 작성
- [ ] API response sample 작성
- [ ] 이력서 한 줄 설명 작성
- [ ] 면접 예상 질문 답변 작성
