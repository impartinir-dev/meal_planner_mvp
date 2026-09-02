/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
      },
      colors: {
        brand: {
          DEFAULT: '#1B4332',
          light: '#2D6A4F',
          accent: '#40916C',
          soft: '#E8F5E9',
          dark: '#081C15',
        },
        canvas: '#F4F5F7',
        surface: '#FFFFFF',
        ink: {
          DEFAULT: '#0B0F0E',
          muted: '#5C6560',
          light: '#8B9390',
        },
      },
    },
  },
  plugins: [],
}
