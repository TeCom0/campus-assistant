import { prefersReducedMotion } from "./theme";
import type { ChatEvent, Citation } from "./types";

// The example questions on the empty state (2 English, 2 French).
export interface ExampleQuestion {
  id: string;
  language: "en" | "fr";
  question: string;
  short: string; // for the small chips under a limit notice
}

export const EXAMPLE_QUESTIONS: ExampleQuestion[] = [
  {
    id: "acc2302_prereqs_en",
    language: "en",
    question: "What do I need before taking ACC 2302?",
    short: "ACC 2302 prerequisites",
  },
  {
    id: "transfer_credits_en",
    language: "en",
    question: "How many credits can I transfer to AUI?",
    short: "Transfer credits",
  },
  {
    id: "add_drop_fr",
    language: "fr",
    question: "Comment ajouter ou supprimer un cours ?",
    short: "Ajouter ou supprimer un cours",
  },
  {
    id: "academic_probation_fr",
    language: "fr",
    question: "Que se passe-t-il si mon GPA est entre 1,5 et 1,99 ?",
    short: "GPA entre 1,5 et 1,99",
  },
];

// A saved answer: generated once by the real agent (backend/app/generate_examples.py),
// checked by the author, committed as src/examples/<id>.json. Replaying one makes
// no API call, so it costs no LLM tokens and isn't counted by the demo limits.
// `cached_example: true` marks it: it is never part of the evaluation, which
// reads only eval/results/.
export interface SavedExample {
  id: string;
  question: string;
  language: "en" | "fr";
  cached_example: true;
  generated_at: string;
  model: string;
  tool_calls: { tool: string; label: string }[];
  answer: string;
  citations: Citation[];
}

const saved = import.meta.glob<SavedExample>("./examples/*.json", {
  eager: true,
  import: "default",
});

export function savedExample(id: string): SavedExample | undefined {
  return Object.values(saved).find((example) => example.id === id);
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Plays a saved answer back as the same events /chat streams, with a short
// pause per tool call and the text arriving a few words at a time, so it looks
// and behaves exactly like a live answer. With reduced motion, the text
// arrives at once.
export async function replayExample(
  example: SavedExample,
  onEvent: (event: ChatEvent) => void,
): Promise<void> {
  const reduced = prefersReducedMotion();
  for (const call of example.tool_calls) {
    onEvent({ type: "tool_call", tool: call.tool, args: {}, label: call.label });
    await wait(reduced ? 0 : 450);
  }
  if (reduced) {
    onEvent({ type: "token", text: example.answer });
  } else {
    const pieces = example.answer.match(/\S+\s*/g) ?? [example.answer];
    for (let i = 0; i < pieces.length; i += 3) {
      onEvent({ type: "token", text: pieces.slice(i, i + 3).join("") });
      await wait(28);
    }
  }
  onEvent({ type: "citations", citations: example.citations });
  onEvent({ type: "done" });
}
