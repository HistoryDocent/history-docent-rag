# Solar Pro 3 Live Generation Smoke Runbook

## 목적

private retrieval 결과를 Solar Pro 3 provider에 실제로 전달해 다음 경계를 검증한다.

- retrieval-backed evidence pack이 `CitationDraftRequest`로 변환되는지 확인한다.
- Solar Pro 3 structured output이 `CitationRagDraft` schema를 만족하는지 확인한다.
- draft가 `CitationRagAnswerAssembler`를 거쳐 citation contract로 조립되는지 확인한다.
- generation eval harness가 live call count, citation metric, no-answer abstention을 public-safe report로 남기는지 확인한다.

이 smoke는 최종 답변 품질 개선 주장이 아니다. 작은 private dev subset으로 live 연결과 공개 산출물 경계만 검증한다.

## 실행 전 조건

| 항목 | 기준 |
| --- | --- |
| API key | `UPSTAGE_API_KEY` 환경변수에만 설정 |
| private dataset | `<private retrieval eval dataset: retrieval_eval_dev.jsonl>` |
| private chunks | `<private parent_child_chunks report>` |
| retrieval backend | `dense_multilingual_e5_small_voice_rewrite` |
| packing policy | `P0_rank_order` |
| answerable smoke count | 기본 2 |
| no-answer smoke count | 기본 1 |

API key, raw prompt, raw evidence, raw answer는 report/result row에 저장하지 않는다.

## 실행 명령

```powershell
python -m pipelines.run_solar_live_generation_smoke
```

필요하면 smoke 크기를 줄인다.

```powershell
python -m pipelines.run_solar_live_generation_smoke --answerable-limit 1 --no-answer-limit 1
```

## 산출물

| 산출물 | 공개 여부 | 설명 |
| --- | --- | --- |
| `evals/reports/solar_live_generation_smoke_report.md` | public 가능 | aggregate metric과 public-safe gate만 포함 |
| `private_data/evals/results/solar_live_generation_smoke_results.jsonl` | private | raw answer/evidence 없는 평가 row |

## 통과 기준

- `solar_call_count > 0`
- `answerable_count > 0`
- `missing_citation_count = 0`
- `unsupported_high_count = 0`
- `public_raw_text_leakage_count = 0`
- `private_path_leakage_count = 0`
- `secret_like_leakage_count = 0`
- `forbidden_result_field_count = 0`

`Correct-with-Evidence`, `citation_precision`, `citation_recall`, `unsupported_claim_rate`는 기록하되 이 smoke만으로 개선을 주장하지 않는다.

## 해석 기준

PASS이면 live provider 연결과 평가 산출물 경계가 동작한다는 뜻이다.

FAIL이면 다음 순서로 분리한다.

1. API key/config 오류
2. Solar response schema 오류
3. retrieval evidence text 누락
4. citation assembler contract 오류
5. public output leakage 오류

정식 성능 비교는 같은 harness를 사용하되 locked test split과 paired comparison, bootstrap confidence interval까지 포함해야 한다.
