import { useEffect, useState } from "react";
import { API_URL } from "./chatStream";

// The demo's limits, as the API reports them (GET /limits). They live in the
// server's settings, so the UI asks instead of keeping a copy that can drift.
export interface DemoLimits {
  daily_question_cap: number;
  per_ip_limit: number;
  per_ip_window_minutes: number;
}

// null if the API doesn't answer: the page then states the limits without numbers.
export async function fetchDemoLimits(): Promise<DemoLimits | null> {
  try {
    const response = await fetch(`${API_URL}/limits`);
    return response.ok ? ((await response.json()) as DemoLimits) : null;
  } catch {
    return null;
  }
}

export function limitsSentence(limits: DemoLimits | null): string {
  if (!limits) return "The live demo limits the questions it answers each day and per visitor.";
  const { daily_question_cap, per_ip_limit, per_ip_window_minutes } = limits;
  return `The live demo answers ${daily_question_cap} questions a day in total, and ${per_ip_limit} per visitor per ${per_ip_window_minutes} minutes.`;
}

export function useDemoLimits(): DemoLimits | null {
  const [limits, setLimits] = useState<DemoLimits | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetchDemoLimits().then((fetched) => {
      if (!cancelled) setLimits(fetched);
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return limits;
}
