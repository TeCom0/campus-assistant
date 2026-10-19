import { MoonIcon, SunIcon } from "./icons";

export function TopBar({ theme, onToggleTheme }: { theme: string; onToggleTheme: () => void }) {
  const next = theme === "dark" ? "light" : "dark";
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <span className="brand">Campus Assistant</span>
        <span className="pill">
          <span className="pill-long">Unofficial student project</span>
          <span className="pill-short">Unofficial</span>
        </span>
        <span className="spacer" />
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
