# Place Catalog Validation Report

## 목적

서울/한양 관광 도슨트 RAG에서 사용할 장소 기준 catalog를 검증한다.

이 문서는 retrieval 성능 개선 주장이 아니다. query rewrite, place-aware retrieval, route-aware retrieval에서 참조할 public-safe seed 데이터의 무결성 기록이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `place-catalog-validation/v1` |
| catalog_version | `place-catalog/v1` |
| generated_at_utc | `2026-05-09T17:44:03+00:00` |
| catalog_path | `data_samples/place_catalog_seed.json` |

## 정량 리포트

| metric | value |
| --- | ---: |
| place_count | 9 |
| alias_count | 36 |
| relation_count | 18 |
| minimum_place_count | 8 |
| minimum_alias_count | 20 |
| duplicate_place_id_count | 0 |
| duplicate_canonical_name_count | 0 |
| duplicate_alias_count | 0 |
| unknown_related_place_count | 0 |
| self_relation_count | 0 |
| place_without_relation_count | 0 |
| place_without_context_tag_count | 0 |
| public_false_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

## Category Breakdown

| category | count |
| --- | ---: |
| city_wall | 1 |
| district | 1 |
| gate_square | 1 |
| mountain | 1 |
| palace | 3 |
| route_anchor | 1 |
| shrine | 1 |

## Alias Language Breakdown

| language | count |
| --- | ---: |
| en | 18 |
| hanja | 9 |
| ko | 9 |

## Relation Type Breakdown

| relation_type | count |
| --- | ---: |
| historical_context | 3 |
| nearby | 4 |
| route_neighbor | 5 |
| same_area | 4 |
| viewpoint | 2 |

## 정성 리포트

- `catalog_scope`: 경복궁, 광화문, 종묘, 창덕궁, 북촌, 한양도성, 남산, 덕수궁, 종로를 서울/한양 관광 도슨트의 초기 장소 기준으로 고정했다.
- `public_policy`: 원문 PDF, parser text, chunk text를 포함하지 않고 장소명, alias, 관계 ID만 공개한다.
- `gate_result`: hard gate 통과
- `retrieval_use`: 다음 단계에서 place-aware query rewrite와 retrieval failure analysis의 기준 dimension으로 사용한다.

## 해석

place catalog는 원문 도서 내용을 복제하지 않는 수동 seed다.

이번 gate가 확인하는 것은 장소 ID, 별칭, 관계 target, public seed 정책의 기계적 무결성이다. 역사 설명문 생성 품질은 이후 citation RAG generation eval에서 별도로 측정한다.

허용 필드 내부의 임의 원문 유출은 길이와 줄바꿈 기반 휴리스틱으로 통제한다. 전체 원문 대조 감사는 parser/chunk private artifact 단계에서 별도로 수행한다.
