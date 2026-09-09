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
          accent: '#00f2fe',
          cyan: '#00d2ff',
          neonGreen: '#10b981',
          warning: '#f59e0b',
          danger: '#ef4444',
        }
      }
    },
  },
  plugins: [],
}
