/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        aegis: {
          900: '#070b14',
          850: '#0b1120',
          800: '#11192e',
          700: '#1e2945',
          600: '#2e3c63',
          500: '#465b8c',
          accent: '#ef4444',
          crimson: '#dc2626',
          ruby: '#b91c1c',
          rose: '#f43f5e',
          neonGreen: '#10b981',
          warning: '#f59e0b',
          danger: '#ef4444',
        }
      }
    },
  },
  plugins: [],
}
