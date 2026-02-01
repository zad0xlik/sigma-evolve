/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        background: {
          DEFAULT: '#0a0a0a',
          secondary: '#111111',
          tertiary: '#1a1a1a',
        },
        primary: {
          DEFAULT: '#00FFC8',
          foreground: '#0a0a0a',
        },
        terminal: {
          green: '#00FF41',
          yellow: '#FFD700',
          purple: '#9D4EDD',
          blue: '#00B4D8',
          red: '#EF476F',
        },
        text: {
          primary: '#E0E0E0',
          secondary: '#A0A0A0',
          muted: '#606060',
        },
        border: {
          DEFAULT: '#00FFC8',
          subtle: '#333333',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      keyframes: {
        "glow": {
          "0%, 100%": { boxShadow: "0 0 5px #00FFC8, 0 0 10px #00FFC8" },
          "50%": { boxShadow: "0 0 20px #00FFC8, 0 0 30px #00FFC8" },
        },
        "terminal-blink": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        "fadeIn": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slideDown": {
          from: { transform: "translateY(-10px)", opacity: "0" },
          to: { transform: "translateY(0)", opacity: "1" },
        },
      },
      animation: {
        "glow": "glow 2s ease-in-out infinite",
        "terminal-blink": "terminal-blink 1s step-end infinite",
        "fadeIn": "fadeIn 0.3s ease-in",
        "slideDown": "slideDown 0.3s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
