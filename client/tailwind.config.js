/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}'
  ],
  darkMode: 'media',
  theme: {
    extend: {
      colors: {
        space: {
          bg: '#0b1120',
          panel: '#1e293b'
        }
      }
    },
  },
  plugins: [],
}
