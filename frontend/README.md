# Rehabify Frontend - Next.js

Property investment analysis application built with Next.js.

## Getting Started

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── src/
│   ├── app/              # Next.js App Router
│   │   ├── layout.tsx    # Root layout
│   │   ├── page.tsx      # Home page
│   │   ├── report/       # Report page
│   │   └── globals.css   # Global styles
│   ├── components/       # React components
│   └── services/         # API services
├── public/               # Static assets
└── package.json
```

## Environment Variables

Create a `.env.local` file in the root directory:

```
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

## Migration Notes

This project has been migrated from React/Vite to Next.js:

- **Routing**: Changed from React Router to Next.js App Router
- **Pages**: Converted to Next.js pages in `src/app/`
- **Components**: Moved to `src/components/` (kept same structure)
- **API**: Updated to use Next.js environment variables
- **Styling**: Tailwind CSS configuration updated for Next.js
