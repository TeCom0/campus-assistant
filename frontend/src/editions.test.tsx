// @vitest-environment jsdom
// The catalog edition the interface names comes from GET /editions (A2.3). With the edition
// the server reports today, every text reads exactly as the built-in one (scope.test.tsx pins
// that text, rendered without effects, so it also checks the fallback). With another edition,
// as after an activation or a rollback, all four places name it; if the API fails, the
// built-in text stays.
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LIMITATIONS } from "./about";
import { AboutPage } from "./components/AboutPage";
import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";
import {
  BUILT_IN_EDITION,
  fetchCatalogEdition,
  forgetCatalogEdition,
  withEdition,
} from "./editions";
import scope from "./scope.json";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const TODAY = { label: "2024-2025", card_title: "Academic Catalog 2024–2025", course_tables: true };
const NEWER = { label: "2025-2026", card_title: "Academic Catalog 2025–2026", course_tables: true };
const SCHOLARSHIPS = { label: "2026", card_title: "Graduate scholarships", course_tables: false };

function served(...editions: object[]): Response {
  return new Response(JSON.stringify({ editions }));
}

// Answers /editions with `editions`, and /limits as the About page asks for it too.
function stubApi(editions: () => Promise<Response>) {
  const fetchMock = vi.fn(async (url: string) =>
    url.endsWith("/limits")
      ? new Response(JSON.stringify({ daily_question_cap: 35, per_ip_limit: 5, per_ip_window_minutes: 10 }))
      : editions(),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function render(element: React.ReactElement): Promise<string> {
  const container = document.createElement("div");
  const root = createRoot(container);
  await act(async () => root.render(element));
  await act(async () => {}); // let the fetch's promise settle and re-render
  const text = container.textContent ?? "";
  act(() => root.unmount());
  return text;
}

const composer = <Composer value="" onChange={() => {}} onSubmit={() => {}} busy={false} placeholder="" />;

beforeEach(() => {
  forgetCatalogEdition();
  // The About page's diagram asks whether this is a phone; jsdom has no matchMedia.
  window.matchMedia = (() => ({ matches: false, addEventListener() {}, removeEventListener() {} })) as never;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchCatalogEdition", () => {
  it("takes the one catalog edition, with an en dash", async () => {
    stubApi(async () => served(SCHOLARSHIPS, NEWER));
    expect(await fetchCatalogEdition()).toEqual({ label: "2025–2026", cardTitle: "Academic Catalog 2025–2026" });
  });

  it("returns what the built-in text says, for the edition in force today", async () => {
    stubApi(async () => served(TODAY));
    expect(await fetchCatalogEdition()).toEqual(BUILT_IN_EDITION);
  });

  it.each([
    ["an error status", async () => new Response("", { status: 503 })],
    ["a failed request", async () => Promise.reject(new TypeError("offline"))],
    ["no catalog edition", async () => served(SCHOLARSHIPS)],
    ["two catalog editions", async () => served(TODAY, NEWER)],
    ["a malformed edition", async () => served({ course_tables: true, label: 2025 })],
  ])("returns null on %s, so the built-in text stands", async (_case, answer) => {
    stubApi(answer);
    expect(await fetchCatalogEdition()).toBeNull();
  });
});

describe("the generated sentences", () => {
  it("each hold the built-in year exactly once, so swapping it can't miss or double", () => {
    const sentences = [scope.first_screen_documents, scope.about_documents, LIMITATIONS[3]];
    for (const sentence of sentences) {
      expect(sentence.split(BUILT_IN_EDITION.label)).toHaveLength(2);
    }
    expect(withEdition(scope.about_documents, { label: "2025–2026", cardTitle: "" })).toBe(
      "2025–2026 Academic Catalog and scholarship pages",
    );
  });
});

describe("the interface", () => {
  it("reads exactly as before with the edition in force today", async () => {
    stubApi(async () => served(TODAY));
    expect(await render(composer)).toContain(
      "Answers are based on the Academic Catalog 2024–2025. Unofficial student project",
    );
    expect(await render(<EmptyState onAsk={() => {}} />)).toContain(
      "An AI agent searches the public 2024–2025 Academic Catalog and AUI's scholarship pages, looks up",
    );
    const about = await render(<AboutPage />);
    expect(about).toContain("search the 2024–2025 Academic Catalog and scholarship pages or to look up");
    expect(about).toContain("One catalog edition, 2024–2025; newer editions exist.");
  });

  it("names another edition everywhere once the server reports it", async () => {
    stubApi(async () => served(SCHOLARSHIPS, NEWER));
    expect(await render(composer)).toContain("Answers are based on the Academic Catalog 2025–2026.");
    expect(await render(<EmptyState onAsk={() => {}} />)).toContain(
      "searches the public 2025–2026 Academic Catalog and AUI's scholarship pages",
    );
    const about = await render(<AboutPage />);
    expect(about).toContain("search the 2025–2026 Academic Catalog and scholarship pages");
    expect(about).toContain("One catalog edition, 2025–2026; newer editions exist.");
    expect(about).not.toContain("2024–2025");
  });

  it("keeps the built-in text when the API fails", async () => {
    stubApi(async () => new Response("", { status: 503 }));
    expect(await render(composer)).toContain("Answers are based on the Academic Catalog 2024–2025.");
  });

  it("asks once per page, however many places name the edition", async () => {
    const fetchMock = stubApi(async () => served(TODAY));
    await render(
      <>
        <EmptyState onAsk={() => {}} />
        {composer}
      </>,
    );
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/editions"))).toHaveLength(1);
  });
});
