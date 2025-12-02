# Gap Assessment System

A production-grade automated gap assessment system for tax technology and compliance digitization, specifically designed for BP (British Petroleum).

## Features

- **Web Scraping**: Automated data extraction from company websites and public reports
- **Vector Database**: Pinecone-based storage for efficient similarity search
- **RAG System**: Retrieval Augmented Generation with optimized LLM usage (6 calls vs 71)
- **Gap Analysis**: Automated comparison with industry benchmarks (KPMG, EY, Deloitte, PWC)
- **Interactive Frontend**: Modern React-based UI with BP branding
- **Dashboard**: PowerBI-like analytics with charts and metrics

## Architecture

- **Backend**: FastAPI with Google Gemini LLM
- **Frontend**: React + Vite + Tailwind CSS
- **Vector DB**: Pinecone (768 dimensions)
- **Embeddings**: sentence-transformers (all-mpnet-base-v2)
- **Web Scraping**: browser-use + Playwright

## Setup

### Backend

1. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure API keys:
```bash
# IMPORTANT: Copy example files to actual config files
cp config/agent_config.json.example config/agent_config.json
cp config/company_config.json.example config/company_config.json

# Edit config/agent_config.json and add your API keys:
# - Google Gemini API key (under "agent.llm.api_key")
# - Pinecone API key (under "vector_db.api_key")
# - Browser-use API key (under "extraction.browser_use_api_key")
```

**Note:** The code expects `config/agent_config.json` and `config/company_config.json` (not `.example` files). You must copy the example files and rename them.

4. Start API server:
```bash
./START_API.sh
# OR
uvicorn api.gap_assessment_api:app --host 0.0.0.0 --port 8000
```

### Frontend

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start development server:
```bash
npm run dev
# OR
./START_FRONTEND.sh
```

3. Open browser: `http://localhost:3000`

## API Usage

### Endpoint: POST `/assess`

**Request:**
```json
{
  "query": "What are the gaps in BP tax technology compared to industry benchmarks?",
  "force_extraction": false
}
```

**Response:**
```json
{
  "status": "success",
  "query": "...",
  "assessment": {
    "gaps": [...],
    "summary": {...},
    "metrics": {...}
  },
  "message": "Gap assessment completed successfully"
}
```

## Configuration

**Required Setup Steps:**
1. Copy example config files:
   ```bash
   cp config/agent_config.json.example config/agent_config.json
   cp config/company_config.json.example config/company_config.json
   ```

2. Edit `config/agent_config.json` and add your API keys:
   - `agent.llm.api_key`: Google Gemini API key
   - `vector_db.api_key`: Pinecone API key
   - `extraction.browser_use_api_key`: Browser-use API key

3. The system will automatically create `config/extraction_dates.json` on first run.

**Configuration Files:**
- `config/agent_config.json`: Agent and API configuration (REQUIRED - copy from .example)
- `config/company_config.json`: Company-specific scraping rules (REQUIRED - copy from .example)
- `config/extraction_dates.json`: Last extraction timestamps (auto-generated)

## Performance

- **LLM Calls**: 6 per request (97% reduction from 71)
- **Latency**: ~15 seconds
- **Cost**: $0.06-$0.60 per request
- **Quality**: Maintained with optimized RAG

## Project Structure

```
Gap_assesment/
├── agent/                 # Gap assessment agent
├── agent_tools/          # RAG and extraction tools
├── api/                  # FastAPI endpoints
├── config/               # Configuration files
├── frontend/             # React frontend
├── utilities/            # Helper utilities
├── vector_db/            # Pinecone manager
├── web_scraper/          # Web scraping tools
└── requirements.txt     # Python dependencies
```

## License

Proprietary - BP Internal Use

