import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RejectedError, streamChat } from "./chatStream";
import { AssistantTurn } from "./components/AssistantTurn";
import { Composer } from "./components/Composer";
import { limitMessages } from "./limitMessages";
import type { AssistantMessage } from "./messages";
import {
  charCount,
  chatRequestBody,
  historyToSend,
  MAX_ASSISTANT_CONTENT_CHARS,
  MAX_BODY_BYTES,
  MAX_QUESTION_CHARS,
  MAX_REQUEST_MESSAGES,
  MAX_USER_CONTENT_CHARS,
} from "./requestLimits";
import type { HistoryMessage } from "./types";

afterEach(() => {
  vi.unstubAllGlobals();
});

const user = (content: string): HistoryMessage => ({ role: "user", content });
const assistant = (content: string): HistoryMessage => ({ role: "assistant", content });

// n question-and-answer turns, each one recognisable: q0/a0 is the oldest.
function pairs(n: number, answer: (i: number) => string = (i) => `a${i}`): HistoryMessage[] {
  return Array.from({ length: n }, (_, i) => [user(`q${i}`), assistant(answer(i))]).flat();
}

function bytesSent(question: string, messages: HistoryMessage[]): number {
  return new TextEncoder().encode(chatRequestBody(question, messages)).length;
}

// Every answer kept is right after its own question: no turn was split.
function expectWholeTurns(sent: HistoryMessage[]) {
  sent.forEach((message, i) => {
    if (message.role === "assistant") {
      expect(sent[i - 1].role).toBe("user");
      expect(message.content.slice(0, 2).replace("a", "q")).toBe(sent[i - 1].content.slice(0, 2));
    }
  });
  if (sent.length > 0) expect(sent[0].role).toBe("user");
}

describe("charCount", () => {
  it("counts as Python's len does", () => {
    expect(charCount("é")).toBe(1);
    expect("😀".length).toBe(2);
    expect(charCount("😀")).toBe(1);
  });
});

describe("historyToSend: the 20-message cap", () => {
  it("sends everything under the limits, unchanged", () => {
    const history = pairs(3);
    expect(historyToSend("next", history)).toEqual(history);
  });

  it("keeps exactly 10 turns: 20 messages", () => {
    const sent = historyToSend("next", pairs(10));
    expect(sent).toHaveLength(MAX_REQUEST_MESSAGES);
    expect(sent[0]).toEqual(user("q0"));
  });

  it("drops the oldest whole turn at 11 turns", () => {
    const sent = historyToSend("next", pairs(11));
    expect(sent).toHaveLength(MAX_REQUEST_MESSAGES);
    expect(sent[0]).toEqual(user("q1"));
    expect(sent.at(-1)).toEqual(assistant("a10"));
    expectWholeTurns(sent);
  });

  it("drops a whole turn even when dropping one message would have been enough", () => {
    // 10 pairs and a question whose answer was interrupted: 21 messages. Removing
    // only q0 would reach 20, but leave a0 with no question.
    const sent = historyToSend("next", [...pairs(10), user("q10")]);
    expect(sent).toHaveLength(19);
    expect(sent[0]).toEqual(user("q1"));
    expect(sent.at(-1)).toEqual(user("q10"));
    expectWholeTurns(sent);
  });

  it("keeps a question whose answer is missing as a turn of its own", () => {
    const history = [user("q0"), user("q1"), assistant("a1")];
    expect(historyToSend("next", history)).toEqual(history);
  });

  it("stays under the cap for any length of conversation, with whole turns", () => {
    for (let n = 0; n <= 40; n++) {
      const sent = historyToSend("next", pairs(n));
      expect(sent.length).toBeLessThanOrEqual(MAX_REQUEST_MESSAGES);
      expectWholeTurns(sent);
    }
  });
});

describe("historyToSend: the 64 KiB budget", () => {
  // The cap alone would allow 10 of these: 10 x 12,000 bytes is far over 64 KiB.
  const accented = (i: number) => `a${i}` + "é".repeat(MAX_ASSISTANT_CONTENT_CHARS - 2);

  it("drops the oldest whole turns until the body fits", () => {
    const history = pairs(10, accented);
    const sent = historyToSend("next", history);

    expect(sent.length).toBeLessThan(history.length);
    expect(sent.at(-1)).toEqual(history.at(-1));
    expect(bytesSent("next", sent)).toBeLessThanOrEqual(MAX_BODY_BYTES);
    expectWholeTurns(sent);
  });

  it("keeps as many turns as fit: one more would go over", () => {
    const history = pairs(10, accented);
    const sent = historyToSend("next", history);
    const oneMore = history.slice(history.length - sent.length - 2);
    expect(bytesSent("next", oneMore)).toBeGreaterThan(MAX_BODY_BYTES);
  });

  it("measures bytes, not characters", () => {
    const ascii = historyToSend("next", pairs(10, (i) => `a${i}` + "e".repeat(5998)));
    const accents = historyToSend("next", pairs(10, accented));
    // Same characters: 10 ASCII turns fit, the accented ones take twice the bytes.
    expect(ascii).toHaveLength(20);
    expect(accents.length).toBeLessThan(ascii.length);
  });

  it("counts what JSON adds: a newline is written as 2 characters", () => {
    const history = pairs(10, (i) => `a${i}` + "\n".repeat(5998));
    const sent = historyToSend("next", history);
    expect(sent.length).toBeLessThan(history.length);
    expect(bytesSent("next", sent)).toBeLessThanOrEqual(MAX_BODY_BYTES);
    expectWholeTurns(sent);
  });

  it("counts the question too", () => {
    const history = pairs(10, accented);
    const short = historyToSend("next", history);
    const long = "é".repeat(MAX_QUESTION_CHARS);
    const sent = historyToSend(long, history);
    expect(bytesSent(long, sent)).toBeLessThanOrEqual(MAX_BODY_BYTES);
    expect(sent.length).toBeLessThanOrEqual(short.length);
  });
});

