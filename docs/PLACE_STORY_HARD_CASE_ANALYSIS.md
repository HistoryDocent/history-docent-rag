# Place Story Hard-case 원인 진단

## 결론

`q-dev-place-story-001` 실패는 청킹 문제로 바로 돌리면 안 된다.

현재 진단 결과는 `target_grain_mismatch`다. target doc은 retrieval/evidence pack에 들어왔지만, target child와 target parent는 들어오지 않았다. target doc도 retrieval rank 5, pack rank 5에 위치했다. 즉 v2 generation이 실패한 것은 맞지만, 입력 evidence 자체도 강한 상태가 아니다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | 전체 청킹 재실험보다 target grain, top-rank retrieval, generation prompt를 분리해야 한다. |
| Retrieval | target doc은 들어왔지만 child/parent가 빠졌고 rank가 낮다. retrieval hard-case로 봐야 한다. |
| Evidence packing | P0 pack에 doc-level target은 포함됐지만 근거로 쓰기 좋은 child가 빠졌다. |
| Generation | v2 regression은 확인됐지만 prompt만 고쳐서 해결된다고 단정할 수 없다. |
| 평가 | judgment가 child/parent/doc 중 어느 grain을 실제 정답으로 삼는지 재점검해야 한다. |
| 보안 | raw query, raw answer, evidence text, chunk text는 public report에 기록하지 않는다. |
| 포트폴리오 | 실패를 단일 원인으로 몰지 않고 retrieval/generation 경계를 분해한 점을 강조한다. |

## 입력과 산출물

입력:

- private retrieval eval dataset
- private parent-child chunks report
- private Solar Pro 3 v1/v2 live comparison metric rows
- 추가 Solar Pro 3 호출: 0

산출물:

- public report: `evals/reports/place_story_hard_case_analysis_report.md`
- private diagnostic rows: `private_data/evals/results/place_story_hard_case_analysis_rows.jsonl`

## 정량 결과

| metric | value |
| --- | ---: |
| analyzed_query_count | 1 |
| target_child_covered_count | 0 |
| target_parent_covered_count | 0 |
| target_doc_covered_count | 1 |
| target_min_retrieval_rank | 5 |
| target_min_pack_rank | 5 |
| citation_recoverability | 1.000000 |
| evidence_order_relevance_proxy | 0.200000 |
| generation_regression_count | 1 |
| root_cause_decision | `target_grain_mismatch` |

## 해석

이 결과는 세 가지를 말한다.

1. 청킹 전체가 틀렸다고 볼 증거는 아직 없다.
2. retrieval이 완전히 실패한 것도 아니다. target doc은 들어왔다.
3. 다만 target child/parent가 빠졌고 rank가 낮기 때문에 generation v2가 좋은 답을 만들기 어려운 입력이었다.

따라서 다음 실험은 다음 순서가 맞다.

1. `place_story` judgment target grain 점검
2. `place_story` top-rank retrieval coverage 개선 후보 검토
3. v2 selected evidence prompt repair 계획 작성
4. 필요 시 소규모 live 재실험

## 다음 작업 기준

청킹 비교를 다시 하려면 다음 중 하나의 증거가 필요하다.

- target child가 반복적으로 parent/doc 안에 묻혀 검색되지 않는다.
- parent-child boundary 때문에 target evidence가 citation 단위로 복구되지 않는다.
- `place_story` hard subset에서 chunk variant가 target child coverage를 유의미하게 개선한다.

현재는 이 조건을 만족하지 않는다. 그러므로 다음 작업은 전체 청킹 재실험이 아니라 `place_story` target grain과 retrieval coverage를 먼저 보는 것이다.
