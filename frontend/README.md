# Clipping Automation 2.0 - Frontend Dashboard

## Overview

Modern React dashboard for the Clipping Automation 2.0 AI-powered Twitch clipping system.

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (Radix UI primitives)
- **State Management**: TanStack React Query
- **Routing**: React Router v6

## Features

- 🎨 Beautiful dark-themed dashboard
- 🔴 Real-time stream monitoring
- 📹 Clips library with search/filter
- 📊 Analytics and performance metrics
- ⚙️ AI configuration settings
- 📱 Fully responsive (mobile, tablet, desktop)
- ⚡ Live updates every 10 seconds

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend API running on http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at: **http://localhost:5173**

### Build for Production

```bash
npm run build
npm run preview
```

## Backend Integration

This frontend connects to the FastAPI backend at `http://localhost:8000`.

### Environment Variables

Create a `.env` file:
```
VITE_API_URL=http://localhost:8000
```

### API Endpoints Used

- `GET /api/v1/streams` - Stream monitors
- `GET /api/v1/clips` - Clip library
- `GET /api/v1/analytics/summary` - Dashboard stats
- `POST /api/v1/clips/predict` - AI predictions
- `GET /api/v1/health` - System health

## Project Structure

```
src/
├── components/         # React components
│   ├── ui/            # shadcn/ui components
│   ├── dashboard/     # Dashboard widgets
│   └── clips/         # Clip-related components
├── pages/             # Route pages
├── hooks/             # Custom React hooks
├── lib/               # Utilities and API client
└── assets/            # Images and static files
```

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Adding Components

This project uses shadcn/ui. To add new components:

```bash
npx shadcn@latest add [component-name]
```

## Deployment

Deploy to:
- **Vercel**: Connect your GitHub repo for auto-deploy
- **Netlify**: Drag & drop the `dist/` folder
- **Cloudflare Pages**: Connect repo or upload build

## License

Part of the Clipping Automation 2.0 project.
