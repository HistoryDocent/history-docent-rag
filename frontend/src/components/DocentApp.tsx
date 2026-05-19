import { useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  FileText,
  Languages,
  MapPin,
  Mic,
  Send,
  ShieldCheck,
  Volume2,
} from "lucide-react";
import { sendChat } from "../lib/chatClient";
import { createVoiceContractAdapter } from "../lib/voiceAdapters";
import type { ChatRequest, ChatResponse, LanguageCode } from "../types/chat";

const places = [
  { id: "gyeongbokgung", label: "경복궁" },
  { id: "gwanghwamun", label: "광화문" },
  { id: "bukchon", label: "북촌" },
  { id: "hanyangdoseong", label: "한양도성" },
];

const initialQuery = "경복궁을 한양 역사 관점에서 짧게 설명해줘";

type RequestStatus = "idle" | "loading" | "success" | "error";

export function DocentApp() {
  const [query, setQuery] = useState(initialQuery);
  const [language, setLanguage] = useState<LanguageCode>("ko");
  const [selectedPlaces, setSelectedPlaces] = useState<string[]>(["gyeongbokgung"]);
  const [status, setStatus] = useState<RequestStatus>("idle");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [citationsOpen, setCitationsOpen] = useState(true);

  const voiceAdapter = useMemo(() => createVoiceContractAdapter(), []);

  const submit = async () => {
    if (!query.trim()) {
      return;
    }

    setStatus("loading");
    setErrorMessage("");

    const request: ChatRequest = {
      query: query.trim(),
      language,
      query_type: "place_story",
      place_context: selectedPlaces,
      voice_mode: true,
      retrieval_mode: "contract_only",
      provider_mode: "contract_only",
      active_route_mode: "disabled",
    };

    try {
      const nextResponse = await sendChat(request);
      setResponse(nextResponse);
      setStatus("success");
      setDetailsOpen(false);
      setCitationsOpen(!nextResponse.abstained);
    } catch {
      setStatus("error");
      setResponse(null);
      setErrorMessage("요청을 처리하지 못했습니다. 잠시 뒤 다시 시도해 주세요.");
    }
  };

  const togglePlace = (placeId: string) => {
    setSelectedPlaces((current) => {
      if (current.includes(placeId)) {
        const next = current.filter((id) => id !== placeId);
        return next.length > 0 ? next : current;
      }
      return [...current, placeId];
    });
  };

  return (
    <main className="app-shell">
      <section className="workspace" aria-label="History Docent workspace">
        <aside className="control-panel" aria-label="질문 설정">
          <div className="brand-row">
            <div>
              <p className="eyebrow">History Docent</p>
              <h1>한양 도슨트</h1>
            </div>
            <ShieldCheck aria-hidden="true" />
          </div>

          <div className="field-group">
            <div className="field-label">
              <MapPin size={18} aria-hidden="true" />
              <span>장소</span>
            </div>
            <div className="place-grid" aria-label="장소 선택">
              {places.map((place) => (
                <button
                  key={place.id}
                  className={selectedPlaces.includes(place.id) ? "chip selected" : "chip"}
                  type="button"
                  onClick={() => togglePlace(place.id)}
                >
                  {place.label}
                </button>
              ))}
            </div>
          </div>

          <div className="field-group">
            <div className="field-label">
              <Languages size={18} aria-hidden="true" />
              <span>언어</span>
            </div>
            <div className="segmented" role="group" aria-label="언어 선택">
              {(["ko", "en", "mixed"] as const).map((code) => (
                <button
                  key={code}
                  className={language === code ? "segment active" : "segment"}
                  type="button"
                  onClick={() => setLanguage(code)}
                >
                  {code.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <label className="query-label" htmlFor="docent-query">
            질문
          </label>
          <textarea
            id="docent-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            maxLength={1000}
            rows={6}
          />

          <div className="action-row">
            <button
              className="icon-button"
              type="button"
              disabled
              title={voiceAdapter.stt.title}
              aria-label={voiceAdapter.stt.ariaLabel}
            >
              <Mic size={19} aria-hidden="true" />
            </button>
            <button
              className="primary-button"
              type="button"
              onClick={submit}
              disabled={status === "loading"}
            >
              <Send size={18} aria-hidden="true" />
              <span>{status === "loading" ? "검색 중" : "질문하기"}</span>
            </button>
          </div>

          <div className="scenario-row" aria-label="fixture 상태 선택">
            <button type="button" onClick={() => setQuery(initialQuery)}>
              답변
            </button>
            <button type="button" onClick={() => setQuery("모르는 사건을 알려줘")}>
              근거 없음
            </button>
            <button type="button" onClick={() => setQuery("error")}>
              오류
            </button>
          </div>
        </aside>

        <section className="answer-panel" aria-live="polite">
          {status === "idle" && (
            <InitialState onStart={submit} voiceMode={voiceAdapter.mode} />
          )}

          {status === "loading" && <p className="status-text">근거를 확인하는 중입니다.</p>}

          {status === "error" && (
            <div className="empty-state" role="alert">
              <p className="state-label">API error</p>
              <h2>{errorMessage}</h2>
            </div>
          )}

          {status === "success" && response && (
            <article className={response.abstained ? "answer abstained" : "answer"}>
              <div className="answer-header">
                <div>
                  <p className="state-label">
                    {response.abstained ? "No answer" : "Spoken answer"}
                  </p>
                  <h2>{response.spoken_answer}</h2>
                </div>
                <button
                  className="icon-button"
                  type="button"
                  disabled
                  title={voiceAdapter.tts.title}
                  aria-label={voiceAdapter.tts.ariaLabel}
                >
                  <Volume2 size={19} aria-hidden="true" />
                </button>
              </div>

              <div className="status-strip">
                <span>{response.abstained ? "abstained" : "answerable"}</span>
                <span>risk: {response.unsupported_claim_risk}</span>
                <span>solar calls: {response.usage.solar_call_count}</span>
                <span>
                  voice calls: {voiceAdapter.metrics.liveSttCallCount}/
                  {voiceAdapter.metrics.liveTtsCallCount}
                </span>
                <span>
                  active route:{" "}
                  {response.classifier_router_dry_run.active_route_applied ? "on" : "off"}
                </span>
              </div>

              <button
                className="fold-button"
                type="button"
                onClick={() => setDetailsOpen((open) => !open)}
                aria-expanded={detailsOpen}
              >
                <FileText size={18} aria-hidden="true" />
                <span>상세 답변</span>
                {detailsOpen ? (
                  <ChevronUp size={18} aria-hidden="true" />
                ) : (
                  <ChevronDown size={18} aria-hidden="true" />
                )}
              </button>
              {detailsOpen && <p className="detail-answer">{response.answer}</p>}

              <button
                className="fold-button"
                type="button"
                onClick={() => setCitationsOpen((open) => !open)}
                aria-expanded={citationsOpen}
              >
                <FileText size={18} aria-hidden="true" />
                <span>근거 {response.citations.length}</span>
                {citationsOpen ? (
                  <ChevronUp size={18} aria-hidden="true" />
                ) : (
                  <ChevronDown size={18} aria-hidden="true" />
                )}
              </button>
              {citationsOpen && <CitationDrawer response={response} />}
            </article>
          )}
        </section>
      </section>
    </main>
  );
}

function InitialState({
  onStart,
  voiceMode,
}: {
  onStart: () => void;
  voiceMode: string;
}) {
  return (
    <div className="empty-state">
      <p className="state-label">Ready</p>
      <h2>경복궁과 한양의 맥락을 바로 확인합니다.</h2>
      <div className="status-strip">
        <span>contract fixture</span>
        <span>voice {voiceMode}</span>
        <span>voice live calls: 0</span>
      </div>
      <button className="primary-button" type="button" onClick={onStart}>
        <Send size={18} aria-hidden="true" />
        <span>시작</span>
      </button>
    </div>
  );
}

function CitationDrawer({ response }: { response: ChatResponse }) {
  if (response.citations.length === 0) {
    return <p className="citation-empty">표시할 citation이 없습니다.</p>;
  }

  return (
    <ul className="citation-list" aria-label="citation drawer">
      {response.citations.map((citation) => (
        <li className="citation-item" key={citation.citation_id}>
          <div>
            <strong>{citation.citation_id}</strong>
            <span>{citation.doc_id}</span>
          </div>
          <dl>
            <div>
              <dt>source</dt>
              <dd>{citation.source_rank}</dd>
            </div>
            <div>
              <dt>pack</dt>
              <dd>{citation.pack_rank}</dd>
            </div>
            <div>
              <dt>recoverable</dt>
              <dd>{citation.citation_recoverable ? "true" : "false"}</dd>
            </div>
          </dl>
        </li>
      ))}
    </ul>
  );
}
