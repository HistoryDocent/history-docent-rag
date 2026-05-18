import { answerableFixture, noAnswerFixture } from "../fixtures/chatFixtures";
import type { ChatRequest, ChatResponse } from "../types/chat";

type ChatMode = "fixture" | "backend";

interface SendChatOptions {
  mode?: ChatMode;
  apiBaseUrl?: string;
  fetcher?: typeof fetch;
}

const envChatMode: ChatMode =
  import.meta.env.VITE_HISTORY_DOCENT_CHAT_MODE === "backend" ? "backend" : "fixture";
const envApiBaseUrl = import.meta.env.VITE_HISTORY_DOCENT_API_BASE_URL ?? "";

export async function sendChat(
  request: ChatRequest,
  options: SendChatOptions = {},
): Promise<ChatResponse> {
  const mode = options.mode ?? envChatMode;

  if (mode === "fixture") {
    return sendFixtureChat(request);
  }

  const response = await (options.fetcher ?? fetch)(resolveChatEndpoint(options.apiBaseUrl), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error("chat_request_failed");
  }

  return (await response.json()) as ChatResponse;
}

export function resolveChatEndpoint(apiBaseUrl = envApiBaseUrl): string {
  const trimmed = apiBaseUrl.trim().replace(/\/$/, "");
  return trimmed ? `${trimmed}/api/v1/chat` : "/api/v1/chat";
}

function sendFixtureChat(request: ChatRequest): Promise<ChatResponse> {
  if (request.query.toLowerCase().includes("error")) {
    throw new Error("fixture_api_error");
  }

  return Promise.resolve(fixtureResponseFor(request));
}

function fixtureResponseFor(request: ChatRequest): ChatResponse {
  const normalizedQuery = request.query.toLowerCase();
  const shouldAbstain =
    normalizedQuery.includes("모르는") ||
    normalizedQuery.includes("근거 없음") ||
    normalizedQuery.includes("unknown");

  const fixture = shouldAbstain ? noAnswerFixture : answerableFixture;

  return {
    ...fixture,
    request_id: request.request_id ?? fixture.request_id,
    query_type: shouldAbstain ? "no_answer" : request.query_type,
    place_ids: shouldAbstain ? [] : request.place_context,
  };
}
