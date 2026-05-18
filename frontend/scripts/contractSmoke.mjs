const frontendUrl = process.env.HISTORY_DOCENT_FRONTEND_URL ?? "http://127.0.0.1:5173";
const apiBaseUrl = process.env.HISTORY_DOCENT_API_BASE_URL ?? "http://127.0.0.1:8000";

const answerableRequest = {
  request_id: "voice-ui-smoke-answerable",
  query: "경복궁을 한양 맥락에서 짧게 설명해줘",
  language: "ko",
  query_type: "place_story",
  place_context: ["gyeongbokgung"],
  voice_mode: true,
  retrieval_mode: "contract_only",
  provider_mode: "contract_only",
  active_route_mode: "disabled",
};

const noAnswerRequest = {
  request_id: "voice-ui-smoke-no-answer",
  query: "이 자료에 없는 현대 스포츠 기록을 알려줘",
  language: "ko",
  query_type: "no_answer",
  place_context: [],
  voice_mode: true,
  retrieval_mode: "contract_only",
  provider_mode: "contract_only",
  active_route_mode: "disabled",
};

async function main() {
  const frontend = await fetch(frontendUrl);
  assert(frontend.ok, `frontend status ${frontend.status}`);

  const answerable = await postChat(answerableRequest);
  assert(answerable.abstained === false, "answerable response should not abstain");
  assert(answerable.spoken_answer, "answerable response should include spoken_answer");
  assert(answerable.citations.length === 1, "answerable response should include one citation");
  assert(answerable.usage.solar_call_count === 0, "answerable response should not call Solar");
  assert(
    answerable.classifier_router_dry_run.active_route_applied === false,
    "answerable active route should remain disabled",
  );

  const noAnswer = await postChat(noAnswerRequest);
  assert(noAnswer.abstained === true, "no-answer response should abstain");
  assert(noAnswer.citations.length === 0, "no-answer response should not include citations");
  assert(noAnswer.usage.solar_call_count === 0, "no-answer response should not call Solar");

  console.log(
    JSON.stringify(
      {
        frontend_status: frontend.status,
        answerable_status: "pass",
        no_answer_status: "pass",
        live_solar_call_count: answerable.usage.solar_call_count + noAnswer.usage.solar_call_count,
      },
      null,
      2,
    ),
  );
}

async function postChat(payload) {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  assert(response.ok, `chat status ${response.status}`);
  return response.json();
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

await main();
