import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      animation: {
        pulse_fast: 'pulse 1s cubic-bezier(0.4,0,0.6,1) infinite',
      },
    },
  },
  plugins: [],
} satisfies Config
