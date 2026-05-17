# Chunking Decision Review

## 결론

현재 청킹 기준선은 `C0 current parent-child`로 유지한다.

이 결정은 "모든 청킹 기법을 최적화했다"는 뜻이 아니다. 현재 데이터와 평가 계약에서는 `Heading-aware Parent Chunk + Block-merge Child Chunk + Citation Provenance Recovery`가 가장 방어 가능한 기준선이라는 뜻이다.

이 문서는 public-safe 결정 리뷰다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 현재 청킹 방식

현재 C0는 다음 성격을 가진다.

| 관점 | 현재 적용 |
| --- | --- |
| 구조 인식 | `heading1` 기반 parent boundary 사용 |
| 계층 구조 | parent chunk와 child chunk를 분리 |
| child 생성 | parent 내부 block 병합 |
| overlap | `child_overlap_blocks=1` |
| citation | child가 원천 normalized block id와 page span을 보존 |
| 검색 단위 | child chunk |
| context 확장 단위 | parent chunk |

따라서 C0는 단순 recursive character chunking이 아니라 `structure-aware hierarchical/hybrid chunking`에 가깝다.

## 비교한 후보

| variant | 청킹 관점 매핑 | 설정 차이 | gate | Recall@5 | MRR | nDCG@5 | 판단 |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| `C0` | structure-aware hierarchical parent-child | overlap 1, child max 1100 | PASS | 0.566667 | 0.471389 | 0.344203 | 채택 |
| `C1` | smaller child parent-child | child max 800 | PASS | 0.083333 | 0.044444 | 0.026033 | 기각 |
| `C2` | larger child parent-child | child max 1400 | PASS | 0.533333 | 0.446389 | 0.272112 | 기각 |
| `C3` | micro-parent merge | small parent 병합 | PASS | 0.533333 | 0.453333 | 0.330712 | 기각 |
| `C4` | no-overlap parent-child | overlap 0 | FAIL | 0.483333 | 0.384722 | 0.241390 | 기각 |
| `C5` | high-overlap parent-child | overlap 2 | PASS | 0.533333 | 0.368611 | 0.247787 | 기각 |
| `C6` | fixed-size block baseline | fixed-size block | FAIL | 0.316667 | 0.254167 | 0.145937 | 기각 |

BM25 retriever를 고정한 dev 70개 평가에서 C0가 selection gate와 검색 지표를 동시에 가장 잘 만족했다.

## 사용자가 언급한 청킹 방식별 판단

| 방식 | 현재 상태 | 판단 |
| --- | --- | --- |
| Character | 미채택 | citation provenance와 구조 보존에 불리해 기본 후보로 두지 않는다. |
| Sentence | 미실험 | 한국어 문장 분리 품질과 도서 parser block 구조가 섞여 별도 이점이 불확실하다. |
| Semantic | 미실험 | embedding 기반 boundary가 citation recoverability를 흔들 수 있어 후순위다. |
| Sentence Window | 미실험 | parent-child context expansion이 유사 역할을 하므로 현재는 중복도가 높다. |
| Fixed-size chunking | C6로 근사 비교 | gate 실패와 낮은 Recall@5 때문에 기본값에서 제외했다. |
| Structure-aware | C0-C5에서 비교 | heading boundary 기반 후보 중 C0를 채택했다. |
| Hierarchical/Hybrid | C0로 적용 | parent context와 child retrieval을 분리해 현재 기준선으로 사용한다. |

## Semantic Chunking을 지금 열지 않는 이유

지금 semantic chunking을 새로 열지 않는 이유는 세 가지다.

1. 이미 C0 위에서 Dense, Hybrid, Reranker, Query Rewrite, Evidence Packing, Generation, Router 실험이 누적됐다.
2. 청킹을 바꾸면 이후 실험 결과를 같은 기준선으로 비교하기 어렵다.
3. 이 프로젝트는 최종 답변에서 원문 normalized block 기준 citation을 요구한다. semantic boundary가 citation recoverability를 낮추면 검색 점수가 올라도 제품 목적에는 맞지 않는다.

따라서 semantic chunking은 "더 좋아 보이는 기법"이라서 여는 것이 아니라, 실패 원인이 chunk boundary임을 확인했을 때만 연다.

## 재실험 조건

청킹 비교를 다시 여는 조건은 다음 중 하나다.

| 조건 | 판단 기준 |
| --- | --- |
| boundary failure 확인 | failure analysis 10개 중 3개 이상이 chunk boundary 손실로 판정 |
| citation 손실 | selected evidence가 원천 block/page citation을 안정적으로 복구하지 못함 |
| query type 특정 실패 | `place_story`, `relationship`, `overview` 중 특정 type에서 같은 boundary 문제가 반복 |
| corpus 변화 | parser 버전, source normalization, 도서 범위가 바뀜 |
| locked readiness 실패 | locked test 전 dry-run에서 source coverage 실패가 반복 |

재실험을 열더라도 첫 후보는 전면 교체가 아니라 targeted variant로 둔다.

## 재실험 후보 우선순위

| priority | 후보 | 이유 | 통과 조건 |
| ---: | --- | --- | --- |
| 1 | sentence-window child metadata | C0 구조를 유지하면서 local context만 보강 가능 | citation recoverability 1.000000 유지 |
| 2 | query-type specific chunk expansion | `place_story`나 `relationship`에만 제한 적용 가능 | 전체 latency와 no-answer regression 없음 |
| 3 | semantic boundary audit | boundary failure가 확인된 hard subset에만 적용 | C0 대비 Recall@5 또는 nDCG@5 유의 개선 |
| 4 | pure semantic chunking | 최후순위 | citation, latency, reproducibility 모두 통과 |

## 포트폴리오 표현

사용 가능한 표현:

- "도서 parser output 특성을 분석해 fixed-size보다 citation 가능한 parent-child 청킹을 기준선으로 채택했다."
- "C0-C6 청킹 후보를 BM25 고정 조건에서 비교했고, C0가 gate와 retrieval metric을 동시에 가장 잘 만족했다."
- "semantic chunking은 미적용했으며, citation recoverability와 실험 기준선 유지 때문에 후순위로 분리했다."

금지 표현:

- "모든 청킹 기법을 비교해 최적 청킹을 찾았다."
- "semantic chunking보다 parent-child가 항상 우수하다."
- "청킹 변경으로 최종 RAG 성능이 개선됐다."
- "locked test 또는 production 성능이 검증됐다."

## Data Mart 관점

`fact_chunking_decision_review`의 grain은 `review_id + variant_id + metric_family + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `review_id` | `HD-CHUNK-DECISION-REVIEW-001` |
| `variant_id` | C0-C6 또는 future targeted candidate |
| `metric_family` | chunk_quality, retrieval, latency, security, citation |
| `primary_metric_value` | 대표 metric 값 |
| `decision` | adopt, reject, defer |
| `claim_boundary` | dev-only, report-only, locked-only |
| `evidence_artifact` | public-safe report path |

금지 필드는 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret이다.

## 외부 감사 의견

현재 청킹 결정은 취업 포트폴리오에 넣을 수 있다. 단, 표현은 "C0-C6 후보 비교 후 C0 기준선 채택"으로 제한해야 한다.

semantic chunking, sentence window, character chunking은 전체 최적화 대상이 아니라 후속 failure-driven experiment 후보로 분리하는 것이 맞다.
