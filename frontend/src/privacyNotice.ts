// Shown under the composer. The chat UI has no language setting of its own (it
// is written in English and answers in the language of each question), so the
// browser's language is the only thing known before the visitor types anything.
export type NoticeLanguage = "en" | "fr";

const NOTICES: Record<NoticeLanguage, string> = {
  en: "Please don't enter personal information (names, student IDs, grades): questions are processed by a third-party AI provider.",
  // French puts a space before the colon: a no-break one, so the colon can't start a line.
  fr: "N'indiquez pas d'informations personnelles (noms, numéros d'étudiant, notes) : les questions sont traitées par un fournisseur d'IA tiers.",
};

// The part before the "-": "fr", "fr-MA", "FR-ca" are French, "fry" (Frisian)
// isn't. Anything else gets the English text.
export function noticeLanguage(browserLanguage: string): NoticeLanguage {
  return browserLanguage.toLowerCase().split("-")[0] === "fr" ? "fr" : "en";
}

export function privacyNotice(browserLanguage: string): { language: NoticeLanguage; text: string } {
  const language = noticeLanguage(browserLanguage);
  return { language, text: NOTICES[language] };
}
