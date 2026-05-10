# Portfolio Strategy

## 대표 메시지

```text
서울 관광객의 장소 기반 질문에 대해, 한국사 도서 parser 결과에서 근거를 검색하고 citation 기반 도슨트 답변을 생성하는 RAG 백엔드
```

## README 첫 화면 구성

1. 프로젝트 한 줄 정의
2. 문제 정의
3. 대상 사용자
4. 내 역할
5. 핵심 기술
6. 아키텍처
7. 평가 설계
8. 결과 표
9. 데이터 공개 정책
10. 한계와 다음 개선

## 이력서 문장 초안

```text
HistoryDocent | 서울/한양 역사 관광 도슨트 RAG 백엔드 | 개인 프로젝트
- Upstage Parser 기반 한국사 도서 데이터를 element 단위로 정규화하고 page/section/chunk provenance를 보존하는 전처리 pipeline 설계
- 서울 주요 장소와 한양 역사 맥락을 연결하기 위해 place catalog, parent-child chunking, BM25 baseline, retrieval evaluation harness 구현
- Dense, Hybrid, Reranker, Query Rewrite, RAPTOR-lite, GraphRAG-lite 비교를 위한 dev/test 평가셋과 ablation 계획 설계
- Solar Pro 3 기반 citation RAG API는 answer contract와 evaluation gate를 먼저 고정한 뒤 구현 예정
```

실제 수치 확보 전에는 “개선” 문장을 쓰지 않는다.

수치 확보 후 교체할 문장:

```text
- Hybrid + Query Rewrite 적용 후 place-based 질문에서 Correct-with-Evidence를 기준선 대비 {x.x}%p 개선
- 질문 유형별 최적 retrieval 전략을 분리하고 p95 latency {x}ms 내 응답 구조 설계
```

## 면접 답변 포인트

### 왜 이 프로젝트를 했는가

서울 관광에서 장소와 역사 맥락이 분리되는 문제를 해결하기 위해 시작했다. 단순 챗봇이 아니라 원문 근거를 추적할 수 있는 RAG 백엔드로 범위를 좁혔다.

### 왜 GraphRAG를 처음부터 쓰지 않았는가

GraphRAG는 relationship 질문에 유리하지만 entity extraction과 canonicalization 오류가 전체 결과를 오염시킬 수 있다. 그래서 BM25/Hybrid/Parent-Child/Citation 구조를 기준선으로 먼저 만들고, GraphRAG-lite는 relationship 질문 전용 실험군으로 분리했다.

### 성능을 어떻게 검증했는가

retrieval과 generation을 분리했다. Retrieval은 Recall@k, MRR, nDCG로 보고, 최종 답변은 Correct-with-Evidence와 citation precision/recall로 판단했다. 개선 여부는 query 단위 paired comparison과 bootstrap confidence interval로 판단했다.

### 저작권 데이터는 어떻게 처리했는가

원본 PDF, 전체 parser output, 전체 chunk text는 public repo에 올리지 않았다. 공개 repo에는 schema, code, aggregate metric, redacted sample만 포함했다.

### 음성 서비스와 RAG 백엔드는 어떻게 연결되는가

음성 UI보다 먼저 짧은 질문 처리, 지시어 해소, spoken_answer 생성, citation display 구조를 백엔드에서 검증했다. STT/TTS는 그 다음 단계로 분리했다.

## 금지 표현

- 음성 관광 앱 완성
- 상용 수준 서비스
- GraphRAG 적용 완료
- 성능 개선 입증
- 전체 도서 데이터 공개
- 최신 RAG 기법 다수 적용

## 제출 전 검수

- GitHub 링크가 public으로 열리는가
- README 첫 화면에서 문제/역할/기술/평가가 보이는가
- 원본 저작권 데이터가 없는가
- 미검증 수치가 없는가
- notebook이 원문을 대량 출력하지 않는가
