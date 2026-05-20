# Voice Local Korean TTS Alternative Review Report

## 결론

`HD-VOICE-LOCAL-KOREAN-TTS-ALTERNATIVE-REVIEW-001`는 Piper 이후 무료 로컬 한국어 TTS 후보를 재정렬한 평가 리포트다.

다음 smoke 후보는 `local_sherpa_onnx_supertonic3_ko`다. 이 판단은 실제 합성 품질 검증이 아니라 설치/다운로드 전 후보 선정이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-local-korean-tts-alternative-review-report/v1` |
| review_id | `voice-local-korean-tts-alt-review-c7-c7e05891` |
| work_id | `HD-VOICE-LOCAL-KOREAN-TTS-ALTERNATIVE-REVIEW-001` |
| depends_on | `HD-VOICE-LOCAL-PIPER-TTS-SMOKE-001` |
| generated_at_utc | `2026-05-20T11:58:26+00:00` |
| result_path | `<private artifact: voice_local_korean_tts_alternative_review_rows.jsonl>` |
| source_checked_at | `2026-05-20` |
| source_fingerprint | `7ab55dfcabeba642` |
| resolved_device | `cuda` |
| cuda_device_name | `NVIDIA GeForce RTX 4080 SUPER` |
| review_status | `PASS` |

## 정량 리포트

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
| fallback_only_candidate_count | 0 |
| package_install_attempted_count | 0 |
| model_download_attempted_count | 0 |
| local_tts_execution_count | 0 |
| live_tts_call_count | 0 |
| live_stt_call_count | 0 |
| live_solar_call_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| selected_next_smoke_candidate_id | `local_sherpa_onnx_supertonic3_ko` |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |
| review_decision | `select_sherpa_onnx_supertonic3_for_smoke` |

## Candidate Rows

| provider_candidate_id | family | korean | local_free | cuda | license_review | windows_blocker | execution_ready | decision | next_action |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| local_sherpa_onnx_supertonic3_ko | sherpa-onnx + Supertonic 3 | 1 | 1 | 0 | 1 | 0 | 0 | `selected_next_smoke` | next smoke target: install runtime only after approval, download Korean model privately, synthesize 5 public-safe scripts to private wav artifacts |
| local_supertonic3_python_sdk_ko | Supertonic 3 Python SDK | 1 | 1 | 0 | 1 | 0 | 0 | `candidate_after_license_review` | keep as second integration path if sherpa-onnx packaging is blocked |
| local_melotts_korean_retry | MeloTTS | 1 | 1 | 1 | 0 | 1 | 0 | `blocked_dependency` | run only after explicit Windows dependency fix approval |
| local_kani_tts_ko_review | KaniTTS2 | 1 | 1 | 1 | 1 | 0 | 0 | `candidate_after_license_review` | keep as research candidate after sherpa-onnx and MeloTTS paths are exhausted |
| local_coqui_xtts_v2_ko_review | Coqui XTTS-v2 | 1 | 1 | 1 | 1 | 0 | 0 | `candidate_after_license_review` | do not use as default; keep for optional research-only benchmark |
| local_styletts2_research_only | StyleTTS2 | 0 | 1 | 0 | 1 | 0 | 0 | `research_only` | exclude from immediate smoke; cite as research-only alternative |
| local_piper_tts_ko_blocked | Piper | 0 | 1 | 1 | 1 | 0 | 0 | `blocked_missing_korean_voice` | do not continue Piper until an official Korean voice appears |

## Source Rows

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

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 7 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
korean_tts_alternative_review_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | Piper Korean voice 부재 이후 무료 로컬 한국어 TTS 후보를 재검토했다. |
| selection | sherpa-onnx + Supertonic 3 Korean 경로를 다음 smoke 대상으로 선정했다. |
| why_not_piper | Piper는 runtime smoke가 통과했지만 Korean voice availability가 0이라 현재 중단한다. |
| why_not_melotts_first | MeloTTS는 Korean/MIT 장점이 있으나 이전 Windows eunjeon blocker가 해결되지 않았다. |
| cuda | 현재 local CUDA preflight는 resolved_device=cuda다. 다만 TTS 후보 선정 gate에서는 CUDA 실행을 주장하지 않는다. |
| security | 설치, 모델 다운로드, 음성 합성, 외부 provider 호출, 외부 음성 전송은 모두 0으로 유지했다. |
| data_mart | 후보 검토 grain은 review_id + provider_candidate_id + metric_name으로 고정했다. |
| portfolio | 좋아 보이는 TTS를 바로 채택하지 않고 source/license/runtime risk를 분리한 evidence로 사용한다. |
| external_audit | 다음 smoke 후보를 하나로 좁히되 품질 검증 완료 claim을 금지한 판단은 타당하다. |
| decision | select_sherpa_onnx_supertonic3_for_smoke |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
