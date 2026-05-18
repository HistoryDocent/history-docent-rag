# Voice UI Skeleton

## 결론

`HD-VOICE-UI-002`는 browser frontend skeleton 구현이다.

이번 작업은 `/api/v1/chat` contract fixture를 렌더링하는 첫 UI 표면을 만든다. 실제 STT/TTS 품질 검증, production voice app, live Solar Pro 3 호출, retrieval 성능 개선은 범위가 아니다.

## 구현 범위

| 영역 | 구현 |
| --- | --- |
| frontend stack | `frontend/` 독립 Vite React TypeScript package |
| chat surface | 장소 chip, 언어 선택, 질문 입력, 전송 버튼 |
| response | `spoken_answer` 우선 렌더링, 상세 `answer` disclosure |
| citation | citation drawer, citation id, doc id, rank, recoverable 표시 |
| no-answer | `abstained=true` fixture를 안전 상태로 표시 |
| voice fallback | microphone unsupported disabled state, speaker button fallback |
| API boundary | 기본 fixture mode, optional `VITE_HISTORY_DOCENT_API_BASE_URL`만 사용 |
| security | frontend에 secret, raw evidence, raw prompt, private path 없음 |

## 파일 구조

| path | 목적 |
| --- | --- |
| `frontend/src/components/DocentApp.tsx` | voice-ready docent UI |
| `frontend/src/lib/chatClient.ts` | fixture-first chat client와 optional backend call |
| `frontend/src/fixtures/chatFixtures.ts` | public-safe answerable/no-answer fixture |
| `frontend/src/types/chat.ts` | `/api/v1/chat` TypeScript contract |
| `frontend/src/App.test.tsx` | UI state regression tests |
| `frontend/src/styles.css` | responsive UI styles |

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| Product | 첫 화면을 marketing page가 아니라 실제 도슨트 chat surface로 만들었다. |
| Frontend | React state와 fixture client로 answerable/no-answer/error/voice fallback 상태를 분리했다. |
| API | 기존 `/api/v1/chat` field를 TypeScript type으로 반영했다. |
| Security | credential 주입 없이 public-safe fixture만 사용한다. |
| Evaluation | Vitest component tests와 Python public-safe regression test로 고정한다. |
| Data warehouse | `fact_voice_ui_skeleton_eval` grain으로 UI state와 gate 결과를 기록한다. |
| 외부 감사 | skeleton으로는 충분하지만, live backend integration과 real browser voice QA는 다음 gate가 필요하다. |

## Non-goal

- production 배포
- 실제 microphone transcript 수집
- STT/TTS 품질 검증
- live Solar Pro 3 호출
- RAG retrieval route 변경
- raw corpus 또는 raw evidence 표시

## 다음 작업

`HD-VOICE-UI-003`은 frontend/backend contract smoke다.

다음 gate에서는 FastAPI dev server와 frontend dev server를 동시에 띄우고, `/api/v1/chat` contract-only 요청이 UI에 표시되는지 확인한다. live provider는 여전히 별도 승인 전에는 사용하지 않는다.
