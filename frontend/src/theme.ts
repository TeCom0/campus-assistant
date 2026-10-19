import { useEffect, useState } from "react";

// The theme follows the system unless the visitor picks one with the moon/sun
// button; the pick sets data-theme on <html> (see index.css) and is remembered
// in this browser. Storage can be unavailable (private windows, blocked site
// data), so every access is guarded and the page works without it.
type Theme = "light" | "dark";
const STORAGE_KEY = "campus-assistant-theme";

function storedTheme(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null;
  }
}

function systemTheme(): Theme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function useTheme(): [Theme, () => void] {
  const [picked, setPicked] = useState<Theme | null>(storedTheme);
  const [system, setSystem] = useState<Theme>(systemTheme);

  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setSystem(query.matches ? "dark" : "light");
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (picked) document.documentElement.dataset.theme = picked;
    else delete document.documentElement.dataset.theme;
  }, [picked]);

  const current = picked ?? system;
  function toggle() {
    const next: Theme = current === "dark" ? "light" : "dark";
    setPicked(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Not remembered; still applied for this visit.
    }
  }
  return [current, toggle];
}

export function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
