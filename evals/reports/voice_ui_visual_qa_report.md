# Voice UI Visual QA Report

## 결론

`HD-VOICE-UI-004`는 통과다.

실제 브라우저에서 voice UI의 desktop answerable, mobile no-answer, desktop sanitized error 상태를 확인했다. 이번 결과는 화면 렌더링과 contract fixture UI 검증이며, production voice app 완성이나 live Solar Pro 3 품질 검증을 의미하지 않는다.

## 정량 결과

| metric | value |
| --- | ---: |
| visual_qa_scenario_count | 3 |
| visual_qa_viewport_class_count | 2 |
| screenshot_artifact_count | 3 |
| desktop_answerable_viewport_width | 1280 |
| desktop_answerable_viewport_height | 800 |
| desktop_answerable_horizontal_overflow | false |
| desktop_answerable_citation_item_count | 1 |
| desktop_answerable_detail_answer_visible | true |
| desktop_answerable_solar_call_count_text_visible | true |
| mobile_no_answer_viewport_width | 390 |
| mobile_no_answer_viewport_height | 844 |
| mobile_no_answer_horizontal_overflow | false |
| mobile_no_answer_workspace_single_column | true |
| mobile_no_answer_citation_item_count | 0 |
| mobile_no_answer_empty_citation_visible | true |
| mobile_no_answer_abstained_status_visible | true |
| desktop_error_viewport_width | 1280 |
| desktop_error_viewport_height | 800 |
| desktop_error_horizontal_overflow | false |
| desktop_error_sanitized_error_visible | true |
| desktop_error_raw_error_leaked | false |
| desktop_error_private_path_leaked | false |
| desktop_error_secret_marker_leaked | false |
| voice_control_visible_count | 2 |
| live_solar_call_count | 0 |
| retrieval_execution_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## 정성 평가

| gate | result | 근거 |
| --- | --- | --- |
| Desktop answerable layout | PASS | spoken answer, 상세 답변, citation drawer가 같은 viewport에서 확인됐다. |
| Mobile no-answer layout | PASS | `390x844`에서 single-column layout과 no-answer 상태가 확인됐다. |
| Citation UI | PASS | answerable은 citation 1개, no-answer는 empty citation 상태를 표시한다. |
| Voice controls | PASS | microphone/speaker control이 browser UI에 표시된다. |
| Error safety | PASS | 사용자 화면에는 sanitized error만 표시되고 raw fixture error는 노출되지 않는다. |
| Claim boundary | PASS | live provider와 retrieval execution을 실행하지 않았다. |
| External audit | PASS | contract smoke 이후 visual QA를 분리해 제출용 evidence를 만든 순서가 타당하다. |

## Screenshot Artifacts

| artifact | status |
| --- | --- |
| `evals/reports/assets/voice_ui_visual_qa_desktop_answerable.jpg` | PASS |
| `evals/reports/assets/voice_ui_visual_qa_mobile_no_answer.jpg` | PASS |
| `evals/reports/assets/voice_ui_visual_qa_desktop_error.jpg` | PASS |

## Data Mart Grain

`fact_voice_ui_visual_qa`의 grain은 `work_id + scenario_id + viewport_class + artifact_id + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-VOICE-UI-004` |
| `scenario_id` | answerable, no_answer, error |
| `viewport_class` | desktop, mobile |
| `artifact_id` | screenshot artifact 또는 DOM metric |
| `claim_boundary` | fixture-only, browser-local-only, no-live-call |

금지 필드:

- raw query
- raw evidence
- raw prompt
- chunk text
- private path
- secret

## Claim Boundary

허용:

- 실제 브라우저에서 voice UI skeleton의 desktop/mobile 화면을 확인했다.
- citation drawer, no-answer, sanitized error 상태를 visual QA로 검증했다.
- screenshot artifact와 public-safe report를 추가했다.

금지:

- production voice app 완성
- STT/TTS 품질 검증 완료
- live Solar Pro 3 demo 성공
- retrieval 또는 generation 성능 개선
- locked test 개선 입증

## 다음 Gate

다음 작업 후보는 optional voice STT/TTS provider benchmark plan이다.

권장 작업 단위:

- `id`: `HD-VOICE-STT-TTS-PROVIDER-BENCH-PLAN-001`
- `depends_on`: `HD-PORTFOLIO-REHEARSAL-001`
- `scope`: 실제 음성 입출력 demo 범위, 비용, 개인정보 처리, 실패 대응 계획
- `acceptance_tests`: 공식 문서 확인, 비용 gate, 개인정보 gate, live call budget, CUDA local 후보 범위 고정
- `risk_level`: low
- `rollback_plan`: voice planning 문서만 revert
