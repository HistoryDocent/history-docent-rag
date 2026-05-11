# Retrieval Ablation Plan

## 목적

이 문서는 HistoryDocent RAG를 실서비스 후보 수준으로 최적화하기 위한 비교 실험 순서를 고정한다.

목표는 특정 기법을 많이 붙이는 것이 아니다.

목표는 서울/한양 관광 도슨트 서비스에서 다음 조건을 동시에 만족하는 조합을 찾는 것이다.

- 근거가 있는 chunk를 높은 확률로 찾는다.
- 장소, 인물, 사건, 제도 맥락을 놓치지 않는다.
- 음성형 짧은 질문과 후속 질문에 대응한다.
- corpus 밖 질문에는 답하지 않는다.
- Solar Pro 3 호출 비용과 지연 시간을 통제한다.
- public repository에 원문, private path, vector index, secret을 노출하지 않는다.

## 현재 기준선

현재 구현된 검색 기준선은 BM25다.

```text
chunking = Heading-aware Parent Chunk + Block-merge Child Chunk
retriever = BM25
eval_dataset = retrieval_eval_seed.jsonl
query_count = 14
Recall@5 = 0.250000
MRR = 0.152778
nDCG@5 = 0.120124
```

이 수치는 성능 개선 주장이 아니다.

이 수치는 이후 Dense, Hybrid, Reranker, Query Rewrite, Solar Pro 3 generation을 같은 평가 harness에서 비교하기 위한 기준선이다.

## 담당자별 판단

| 담당자 | 판단 |
| --- | --- |
| Product Lead | 관광 도슨트 핵심은 `place_story`, `route_context`, `voice_followup`, `no_answer`다. 단순 장소 사실 검색만 높아도 제품 품질은 부족하다. |
| RAG Architect | BM25, Dense, Hybrid, Reranker, Query Rewrite, Generation을 한 번에 섞지 않는다. 한 단계에 하나의 변수를 바꾼다. |
| ML Engineer | Upstage API는 embedding, dense retrieval, reranker에는 사용하지 않는다. Solar Pro 3는 LLM이 필요한 rewrite/HyDE 제한 실험과 generation에만 사용한다. |
| Backend Lead | vector DB는 처음부터 붙이지 않는다. in-memory exact retrieval로 알고리즘 유효성을 확인한 뒤 Qdrant production 후보를 검증한다. |
| Eval Lead | dev/test split 없이 최적화를 주장하지 않는다. seed 14개는 smoke test이며 최종 주장은 최소 105개 평가셋 이후에만 가능하다. |
| Security Reviewer | public artifact에는 원문 chunk, parser text, 전체 vector index, raw eval CSV, private absolute path, API key를 포함하지 않는다. |
| Portfolio Reviewer | 포트폴리오 메시지는 "최고 기법을 사용했다"가 아니라 "실험으로 선택 근거를 만들었다"여야 한다. |

## 실험 원칙

1. 같은 평가셋, 같은 judgment, 같은 metric으로 비교한다.
2. 한 번에 하나의 주요 변수만 바꾼다.
3. dev set으로 고르고 test set으로 최종 확인한다.
4. test set 결과는 최종 보고 전까지 튜닝에 사용하지 않는다.
5. 평균 점수만 보고 개선을 주장하지 않는다.
6. query type별 breakdown과 실패 유형을 반드시 남긴다.
7. latency, memory, index build time, Solar Pro 3 호출 비용을 같이 기록한다.
8. citation은 항상 원문 `NormalizedBlock`으로 backtracking 가능한 chunk만 허용한다.
9. RAPTOR-lite와 GraphRAG-lite는 기본 pipeline이 아니라 특정 query type 실험군이다.

## 평가셋 확장 계획

현재 seed 평가셋은 14개다.

최종 비교 전 목표는 105개다.

| query_type | dev | test | total | 핵심 실패 유형 |
| --- | ---: | ---: | ---: | --- |
| `place_fact` | 10 | 5 | 15 | 장소명은 맞지만 시대/사실이 틀림 |
| `place_story` | 10 | 5 | 15 | 현장 설명으로 부적합하거나 재미가 없음 |
| `relationship` | 10 | 5 | 15 | 인물, 사건, 제도 관계를 놓침 |
| `overview` | 10 | 5 | 15 | 여러 문서의 상위 맥락을 통합하지 못함 |
| `route_context` | 10 | 5 | 15 | 여러 장소를 하나의 동선 설명으로 묶지 못함 |
| `voice_followup` | 10 | 5 | 15 | "여기", "그 사람", "그때" 같은 지시어 복원 실패 |
| `no_answer` | 10 | 5 | 15 | corpus 밖 질문에 억지 답변 생성 |

