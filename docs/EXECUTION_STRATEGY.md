# 실행 전략

## 총괄 판정

현재 1순위는 기능 추가가 아니다.

먼저 `평가 가능한 MVP RAG 백엔드`를 만든다.

기본 구조:

```text
Place-aware Hybrid Retrieval
+ Query Rewrite
+ Parent-Child Chunking
+ Citation RAG
```

RAPTOR-lite와 GraphRAG-lite는 기본 구조가 아니라 비교 실험군이다.

## 담당자별 결론

### 제품/UX 담당

MVP는 3가지만 증명한다.

1. 장소를 이해한다.
2. 역사 근거를 찾는다.
3. 관광객이 듣기 좋은 짧은 설명으로 바꾼다.

MVP 필수:

- 서울/한양 장소 catalog
- 장소 기반 query rewrite
- BM25 baseline
- parent-child chunking
- citation answer
- `spoken_answer` field
- no-answer 처리
- retrieval/generation 평가 harness

MVP 제외:

- voice UI
- STT/TTS
- route recommendation
- AR
- 사용자 계정
- GraphRAG-first
- RAPTOR-first
- full frontend

### 데이터 파이프라인 담당

기존 `all_chunks.json`은 최종 chunk로 쓰지 않는다.

이유:

- metadata가 `source`, `page`, `type` 수준이다.
- global page 복구가 부족하다.
- element id, section path, bbox, quality flag가 없다.
- citation backtracking에 부적합하다.

먼저 데이터 계약을 고정한다.

필수 산출물:

- `data_manifest.json`
- `normalized_blocks.jsonl`
- `parser_quality_report.md`
- `chunks_child.jsonl`
- `chunks_parent.jsonl`
- `index_manifest.json`

public repo에는 sample과 aggregate metric만 둔다.

### RAG·평가 담당

기존 50개 샘플 결과만으로 최종 결정을 내리지 않는다.

비교 기준은 다음 순서다.

1. parser/chunk 품질 평가
2. retrieval dev/test 평가셋 고정
3. chunking ablation으로 검색 단위 선택
4. Dense retrieval baseline 재현
5. Hybrid RRF/Weighted retrieval 비교
6. reranker top-k 비교
7. place catalog + query rewrite 평가
8. evidence packing 평가
9. Solar Pro 3 citation generation 평가
10. external_human + stress_set 구축
11. RAPTOR-lite 비교
12. GraphRAG-lite 비교
13. query-type router 판단
14. ablation/failure report 작성

대표 지표:

- `Evidence Recall@5`
- `Correct-with-Evidence`
- `citation_precision`
- `citation_recall`
- `place_relevance`
- `latency_p95`
- `estimated_cost`

### 백엔드·보안·운영 담당

백엔드 포트폴리오로 의미 있으려면 `/chat` 하나로 부족하다.

필수 증명 항목:

- FastAPI API contract
- Solar Pro 3 provider abstraction
- 유료 LLM 호출 비용 보호
- rate limit
- cache
- retry/timeout
- `/live`, `/ready` health check 분리
- structured logging
- 테스트 기반 장애 처리

필수 endpoint:

```text
GET  /api/v1/health/live
GET  /api/v1/health/ready
POST /api/v1/chat
POST /api/v1/places/search
```

### 포트폴리오 담당

포트폴리오 메시지는 하나로 고정한다.

```text
서울 관광객의 장소 기반 질문에 대해, 한국사 도서 parser 결과에서 근거를 검색하고 citation 기반 도슨트 답변을 생성하는 RAG 백엔드
```

README와 이력서에는 기술명 나열이 아니라 다음 구조를 보여준다.

```text
문제:
서울 관광 질문은 짧고 모호하며, 한양 역사 맥락과 근거 citation이 동시에 필요했다.

역할:
parser 결과 정규화, chunk 재설계, retrieval 비교, evaluation harness 설계, citation RAG 구현.

행동:
BM25/Dense/Hybrid/RAPTOR-lite/GraphRAG-lite를 query type별로 비교했다.

결과:
Correct-with-Evidence, Recall@5, citation_precision, latency 기준으로 최종 구조를 선택했다.

한계:
저작권 데이터 공개 제한, synthetic QA 누수 위험, GraphRAG entity 정규화 난도.
```

## Phase 1. 데이터 계약과 Parser Normalization

목표:

원본 PDF와 Upstage Parser 결과를 public repo에 노출하지 않고, citation 가능한 canonical schema로 변환한다.

구현:

- `data_manifest` schema
- `normalized_blocks` schema
- parser normalization pipeline
- parser quality report
- redacted public sample 생성

정량 테스트:

- 문서 누락 수
- `doc_id` 중복 수
- 필수 field null 수
- `page_global` 역전 수
- base64 잔존 수
- OCR noise block 수
- private path leakage 수

정성 테스트:

- 표지 페이지
- 목차 페이지
- 장 시작 페이지
- 일반 본문 페이지
- 표/그림 포함 페이지
- OCR 깨짐 페이지
- 배치 경계 페이지

통과 기준:

