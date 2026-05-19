# Voice Provider Decision Report

## 결론

`HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001`은 PASS다.

STT/TTS 기본 전략을 무료 로컬 provider 우선으로 변경했다. managed provider는 optional paid comparison 후보로만 남긴다. 이번 report는 decision/report artifact이며 실제 STT/TTS 모델 실행, Azure 호출, raw audio 생성, raw transcript 생성은 수행하지 않았다.

## 정량 결과

| metric | value |
| --- | ---: |
| `local_first_strategy_document_count` | 1 |
| `local_first_strategy_report_count` | 1 |
| `primary_local_stt_candidate_count` | 1 |
| `primary_local_tts_candidate_count` | 1 |
| `secondary_local_candidate_count` | 1 |
| `optional_local_license_review_candidate_count` | 1 |
| `optional_paid_managed_provider_count` | 3 |
| `managed_provider_default_count` | 0 |
| `default_external_audio_transmission_count` | 0 |
| `secret_required_for_default_voice_count` | 0 |
| `live_stt_call_count` | 0 |
| `live_tts_call_count` | 0 |
| `managed_provider_api_call_count` | 0 |
| `external_audio_transmission_count` | 0 |
| `raw_audio_public_artifact_count` | 0 |
| `raw_transcript_public_artifact_count` | 0 |
| `public_private_path_leakage_count` | 0 |
| `public_secret_like_leakage_count` | 0 |
| `public_raw_payload_leakage_count` | 0 |

## 정성 평가

| 평가 항목 | 판단 |
| --- | --- |
| 제품 적합성 | local-first가 서울 관광 demo의 반복 실행성과 비용 통제에 유리하다. |
| 개인정보 | 기본 external audio transmission을 0으로 둘 수 있어 managed-first보다 안전하다. |
| 포트폴리오 설명력 | RTX 4080 SUPER와 local CUDA 실험을 활용한 엔지니어링 메시지가 강하다. |
| 비용 통제 | 기본 provider에 cloud billing과 credential이 필요하지 않다. |
| 기술 리스크 | TTS 품질은 아직 검증되지 않았으므로 `MeloTTS Korean` smoke가 다음 gate다. |
| 문서 정합성 | Azure 문서는 삭제하지 않고 optional paid comparison으로 격하해야 한다. |

## Data Mart Grain

`fact_voice_provider_decision`의 grain은 `work_id + provider_candidate_id + modality + metric_family + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001` |
| `provider_candidate_id` | local/managed provider 후보 id |
| `provider_class` | `local_free`, `local_license_review`, `managed_paid_optional` |
| `modality` | `stt`, `tts`, `stt_tts` |
| `metric_family` | cost, privacy, latency, quality, governance |
| `claim_boundary` | decision-only |
| `decision` | primary, secondary, optional_paid, optional_license_review |

금지 필드:

- raw audio
- raw transcript
- raw payload
- raw prompt
- private file path
- secret

## 외부 감사

PASS.

이번 변경은 기존 실험 결과를 뒤집는 것이 아니라 다음 실행 우선순위를 정정하는 작업이다. Azure 관련 gate는 비용/외부 전송이 필요한 후보를 통제한 기록으로 보관하고, 기본 구현은 무료 로컬 STT/TTS로 진행하는 것이 맞다.