평가셋 공개 정책:

- public dataset에는 seed/sample만 저장한다.
- full dev/test benchmark는 public repository 밖의 local private storage에 저장한다.
- public report에는 private benchmark의 aggregate metric과 failure summary만 저장한다.
- public dataset에는 query, query_type, public-safe rationale, target id만 저장한다.
- 원문 answer, chunk text, OCR text, parser text는 저장하지 않는다.
- 짧은 원문 인용은 자동 gate만으로 막기 어렵기 때문에 human review에서 paraphrase 여부를 확인한다.
- judgment는 `child_id`, `parent_id`, `doc_id` 순서로 세밀도를 높인다.
- 최종 test set은 `<private retrieval eval test dataset>` alias로 분리하고 public repository에는 commit하지 않는다.

## 실험 데이터 Grain

실험 결과는 나중에 비교표와 포트폴리오 지표로 재사용되어야 한다.

따라서 다음 grain을 고정한다.

| Artifact | Grain | 주요 key |
| --- | --- | --- |
| `RetrievalEvalItem` | 질문 1개 | `query_id`, `query_type`, `language` |
| `ChunkingExperimentRun` | chunk config 1개 | `chunk_config_id`, `chunking_run_id` |
| `RetrievalExperimentRun` | method 1개와 corpus 1개의 실행 | `method`, `dataset_fingerprint`, `corpus_fingerprint`, `top_k` |
| `RetrievalRunResult` | query 1개와 method 1개의 결과 | `run_id`, `query_id`, `method` |
| `GenerationEvalRun` | query 1개와 answer policy 1개의 결과 | `generation_run_id`, `query_id`, `answer_policy_id` |
| `FailureCase` | 실패 사례 1개 | `query_id`, `method`, `failure_type` |

금지:

- 하나의 fact table에 query grain과 run grain을 섞지 않는다.
- public result row에 `search_text`, `context_text`, `raw_text`, `answer_text`를 넣지 않는다.
- private path를 결과 row에 넣지 않고 alias만 사용한다.

## Stage 0. 평가 Harness 고정

목적:

BM25, Dense, Hybrid, Reranker, Query Rewrite를 같은 방식으로 평가할 수 있게 한다.

입력:

- `<private parent_child_chunks report>`
- `evals/datasets/retrieval_eval_seed.jsonl`
- 이후 확장될 `<private retrieval eval dev dataset>`
- 이후 확장될 `<private retrieval eval test dataset>`

metric:

- `Recall@1`
- `Recall@3`
- `Recall@5`
- `MRR`
- `nDCG@5`
- `latency_p50_ms`
- `latency_p95_ms`
- `abstain_with_candidate_count`
- query type별 breakdown

통과 기준:

```text
same_dataset = true
same_corpus = true
same_top_k = true
dataset_fingerprint exists
corpus_fingerprint exists
method_config_fingerprint exists
public_raw_text_leakage_count = 0
private_path_leakage_count = 0
secret_like_leakage_count = 0
```

## Stage 1. Chunking Ablation

목적:

retriever를 바꾸기 전에 검색 단위가 적절한지 검증한다.

초기 비교는 BM25로만 진행한다.

| ID | 방식 | 설정 | 가설 |
| --- | --- | --- | --- |
| `C0` | current parent-child | target 700, max 1100, overlap block 1 | 현재 기준선 |
| `C1` | smaller child | target 450, max 800, overlap block 1 | 세밀한 사실 질문의 precision 개선 |
| `C2` | larger child | target 900, max 1400, overlap block 1 | story/overview 질문의 recall 개선 |
| `C3` | micro-parent merge | 짧은 parent 병합 후 C0 child | micro parent로 인한 context fragmentation 완화 |
| `C4` | overlap 0 | target 700, max 1100, overlap block 0 | 중복 감소와 latency 개선 |
| `C5` | overlap 2 | target 700, max 1100, overlap block 2 | boundary context 손실 완화 |
| `C6` | fixed-size block baseline | heading parent/context 비활성화 | 구조 보존 청킹 대비 naive block baseline 검증 |

