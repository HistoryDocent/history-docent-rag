# ColBERT-style Late Interaction Hard Subset

## 결론

`HD-COLBERT-001C`의 결정은 `reject_default_keep_as_experiment_result`이다.

이번 작업은 ColBERT-style late interaction의 dev hard subset 검색 비교다. locked test, Solar Pro 3 generation, production route 적용은 수행하지 않았다.

## 핵심 비교

| 항목 | baseline | best candidate |
| --- | ---: | ---: |
| Recall@5 | 0.809524 | 0.809524 |
| MRR | 0.715873 | 0.738095 |
| nDCG@5 | 0.567386 | 0.545716 |
| latency_p95_ms | 15.483000 | 164.956000 |
| cuda_memory_peak_mb | 0.000000 | 936.381836 |

## 외부 감사 의견

dev hard subset 결과만으로 기존 final ablation 결론을 뒤집으면 안 된다. quality gain, latency, CUDA memory를 같이 봐야 하며, 기본 route 채택은 별도 gate가 필요하다.

## 다음 작업

결과가 후보 유지에 충분하면 larger dev 또는 locked 전 readiness를 별도로 연다. 결과가 부족하면 ColBERT-style 후보는 reranker latency 대안 실험으로만 보관한다.
