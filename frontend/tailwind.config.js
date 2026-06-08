/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#0B0D10",
          surface: "#151922",
          card: "#1C2330",
          elevated: "#222A38",
        },
        primary: {
          DEFAULT: "#FFFFFF",
          muted: "#B9C0CC",
          subtle: "#6B7585",
        },
        accent: {
          DEFAULT: "#4F8CFF",
          hover: "#3B7AFF",
          muted: "rgba(79,140,255,0.15)",
          dim: "rgba(79,140,255,0.08)",
        },
        warning: {
          DEFAULT: "#FF8C42",
          muted: "rgba(255,140,66,0.15)",
        },
        danger: {
          DEFAULT: "#FF3B30",
          muted: "rgba(255,59,48,0.15)",
        },
        success: {
          DEFAULT: "#34C759",
          muted: "rgba(52,199,89,0.15)",
        },
        border: {
          DEFAULT: "rgba(255,255,255,0.06)",
          strong: "rgba(255,255,255,0.12)",
        },
      },
      fontFamily: {
        sans: ["Vazirmatn", "Inter", "system-ui", "sans-serif"],
        latin: ["Inter", "system-ui", "sans-serif"],
        persian: ["Vazirmatn", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "20px",
        "2xl": "24px",
        "3xl": "32px",
      },
      spacing: {
        safe: "env(safe-area-inset-bottom)",
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)",
        elevated:
          "0 4px 16px rgba(0,0,0,0.5), 0 1px 4px rgba(0,0,0,0.3)",
        glow: "0 0 20px rgba(79,140,255,0.25)",
        "danger-glow": "0 0 20px rgba(255,59,48,0.3)",
        "warning-glow": "0 0 20px rgba(255,140,66,0.25)",
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.3s cubic-bezier(0.16,1,0.3,1)",
        "slide-down": "slideDown 0.3s cubic-bezier(0.16,1,0.3,1)",
        "scale-in": "scaleIn 0.2s cubic-bezier(0.16,1,0.3,1)",
        "pulse-slow": "pulse 3s ease-in-out infinite",
        "alert-pulse": "alertPulse 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        slideUp: {
          from: { transform: "translateY(12px)", opacity: "0" },
          to: { transform: "translateY(0)", opacity: "1" },
        },
        slideDown: {
          from: { transform: "translateY(-8px)", opacity: "0" },
          to: { transform: "translateY(0)", opacity: "1" },
        },
        scaleIn: {
          from: { transform: "scale(0.95)", opacity: "0" },
          to: { transform: "scale(1)", opacity: "1" },
        },
        alertPulse: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
      },
      screens: {
        xs: "375px",
        sm: "640px",
        md: "768px",
        lg: "1024px",
        xl: "1280px",
      },
    },
  },
  plugins: [],
};
