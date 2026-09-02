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
        canvas: '#FBFBFA',
        surface: '#FFFFFF',
        ink: {
          DEFAULT: '#18181B',
          muted: '#71717A',
          light: '#A1A1AA',
        },
      },
    },
  },
  plugins: [],
}
