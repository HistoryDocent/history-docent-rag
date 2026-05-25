# Voice Demo Stack Decision Report

## 결론

`HD-VOICE-DEMO-STACK-DECISION-001`은 PASS다.

무료 로컬 음성 demo stack은 `local_faster_whisper_small_cuda` STT와 `local_sherpa_onnx_supertonic3_ko` TTS demo review 후보로 정리한다. 이번 결과는 사람 청취 점수 30/30 평균 5.0을 반영한 demo 후보 판단이며, production final provider 확정이나 실제 관광객 음성 품질 검증은 아니다.

## 정량 결과

| metric | value |
| --- | ---: |
| demo_stack_decision_document_count | 1 |
| demo_stack_decision_report_count | 1 |
| primary_local_stt_candidate_count | 1 |
| tts_demo_candidate_count | 1 |
| tts_final_provider_count | 0 |
| managed_provider_default_count | 0 |
| optional_paid_provider_candidate_count | 3 |
| local_tts_private_audio_available_count | 5 |
| tts_automated_proxy_pass_count | 4 |
| tts_automated_proxy_total_count | 5 |
| tts_human_score_completed_count | 30 |
| tts_human_score_expected_count | 30 |
| tts_human_score_overall_avg | 5.000000 |
| tts_human_score_reviewer_count | 1 |
| human_score_public_detail_row_count | 0 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_audio_public_artifact_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| production_voice_claim_count | 0 |

## 정성 평가

| gate | result | 근거 |
| --- | --- | --- |
| Product fit | PASS | local-first demo는 비용 없이 반복 실행 가능하고 포트폴리오 설명력이 높다. |
| STT decision | PASS | `faster-whisper small CUDA`를 현재 demo evidence 기준 STT 후보로 유지한다. |
| TTS decision | PASS | `sherpa-onnx Supertonic 3 Korean`은 자동 proxy 4/5와 사람 청취 30/30 평균 5.0으로 demo review 후보가 됐다. |
| Claim boundary | PASS | TTS final provider count는 0이고 production voice claim count도 0이다. |
| Privacy | PASS | raw audio, raw transcript, 개별 human score detail은 public artifact에 포함하지 않는다. |
| Cost | PASS | external provider call, external audio transmission, live STT/TTS/Solar call은 모두 0이다. |
| External audit | PASS | 이전 차단 결과를 되돌리지 않고 최신 decision layer를 별도로 추가한 판단은 타당하다. |

## Data Mart Grain

`fact_voice_demo_stack_decision`의 grain은 `work_id + provider_candidate_id + modality + metric_family + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `work_id` | `HD-VOICE-DEMO-STACK-DECISION-001` |
| `provider_candidate_id` | `local_faster_whisper_small_cuda`, `local_sherpa_onnx_supertonic3_ko` |
| `modality` | `stt`, `tts` |
| `metric_family` | quality, privacy, cost, runtime, claim_boundary |
| `claim_boundary` | demo evidence only, demo review candidate only, no production final claim |

금지 필드:

- raw audio
- raw transcript
- raw prompt
- raw payload
- private file path
- individual reviewer score detail
- secret

## Claim Boundary

허용:

- 무료 로컬 음성 demo stack 후보를 정리했다.
- TTS demo review 후보는 사람 청취 점수 30/30 평균 5.0을 근거로 수락했다.
- 외부 provider 호출과 외부 음성 전송은 0이다.

금지:

- 무료 로컬 TTS 최종 provider 확정
- Supertonic 3 음성 품질 우수 production 검증 완료
- 실제 관광객 음성 품질 검증 완료
- production 음성 관광 앱 완성
- managed provider보다 local TTS가 품질 우수하다는 주장

## Gate Result

```text
voice_demo_stack_decision_failures=[]
voice_demo_stack_decision_blockers=[]
```

