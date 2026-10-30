import { REPO_URL } from "../about";
import type { View } from "../view";
import { GitHubIcon, MoonIcon, SunIcon } from "./icons";

export function TopBar({
  theme,
  onToggleTheme,
  view,
}: {
  theme: string;
  onToggleTheme: () => void;
  view: View;
}) {
  const next = theme === "dark" ? "light" : "dark";
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <span className="brand">
          <span className="brand-mark" aria-hidden="true" />
          Campus Assistant
        </span>
        <span className="pill">
          <span className="pill-long">Unofficial student project</span>
          <span className="pill-short">Unofficial</span>
        </span>
        <span className="spacer" />
        {/* Plain links to the two hashes (view.ts): the browser's own history and back button. */}
        <nav className="nav" aria-label="Pages">
          <a href="#" aria-current={view === "chat" ? "page" : undefined}>
            Chat
          </a>
          <a href="#about" aria-current={view === "about" ? "page" : undefined}>
            About
          </a>
        </nav>
        <a
          className="icon-btn github"
          href={REPO_URL}
          target="_blank"
          rel="noreferrer"
          aria-label="Source on GitHub"
          title="Source on GitHub"
        >
          <GitHubIcon />
        </a>
        <button
          type="button"
          className="icon-btn"
          onClick={onToggleTheme}
          aria-label={`Switch to ${next} mode`}
          title={`Switch to ${next} mode`}
        >
          {theme === "dark" ? <SunIcon /> : <MoonIcon />}
        </button>
      </div>
    </header>
  );
}