측정:

- retrieval metric
- child length distribution
- parent length distribution
- citation recoverability
- duplicate child text hash
- replacement char child rate
- micro parent count

선택 기준:

```text
hard gate 통과
Recall@5 또는 MRR 개선
no_answer 악화 없음
citation_recoverability >= 0.99
child_length_p95 <= configured max
```

실행 결과:

| ID | gate | Recall@5 | MRR | nDCG@5 | latency_p95_ms | 판단 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `C0` | PASS | 0.566667 | 0.471389 | 0.344203 | 7.504000 | 유지 |
| `C1` | PASS | 0.083333 | 0.044444 | 0.026033 | 10.086600 | 개선 조건 미충족 |
| `C2` | PASS | 0.533333 | 0.446389 | 0.272112 | 6.141000 | 개선 조건 미충족 |
| `C3` | PASS | 0.533333 | 0.453333 | 0.330712 | 6.343100 | 개선 조건 미충족 |
| `C4` | FAIL | 0.483333 | 0.384722 | 0.241390 | 6.154800 | `short_standalone_child` gate 실패 |
| `C5` | PASS | 0.533333 | 0.368611 | 0.247787 | 8.998300 | 개선 조건 미충족 |
| `C6` | FAIL | 0.316667 | 0.254167 | 0.145937 | 5.483900 | `short_standalone_child` gate 실패 |

결론:

`selected_variant_id=C0`으로 유지한다. C3 micro-parent merge는 parent 수와 duplicate hash는 줄였지만 Recall@5/MRR 개선 조건을 충족하지 못했다. C4/C6은 짧은 독립 child가 발생해 gate를 통과하지 못했다. 이 결과는 private dev split에서 BM25만 사용한 청킹 단위 선택 근거이며, locked test split은 사용하지 않았다. 성능 개선 주장이 아니라 Dense/Hybrid 비교를 위한 검색 단위 고정이다.

## Stage 2. Dense Embedding Baseline

목적:

BM25가 약한 semantic query, 영어 query, route query를 보완할 수 있는지 확인한다.

Upstage API는 사용하지 않는다.

| ID | embedding | 검색 방식 | 비고 |
| --- | --- | --- | --- |
| `D0` | `sklearn-tfidf-svd-v1` | cosine exact search | dependency-free dense baseline, CI와 dev 실험용 |
| `E1` | `BAAI/bge-m3` dense | cosine exact search | multilingual, dense/sparse/multi-vector 확장 가능 |
| `E2` | `intfloat/multilingual-e5-large` | cosine exact search | multilingual dense 비교군 |
| `E3` | `intfloat/multilingual-e5-large-instruct` | cosine exact search | query instruction 효과 비교 |

초기 구현 원칙:

- vector DB 없이 in-memory exact cosine으로 시작한다.
- embedding cache는 private artifact로 저장한다.
- public repo에는 embedding vector와 전체 index를 올리지 않는다.
- model name, dimension, pooling, normalization, device, batch size를 method config에 저장한다.

선택 기준:

```text
BM25 대비 Recall@5 +5%p 이상 또는 특정 query type에서 명확한 개선
latency_p95 허용 범위
embedding cache 재현 가능
public artifact leakage 0
```

실행 결과:

| ID | encoder | Recall@5 | MRR | nDCG@5 | latency_p95_ms | BM25 대비 Recall@5 delta | 판단 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `BM25` | regex-ko-en-num/v1 | 0.566667 | 0.471389 | 0.344203 | 5.967000 | 0.000000 | 기준선 |
| `D0` | sklearn-tfidf-svd-v1 | 0.350000 | 0.261111 | 0.220955 | 15.437200 | -0.216667 | 개선 후보 아님 |

결론:

`D0` dense baseline은 BM25보다 낮다. 이 결과는 neural embedding 모델 결과가 아니므로 BGE-M3 또는 multilingual-E5의 성능을 부정하는 근거로 사용하지 않는다. 현재 단계에서는 dense harness, cache, public-safe report를 고정한 것이 산출물이다.

### Neural embedding 실행 결과

private dev split 70개에서 sentence-transformers backend를 사용해 neural dense 후보를 비교했다.

