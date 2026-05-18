import { answerableFixture, noAnswerFixture } from "../fixtures/chatFixtures";
import { resolveChatEndpoint, sendChat } from "./chatClient";
import type { ChatRequest } from "../types/chat";

const baseRequest: ChatRequest = {
  query: "경복궁을 한양 맥락에서 설명해줘",
  language: "ko",
  query_type: "place_story",
  place_context: ["gyeongbokgung"],
  voice_mode: true,
  retrieval_mode: "contract_only",
  provider_mode: "contract_only",
  active_route_mode: "disabled",
};

describe("chatClient backend contract mode", () => {
  test("uses same-origin proxy endpoint when backend mode has no base URL", async () => {
    const fetcher = vi.fn(async () => responseFrom(answerableFixture));

    const response = await sendChat(baseRequest, {
      mode: "backend",
      apiBaseUrl: "",
      fetcher: fetcher as typeof fetch,
    });

    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/chat",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );
    expect(response.spoken_answer).toContain("경복궁");
    expect(response.usage.solar_call_count).toBe(0);
  });

  test("uses explicit backend base URL when provided", async () => {
    const fetcher = vi.fn(async () => responseFrom(noAnswerFixture));

    const response = await sendChat(
      { ...baseRequest, query_type: "no_answer", query: "현대 스포츠 기록 알려줘" },
      {
        mode: "backend",
        apiBaseUrl: "http://127.0.0.1:8000/",
        fetcher: fetcher as typeof fetch,
      },
    );

    expect(fetcher).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/chat",
      expect.any(Object),
    );
    expect(response.abstained).toBe(true);
    expect(response.citations).toEqual([]);
  });

  test("keeps fixture error branch out of backend mode", async () => {
    const fetcher = vi.fn(async () => responseFrom(answerableFixture));

    await sendChat(
      { ...baseRequest, query: "error" },
      {
        mode: "backend",
        fetcher: fetcher as typeof fetch,
      },
    );

    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  test("resolves contract smoke endpoints", () => {
    expect(resolveChatEndpoint()).toBe("/api/v1/chat");
    expect(resolveChatEndpoint("http://127.0.0.1:8000/")).toBe(
      "http://127.0.0.1:8000/api/v1/chat",
    );
  });
});

function responseFrom(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
