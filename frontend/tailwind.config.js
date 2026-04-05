
export default {
  content: [
    "./index.html",
    "./src*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {

        background: '#FCF8F1',
        surface: '#FFFBF5',
        surfaceHover: '#F6ECDD',
        surfaceAlt: '#FDFAF7',

        border: '#B7783E',
        borderLight: '#F6ECDD',

        primary: '#C96E2D',
        primaryHover: '#D77F36',
        primaryStrong: '#E08A42',
        primaryDark: '#BF6225',
        primaryShadow: '#7E532A',

        accent: '#D77F36',
        accentHover: '#E08A42',

        textMain: '#34261C',
        textSub: '#5C4939',
        textMuted: '#8D7766',
        textDim: '#B7783E',

        riskLow: '#6C8B58',
        riskLowText: '#4A5D3C',
        riskMedium: '#C96E2D',
        riskMediumText: '#7E532A',
        riskHigh: '#C76A54',
        riskHighText: '#8A3D2B',

        contradiction: '#C76A54',
        duplicate: '#6C8B58',
        outdated: '#C96E2D',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        body: ['"DM Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      backgroundImage: {
        'night': "url('/night_bg.png')",
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-down': {
          '0%': { opacity: '0', transform: 'translateY(-12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'glow-pulse': {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.8' },
        },
        'twinkle': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.15' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.6s cubic-bezier(0.16,1,0.3,1) forwards',
        'fade-down': 'fade-down 0.4s cubic-bezier(0.16,1,0.3,1) forwards',
        'fade-in': 'fade-in 0.5s ease-out forwards',
        'scale-in': 'scale-in 0.3s ease-out forwards',
        'glow-pulse': 'glow-pulse 3s ease-in-out infinite',
        'twinkle': 'twinkle 3s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}