| ID | encoder | Recall@1 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | BM25 대비 Recall@5 delta | 판단 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `BM25` | regex-ko-en-num/v1 | 0.400000 | 0.566667 | 0.471389 | 0.344203 | 6.323600 | 0.000000 | 기준선 |
| `D0` | sklearn-tfidf-svd-v1 | 0.200000 | 0.350000 | 0.261111 | 0.220955 | 18.228000 | -0.216667 | 개선 후보 아님 |
| `E1` | BAAI/bge-m3 | 0.566667 | 0.800000 | 0.658611 | 0.567476 | 57.088400 | +0.233333 | 품질 상한 후보, latency 비용 큼 |
| `E2` | intfloat/multilingual-e5-small | 0.633333 | 0.733333 | 0.675556 | 0.533797 | 15.717100 | +0.166666 | 1차 실서비스 후보 |
| `E3` | paraphrase-multilingual-MiniLM-L12-v2 | 0.050000 | 0.100000 | 0.065000 | 0.039444 | 15.559500 | -0.466667 | 개선 후보 아님 |

결론:

`multilingual-e5-small`은 BM25 대비 Recall@1, Recall@5, MRR, nDCG@5가 모두 높고 BGE-M3보다 latency가 낮다. 다음 Hybrid/Reranker 비교의 1차 dense 후보는 `multilingual-e5-small`이다. BGE-M3는 Recall@5와 nDCG@5가 가장 높으므로 품질 상한 후보로 유지하되 CPU latency가 크다. 이 결과는 dev-only 후보 선별이며 locked test와 generation 평가 전에는 최종 개선 주장으로 사용하지 않는다.

## Stage 2.5. BM25-Dense Complementarity Analysis

목적:

Dense D0가 BM25를 대체할 수 있는지가 아니라 BM25 실패 query를 보완할 수 있는지 확인한다.

실행 결과:

| metric | value |
| --- | ---: |
| retrieve_query_count | 60 |
| bm25_only_hit_count | 15 |
| dense_only_hit_count | 2 |
| both_hit_count | 19 |
| both_fail_count | 24 |
| bm25_recall_at_5 | 0.566667 |
| dense_recall_at_5 | 0.350000 |
| oracle_union_recall_at_5 | 0.600000 |
| oracle_union_delta_vs_bm25 | 0.033333 |

결론:

Dense D0 단독은 BM25보다 낮지만 BM25가 놓친 query 2개를 보완했다. oracle union은 실제 retriever가 아니라 상한이므로 성능 개선 주장은 금지한다. 다만 Hybrid RRF/Weighted 실험을 진행할 근거는 있다.

## Stage 3. Hybrid Retrieval

목적:

lexical precision과 dense semantic recall을 결합한다.

| ID | 방식 | 설정 | 가설 |
| --- | --- | --- | --- |
| `H1` | BM25 + Dense RRF | candidate_k 50, top_k 5 | score scale 차이 없이 안정적 결합 |
| `H2` | BM25 + Dense Weighted | alpha 0.3 | BM25 가중 |
| `H3` | BM25 + Dense Weighted | alpha 0.5 | 균형 |
| `H4` | BM25 + Dense Weighted | alpha 0.7 | Dense 가중 |
| `H5` | BGE-M3 sparse + dense | Qdrant 단계에서 검증 | unified sparse/dense 후보 |

선택 기준:

```text
BM25와 Dense 단독보다 Recall@5 또는 MRR 개선
query type별 악화가 설명 가능
no_answer false positive 증가 없음
latency_p95 +20% 이내
```

실행 결과:

| ID | run_label | Recall@1 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | BM25 대비 Recall@5 delta | BM25 대비 MRR delta | 판단 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `BM25` | `bm25` | 0.400000 | 0.566667 | 0.471389 | 0.344203 | 5.697700 | 0.000000 | 0.000000 | 기준선 유지 |
| `D0` | `dense` | 0.200000 | 0.350000 | 0.261111 | 0.220955 | 19.703900 | -0.216667 | -0.210278 | 개선 후보 아님 |
| `H1` | `hybrid_rrf` | 0.266667 | 0.516667 | 0.359722 | 0.282463 | 22.643800 | -0.050000 | -0.111667 | 개선 후보 아님 |
| `H2` | `hybrid_weighted_alpha_0_3` | 0.416667 | 0.566667 | 0.479722 | 0.347259 | 23.038700 | 0.000000 | +0.008333 | latency gate 실패 |
| `H3` | `hybrid_weighted_alpha_0_5` | 0.350000 | 0.533333 | 0.427778 | 0.323149 | 25.907100 | -0.033334 | -0.043611 | 개선 후보 아님 |
| `H4` | `hybrid_weighted_alpha_0_7` | 0.300000 | 0.450000 | 0.354722 | 0.285376 | 22.609100 | -0.116667 | -0.116667 | 개선 후보 아님 |

