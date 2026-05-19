import { createVoiceContractAdapter } from "./voiceAdapters";

describe("voice adapter contract skeleton", () => {
  test("keeps STT and TTS disabled even when browser capabilities exist", () => {
    const adapter = createVoiceContractAdapter({
      SpeechRecognition: function SpeechRecognition() {},
      speechSynthesis: { speak: vi.fn(), cancel: vi.fn() },
    });

    expect(adapter.mode).toBe("contract_only");
    expect(adapter.stt.browserSupported).toBe(true);
    expect(adapter.tts.browserSupported).toBe(true);
    expect(adapter.stt.status).toBe("disabled_by_contract");
    expect(adapter.tts.status).toBe("disabled_by_contract");
  });

  test("returns zero-call contract results for transcript and playback actions", () => {
    const adapter = createVoiceContractAdapter();

    expect(adapter.createTranscriptDraft()).toEqual({
      ok: false,
      reason: "contract_only",
      transcriptDraft: null,
      spokenText: null,
      metrics: {
        liveSttCallCount: 0,
        liveTtsCallCount: 0,
        providerFinalizedCount: 0,
        privateAudioSavedCount: 0,
        rawTranscriptPublicArtifactCount: 0,
      },
    });
    expect(adapter.playSpokenAnswer("테스트 음성 답변")).toEqual({
      ok: false,
      reason: "contract_only",
      transcriptDraft: null,
      spokenText: null,
      metrics: {
        liveSttCallCount: 0,
        liveTtsCallCount: 0,
        providerFinalizedCount: 0,
        privateAudioSavedCount: 0,
        rawTranscriptPublicArtifactCount: 0,
      },
    });
  });
});
