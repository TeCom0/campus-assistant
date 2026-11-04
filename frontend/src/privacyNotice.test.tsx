import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Composer } from "./components/Composer";
import { privacyNotice } from "./privacyNotice";

function composerIn(browserLanguage: string): string {
  vi.stubGlobal("navigator", { language: browserLanguage });
  return renderToStaticMarkup(
    <Composer value="" onChange={() => {}} onSubmit={() => {}} busy={false} placeholder="" />,
  );
}

// renderToStaticMarkup escapes apostrophes, so compare against the escaped form.
function escaped(text: string): string {
  return text.replaceAll("'", "&#x27;");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("privacyNotice", () => {
  it.each(["fr", "fr-FR", "fr-MA", "FR-ca"])("is French for %s", (browserLanguage) => {
    expect(privacyNotice(browserLanguage).language).toBe("fr");
  });

  it.each(["en", "en-US", "ar-MA", "es", "fry", ""])("is English for %s", (browserLanguage) => {
    expect(privacyNotice(browserLanguage).language).toBe("en");
  });

  // The whole sentences: a stray character would be published as is.
  it("has the agreed wording in both languages", () => {
    expect(privacyNotice("en").text).toBe(
      "Please don't enter personal information (names, student IDs, grades): questions are processed by a third-party AI provider.",
    );
    expect(privacyNotice("fr").text).toBe(
      "N'indiquez pas d'informations personnelles (noms, numéros d'étudiant, notes) : les questions sont traitées par un fournisseur d'IA tiers.",
    );
  });
});

describe("Composer", () => {
  it("shows the English notice to an English browser, marked as English", () => {
    const html = composerIn("en-US");
    expect(html).toContain(`<p class="disclaimer" lang="en">${escaped(privacyNotice("en").text)}</p>`);
    expect(html).not.toContain(escaped(privacyNotice("fr").text));
  });

  it("shows the French notice to a French browser, marked as French", () => {
    const html = composerIn("fr-MA");
    expect(html).toContain(`<p class="disclaimer" lang="fr">${escaped(privacyNotice("fr").text)}</p>`);
    expect(html).not.toContain(escaped(privacyNotice("en").text));
  });

  it("keeps the unofficial-project disclaimer next to the notice", () => {
    expect(composerIn("fr")).toContain("Unofficial student project");
  });
});
