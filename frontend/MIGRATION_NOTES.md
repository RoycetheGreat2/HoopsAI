# Next.js → React + Vite Migration

## What Changed

This project has been successfully migrated from **Next.js 16** to **React 19 + Vite 8** SPA (Single Page Application).

### Key Benefits

✅ **Instant HMR** - Vite provides near-instant hot module replacement  
✅ **Simpler Architecture** - Pure React SPA without server-side complexity  
✅ **Faster Dev Server** - Vite starts in milliseconds vs Next.js dev startup time  
✅ **Smaller Bundle** - SPA bundle is lean and efficient  
✅ **Easier Deployment** - Static output, deploy anywhere (Vercel, Netlify, etc.)  

## File Structure

```
project/
├── src/
│   ├── main.tsx              # Entry point
│   ├── App.tsx               # Root component
│   ├── index.css             # Global styles & Tailwind
│   ├── components/           # All React components
│   │   ├── hoops/           # Domain components
│   │   └── ui/              # UI library components
│   └── pages/               # Page components (if using routing)
├── index.html               # HTML entry point
├── vite.config.ts           # Vite configuration
├── tsconfig.json            # TypeScript config
└── package.json
```

## Running the Project

```bash
# Development - starts on port 3000 (or next available)
pnpm run dev

# Build for production
pnpm run build

# Preview production build locally
pnpm run preview
```

## Reverting to Next.js

If needed, you can revert to the Next.js version using Git:

```bash
# View previous commits
git log --oneline

# Revert to checkpoint (look for "CHECKPOINT: Next.js NBA analytics dashboard")
git checkout <CHECKPOINT_HASH>
```

## Key Changes Made

### Removed
- `next.config.mjs` (disabled as `next.config.mjs.disabled`)
- `app/` directory (disabled as `app.disabled/`)
- All Next.js specific imports (`next/image`, `next/link`, etc.)
- 'use client' directives from components
- Next.js dependencies

### Added
- `vite.config.ts` - Vite bundler configuration
- `src/main.tsx` - React entry point
- `src/App.tsx` - Root React component
- `index.html` - HTML template
- Vite & React Router dependencies

### Component Updates
- Replaced Next.js `Image` with standard `<img>` tags
- Removed server component directives
- All components are now client-side React

## Tailwind CSS v4

This project uses **Tailwind CSS v4** with the new `@theme` directive in `src/index.css`.

Design tokens are defined in the `@theme` block with full CSS variable support.

## Dependencies

Key libraries:
- **React 19** - UI framework
- **Vite 8** - Build tool & dev server
- **React Router DOM 7** - Client-side routing (if needed)
- **Tailwind CSS v4** - Utility-first CSS
- **Lucide React** - Icon library
- **Recharts** - Data visualization
- **shadcn/ui** - Component library

## Notes

- This is a pure frontend SPA - no backend included
- All data is currently mock data in the components
- To add a backend, connect it via API calls from React components
- The production build outputs to `dist/` folder
