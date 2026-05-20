# Voice Local Korean TTS Alternative Review

## 결론

`HD-VOICE-LOCAL-KOREAN-TTS-ALTERNATIVE-REVIEW-001`의 결론은 Piper를 더 밀지 않고 `local_sherpa_onnx_supertonic3_ko`를 다음 무료 로컬 한국어 TTS smoke 후보로 선정하는 것이다.

이 문서는 실제 TTS 품질 검증이 아니라 후보 선정 gate다. 패키지 설치, 모델 다운로드, 로컬 합성, 외부 provider 호출은 모두 0으로 유지한다.

## Candidate Matrix

| provider_candidate_id | family | korean_support_status | decision | risk | next_action |
| --- | --- | --- | --- | --- | --- |
| local_sherpa_onnx_supertonic3_ko | sherpa-onnx + Supertonic 3 | `official_korean_support` | `selected_next_smoke` | medium | next smoke target: install runtime only after approval, download Korean model privately, synthesize 5 public-safe scripts to private wav artifacts |
| local_supertonic3_python_sdk_ko | Supertonic 3 Python SDK | `model_card_korean_support` | `candidate_after_license_review` | medium | keep as second integration path if sherpa-onnx packaging is blocked |
| local_melotts_korean_retry | MeloTTS | `official_korean_support` | `blocked_dependency` | high | run only after explicit Windows dependency fix approval |
| local_kani_tts_ko_review | KaniTTS2 | `model_card_korean_support` | `candidate_after_license_review` | medium | keep as research candidate after sherpa-onnx and MeloTTS paths are exhausted |
| local_coqui_xtts_v2_ko_review | Coqui XTTS-v2 | `model_card_korean_support` | `candidate_after_license_review` | high | do not use as default; keep for optional research-only benchmark |
| local_styletts2_research_only | StyleTTS2 | `not_out_of_box_korean_candidate` | `research_only` | high | exclude from immediate smoke; cite as research-only alternative |
| local_piper_tts_ko_blocked | Piper | `blocked_no_official_korean_voice` | `blocked_missing_korean_voice` | high | do not continue Piper until an official Korean voice appears |

## 정량 요약

| metric | value |
| --- | ---: |
| candidate_count | 7 |
| source_reference_count | 10 |
| source_checked_candidate_count | 7 |
| korean_support_candidate_count | 5 |
| local_free_candidate_count | 7 |
| cuda_capable_candidate_count | 4 |
| selected_next_smoke_candidate_count | 1 |
| license_review_required_count | 6 |
| windows_blocker_candidate_count | 1 |
| blocked_missing_korean_voice_count | 1 |
| research_only_candidate_count | 1 |
| package_install_attempted_count | 0 |
| model_download_attempted_count | 0 |
| local_tts_execution_count | 0 |
| live_tts_call_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| selected_next_smoke_candidate_id | `local_sherpa_onnx_supertonic3_ko` |
| review_decision | `select_sherpa_onnx_supertonic3_for_smoke` |

## Source Boundary

확인일: `2026-05-20`

| source_id | 확인 내용 | source_ref |
| --- | --- | --- |
| `sherpa_onnx_supertonic_tts` | sherpa-onnx supports SupertonicTTS offline TTS integration. | `official_docs` |
| `sherpa_onnx_supertonic_ko` | sherpa-onnx provides a Korean Supertonic 3 TTS example page. | `official_docs` |
| `supertonic3_huggingface` | Supertonic 3 model card states multilingual on-device TTS and license details. | `model_card` |
| `supertonic_github` | Supertonic repository provides Python examples and installation path. | `official_repository` |
| `melotts_github` | MeloTTS repository documents Korean support and MIT license. | `official_repository` |
| `kani_tts_github` | KaniTTS2 repository documents Korean TTS model family and runtime examples. | `official_repository` |
| `kani_tts_huggingface` | KaniTTS Hugging Face model card provides model/license metadata requiring review. | `model_card` |
| `coqui_xtts_v2_huggingface` | XTTS-v2 model card lists Korean support and CPML license boundary. | `model_card` |
| `styletts2_github` | StyleTTS2 repository is research-oriented and not an out-of-box Korean provider. | `official_repository` |
| `piper_voice_manifest` | Piper voice repository was already checked and Korean voice was absent in the current manifest. | `model_repository` |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_korean_tts_alternative_public` | `review_id + provider_candidate_id + metric_name` | public-safe |
| `fact_voice_local_korean_tts_smoke_private` | `smoke_id + provider_candidate_id + script_id + audio_artifact_id` | private only |

## 다음 작업 지시서

| field | value |
| --- | --- |
| `id` | `HD-VOICE-LOCAL-SHERPA-ONNX-SUPERTONIC3-KO-SMOKE-001` |
| `depends_on` | `HD-VOICE-LOCAL-KOREAN-TTS-ALTERNATIVE-REVIEW-001` |
| `scope` | `sherpa-onnx` 또는 Supertonic 3 Korean ONNX 경로로 5개 public-safe script를 private wav로 합성한다. 설치, 모델 다운로드, 음성 artifact는 private boundary에만 둔다. |
| `acceptance_tests` | Korean model source/license recorded, package install/download count recorded, selected script count 5, local TTS execution 5 or blocked reason recorded, external provider call 0, external audio transmission 0, raw audio public artifact 0 |
| `risk_level` | Medium |
| `rollback_plan` | sherpa-onnx smoke runner, docs, report, tests, private generated audio만 제거한다. |

## Claim Boundary

허용 claim:

- 무료 로컬 한국어 TTS 후보를 source 기반으로 재검토했다.
- Piper는 현재 Korean voice 부재로 기본 TTS provider가 아니다.
- 다음 smoke 후보는 `local_sherpa_onnx_supertonic3_ko`다.
- 이번 gate의 external provider call과 external audio transmission은 0이다.

금지 claim:

- Supertonic 3 또는 sherpa-onnx 한국어 TTS 품질 검증 완료
- 무료 로컬 TTS 최종 provider 확정
- 실제 관광객 음성 품질 검증 완료
- production 음성 관광 앱 완성
