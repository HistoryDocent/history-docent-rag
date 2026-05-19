export type VoiceAdapterMode = "contract_only";
export type VoiceFeatureStatus = "disabled_by_contract";
export type VoiceActionReason = "contract_only";

export interface VoiceAdapterEnvironment {
  SpeechRecognition?: unknown;
  webkitSpeechRecognition?: unknown;
  speechSynthesis?: unknown;
}

export interface VoiceFeatureContract {
  status: VoiceFeatureStatus;
  browserSupported: boolean;
  ariaLabel: string;
  title: string;
  disabledReason: string;
}

export interface VoiceContractMetrics {
  liveSttCallCount: 0;
  liveTtsCallCount: 0;
  providerFinalizedCount: 0;
  privateAudioSavedCount: 0;
  rawTranscriptPublicArtifactCount: 0;
}

export interface VoiceActionResult {
  ok: false;
  reason: VoiceActionReason;
  transcriptDraft: null;
  spokenText: null;
  metrics: VoiceContractMetrics;
}

export interface VoiceAdapterContract {
  mode: VoiceAdapterMode;
  stt: VoiceFeatureContract;
  tts: VoiceFeatureContract;
  metrics: VoiceContractMetrics;
  createTranscriptDraft: () => VoiceActionResult;
  playSpokenAnswer: (spokenAnswer: string) => VoiceActionResult;
}

export const zeroVoiceContractMetrics: VoiceContractMetrics = {
  liveSttCallCount: 0,
  liveTtsCallCount: 0,
  providerFinalizedCount: 0,
  privateAudioSavedCount: 0,
  rawTranscriptPublicArtifactCount: 0,
};

export function createVoiceContractAdapter(
  environment: VoiceAdapterEnvironment = globalThis as VoiceAdapterEnvironment,
): VoiceAdapterContract {
  const sttBrowserSupported =
    Boolean(environment.SpeechRecognition) || Boolean(environment.webkitSpeechRecognition);
  const ttsBrowserSupported = Boolean(environment.speechSynthesis);

  return {
    mode: "contract_only",
    stt: disabledVoiceFeature("음성 입력 contract only", sttBrowserSupported),
    tts: disabledVoiceFeature("음성 재생 contract only", ttsBrowserSupported),
    metrics: zeroVoiceContractMetrics,
    createTranscriptDraft: () => contractOnlyResult(),
    playSpokenAnswer: () => contractOnlyResult(),
  };
}

function disabledVoiceFeature(ariaLabel: string, browserSupported: boolean): VoiceFeatureContract {
  return {
    status: "disabled_by_contract",
    browserSupported,
    ariaLabel,
    title: ariaLabel,
    disabledReason: "provider 호출 없는 contract skeleton 단계입니다.",
  };
}

function contractOnlyResult(): VoiceActionResult {
  return {
    ok: false,
    reason: "contract_only",
    transcriptDraft: null,
    spokenText: null,
    metrics: zeroVoiceContractMetrics,
  };
}
