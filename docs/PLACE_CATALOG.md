# Place Catalog

## 목적

place catalog는 서울/한양 관광 도슨트 RAG의 장소 기준 dimension이다.

검색 성능을 직접 올리는 모델이 아니라, 다음 기능의 기준 데이터로 사용한다.

- place-aware query rewrite
- route-aware retrieval
- 장소별 failure analysis
- retrieval 평가셋의 query type breakdown
- 최종 answer contract의 place relevance 평가

## Grain

| 계약 | Grain | 설명 |
| --- | --- | --- |
| `PlaceCatalog` | catalog version 1개 | 공개 가능한 장소 seed 묶음 |
| `Place` | 관광 장소 1개 | 검색과 평가에서 사용하는 장소 기준 dimension |
| `PlaceAlias` | 장소 별칭 1개 | 한국어, 영어, 한자, 관광 표기 대응 |
| `PlaceRelation` | 장소 간 관계 1개 | 동선, 근접성, 역사 맥락, 조망 관계 |
| `PlaceCatalogReport` | catalog validation run 1회 | 정량/정성 gate 결과 |

하나의 `Place`는 원문 문장이나 요약문을 저장하지 않는다.

## Seed Scope

초기 seed는 서울 관광에서 질문 가능성이 높은 장소를 우선한다.

| place_id | canonical_name | category |
| --- | --- | --- |
| `gyeongbokgung` | 경복궁 | palace |
| `gwanghwamun` | 광화문 | gate_square |
| `jongmyo` | 종묘 | shrine |
| `changdeokgung` | 창덕궁 | palace |
| `bukchon` | 북촌 | district |
| `hanyangdoseong` | 한양도성 | city_wall |
| `namsan` | 남산 | mountain |
| `deoksugung` | 덕수궁 | palace |
| `jongno` | 종로 | route_anchor |

## Schema

`Place` 필수 필드:

| field | 목적 |
| --- | --- |
| `place_id` | 코드와 평가에서 사용하는 stable key |
| `canonical_name` | 대표 한국어 장소명 |
| `category` | 장소 유형 |
| `aliases` | 한국어, 영어, 한자, 관광 표기 |
| `related_place_ids` | catalog 내부 장소 관계 target |
| `relations` | 관계 유형과 간단한 공개용 근거 |
| `tour_context_tags` | route/query 분석용 tag |
| `source_policy` | 공개 seed 작성 정책 |
| `public_allowed` | 공개 가능 여부 |

`PlaceRelation`은 원문 인용이 아니라 public-safe 관계 설명만 저장한다. 최종 citation은 항상 chunk와 `NormalizedBlock`에서 복구한다.

## Public Data Policy

허용:

- 장소 ID
- 대표명과 alias
- 장소 category
- 장소 간 relation ID
- 공개 가능한 짧은 relation rationale
- 집계 metric

금지:

- 원본 PDF
- parser 원문
- chunk 본문
- 평가 raw text
- private absolute path
- API key 또는 token

허용 필드 내부의 원문 유출은 구조적으로 완벽히 증명할 수 없다. 이 catalog 단계에서는 필드명 차단, 단일 라인 제한, 길이 제한, Windows/POSIX 경로 탐지, secret-like 문자열 탐지로 public seed를 통제한다. 전체 원문 대조 감사는 parser/chunk private artifact 단계에서 별도로 수행한다.

## Gate

| gate | 기준 |
| --- | --- |
| minimum place | `place_count >= 8` |
| minimum alias | `alias_count >= 20` |
| duplicate place id | 0 |
| duplicate canonical name | 0 |
| duplicate alias | 0 |
| unknown related place | 0 |
| self relation | 0 |
| place without relation | 0 |
| place without context tag | 0 |
| public false | 0 |
| public raw text leakage | 0 |
| private path leakage | 0 |
| secret-like leakage | 0 |

## 현재 결과

현재 seed 기준:

```text
place_count=9
alias_count=36
relation_count=18
duplicate_place_id_count=0
duplicate_alias_count=0
unknown_related_place_count=0
self_relation_count=0
public_raw_text_leakage_count=0
private_path_leakage_count=0
secret_like_leakage_count=0
status=PASS
```

전체 리포트는 [Place Catalog Validation Report](../evals/reports/place_catalog_validation_report.md)에 둔다.

## 다음 사용 위치

다음 단계에서는 이 catalog를 바로 generation에 넣지 않는다.

우선순위:

1. Dense retrieval과 Hybrid retrieval 비교에서 query type별 실패를 장소 기준으로 태깅한다.
2. place alias를 사용한 query rewrite ablation을 별도 실험으로 만든다.
3. route 질문에서 여러 장소가 동시에 등장할 때 parent context expansion 결과를 비교한다.
4. 최종 answer contract에서 `place_relevance`를 평가한다.
