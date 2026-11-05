// @vitest-environment jsdom
// The real App in a DOM, because this is about state after a failed fetch, which
// a static render can't reach. When the server refuses a question, the message
// says to edit it, so the question must come back to the composer.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "./App";

const QUESTION = "How many credits can I transfer?";

let root: Root;
let container: HTMLDivElement;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  window.scrollTo = () => {}; // jsdom has no layout
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia;
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root.render(<App />));
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

function composer(): HTMLTextAreaElement {
  return container.querySelector("textarea")!;
}

// Through the native setter, as React only sees a change made that way.
function type(text: string) {
  const setValue = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
  act(() => {
    setValue.call(composer(), text);
    composer().dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function send() {
  await act(async () => {
    container
      .querySelector<HTMLButtonElement>('button[aria-label="Send question"]')!
      .click();
  });
}

it.each([
  [413, ""], // Caddy's has no body
  [422, '{"kind":"invalid_request"}'],
])("a question refused with HTTP %i returns to the composer", async (status, body) => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body, { status })));
  type(QUESTION);

  await send();

  expect(composer().value).toBe(QUESTION);
  expect(container.querySelector(".state-error")?.textContent).toContain("couldn't be sent");
  expect(container.textContent).not.toContain("Ask again");
});

it("doesn't overwrite what was typed while the request was on its way", async () => {
  let respond: (response: Response) => void = () => {};
  vi.stubGlobal(
    "fetch",
    vi.fn(() => new Promise<Response>((resolve) => (respond = resolve))),
  );
  type(QUESTION);
  await send();
  expect(composer().value).toBe(""); // it left the composer when sent

  type("A newer question");
  await act(async () => respond(new Response("", { status: 413 })));

  expect(composer().value).toBe("A newer question");
});

it("leaves the composer empty after any other failure, where Ask again resends it", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 500 })));
  type(QUESTION);

  await send();

  expect(composer().value).toBe("");
  expect(container.textContent).toContain("Ask again");
});
