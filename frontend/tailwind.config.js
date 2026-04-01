/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0e1c',
        surface: '#111827',
        surfaceHover: '#1c2333',
        border: '#1f2937',
        primary: '#6366f1',
        primaryHover: '#4f46e5',
        textMain: '#f1f5f9',
        textMuted: '#64748b',
        textSub: '#94a3b8',
        riskLow: '#22c55e',
        riskMedium: '#f59e0b',
        riskHigh: '#ef4444'
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'night': "url('/night_bg.png')",
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'twinkle': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.3' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.5s ease-out forwards',
        'twinkle': 'twinkle 3s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