결론:

`hybrid_weighted_alpha_0_3`은 `Recall@1`, `MRR`, `nDCG@5`를 소폭 개선했지만 `Recall@5`는 BM25와 동일하고 latency가 BM25 대비 크게 증가했다. 선택 기준의 `latency_p95 +20% 이내`를 통과하지 못했으므로 production 후보로 채택하지 않는다. 이 Hybrid 실험은 D0 dense 기반이므로 neural dense 결과를 반영하지 않는다.

### Neural dense Hybrid 실행 결과

private dev split 70개에서 E5-small과 BGE-M3를 dense leg로 사용해 Hybrid RRF/Weighted를 비교했다.

| ID | run_label | dense leg | fusion | Recall@1 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | 판단 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `BM25` | `bm25` | none | lexical | 0.400000 | 0.566667 | 0.471389 | 0.344203 | 6.769400 | 기준선 |
| `E2` | `dense_multilingual_e5_small` | `intfloat/multilingual-e5-small` | dense only | 0.633333 | 0.733333 | 0.675556 | 0.533797 | 16.606300 | 1차 기본 검색 후보 |
| `E1` | `dense_bge_m3` | `BAAI/bge-m3` | dense only | 0.566667 | 0.800000 | 0.658611 | 0.567476 | 61.248100 | 품질 상한 후보, latency 큼 |
| `H6` | `hybrid_rrf_e5_small` | `intfloat/multilingual-e5-small` | RRF | 0.583333 | 0.700000 | 0.629167 | 0.475437 | 29.268200 | E5 dense 단독보다 낮음 |
| `H7` | `hybrid_weighted_e5_small_alpha_0_3` | `intfloat/multilingual-e5-small` | weighted alpha 0.3 | 0.450000 | 0.666667 | 0.538611 | 0.414977 | 28.607700 | E5 dense 단독보다 낮음 |
| `H8` | `hybrid_weighted_e5_small_alpha_0_5` | `intfloat/multilingual-e5-small` | weighted alpha 0.5 | 0.566667 | 0.783333 | 0.655278 | 0.509310 | 27.547000 | recall-oriented reranker 후보 |
| `H9` | `hybrid_rrf_bge_m3` | `BAAI/bge-m3` | RRF | 0.533333 | 0.733333 | 0.613889 | 0.462699 | 72.581100 | BGE dense 단독보다 낮음 |
| `H10` | `hybrid_weighted_bge_m3_alpha_0_3` | `BAAI/bge-m3` | weighted alpha 0.3 | 0.466667 | 0.666667 | 0.545833 | 0.415055 | 74.303700 | BGE dense 단독보다 낮음 |

결론:

Neural dense 기반 Hybrid는 BM25보다 높지만, 대부분의 핵심 지표에서 대응하는 dense 단독보다 낮다. `hybrid_weighted_e5_small_alpha_0_5`만 E5-small dense 단독보다 `Recall@5`가 높지만 `MRR`, `nDCG@5`, latency는 나쁘다. 따라서 기본 검색 후보는 `dense_multilingual_e5_small`로 유지하고, `hybrid_weighted_e5_small_alpha_0_5`는 reranker가 top-rank 품질을 회복할 수 있는지 확인하는 recall-oriented 후보로만 사용한다. `dense_bge_m3`는 품질 상한 후보지만 CPU latency가 커서 실서비스 기본 후보로 바로 채택하지 않는다.

## Stage 4. Reranker

목적:

candidate recall은 좋은데 top rank가 약한 경우 reranker가 실제 generation 품질을 개선하는지 확인한다.

상위 retriever 2개에만 적용한다.

