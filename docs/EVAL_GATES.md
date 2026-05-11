# Eval Gates

## 원칙

성능 개선은 평균 점수만으로 주장하지 않는다.

비교 실험의 실행 순서와 후보군은 [Retrieval Ablation Plan](RETRIEVAL_ABLATION_PLAN.md)을 기준으로 한다.

필수 조건:

- query 단위 paired comparison
- bootstrap 10,000회
- 95% confidence interval
- query type별 breakdown
- latency/cost delta
- external_human 또는 stress_set에서 유지

## Query Types

| Type | 설명 |
| --- | --- |
| `place_fact` | 특정 장소의 역사 사실 |
| `place_story` | 관광객에게 들려줄 짧은 이야기 |
| `relationship` | 인물, 사건, 제도 관계 |
| `overview` | 한양 또는 조선 전기 흐름 설명 |
| `route_context` | 현재 장소와 주변 장소 연결 |
| `voice_followup` | “여기”, “그 사람”, “그때” 같은 후속 질문 |
| `no_answer` | 근거 없는 질문 |

## Parser Gate

정량 지표:

- `document_missing_count`
- `duplicate_doc_id_count`
- `required_field_null_count`
- `page_global_reverse_count`
- `base64_remaining_count`
- `private_path_leakage_count`
- `ocr_noise_block_count`

통과 기준:

```text
document_missing_count = 0
duplicate_doc_id_count = 0
required_field_null_count = 0
page_global_reverse_count = 0
base64_remaining_count = 0
private_path_leakage_count = 0
```

정성 검수:

- 표지
- 목차
- 장 시작
- 일반 본문
- 표/그림 포함 페이지
- OCR 깨짐 페이지
- 배치 경계 페이지

## Chunking Gate

정량 지표:

- `child_chunk_count`
- `parent_chunk_count`
- `orphan_child_count`
- `invalid_page_range_count`
- `unknown_element_id_count`
- `duplicate_chunk_id_count`
- `citation_recoverability`

통과 기준:

```text
orphan_child_count = 0
invalid_page_range_count = 0
unknown_element_id_count = 0
duplicate_chunk_id_count = 0
citation_recoverability >= 0.99
```

## Retrieval Gate

비교군:

- BM25
- Dense
- Hybrid Weighted
- Hybrid RRF
- Reranker applied top-k

정량 지표:

- `Recall@1`
- `Recall@3`
- `Recall@5`
- `MRR`
- `nDCG@5`
- `latency_p50`
- `latency_p95`

통과 기준:

- 모든 비교군이 같은 평가셋에서 실행된다.
- query type별 breakdown이 존재한다.
- 실패 유형이 분류된다.
- latency가 같이 보고된다.
- `dataset_fingerprint`, `corpus_fingerprint`, `method_config_fingerprint`가 존재한다.
- dev set에서 선택한 조합을 test set에서 별도로 확인한다.

## Ablation Gate

비교 순서:

1. Chunking
2. Dense embedding
3. Hybrid retrieval
4. Reranker
5. Query rewrite
6. Evidence packing
7. Solar Pro 3 generation
8. RAPTOR-lite / GraphRAG-lite

통과 기준:

```text
one_major_variable_changed = true
same_eval_dataset = true
same_judgment = true
same_metric_definition = true
query_type_breakdown_exists = true
failure_analysis_exists = true
public_leakage_count = 0
```

금지:

```text
chunking, embedding, reranker를 동시에 바꾼 결과를 단일 개선으로 주장
dev set에서 고른 조합을 test set 없이 최종 성능으로 주장
Solar Pro 3 rewrite 비용을 숨김
GraphRAG/RAPTOR 결과를 전체 query type 개선으로 포장
```

## Query Rewrite Gate

비교군:

- Dense 기본 후보
- Dense + 전체 place rewrite
- Dense + voice-only rewrite
- 후속 단계에서 Hybrid + query rewrite

정량 지표:

- `voice_followup Recall@5`
- `place_fact Recall@5`
- `place_story Recall@5`
- `route_context Recall@5`
- `rewrite_success_rate`
- `rewrite_invalid_json_rate`
- `query_rewrite_solar_call_count`
- `latency_p95_ms`

통과 기준:

```text
rewrite_invalid_json_rate = 0
voice_followup 유형 개선
비대상 query type 악화 없음
근거 없는 확장 질의 생성 없음
```

## Generation Gate

정량 지표:

- `Correct-with-Evidence`
- `faithfulness`
- `citation_precision`
- `citation_recall`
- `place_relevance`
- `docent_usefulness`
- `unsupported_claim_rate`
- `abstention_accuracy`

통과 기준:

- 답변이 맞다.
- citation이 답변을 지지한다.
- 장소 맥락이 맞다.
- 핵심 unsupported claim이 없다.
- no-answer 질문에서 환각하지 않는다.

## Advanced RAG Gate

RAPTOR-lite 성공 기준:

```text
overview 유형 Correct-with-Evidence +3%p 이상
citation_precision 하락 없음
p95 latency +20% 이내
```

GraphRAG-lite 성공 기준:

```text
relationship 유형 Correct-with-Evidence +3%p 이상
unsupported_claim_rate 증가 없음
entity resolution 오류율 <= 5%
citation backtracking 성공률 >= 95%
```

## 개선 주장 허용 기준

```text
Retrieval Recall@5 +5%p 이상
Correct-with-Evidence +3%p 이상
citation_precision +3%p 이상
p95 latency +20% 이내
cost +20% 이내
95% CI가 0을 지나지 않음
```

## 개선 주장 금지 기준

```text
dev_synthetic에서만 좋아짐
external_human에서 효과 없음
CI가 0을 지남
latency/cost 악화 설명 없음
특정 query type만 좋아지고 전체 결론처럼 포장
```
