import { fireEvent, render, screen } from "@testing-library/react";
import App from "./App";

describe("History Docent voice UI skeleton", () => {
  test("renders answerable fixture with spoken answer and citations", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "시작" }));

    expect(await screen.findByText("Spoken answer")).toBeInTheDocument();
    expect(screen.getByText(/경복궁은 조선이 한양을 수도로 삼은 뒤/)).toBeInTheDocument();
    expect(screen.getByText("근거 1")).toBeInTheDocument();
    expect(screen.getByText("cite-fixture-001")).toBeInTheDocument();
    expect(screen.getByText("solar calls: 0")).toBeInTheDocument();
  });

  test("keeps detailed answer behind an explicit disclosure", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "시작" }));
    await screen.findByText("Spoken answer");

    expect(screen.queryByText(/경복궁은 조선 왕조가 한양을 수도로 삼은 뒤/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "상세 답변" }));
    expect(screen.getByText(/경복궁은 조선 왕조가 한양을 수도로 삼은 뒤/)).toBeInTheDocument();
  });

  test("renders no-answer state without citations", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "근거 없음" }));
    fireEvent.click(screen.getByRole("button", { name: "질문하기" }));

    expect(await screen.findByText("No answer")).toBeInTheDocument();
    expect(screen.getByText(/지금 근거로는 답하기 어렵습니다/)).toBeInTheDocument();
    expect(screen.getByText("근거 0")).toBeInTheDocument();
    expect(screen.getByText("abstained")).toBeInTheDocument();
  });

  test("renders sanitized API error state", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "오류" }));
    fireEvent.click(screen.getByRole("button", { name: "질문하기" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "요청을 처리하지 못했습니다.",
    );
    expect(screen.queryByText("fixture_api_error")).not.toBeInTheDocument();
  });

  test("renders voice fallback controls in jsdom", async () => {
    render(<App />);

    expect(screen.getByRole("button", { name: "음성 입력 미지원" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "시작" }));

    expect(await screen.findByRole("button", { name: "음성 재생 미지원" })).toBeDisabled();
    expect(screen.getByText(/경복궁은 조선이 한양을 수도로 삼은 뒤/)).toBeInTheDocument();
  });
});