| ID | 방식 | 설정 |
| --- | --- | --- |
| `K0` | reranker 없음 | retriever top 5 |
| `K1` | `BAAI/bge-reranker-v2-m3` | retrieve top 20 -> rerank top 5 |
| `K2` | `BAAI/bge-reranker-v2-m3` | retrieve top 30 -> rerank top 5 |
| `K3` | `BAAI/bge-reranker-v2-m3` | retrieve top 50 -> rerank top 5 |

metric:

- `MRR`
- `nDCG@5`
- `latency_p95_ms`
- `reranker_candidate_count`
- `reranker_empty_result_count`

선택 기준:

```text
nDCG@5 또는 MRR 개선
Recall@5 유지
latency_p95 증가가 제품 SLO 안에 있음
generation unsupported_claim_rate 하락
```

실행 결과 v1:

private dev split 70개에서 E5-small dense 단독, E5-small weighted Hybrid, E5-small dense + BGE reranker top20을 비교했다. top30/top50과 Hybrid reranker는 코드 실험군으로 구현했지만 CPU CrossEncoder 비용이 커서 v1 public report에는 포함하지 않았다.

| ID | run_label | 방식 | Recall@1 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | 판단 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `BM25` | `bm25` | lexical baseline | 0.400000 | 0.566667 | 0.471389 | 0.344203 | 7.983400 | 기준선 |
| `E2` | `dense_multilingual_e5_small` | dense only | 0.633333 | 0.733333 | 0.675556 | 0.533797 | 17.921900 | 기본 검색 후보 유지 |
| `H8` | `hybrid_weighted_e5_small_alpha_0_5` | weighted Hybrid | 0.566667 | 0.783333 | 0.655278 | 0.509310 | 30.737600 | recall 후보, top-rank 약함 |
| `K1` | `dense_multilingual_e5_small_rerank_bge_m3_top20` | dense top20 -> BGE rerank top5 | 0.716667 | 0.833333 | 0.761667 | 0.635787 | 13140.690300 | 품질 최고, CPU latency로 기본 후보 탈락 |

결론:

`BAAI/bge-reranker-v2-m3`는 top-rank 품질을 확실히 올렸다. 그러나 CPU 기준 `latency_p95_ms`가 약 13.1초로 실시간 관광 도슨트 API의 기본 검색 경로로는 부적합하다. 현재 실서비스 기본 후보는 `dense_multilingual_e5_small`로 유지한다. reranker는 GPU 배포, 더 작은 reranker, hard query 전용 라우팅, 오프라인 평가용 품질 상한 후보로만 남긴다.

## Stage 5. Query Rewrite와 Place Expansion

목적:

음성형 질문, 후속 질문, 장소 alias, 영어/혼합 질문을 검색 가능한 query로 바꾼다.

비교 순서:

| ID | 방식 | Solar Pro 3 사용 | 적용 query type |
| --- | --- | --- | --- |
| `Q0` | rewrite 없음 | no | 전체 |
| `Q1` | deterministic place alias expansion | no | `place_fact`, `place_story`, `route_context` |
| `Q2` | conversation context resolver | no | `voice_followup` |
| `Q3` | Rewrite-Retrieve-Read style LLM rewrite | yes | 실패 query subset |
| `Q4` | HyDE | yes | `overview`, `relationship` subset |

Solar Pro 3 사용 원칙:

- 기본 검색 최적화에는 사용하지 않는다.
- LLM rewrite와 HyDE는 비용과 지연을 기록하는 실험군으로만 사용한다.
- rewrite 결과는 JSON schema로 검증한다.
- corpus 밖 질문을 검색 가능한 질문으로 억지 변환하면 실패로 기록한다.

metric:

- `rewrite_success_rate`
- `rewrite_invalid_json_rate`
- `voice_followup Recall@5`
- `place_relevance`
- `no_answer false_positive_rate`
- `rewrite_latency_p95_ms`
- `solar_call_count`
- `estimated_cost`

통과 기준:

```text
rewrite_invalid_json_rate = 0
voice_followup Recall@5 개선
no_answer 악화 없음
Solar Pro 3 비용 설명 가능
```

## Stage 6. Evidence Packing

목적:

검색된 evidence를 Solar Pro 3가 잘 사용할 수 있는 순서와 양으로 구성한다.

`Lost in the Middle` 관찰을 반영해 긴 context를 무작정 넣지 않는다.

