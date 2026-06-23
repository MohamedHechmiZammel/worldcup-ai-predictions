import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Barlow Condensed"', 'ui-sans-serif', 'system-ui'],
      },
      colors: {
        pitch: '#080E1A',
        card: '#0F172A',
        gold: {
          DEFAULT: '#C9AB55',
          dim: '#7A6330',
          bright: '#F0CE7A',
        },
      },
      animation: {
        pulse_fast: 'pulse 1s cubic-bezier(0.4,0,0.6,1) infinite',
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config
