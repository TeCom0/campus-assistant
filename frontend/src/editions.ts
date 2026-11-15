import { useEffect, useState } from "react";
import { API_URL } from "./chatStream";
import scope from "./scope.json";

// Which catalog edition is in force, as the API reports it (GET /editions, A2.3). Status
// lives in the server's database and can change without a rebuild (an activation, or a
// rollback), so the interface asks instead of keeping a copy that can drift: the generated
// scope.json is the text it was built with, used until the answer arrives and whenever the
// API doesn't answer, like demoLimits.ts.
export interface CatalogEdition {
  label: string; // "2024–2025", with an en dash as everywhere it's shown
  cardTitle: string; // "Academic Catalog 2024–2025"
}

export const BUILT_IN_EDITION: CatalogEdition = {
  label: scope.catalog_label,
  cardTitle: scope.catalog_card_title,
};

interface ServedEdition {
  label: string;
  card_title: string;
  course_tables: boolean;
}

// null if the API doesn't answer, or if it doesn't name exactly one catalog edition: the
// built-in text then stands rather than a guess.
export async function fetchCatalogEdition(): Promise<CatalogEdition | null> {
  try {
    const response = await fetch(`${API_URL}/editions`);
    if (!response.ok) return null;
    const body = (await response.json()) as { editions?: ServedEdition[] };
    const catalogs = (body.editions ?? []).filter((edition) => edition.course_tables);
    if (catalogs.length !== 1) return null;
    const [catalog] = catalogs;
    if (typeof catalog.label !== "string" || typeof catalog.card_title !== "string") return null;
    // The registry writes "2024-2025"; app/scope.py shows it with an en dash, and so does this.
    return { label: catalog.label.replace(/-/g, "–"), cardTitle: catalog.card_title };
  } catch {
    return null;
  }
}

// The generated sentences that name the year ("the public 2024–2025 Academic Catalog and
// ...") keep their wording; only the year is swapped for the one in force. scope.test.tsx
// checks each of them holds the built-in label exactly once.
export function withEdition(text: string, edition: CatalogEdition): string {
  return text.replace(BUILT_IN_EDITION.label, edition.label);
}

// One request per page load, shared by every component that names the edition.
let pending: Promise<CatalogEdition | null> | null = null;

export function catalogEditionOnce(): Promise<CatalogEdition | null> {
  pending ??= fetchCatalogEdition();
  return pending;
}

export function forgetCatalogEdition(): void {
  pending = null; // for tests
}

export function useCatalogEdition(): CatalogEdition {
  const [edition, setEdition] = useState<CatalogEdition>(BUILT_IN_EDITION);
  useEffect(() => {
    let cancelled = false;
    catalogEditionOnce().then((fetched) => {
      if (!cancelled && fetched) setEdition(fetched);
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return edition;
}
