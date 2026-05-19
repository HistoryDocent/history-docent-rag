# Voice STT/TTS Local Model Ablation Report

## 결론

`HD-VOICE-STT-TTS-LOCAL-MODEL-ABLATION-001`는 local CUDA Whisper 모델 크기 후보를 external provider 호출 없이 비교한다.

이 리포트는 STT/TTS 품질 최종 검증이 아니다. raw audio와 raw transcript는 public artifact에 저장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `voice-stt-tts-local-model-ablation-report/v1` |
| ablation_id | `voice-local-model-ablation-m3-s5-c7a93214` |
| work_id | `HD-VOICE-STT-TTS-LOCAL-MODEL-ABLATION-001` |
| depends_on | `HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-LOCAL-001` |
| generated_at_utc | `2026-05-19T12:27:06+00:00` |
| scripts_path | `data_samples/voice_benchmark_scripts.sample.jsonl` |
| result_path | `<private artifact: voice_stt_tts_local_model_ablation_rows.jsonl>` |
| private_audio_path_alias | `<private artifact: local_smoke_audio>` |
| provider_candidate_id | `local_cuda_whisper` |
| source_fingerprint | `d31b1df3ba7cc422` |
| ablation_status | `completed_local_model_ablation` |

## 정량 리포트

| metric | value |
| --- | ---: |
| model_candidate_count | 3 |
| selected_script_count | 5 |
| public_safe_script_fixture_count | 5 |
| runtime_available_count | 1 |
| audio_fixture_available_count | 5 |
| local_stt_execution_requested_count | 15 |
| total_local_stt_execution_count | 15 |
| total_local_cuda_whisper_call_count | 15 |
| external_provider_call_count | 0 |
| external_audio_transmission_count | 0 |
| live_stt_call_count | 0 |
| live_tts_call_count | 0 |
| live_solar_call_count | 0 |
| raw_transcript_public_artifact_count | 0 |
| raw_audio_public_artifact_count | 0 |
| client_secret_exposure_count | 0 |
| resolved_device | `cuda` |
| local_cuda_available_count | 1 |
| cuda_device_count | 1 |
| best_cer_model_id | `small` |
| best_place_name_accuracy_model_id | `small` |
| recommended_model_id | `small` |
| public_private_path_leakage_count | 0 |
| public_secret_like_leakage_count | 0 |
| public_raw_payload_leakage_count | 0 |

## Model Summary

| model_id | executed | load_ms | wer_avg | cer_avg | place_name_accuracy_avg | latency_p95_ms | cer_delta_from_tiny | place_delta_from_tiny | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| tiny | 5 | 689.723900 | 0.553333 | 0.164183 | 0.600000 | 386.957040 | 0.000000 | 0.000000 | `baseline` |
| base | 5 | 13515.711300 | 0.266667 | 0.088628 | 0.400000 | 207.024420 | 0.075555 | -0.200000 | `quality_candidate_check_latency` |
| small | 5 | 44491.524000 | 0.080000 | 0.053333 | 0.800000 | 360.612560 | 0.110850 | 0.200000 | `quality_candidate_check_latency` |

## Result Row Summary

| model_id | script_id | query_type | status | latency_ms | wer | cer | place_name_accuracy | place_count | error_code |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| tiny | voice-script-place-fact-001 | place_fact | `executed` | 462.651900 | 1.000000 | 0.466667 | 0.000000 | 1 | `` |
| tiny | voice-script-place-fact-002 | place_fact | `executed` | 70.675100 | 0.600000 | 0.066667 | 1.000000 | 1 | `` |
| tiny | voice-script-place-fact-003 | place_fact | `executed` | 84.177600 | 0.666667 | 0.176471 | 0.000000 | 2 | `` |
| tiny | voice-script-place-fact-004 | place_fact | `executed` | 71.048000 | 0.500000 | 0.111111 | 1.000000 | 1 | `` |
| tiny | voice-script-place-fact-005 | place_fact | `executed` | 82.053700 | 0.000000 | 0.000000 | 1.000000 | 1 | `` |
| base | voice-script-place-fact-001 | place_fact | `executed` | 209.733200 | 0.400000 | 0.200000 | 0.000000 | 1 | `` |
| base | voice-script-place-fact-002 | place_fact | `executed` | 159.927700 | 0.200000 | 0.066667 | 0.000000 | 1 | `` |
| base | voice-script-place-fact-003 | place_fact | `executed` | 196.189300 | 0.333333 | 0.176471 | 0.000000 | 2 | `` |
| base | voice-script-place-fact-004 | place_fact | `executed` | 163.457300 | 0.000000 | 0.000000 | 1.000000 | 1 | `` |
| base | voice-script-place-fact-005 | place_fact | `executed` | 190.290100 | 0.400000 | 0.000000 | 1.000000 | 1 | `` |
| small | voice-script-place-fact-001 | place_fact | `executed` | 348.013400 | 0.400000 | 0.266667 | 0.000000 | 1 | `` |
| small | voice-script-place-fact-002 | place_fact | `executed` | 275.962600 | 0.000000 | 0.000000 | 1.000000 | 1 | `` |
| small | voice-script-place-fact-003 | place_fact | `executed` | 362.916000 | 0.000000 | 0.000000 | 1.000000 | 2 | `` |
| small | voice-script-place-fact-004 | place_fact | `executed` | 298.581900 | 0.000000 | 0.000000 | 1.000000 | 1 | `` |
| small | voice-script-place-fact-005 | place_fact | `executed` | 351.398800 | 0.000000 | 0.000000 | 1.000000 | 1 | `` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 15 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Gate Result

```text
local_model_ablation_failures=[]
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
| scope | external provider 호출 없이 local_cuda_whisper 모델 크기 후보만 비교했다. |
| cuda | CUDA 가능 시 사용하며 resolved_device=cuda로 기록했다. |
| metric | WER, CER, place_name_accuracy, latency, model load time을 같은 fixture로 비교했다. |
| privacy | raw audio는 private artifact이며 public report에는 raw transcript를 저장하지 않는다. |
| cost | managed cloud STT/TTS 호출이 없어 external provider 비용은 발생하지 않는다. |
| data_mart | private script-level fact와 public model summary grain을 분리했다. |
| portfolio | provider 선택 전 로컬 GPU 후보군을 좁힌 실험으로 설명한다. |
| external_audit | managed provider 전송 전 local model ablation을 수행한 순서는 타당하다. |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
