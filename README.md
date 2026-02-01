# 🧬 AI-Powered Drug Discovery Platform

<div align="center">

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

**Transform disease queries into ranked drug candidates in 8-10 seconds**

[Features](#-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [API](#-api-documentation) • [Contributing](#-contributing)

</div>

---

## 📋 Overview

The AI-Powered Drug Discovery Platform is a full-stack application that accelerates early-stage drug discovery by automating the proteome-to-cure pipeline. It integrates multiple biomedical databases and AI analysis to identify and rank potential drug candidates for any disease.

### What It Does

1. **Disease → Targets**: Identifies protein targets associated with diseases (Open Targets API)
2. **Targets → Structures**: Retrieves 3D protein structures (AlphaFold Database)
3. **Targets → Molecules**: Finds bioactive molecules tested against targets (ChEMBL Database)
4. **Molecules → Properties**: Calculates molecular properties and toxicity (RDKit)
5. **Properties → Scores**: Scores and ranks drug candidates using composite scoring
6. **Candidates → Insights**: Generates AI-powered analysis (BioMistral-7B via Ollama)
7. **Optional Docking**: Performs molecular docking simulations (AutoDock Vina)

---

## ✨ Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| 🔍 **Disease Search** | Query any disease and get relevant drug candidates |
| 🎯 **Target Identification** | Automatic discovery of protein targets using Open Targets |
| 🧪 **Molecule Discovery** | Retrieval of bioactive compounds from ChEMBL |
| 📊 **Property Analysis** | Drug-likeness, toxicity, and ADMET property calculations |
| 🤖 **AI Analysis** | BioMistral-7B powered insights for each candidate |
| ⚡ **Fast Performance** | Results in 8-10 seconds with aggressive caching |
| 🔬 **Molecular Docking** | AutoDock Vina integration for binding affinity predictions |

### Technical Highlights

- **Concurrent Processing**: Async/await architecture for parallel API calls
- **Smart Caching**: 24-hour TTL Redis cache for API responses
- **Graceful Degradation**: Continues processing when non-critical components fail
- **Property-Based Testing**: Hypothesis framework for robust testing
- **Rate Limiting**: Protection against API abuse (100 req/min)
- **Modern UI**: Next.js 14 with responsive Tailwind CSS design

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                    │
│                    Next.js 14 + TypeScript + Tailwind                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │   Search    │  │   Results   │  │  Candidate  │  │   Docking   │   │
│  │    Page     │  │    Page     │  │   Details   │  │   Tracker   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ REST API
┌────────────────────────────────▼────────────────────────────────────────┐
│                              Backend                                     │
│                         FastAPI + Python 3.11+                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Discovery Pipeline                           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐│   │
│  │  │  Open    │  │ AlphaFold│  │  ChEMBL  │  │    BioMistral    ││   │
│  │  │ Targets  │  │  Client  │  │  Client  │  │     AI Engine    ││   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘│   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────────────┐  │   │
│  │  │  RDKit   │  │ Scoring  │  │     Docking Service          │  │   │
│  │  │ Analyzer │  │  Engine  │  │   (AutoDock Vina + Celery)   │  │   │
│  │  └──────────┘  └──────────┘  └──────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────┬────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────────────┐
│                        External Services                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Redis   │  │  SQLite  │  │  Ollama  │  │  Open    │  │  ChEMBL  │  │
│  │  Cache   │  │   (DB)   │  │(BioMist) │  │ Targets  │  │   API    │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ai_boomi/
├── backend/                      # FastAPI Backend
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── models.py            # Pydantic data models
│   │   ├── discovery_pipeline.py # Main orchestration logic
│   │   ├── open_targets_client.py # Open Targets API client
│   │   ├── alphafold_client.py  # AlphaFold API client
│   │   ├── chembl_client.py     # ChEMBL API client
│   │   ├── rdkit_analyzer.py    # Molecular property calculations
│   │   ├── scoring_engine.py    # Candidate scoring & ranking
│   │   ├── biomistral_engine.py # AI analysis engine
│   │   ├── cache.py             # Redis cache layer
│   │   ├── rate_limiter.py      # Rate limiting middleware
│   │   └── docking/             # Molecular docking module
│   │       ├── router.py        # Docking API endpoints
│   │       ├── service.py       # Job management service
│   │       ├── executor.py      # AutoDock Vina executor
│   │       └── ...
│   ├── config/
│   │   └── settings.py          # Environment configuration
│   ├── tests/                   # Comprehensive test suite
│   ├── requirements.txt         # Python dependencies
│   └── docker-compose.yml       # Docker setup for Redis
│
├── frontend/                     # Next.js Frontend
│   ├── app/
│   │   ├── page.tsx             # Home page with search
│   │   ├── results/             # Discovery results page
│   │   ├── candidates/          # Candidate details
│   │   ├── docking/             # Docking job tracking
│   │   └── about/               # Platform information
│   ├── components/              # Reusable UI components
│   │   ├── SearchBar.tsx        # Disease search input
│   │   ├── CandidateCard.tsx    # Drug candidate display
│   │   ├── ScoreDisplay.tsx     # Score visualization
│   │   ├── MoleculeViewer3D.tsx # 3D structure viewer
│   │   └── ...
│   ├── hooks/                   # Custom React hooks
│   ├── lib/                     # API client & utilities
│   └── types/                   # TypeScript definitions
│
└── README.md                    # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Redis** - For caching (or use Docker)
- **Ollama** (optional) - For AI analysis [Download](https://ollama.ai/)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ai_boomi
```

### 2. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Redis (using Docker)
docker-compose up -d

# Run the backend
python run.py
```

The backend will be available at `http://localhost:8000`

### 3. Frontend Setup

```bash
# Navigate to frontend (new terminal)
cd frontend

# Install dependencies
npm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

### 4. Optional: AI Analysis Setup

```bash
# Install Ollama and pull BioMistral model
ollama pull biomistral
```

---

## 🔌 API Documentation

### Main Endpoint

#### `POST /api/discover`

Transform a disease query into ranked drug candidates.

**Request:**
```json
{
  "disease_name": "Alzheimer's disease",
  "max_targets": 5,
  "max_molecules_per_target": 20
}
```

**Response:**
```json
{
  "query": "Alzheimer's disease",
  "candidates": [
    {
      "chembl_id": "CHEMBL12345",
      "name": "Example Compound",
      "smiles": "CC(=O)Nc1ccc(O)cc1",
      "score": 0.85,
      "binding_affinity_score": 0.9,
      "drug_likeness_score": 0.8,
      "safety_score": 0.85,
      "target": {
        "uniprot_id": "P12345",
        "gene_symbol": "APP",
        "name": "Amyloid-beta precursor protein"
      },
      "properties": {
        "molecular_weight": 325.4,
        "logp": 2.1,
        "hbd": 2,
        "hba": 4
      },
      "ai_analysis": "This compound shows promise..."
    }
  ],
  "processing_time_ms": 8500,
  "targets_found": 5,
  "molecules_screened": 100
}
```

### Docking Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/docking/submit` | Submit docking job(s) |
| GET | `/api/docking/status/{job_id}` | Get job status |
| GET | `/api/docking/results/{job_id}` | Get docking results |
| DELETE | `/api/docking/cancel/{job_id}` | Cancel a job |
| GET | `/api/docking/jobs` | List user's jobs |

### Other Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/docs` | Interactive Swagger documentation |
| GET | `/redoc` | ReDoc documentation |

---

## 🧮 Scoring Algorithm

Drug candidates are ranked using a composite score:

```
Composite Score = (0.40 × Binding) + (0.30 × Drug-likeness) + (0.20 × Safety) + (0.10 × Novelty)
```

| Component | Weight | Calculation |
|-----------|--------|-------------|
| **Binding Affinity** | 40% | Normalized pChEMBL value (4-10 → 0-1) |
| **Drug-likeness** | 30% | Lipinski's Rule of Five compliance |
| **Safety** | 20% | Toxicophore absence score |
| **Novelty** | 10% | Structural uniqueness vs known drugs |

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest tests/test_*_unit.py        # Unit tests
pytest tests/test_*_properties.py  # Property-based tests
pytest tests/test_integration.py   # Integration tests
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

---

## 🛠 Technology Stack

### Backend

| Technology | Purpose |
|------------|---------|
| FastAPI | Web framework with async support |
| Python 3.11+ | Core language |
| Redis | Caching layer (24-hour TTL) |
| SQLite/PostgreSQL | Database for docking jobs |
| RDKit | Cheminformatics library |
| Celery | Async task queue for docking |
| OpenBabel | Molecular format conversion |
| AutoDock Vina | Molecular docking |

### Frontend

| Technology | Purpose |
|------------|---------|
| Next.js 14 | React framework with App Router |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| TanStack Query | Data fetching & caching |
| Zustand | State management |
| NGL Viewer | 3D molecular visualization |

### External APIs

| Service | Purpose |
|---------|---------|
| Open Targets | Disease-target associations |
| ChEMBL | Bioactive molecules database |
| AlphaFold | Protein 3D structures |
| Ollama + BioMistral | AI analysis |

---

## ⚙️ Configuration

### Environment Variables (Backend)

Create a `.env` file in the `backend/` directory:

```env
# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Redis
REDIS_URL=redis://localhost:6379

# AI (optional)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=biomistral
OLLAMA_TIMEOUT=30

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# Database
DATABASE_URL=sqlite+aiosqlite:///./docking.db
```

### Environment Variables (Frontend)

Create a `.env.local` file in the `frontend/` directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| End-to-end latency | 8-10 seconds |
| Cache hit response | <100ms |
| Concurrent API calls | Up to 5 per external service |
| Cache TTL | 24 hours |
| Rate limit | 100 requests/minute |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

This platform is intended for **research and educational purposes only**. The drug candidates identified are computational predictions and have not been validated through clinical trials. Always consult with qualified healthcare professionals and regulatory bodies before any drug development activities.

---

## 📞 Support

- 📚 [Backend Documentation](backend/README.md)
- 📚 [Frontend Documentation](frontend/README.md)
- 📚 [API Documentation](backend/API_DOCUMENTATION.md)
- 🐛 [Report Issues](../../issues)

---

<div align="center">
  <strong>Built with ❤️ for accelerating drug discovery</strong>
</div>
