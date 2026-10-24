// Small inline icons (stroke = currentColor, so they follow the theme tokens).
// Decorative: hidden from screen readers; buttons carry their own labels.

const common = {
  width: 16,
  height: 16,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export const MoonIcon = () => (
  <svg {...common}>
    <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z" />
  </svg>
);

export const SunIcon = () => (
  <svg {...common}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </svg>
);

export const SendIcon = () => (
  <svg {...common} strokeWidth={2}>
    <path d="M12 19V5M5 12l7-7 7 7" />
  </svg>
);

export const CheckIcon = () => (
  <svg {...common} strokeWidth={2.2}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </svg>
);

export const ClockIcon = () => (
  <svg {...common}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </svg>
);

// GitHub's mark is a filled shape, not a stroke, so it overrides `common`'s fill.
export const GitHubIcon = () => (
  <svg {...common} viewBox="0 0 16 16" fill="currentColor" stroke="none">
    <path d="M8 0a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.07-2.7-1.07-.36-.92-.89-1.17-.89-1.17-.73-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.72 1.22 1.88.87 2.34.66.07-.52.28-.87.5-1.07-1.78-.2-3.65-.89-3.65-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.03 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0 0 8 0Z" />
  </svg>
);

export const AlertIcon = () => (
  <svg {...common}>
    <path d="M12 3 2.5 20h19L12 3Z" />
    <path d="M12 10v4M12 17h.01" />
  </svg>
);
