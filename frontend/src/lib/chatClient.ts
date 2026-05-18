import { answerableFixture, noAnswerFixture } from "../fixtures/chatFixtures";
import type { ChatRequest, ChatResponse } from "../types/chat";

const apiBaseUrl = import.meta.env.VITE_HISTORY_DOCENT_API_BASE_URL as string | undefined;

export async function sendChat(request: ChatRequest): Promise<ChatResponse> {
  if (request.query.toLowerCase().includes("error")) {
    throw new Error("fixture_api_error");
  }

  if (!apiBaseUrl) {
    return fixtureResponseFor(request);
  }

  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/api/v1/chat`, {
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