describe("historyToSend: the field limits", () => {
  it("leaves out a whole turn whose answer is over the limit", () => {
    const tooLong = "a1" + "x".repeat(MAX_ASSISTANT_CONTENT_CHARS);
    const sent = historyToSend("next", [user("q0"), assistant("a0"), user("q1"), assistant(tooLong), user("q2"), assistant("a2")]);
    expect(sent).toEqual([user("q0"), assistant("a0"), user("q2"), assistant("a2")]);
  });

  it("leaves out a whole turn whose question is over the limit", () => {
    const tooLong = "q1" + "x".repeat(MAX_USER_CONTENT_CHARS);
    const sent = historyToSend("next", [user("q0"), assistant("a0"), user(tooLong), assistant("a1")]);
    expect(sent).toEqual([user("q0"), assistant("a0")]);
  });

  it("keeps content exactly at the limit, counted as the server counts it", () => {
    const history = [
      user("😀".repeat(MAX_USER_CONTENT_CHARS)),
      assistant("😀".repeat(MAX_ASSISTANT_CONTENT_CHARS)),
    ];
    expect(historyToSend("next", history)).toEqual(history);
  });
});

function composerWith(value: string, browserLanguage = "en-US", busy = false): string {
  vi.stubGlobal("navigator", { language: browserLanguage });
  return renderToStaticMarkup(
    <Composer value={value} onChange={() => {}} onSubmit={() => {}} busy={busy} placeholder="" />,
  );
}

describe("the composer's counter", () => {
  it("is hidden below 1,800 characters", () => {
    expect(composerWith("x".repeat(1799))).not.toContain("composer-count");
  });

  it("appears at 1,800, and sending stays possible up to the limit", () => {
    const at1800 = composerWith("x".repeat(1800));
    expect(at1800).toContain("1,800 / 2,000");
    expect(at1800).not.toContain("disabled");

    const atLimit = composerWith("x".repeat(MAX_QUESTION_CHARS));
    expect(atLimit).toContain("2,000 / 2,000");
    expect(atLimit).not.toContain("Too long");
    expect(atLimit).not.toContain("disabled");
  });

  it("blocks sending over the limit, and keeps the text", () => {
    const over = composerWith("x".repeat(MAX_QUESTION_CHARS + 1));
    expect(over).toContain("2,001 / 2,000");
    expect(over).toContain("Too long");
    expect(over).toContain("composer-count over");
    expect(over).toContain('aria-invalid="true"');
    expect(over).toMatch(/<button[^>]*disabled/);
    expect(over).not.toContain("maxLength");
    expect(over).toContain("x".repeat(MAX_QUESTION_CHARS + 1));
  });

  it("counts after trimming, as the server does", () => {
    const padded = composerWith(`   ${"x".repeat(MAX_QUESTION_CHARS)}\n\n`);
    expect(padded).toContain("2,000 / 2,000");
    expect(padded).not.toMatch(/<button[^>]*disabled/);
  });

  it("counts an emoji as one character", () => {
    expect(composerWith("😀".repeat(MAX_QUESTION_CHARS))).not.toMatch(/<button[^>]*disabled/);
  });

  it("is in French for a French browser", () => {
    const over = composerWith("x".repeat(MAX_QUESTION_CHARS + 1), "fr-MA");
    const { counter, tooLong } = limitMessages("fr-MA");
    expect(tooLong).toContain("Trop longue");
    expect(over).toContain(counter(MAX_QUESTION_CHARS + 1));
    expect(over).toContain('lang="fr"');
  });
});

describe("a refused request", () => {
  function stubResponse(status: number, body: string) {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body, { status })));
  }

  it.each([
    [413, ""], // Caddy's has no body
    [413, '{"kind": "too_large"}'],
    [422, '{"kind": "invalid_request"}'],
  ])("HTTP %i with body %j is a RejectedError", async (status, body) => {
    stubResponse(status, body);
    await expect(streamChat("hi", [], () => {})).rejects.toBeInstanceOf(RejectedError);
  });

  it("a 500 is not", async () => {
    stubResponse(500, "");
    await expect(streamChat("hi", [], () => {})).rejects.not.toBeInstanceOf(RejectedError);
  });

  it("sends the same body historyToSend measured", async () => {
    const fetchStub = vi.fn().mockResolvedValue(new Response("", { status: 200 }));
    vi.stubGlobal("fetch", fetchStub);
    const history = pairs(2);
    await streamChat("hi", history, () => {});
    expect(fetchStub.mock.calls[0][1].body).toBe(chatRequestBody("hi", history));
  });

  it.each([
    ["en-US", "This question couldn&#x27;t be sent"],
    ["fr-FR", "Cette question n&#x27;a pas pu être envoyée"],
  ])("shows its own message, with no Ask again (%s)", (browserLanguage, title) => {
    const refused = limitMessages(browserLanguage);
    const message: AssistantMessage = {
      role: "assistant",
      text: "",
      steps: [],
      citations: [],
      status: "rejected",
      error: refused.rejectedMessage,
      errorTitle: refused.rejectedTitle,
    };
    const html = renderToStaticMarkup(
      <AssistantTurn message={message} messageIndex={1} isLast onRetry={() => {}} onAskExample={() => {}} />,
    );
    expect(html).toContain(title);
    expect(html).not.toContain("Ask again");
    expect(html).not.toContain("connection");
  });
});
