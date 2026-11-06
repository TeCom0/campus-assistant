import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LIMITATIONS } from "./about";
import { AboutPage } from "./components/AboutPage";
import { ArchitectureSvg } from "./components/ArchitectureDiagram";
import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";

// The sentences a student reads about what the assistant covers. The words come
// from the generated scope.json (backend/app/scope.py). These are written out in
// full so that a change to the generated text shows up here, as a choice.

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the text about what the assistant covers", () => {
  it("is right on the first screen", () => {
    const html = renderToStaticMarkup(<EmptyState onAsk={() => {}} />);
    expect(html).toContain(
      "An AI agent searches the public 2024–2025 Academic Catalog and AUI&#x27;s scholarship pages, looks up",
    );
  });

  it("is right in the note under the composer", () => {
    const html = renderToStaticMarkup(
      <Composer value="" onChange={() => {}} onSubmit={() => {}} busy={false} placeholder="" />,
    );
    expect(html).toContain("Answers are based on the Academic Catalog 2024–2025. Unofficial student project");
  });

  it("is right on the About page", () => {
    // The page draws the diagram, which asks the browser whether this is a phone.
    vi.stubGlobal("window", {
      matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }),
    });
    const html = renderToStaticMarkup(<AboutPage />);
    expect(html).toContain(
      "An agent decides whether to search the 2024–2025 Academic Catalog and scholarship pages or to look up",
    );
  });

  it("is right in the limitations", () => {
    expect(LIMITATIONS).toContain("One catalog edition, 2024–2025; newer editions exist.");
  });

  it("is right on the diagram", () => {
    const html = renderToStaticMarkup(<ArchitectureSvg idPrefix="test" />);
    expect(html).toContain("catalog PDF + 2 scholarship pages → clean → chunk → embed");
  });
});