| ID | 방식 | 설명 |
| --- | --- | --- |
| `P0` | rank order | retriever rank 순서 그대로 |
| `P1` | best evidence first | reranker 상위 evidence를 앞에 배치 |
| `P2` | parent expansion | child hit 주변 parent context 확장 |
| `P3` | MMR diversity | 중복 chunk를 줄이고 장소/사건 다양성 확보 |
| `P4` | compressed evidence | 후순위. 원문 citation backtracking 가능할 때만 |

통과 기준:

```text
context_token_budget 준수
citation_recoverability 유지
unsupported_claim_rate 감소
Correct-with-Evidence 개선
```

## Stage 7. Solar Pro 3 Generation

목적:

최종 사용자가 듣고 읽을 답변 품질을 평가한다.

Solar Pro 3는 이 단계에서만 기본 provider로 사용한다.

answer contract:

```text
answer
spoken_answer
citations
evidence_ids
place_ids
abstained
unsupported_claim_risk
```

metric:

- `Correct-with-Evidence`
- `citation_precision`
- `citation_recall`
- `place_relevance`
- `docent_usefulness`
- `spoken_answer_naturalness`
- `unsupported_claim_rate`
- `abstention_accuracy`
- `latency_p95_ms`
- `solar_call_count`
- `estimated_cost`

통과 기준:

```text
Correct-with-Evidence +3%p 이상
unsupported_claim_rate 감소
no_answer abstention 개선
citation_precision 하락 없음
latency/cost 악화 설명 포함
```

## Stage 8. Advanced RAG Experiments

Advanced RAG는 기본 pipeline 후보가 아니다.

기본 Hybrid + Reranker + Query Rewrite + Citation RAG가 만들어진 뒤 특정 실패 유형에서만 비교한다.

| ID | 기법 | 적용 query type | 검증 가설 |
| --- | --- | --- | --- |
| `A1` | RAPTOR-lite | `overview`, `place_story`, `route_context` | 상위 요약 node가 넓은 맥락 질문을 개선하는가 |
| `A2` | GraphRAG-lite | `relationship`, `overview` | 장소, 인물, 사건 관계 질문을 개선하는가 |
| `A3` | Self-check / CRAG style guard | `no_answer`, low confidence query | 검색 실패 시 답변 거절이 개선되는가 |
| `A4` | ColBERT style late interaction | hard retrieval subset | top rank 품질을 reranker보다 효율적으로 개선하는가 |

제약:

- RAPTOR summary와 graph community summary는 최종 citation이 될 수 없다.
- 최종 citation은 항상 원문 `NormalizedBlock`에서 복구한다.
- entity extraction 오류율과 citation backtracking 실패율을 별도로 기록한다.
- Solar Pro 3를 대량 graph build에 사용하지 않는다. 필요하면 small subset 실험으로 제한한다.

## 실서비스 SLO 후보

1차 backend 목표:

| 항목 | 목표 |
| --- | ---: |
| retrieval only `latency_p95_ms` | 1000 이하 |
| retrieval + reranker `latency_p95_ms` | 2500 이하 |
| `/chat` with Solar Pro 3 `latency_p95_ms` | 8000 이하 |
| no-answer abstention accuracy | 0.80 이상 |
| unsupported claim rate | 0.05 이하 |
| public leakage count | 0 |
| API secret in repo | 0 |

SLO는 최종 성능 주장이 아니라 제품 후보의 운영 기준이다.

## 개선 주장 기준

개선 주장은 다음 조건을 모두 만족해야 한다.

```text
paired comparison
bootstrap 10,000회
95% confidence interval
query type별 breakdown
latency/cost delta
failure analysis
public leakage gate pass
```

허용:

```text
Retrieval Recall@5 +5%p 이상
또는 Correct-with-Evidence +3%p 이상
그리고 95% CI가 0을 넘음
```

금지:

```text
dev set에서만 좋아짐
test set에서 재현 안 됨
no_answer가 악화됨
latency/cost 악화 설명 없음
특정 query type 결과를 전체 개선처럼 표현
```

## 논문과 구현 매핑

