# Voice UI Visual QA

## 결론

`HD-VOICE-UI-004`는 통과다.

이번 작업은 voice UI skeleton을 실제 브라우저에서 확인한 visual QA 단계다. 검증 범위는 fixture 기반 화면 렌더링, desktop/mobile breakpoint, citation drawer, no-answer, sanitized error, voice control 표시다.

이 결과는 production 배포, STT/TTS 품질 검증, live Solar Pro 3 demo 성공, retrieval 성능 개선을 의미하지 않는다.

## 검증 범위

| 영역 | 검증 |
| --- | --- |
| desktop answerable | `1280x800` viewport에서 answerable response, 상세 답변, citation drawer 표시 |
| mobile no-answer | `390x844` viewport에서 single-column layout, no-answer, empty citation drawer 표시 |
| desktop error | `1280x800` viewport에서 sanitized API error 표시와 raw error 비노출 |
| voice controls | microphone/speaker control의 visible state 확인 |
| claim boundary | live Solar Pro 3 호출 0, retrieval 실행 0 |
| public safety | private path, secret-like string, raw evidence 노출 0 |

## Screenshot Artifacts

| artifact | 검증 상태 |
| --- | --- |
| `evals/reports/assets/voice_ui_visual_qa_desktop_answerable.jpg` | desktop answerable, 상세 답변, citation drawer |
| `evals/reports/assets/voice_ui_visual_qa_mobile_no_answer.jpg` | mobile no-answer, single-column layout |
| `evals/reports/assets/voice_ui_visual_qa_desktop_error.jpg` | sanitized error state |

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| Product | RAG API 결과가 사용자에게 보이는 demo surface까지 연결됐다는 증거가 필요했다. |
| Frontend | desktop/mobile breakpoint와 drawer 상태를 실제 browser에서 확인한 순서가 타당하다. |
| API | 새 API 없이 기존 fixture/contract 흐름만 검증했다. |
| Security | screenshot과 report에 private path, secret, raw evidence를 포함하지 않았다. |
| Evaluation | screenshot artifact, DOM metric, public-safe scan을 분리해 기록했다. |
| Data warehouse | `fact_voice_ui_visual_qa` grain으로 scenario, viewport, artifact, claim boundary를 기록한다. |
| 외부 감사 | contract smoke 뒤에 visual QA를 분리한 흐름은 제출용 evidence로 타당하다. |

## Non-goal

- production 배포
- 실제 microphone transcript 수집
- STT/TTS 품질 평가
- live Solar Pro 3 호출
- retrieval-backed private corpus 실행
- raw evidence 또는 raw chunk text 표시

## 다음 작업

다음 단계는 포트폴리오 demo runbook 정리다.

후속 작업에서는 사용자가 clone 후 어떤 순서로 backend/frontend를 실행하고 어떤 claim을 말하면 되는지 정리한다.
