import { afterEach, describe, expect, it, vi } from "vitest";
import aboutPageSource from "./components/AboutPage.tsx?raw";
import { fetchDemoLimits, limitsSentence } from "./demoLimits";

const LIMITS = { daily_question_cap: 7, per_ip_limit: 2, per_ip_window_minutes: 15 };

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("limitsSentence", () => {
  it("states the values the server reports", () => {
    expect(limitsSentence(LIMITS)).toBe(
      "The live demo answers 7 questions a day in total, and 2 per visitor per 15 minutes.",
    );
  });

  it("states no number when the API didn't answer", () => {
    expect(limitsSentence(null)).not.toMatch(/\d/);
  });
});

describe("fetchDemoLimits", () => {
  it("returns what the API sends", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(LIMITS))));
    expect(await fetchDemoLimits()).toEqual(LIMITS);
  });

  it("returns null on an error status", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 502 })));
    expect(await fetchDemoLimits()).toBeNull();
  });

  it("returns null when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("offline"))));
    expect(await fetchDemoLimits()).toBeNull();
  });
});

describe("the About page", () => {
  it("gets the sentence from the server's values, and keeps no number of its own", () => {
    expect(aboutPageSource).toContain("{limitsSentence(limits)}");
    expect(aboutPageSource).not.toMatch(/\d+ questions/);
  });
});