| 근거 | 적용 위치 | 구현 판단 |
| --- | --- | --- |
| [RAG 2020](https://arxiv.org/abs/2005.11401) | 기본 retrieval + generation | 기본 구조 근거 |
| [BGE-M3](https://arxiv.org/abs/2402.03216) | Dense/Sparse/Multi-vector candidate | 우선 구현 후보 |
| [multilingual-E5](https://arxiv.org/abs/2402.05672) | Dense embedding candidate | 비교 후보 |
| [ColBERT](https://arxiv.org/abs/2004.12832) | Late interaction | 후순위 hard subset 실험 |
| [HyDE](https://arxiv.org/abs/2212.10496) | Query expansion | Solar Pro 3 비용 실험군 |
| [Rewrite-Retrieve-Read](https://arxiv.org/abs/2305.14283) | Query rewrite | voice/place query 실험 근거 |
| [Lost in the Middle](https://arxiv.org/abs/2307.03172) | Evidence packing | context 순서 실험 근거 |
| [Self-RAG](https://arxiv.org/abs/2310.11511) | self-check | 후순위 guard 실험 |
| [CRAG](https://arxiv.org/abs/2401.15884) | corrective retrieval | low confidence query guard |
| [RAPTOR](https://arxiv.org/abs/2401.18059) | hierarchical summary retrieval | overview/story subset |
| [GraphRAG](https://arxiv.org/abs/2404.16130) | graph/community summary | relationship/global subset |
| [ARES](https://arxiv.org/abs/2311.09476) | RAG evaluation dimensions | context relevance, answer faithfulness, answer relevance |
| [RAGChecker](https://arxiv.org/abs/2408.08067) | fine-grained diagnosis | retrieval/generation 분리 평가 |
| [mmRAG](https://arxiv.org/abs/2505.11180) | modular benchmark 관점 | text/table/graph component 분리 평가 참고 |
| [Agentic RAG Survey](https://arxiv.org/abs/2501.09136) | agentic extension | 1차 범위 제외, 후순위 참고 |
| [Qdrant Hybrid Queries](https://qdrant.tech/documentation/concepts/hybrid-queries/) | production vector DB 후보 | in-memory 검증 후 적용 |

## 작업 순서

다음 구현 순서는 이 문서를 따른다.

1. 평가셋 확장 schema와 dev/test split 문서화
2. private dev 평가셋 70개 작성, target resolvability 검증, reviewed 승격
3. private test 평가셋 35개 locked 작성과 target resolvability 검증
4. chunking config ablation runner 완료
5. Dense retrieval baseline v1 완료
6. Hybrid RRF/Weighted retrieval 완료
7. neural embedding model 비교 완료
8. neural dense 기반 Hybrid/Reranker 비교
8. reranker comparison
9. place-aware deterministic query expansion
10. Solar Pro 3 answer contract
11. generation eval harness
12. Qdrant production candidate
13. RAPTOR-lite
14. GraphRAG-lite
15. final ablation report

## 포트폴리오 메시지

현재 면접에서 주장할 수 있는 문장:

```text
서울/한양 역사 도슨트 RAG를 재설계하면서 원본 데이터 공개 제한을 지키기 위해 public/private benchmark 경계를 먼저 고정했고, BM25 baseline과 retrieval evaluation harness, private dev 70개 reviewed 평가셋, private test 35개 locked 평가셋까지 구축했습니다. BM25 dev-only chunking ablation v2에서는 C0-C6을 비교했고, smaller/larger child, micro-parent merge, overlap 0/2, fixed-size block baseline 모두 C0를 넘지 못해 현재 parent-child chunking을 유지했습니다. 이후 Dense, Hybrid, Reranker, Query Rewrite, Generation을 같은 평가셋과 같은 metric으로 단계별 비교할 계획입니다.
```

최종 ablation 완료 후에만 주장할 수 있는 문장:

```text
RAG 성능을 단일 모델 교체로 주장하지 않고, chunking, dense embedding, hybrid retrieval, reranking, query rewrite, evidence packing, generation을 단계별 ablation으로 분리해 평가했습니다. 최종 선택은 Recall@k뿐 아니라 citation precision, unsupported claim rate, no-answer abstention, latency, cost를 함께 기준으로 삼았습니다.
```

아직 주장하면 안 되는 문장:

```text
GraphRAG를 적용해 성능을 개선했다.
RAPTOR가 기존 RAG보다 좋다.
Solar Pro 3로 모든 평가를 자동화했다.
최적 RAG 조합을 찾았다.
```