```text
문서 누락 0
doc_id 중복 0
필수 field null 0
page_global 역전 0
base64 잔존 0
public sample 내 private path 0
```

포트폴리오 산출물:

- parser 품질 집계표
- 공개 가능한 redacted parser sample
- parser 문제와 해결 방식 설명

## Phase 2. Place Catalog

목표:

서울 관광지를 한양 역사 맥락과 연결한다.

초기 장소:

```text
gyeongbokgung
gwanghwamun
bukchon
jongno
hanyangdoseong
changdeokgung
sajikdan
```

구현:

- `configs/place_catalog.seed.yaml`
- place schema
- place search
- place alias
- related people/events/institutions

정량 테스트:

- `place_id` 중복 수
- 빈 related field 수
- alias 검색 성공률
- place 관련 chunk 연결 수

정성 테스트:

- 경복궁, 광화문, 북촌, 종로, 한양도성 질문별 관련성 검수
- “여기”, “이 궁”, “광화문 근처” 같은 표현 처리 검수

통과 기준:

```text
place_id 중복 0
modern_name 중복 0
alias 검색 실패 0
각 place별 최소 관련 키워드 존재
```

포트폴리오 산출물:

- place catalog sample
- 장소 기반 질문 예시
- place-aware query rewrite 전후 예시

## Phase 3. Parent/Child Chunking

목표:

검색용 child chunk와 답변용 parent chunk를 분리하고 citation backtracking을 가능하게 한다.

구현:

- `chunks_child.jsonl`
- `chunks_parent.jsonl`
- section path 복원
- parent-child link
- quality flag
- redacted chunk sample

정량 테스트:

- child chunk 수
- parent chunk 수
- orphan child 수
- invalid page range 수
- unknown element id 수
- too short/too long chunk 비율
- citation recoverability

정성 테스트:

- chunk가 의미 단위로 끊기는지 검수
- parent context가 답변 배경을 제공하는지 검수
- 서울 장소 관련 chunk가 관광 질문에 쓸 만한지 검수

통과 기준:

```text
orphan child 0
invalid page range 0
unknown element_id 0
chunk_id 중복 0
citation recoverability >= 99%
```

포트폴리오 산출물:

- chunk 품질 집계표
- parent-child 구조 예시
- 기존 chunk 대비 metadata 개선표

## Phase 4. Retrieval Baseline

목표:

BM25, Dense, Hybrid를 같은 평가셋에서 비교한다.

비교군:

```text
BM25
Dense
Hybrid Weighted
Hybrid RRF
```

정량 테스트:

- `Recall@1`
- `Recall@3`
- `Recall@5`
- `MRR`
- `nDCG@5`
- `latency_p50`
- `latency_p95`

정성 테스트:

- wrong place
- wrong person
- wrong period
- missing context
- OCR noise hit

통과 기준:

```text
BM25 baseline 재현
Hybrid가 query type별로 어디서 이기는지 확인
latency_p95 기록
```

현재 실험 결과:

```text
BM25 Recall@5=0.566667, MRR=0.471389, latency_p95_ms=5.697700
Dense D0 Recall@5=0.350000, MRR=0.261111, latency_p95_ms=19.703900
Hybrid RRF Recall@5=0.516667, MRR=0.359722, latency_p95_ms=22.643800
Hybrid Weighted alpha 0.3 Recall@5=0.566667, MRR=0.479722, latency_p95_ms=23.038700
Hybrid Weighted alpha 0.5 Recall@5=0.533333, MRR=0.427778, latency_p95_ms=25.907100
Hybrid Weighted alpha 0.7 Recall@5=0.450000, MRR=0.354722, latency_p95_ms=22.609100
```

판정:

```text
현재 Hybrid D0 조합은 선택하지 않는다.
alpha 0.3은 MRR만 소폭 개선됐고 Recall@5는 동일하다.
latency_p95가 BM25 대비 크게 증가해 latency gate를 통과하지 못했다.
다음은 BM25 유지 상태에서 neural embedding model 비교 또는 shared dense index 최적화다.
```

포트폴리오 산출물:

- retrieval ablation table
- query type별 실패 분석
- 최종 retrieval 후보 선택 근거

## Phase 5. Query Rewrite와 Place-Aware Retrieval

목표:

짧고 모호한 관광/음성형 질문을 검색 가능한 질의로 변환한다.

비교군:

```text
Hybrid
Hybrid + place catalog
Hybrid + query rewrite
Hybrid + place catalog + query rewrite
```

정량 테스트:

- `voice_followup` Recall@5
- `place_fact` Recall@5
- `place_story` Recall@5
- rewrite success rate
- rewrite invalid JSON rate

정성 테스트:

- “여기가 왜 유명해?”
- “그 사람은 왜 중요해?”
- “이 궁이 세종이랑 관련 있어?”
- “근처에 조선 시대 이야기가 있어?”

통과 기준:

```text
voice_followup 유형 개선
place_relevance 개선
invalid rewrite JSON 0
근거 없는 확장 질의 생성 없음
```

포트폴리오 산출물:

- rewrite 전후 예시
- query type별 개선표
- 실패한 rewrite 사례

