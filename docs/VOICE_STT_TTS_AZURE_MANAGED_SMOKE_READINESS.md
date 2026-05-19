# Voice STT/TTS Azure Managed Smoke Readiness

`HD-VOICE-STT-TTS-AZURE-MANAGED-SMOKE-READINESS-001`는 첫 managed STT/TTS smoke 후보를 Azure AI Speech로 제한하고, 실제 호출 전 준비 조건을 고정한다.

결론: 이 단계는 Azure API를 호출하지 않는다. credential 값, raw audio, raw transcript, provider payload도 public artifact에 기록하지 않는다.

## Scope

| field | value |
| --- | --- |
| work_id | `HD-VOICE-STT-TTS-AZURE-MANAGED-SMOKE-READINESS-001` |
| depends_on | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-PREFLIGHT-001` |
| next_work_id | `HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001` |
| first_managed_provider_candidate | `managed_azure_ai_speech` |
| planned_script_count | 3 |
| planned_stt_call_count | 3 |
| planned_tts_call_count | 3 |
| managed_provider_api_call_count | 0 |
| external_audio_transmission_count | 0 |
| readiness_decision | `ready_for_azure_credential_setup` |

## 왜 Azure 우선인가

| criterion | 판단 |
| --- | --- |
| provider scope | STT와 TTS를 한 provider에서 함께 smoke 가능 |
| credential complexity | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` 2개만 필요 |
| region check | Azure Speech key는 region과 묶이므로 region mismatch를 smoke 전 차단 가능 |
| portfolio value | local CUDA Whisper `small`과 managed provider를 제한된 call budget으로 비교하는 구조가 명확함 |

## Required Local Environment

`.env.example`에는 변수명만 둔다. 실제 값은 `.env` 또는 로컬 shell environment에만 둔다.

| env name | required | public value allowed |
| --- | --- | --- |
| `AZURE_SPEECH_KEY` | yes | no |
| `AZURE_SPEECH_REGION` | yes | no |

## Source Recheck Checklist

실제 smoke 직전 같은 날짜에 다시 확인한다. 이 문서의 source는 readiness 기준 참고용이며, “최신 가격/정책 확인 완료” claim으로 쓰지 않는다.

| check | source | execution gate |
| --- | --- | --- |
| region identifier and resource-region binding | https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions | selected region이 STT/TTS 모두 지원해야 함 |
| Speech pricing and billing unit | https://azure.microsoft.com/en-us/pricing/details/speech/ | STT seconds, TTS characters 기준 비용 상한 확인 |
| Korean STT/TTS language support | https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt-tts | `ko-KR` STT/TTS 지원 확인 |
| STT data/privacy/security | https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/speech-service/speech-to-text/data-privacy-security | audio input 외부 전송과 retention 조건 확인 |
| TTS data/privacy/security | https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/speech-service/text-to-speech/data-privacy-security | text input과 generated audio 처리 조건 확인 |

## Smoke Execution Contract

이번 readiness에서는 실행하지 않는다. 다음 별도 승인 후에도 아래 제한을 넘기지 않는다.

| item | cap |
| --- | ---: |
| provider | 1 |
| script count | 3 |
| STT calls | 3 |
| TTS calls | 3 |
| Solar Pro 3 calls | 0 |
| raw audio public artifact | 0 |
| raw transcript public artifact | 0 |
| raw provider payload public artifact | 0 |

## Evaluation Metrics

실제 Azure smoke가 승인되면 local CUDA `small` 결과와 같은 script set으로 비교한다.

| metric | grain | note |
| --- | --- | --- |
| `wer_avg` | `provider_id + script_id` | reference transcript 기준 |
| `cer_avg` | `provider_id + script_id` | 한국어 음절/문자 오류 보조 지표 |
| `place_name_accuracy_avg` | `provider_id + script_id` | 서울/한양 장소명 보존 여부 |
| `stt_latency_p95_ms` | `provider_id + script_id` | API 왕복 포함 여부를 report에 명시 |
| `tts_character_count` | `provider_id + script_id` | cost estimate용 |
| `external_audio_transmission_count` | `run_id` | Azure smoke에서는 실제 실행 시 3 예상 |

## Data Mart

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_azure_smoke_readiness` | `readiness_id + provider_candidate_id` | public aggregate |
| `fact_voice_azure_smoke_source_check` | `readiness_id + source_check_type` | public aggregate |
| `fact_voice_managed_smoke_private_payload` | `run_id + provider_candidate_id + script_id` | private only |

## Claim Boundary

허용 claim:

- Azure managed STT/TTS smoke 실행 준비 기준을 문서화했다.

- Azure API call과 external audio transmission은 0회다.

- credential 값은 public artifact에 기록하지 않았다.

- 실제 Azure smoke는 credential 설정과 source 재확인 뒤 별도 승인으로만 가능하다.

금지 claim:

- Azure STT/TTS 품질 검증 완료

- managed provider benchmark 완료

- Azure 비용/정책 최신 확인 완료

- production voice service 준비 완료

- 외부 audio 전송 검증 완료
