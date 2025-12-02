# Gap Assessment Frontend

A modern, interactive frontend for the Gap Assessment system.

## Features

- **Query Interface**: Input box for gap assessment queries with force extraction toggle
- **Gap Management**: Tabular view of gaps sorted by priority (Critical > High > Medium > Low)
- **Gap Details**: Detailed view with comments and updates (Azure DevOps style)
- **Dashboard**: PowerBI-like dashboard with charts and metrics
- **Date Filtering**: Filter assessments by date
- **Real-time Metrics**: Line graphs for LLM calls, latency, search results over time

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Build

```bash
npm run build
```

## Environment Variables

Create a `.env` file:

```
VITE_API_URL=http://localhost:8000
```

## Usage

1. **Home Page**: Enter your query and toggle force extraction if needed
2. **Gap Table**: View all gaps sorted by priority, click to see details
3. **Gap Details**: View full gap information and add comments/updates
4. **Dashboard**: View charts and metrics, filter by date