## Phase 6. Citation RAG와 Solar Pro 3

목표:

검색된 evidence를 기반으로 관광객용 답변과 음성용 짧은 답변을 생성한다.

Answer contract:

```text
answer
spoken_answer
citations
unsupported_claims
rewritten_query
retrieval_trace
latency_ms
estimated_cost
```

정량 테스트:

- `Correct-with-Evidence`
- `faithfulness`
- `citation_precision`
- `citation_recall`
- `place_relevance`
- `docent_usefulness`
- `unsupported_claim_rate`
- `abstention_accuracy`

정성 테스트:

- 30초 안에 이해되는가
- 현장 관광객에게 말투가 자연스러운가
- 장소와 역사 사건이 연결되는가
- 과장 없이 흥미를 만드는가
- 근거 없는 질문에 거부하는가

통과 기준:

```text
핵심 unsupported claim 없음
citation이 답변을 지지함
spoken_answer가 짧고 자연스러움
no-answer 질문에서 환각 없음
```

포트폴리오 산출물:

- API response sample
- citation answer 예시
- no-answer 처리 예시
- 실패 분석 10개

## Phase 7. 백엔드 운영 품질

목표:

유료 LLM API를 쓰는 RAG 백엔드의 운영 안정성을 테스트로 증명한다.

구현:

- FastAPI router
- Pydantic schema
- fake provider
- Upstage Solar provider
- rate limiter
- cache interface
- retry/timeout
- structured error envelope
- `/live`, `/ready`

정량 테스트:

- unit/integration/security test 수
- coverage
- rate limit 차단 성공률
- provider retry branch coverage
- cached vs uncached latency
- timeout handling 성공률

통과 기준:

```text
pytest 통과
coverage >= 80%
rate limit 차단 성공률 100%
provider raw error 노출 0
secret 노출 0
```

포트폴리오 산출물:

- 테스트 결과
- API contract
- 장애 처리 설계
- cache/retry/rate limit 설명

## Phase 8. RAPTOR-lite 비교

목표:

overview, place_story, route_context 질문에서 summary node가 도움이 되는지 검증한다.

원칙:

- summary node는 검색 힌트다.
- 최종 citation은 원문 child/parent chunk만 사용한다.
- summary 자체를 근거로 쓰지 않는다.

성공 기준:

```text
overview 유형 Correct-with-Evidence +3%p 이상
citation_precision 하락 없음
p95 latency +20% 이내
```

포트폴리오 산출물:

- RAPTOR-lite가 유효한 질문 유형
- RAPTOR-lite가 실패한 질문 유형
- 기본 구조 채택 여부 판단

## Phase 9. GraphRAG-lite 비교

목표:

relationship 질문에서 graph retrieval이 도움이 되는지 검증한다.

적합 질문:

- 정도전과 이방원의 관계
- 경복궁과 왕권의 관계
- 광화문과 조선 정치 공간의 관계
- 한양도성과 수도 방어 체계의 관계

원칙:

- graph triple은 근거가 아니다.
- graph는 retrieval hint다.
- 최종 citation은 원문 chunk다.

성공 기준:

```text
relationship 유형 Correct-with-Evidence +3%p 이상
unsupported_claim_rate 증가 없음
entity resolution 오류율 <= 5%
citation backtracking 성공률 >= 95%
```

포트폴리오 산출물:

- GraphRAG-lite 유효성 판단
- entity resolution 실패 사례
- router 채택 여부 판단

## 개선 주장 규칙

평균 점수만으로 개선을 주장하지 않는다.

필수:

```text
query 단위 paired comparison
bootstrap 10,000회
95% confidence interval
query type별 breakdown
latency/cost delta
```

개선 주장 허용:

```text
Retrieval Recall@5 +5%p 이상
Correct-with-Evidence +3%p 이상
citation_precision +3%p 이상
p95 latency +20% 이내
cost +20% 이내
95% CI가 0을 지나지 않음
```

개선 주장 금지:

```text
dev_synthetic에서만 좋아짐
external_human에서 효과 없음
CI가 0을 지남
latency/cost 악화 설명 없음
특정 query type만 좋아지고 전체 결론처럼 포장
```

## Git Commit 순서

```text
docs: define execution strategy and evaluation gates
feat: add data manifest schema
test: add parser normalization tests
feat: add parser normalization pipeline
feat: add parser quality report
feat: add place catalog seed
test: add chunk provenance tests
feat: add parent child chunking
feat: add bm25 retrieval baseline
test: add retrieval evaluation harness
feat: add hybrid retrieval experiment
feat: add place aware query rewrite
feat: add citation rag answer contract
feat: add solar provider abstraction
feat: add fastapi chat contract
test: add api resilience tests
docs: add ablation report and failure analysis
```

## 다음 작업

즉시 구현할 것은 `data_manifest`와 `normalized_blocks` schema다.

다음 commit 목표:

```text
feat: add data manifest and normalized block schemas
```

완료 조건:

- Pydantic schema 존재
- schema unit test 존재
- public sample 형식 정의
- private path leakage 테스트 존재
- README 또는 docs에서 schema 위치 설명
