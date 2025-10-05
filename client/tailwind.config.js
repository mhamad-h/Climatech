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
        // New color palette
        'dark-gray': '#293132',
        'brown-gray': '#474044',
        'purple-gray': '#4F5365',
        'geo-blue': '#547AA5',
        'geo-cyan': '#50D8D7',
        
        // Semantic color mappings
        space: {
          bg: '#293132',        // Dark gray background
          panel: '#474044',     // Brown-gray panels
          accent: '#4F5365',    // Purple-gray accents
          primary: '#547AA5',   // Blue for primary actions
          highlight: '#50D8D7', // Cyan for highlights
        }
      }
    },
  },
  plugins: [],
}
