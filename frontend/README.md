# AI-Powered Drug Discovery Platform - Frontend

Next.js 14 frontend application for the AI-Powered Drug Discovery Platform.

## Features

- 🔍 Disease search with autocomplete
- 📊 Real-time drug candidate discovery
- 📈 Interactive results visualization
- 📥 Export results to JSON/CSV
- 🎨 Responsive design with Tailwind CSS
- ⚡ Optimized with React Query caching
- 🧪 Comprehensive test coverage

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Data Fetching**: TanStack React Query (formerly React Query)
- **HTTP Client**: Axios
- **Icons**: Lucide React
- **Testing**: Jest + React Testing Library

## Prerequisites

- Node.js 18+ and npm
- Backend API running (see backend/README.md)

## Installation

1. Install dependencies:

```bash
npm install
```

2. Create environment file:

```bash
cp .env.local.example .env.local
```

3. Update `.env.local` with your backend API URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development

Start the development server:

```bash
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

## Building for Production

Build the application:

```bash
npm run build
```

Start the production server:

```bash
npm start
```

## Testing

Run unit tests:

```bash
npm test
```

Run tests in watch mode:

```bash
npm run test:watch
```

Run tests with coverage:

```bash
npm run test:coverage
```

## Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── page.tsx           # Home page
│   ├── results/           # Results page
│   ├── about/             # About page
│   ├── layout.tsx         # Root layout
│   └── providers.tsx      # React Query provider
├── components/            # React components
│   ├── Layout.tsx         # Main layout
│   ├── SearchBar.tsx      # Search interface
│   ├── CandidateCard.tsx  # Drug candidate card
│   ├── CandidateList.tsx  # Results list
│   └── ...
├── hooks/                 # Custom React hooks
│   ├── useDiscovery.ts    # Discovery API hook
│   └── useExport.ts       # Export functionality
├── lib/                   # Utilities and services
│   ├── api-client.ts      # Axios client
│   ├── discovery-api.ts   # API methods
│   └── store.ts           # Zustand store
├── types/                 # TypeScript types
│   └── index.ts           # Type definitions
└── __tests__/             # Test files
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |
| `NEXT_PUBLIC_APP_NAME` | Application name | `AI-Powered Drug Discovery Platform` |
| `NEXT_PUBLIC_APP_VERSION` | Application version | `1.0.0` |

## Key Components

### SearchBar
Disease search input with autocomplete for common diseases.

### CandidateCard
Displays drug candidate information with expandable details including:
- Composite score and rank
- Binding affinity, drug-likeness, and toxicity scores
- Target information
- Molecular properties
- AI-generated analysis

### CandidateList
Filterable and sortable list of drug candidates with:
- Sort by score, name, or risk level
- Filter by risk level (low/medium/high)

### ResultsHeader
Results summary with:
- Query information
- Processing time
- Export buttons (JSON/CSV)
- Warnings display

## API Integration

The frontend communicates with the backend API through:

- **Base URL**: Configured via `NEXT_PUBLIC_API_URL`
- **Main Endpoint**: `POST /api/discover`
- **Request Format**: `{ disease_name: string }`
- **Response Format**: See `types/index.ts` for full schema

### Error Handling

The application handles various error scenarios:
- Network errors with retry logic
- Invalid input validation
- Server errors with user-friendly messages
- Empty results with helpful suggestions

## Caching Strategy

React Query is configured with:
- **Stale Time**: 1 hour (results remain fresh)
- **Cache Time**: 24 hours (results persist in cache)
- **Refetch on Window Focus**: Disabled
- **Retry**: 1 attempt for failed requests

## Accessibility

The application follows WCAG AA standards:
- Semantic HTML elements
- ARIA labels for interactive elements
- Keyboard navigation support
- Color contrast compliance
- Screen reader compatibility

## Performance Optimizations

- Code splitting with Next.js dynamic imports
- Image optimization with Next.js Image component
- React Query caching for API responses
- Lazy loading of heavy components
- Optimized bundle size

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Follow the existing code style
2. Write tests for new features
3. Update documentation as needed
4. Ensure all tests pass before submitting

## License

This project is for research and educational purposes only.

## Medical Disclaimer

This platform is for research purposes only. Results are computational predictions and require experimental validation. Not a substitute for professional medical advice or clinical trials.
