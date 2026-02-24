/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ash: {
          bg: "#0a0e17",
          card: "#111827",
          border: "#1e293b",
          accent: "#3b82f6",
          success: "#10b981",
          warning: "#f59e0b",
          danger: "#ef4444",
          text: "#e2e8f0",
          muted: "#64748b",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};
