import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "Inter",
          "Segoe UI",
          "system-ui",
          "-apple-system",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      colors: {
        bg: "#0a0b0f",
        "bg-raised": "#0d0f15",
        panel: "#12141b",
        "panel-hover": "#171923",
        surface: "#1a1d27",
        border: "#242836",
        "border-strong": "#323748",
        ink: "#f1f2f5",
        muted: "#8d93a3",
        faint: "#5b6174",
        accent: "#5b7cfa",
        "accent-hover": "#6f8dff",
        "accent-ink": "#eef1ff",
        pass: "#34d399",
        fail: "#f8717a",
        warn: "#f5b544",
      },
      boxShadow: {
        card: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -12px rgba(0,0,0,0.55)",
        raised: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 16px 40px -16px rgba(0,0,0,0.65)",
        ring: "0 0 0 3px rgba(91,124,250,0.18)",
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.125rem",
      },
    },
  },
  plugins: [],
};

export default config;
