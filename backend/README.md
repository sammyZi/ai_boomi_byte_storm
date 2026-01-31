# AI-Powered Drug Discovery Platform - Backend

Backend API for the AI-Powered Drug Discovery Platform that transforms disease queries into ranked drug candidates in 8-10 seconds.

## Overview

This backend implements a complete proteome-to-cure pipeline that:
- Identifies protein targets associated with diseases (Open Targets API)
- Retrieves 3D protein structures (AlphaFold Database)
- Finds bioactive molecules (ChEMBL Database)
- Calculates molecular properties and toxicity (RDKit)
- Scores and ranks drug candidates
- Generates AI-powered analysis (BioMistral-7B via Ollama)

**Performance**: 8-10 seconds end-to-end with aggressive caching (24-hour TTL)

## Technology Stack

- **Framework**: FastAPI with async/await for concurrent processing
- **Python**: 3.11+
- **Caching**: Redis (24-hour TTL)
- **AI**: BioMistral-7B via Ollama
- **Cheminformatics**: RDKit for molecular analysis
- **Testing**: Hypothesis (property-based), pytest (unit tests)
- **External APIs**: Open Targets, ChEMBL, AlphaFold

## Project Structure

```
backend/
├── app/                          # Application code
│   ├── __init__.py
│   ├── main.py                  # FastAPI application and endpoints
│   ├── models.py                # Pydantic data models and schemas
│   ├── discovery_pipeline.py   # Main orchestration logic
│   ├── open_targets_client.py  # Open Targets API client
│   ├── chembl_client.py         # ChEMBL API client
│   ├── alphafold_client.py      # AlphaFold API client
│   ├── rdkit_analyzer.py        # Molecular property calculations
│   ├── biomistral_engine.py     # AI analysis engine
│   ├── scoring_engine.py        # Scoring and ranking logic
│   ├── cache.py                 # Redis cache layer
│   ├── rate_limiter.py          # Rate limiting middleware
│   └── security.py              # Security utilities
├── config/                       # Configuration management
│   ├── __init__.py
│   └── settings.py              # Environment variable handling
├── tests/                        # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_*_unit.py           # Unit tests
│   ├── test_*_properties.py     # Property-based tests
│   ├── test_integration.py      # Integration tests
│   └── test_performance.py      # Performance benchmarks
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest configuration
├── .env.example                  # Example environment variables
├── .gitignore                    # Git ignore patterns
├── docker-compose.yml            # Docker setup for Redis
└── README.md                     # This file
```

## Setup Instructions

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11 or higher** - [Download Python](https://www.python.org/downloads/)
- **Redis server** - For caching API responses
  - Windows: [Download Redis](https://github.com/microsoftarchive/redis/releases)
  - macOS: `brew install redis`
  - Linux: `sudo apt-get install redis-server`
- **Ollama with BioMistral-7B** (optional, for AI analysis)
  - [Download Ollama](https://ollama.ai/)
  - Requires NVIDIA GPU with 8GB+ VRAM for optimal performance

### Installation Steps

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd backend
```

#### 2. Create Virtual Environment

```bash
python -m venv venv
```

#### 3. Activate Virtual Environment

**Windows (Command Prompt):**
```bash
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

#### 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note**: If RDKit installation fails, try using conda:
```bash
conda install -c conda-forge rdkit
```

#### 5. Configure Environment Variables

Copy the example environment file:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Edit `.env` and configure the required values. See the **Environment Variables** section below for details.

#### 6. Start Redis Server

**Windows:**
```bash
redis-server
```

**macOS/Linux:**
```bash
redis-server
# Or as a service:
sudo systemctl start redis
```

Verify Redis is running:
```bash
redis-cli ping
# Should return: PONG
```

#### 7. Install and Start Ollama (Optional)

If you want AI-powered analysis:

```bash
# Install Ollama from https://ollama.ai/

# Pull the BioMistral-7B model
ollama pull biomistral:7b

# Start Ollama service
ollama serve
```

Verify Ollama is running:
```bash
curl http://localhost:11434/api/tags
```

**Note**: The platform will work without Ollama but will skip AI analysis for candidates.

## Environment Variables

The application requires several environment variables to be configured. All variables are documented in `.env.example`.

### Required Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `API_PORT` | Port for FastAPI server | `8000` | `8000` |
| `API_HOST` | Host address for API | `0.0.0.0` | `0.0.0.0` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | - | `http://localhost:3000` |
| `REDIS_URL` | Redis connection URL | - | `redis://localhost:6379` |
| `CACHE_TTL` | Cache time-to-live in seconds | `86400` | `86400` (24 hours) |
| `RATE_LIMIT_PER_MINUTE` | Max requests per minute per IP | `100` | `100` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### External API Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPEN_TARGETS_API_URL` | Open Targets Platform API | `https://api.platform.opentargets.org/api/v4` |
| `CHEMBL_API_URL` | ChEMBL Database API | `https://www.ebi.ac.uk/chembl/api/data` |
| `ALPHAFOLD_API_URL` | AlphaFold Database API | `https://alphafold.ebi.ac.uk/api` |

### Ollama Configuration (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Ollama service URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Model name for analysis | `biomistral:7b` |
| `OLLAMA_TIMEOUT` | Timeout in seconds | `5` |

### Security Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENFORCE_HTTPS` | Enforce HTTPS in production | `false` | 
| `ENVIRONMENT` | Environment name | `development` |

**Validation**: The application validates all required environment variables on startup and will fail fast with clear error messages if any are missing or invalid (Requirement 13.8).

## Running the Application

### Development Server

Start the FastAPI development server with auto-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the provided run script:

```bash
python run.py
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Interactive Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Production Server

For production, use a production-grade ASGI server:

```bash
# Using uvicorn with multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or using gunicorn with uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker Compose

Start Redis using Docker Compose:

```bash
docker-compose up -d
```

This will start a Redis instance on port 6379.

## Running Tests

The backend includes a comprehensive test suite with unit tests, property-based tests, and integration tests.

### Test Environment Setup

If you encounter environment variable errors when running tests, set the test environment variables:

**Windows (PowerShell):**
```powershell
.\set_test_env.ps1
```

**macOS/Linux (Bash):**
```bash
source set_test_env.sh
```

### Run All Tests

```bash
pytest
```

### Run Tests by Type

```bash
# Unit tests only
pytest -m unit

# Property-based tests only (100+ iterations each)
pytest -m property

# Integration tests only
pytest -m integration

# Performance tests
pytest tests/test_performance.py
```

### Run Specific Test Files

```bash
# Test RDKit analyzer
pytest tests/test_rdkit_unit.py tests/test_rdkit_properties.py

# Test API endpoints
pytest tests/test_api_unit.py tests/test_api_properties.py

# Test complete pipeline
pytest tests/test_pipeline_unit.py tests/test_pipeline_properties.py
```

### Run Tests with Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html --cov-report=term

# View HTML coverage report
# Open htmlcov/index.html in your browser
```

### Run Specific Tests

```bash
# Run a specific test function
pytest tests/test_rdkit_unit.py::test_parse_valid_smiles

# Run tests matching a pattern
pytest -k "smiles"
```

### Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.unit` - Unit tests for specific functionality
- `@pytest.mark.property` - Property-based tests (Hypothesis)
- `@pytest.mark.integration` - Integration tests across components
- `@pytest.mark.slow` - Slow-running tests (skipped by default)

### Property-Based Testing

The platform uses Hypothesis for property-based testing to verify universal properties across random inputs:

```python
# Example: Test binding affinity normalization
@given(pchembl=st.floats(min_value=0, max_value=15))
def test_binding_affinity_normalization(pchembl):
    score = normalize_binding_affinity(pchembl)
    assert 0.0 <= score <= 1.0
```

Each property test runs 100+ iterations with randomly generated inputs to ensure correctness across all cases.

### Test Coverage Goals

- **Overall Coverage**: >80%
- **Core Logic**: >90% (scoring, ranking, property calculations)
- **API Endpoints**: 100%
- **Error Handling**: 100%

## API Documentation

Once the server is running, comprehensive API documentation is available at:

- **Swagger UI (Interactive)**: http://localhost:8000/docs
  - Try out API endpoints directly in the browser
  - View request/response schemas
  - See example requests and responses
  
- **ReDoc (Alternative)**: http://localhost:8000/redoc
  - Clean, readable documentation
  - Detailed schema information
  - Searchable endpoint list

### Quick API Reference

#### POST /api/discover

Discover drug candidates for a disease.

**Request:**
```json
{
  "disease_name": "Alzheimer's disease"
}
```

**Response:**
```json
{
  "query": "Alzheimer's disease",
  "timestamp": "2026-01-31T12:34:56.789Z",
  "processing_time_seconds": 8.45,
  "candidates": [
    {
      "molecule": {
        "chembl_id": "CHEMBL123",
        "name": "Example Drug",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "pchembl_value": 7.5,
        "activity_type": "IC50",
        "target_ids": ["P12345"]
      },
      "target": {
        "uniprot_id": "P12345",
        "gene_symbol": "BACE1",
        "protein_name": "Beta-secretase 1",
        "confidence_score": 0.95,
        "disease_association": "Amyloid-beta production"
      },
      "properties": {
        "molecular_weight": 180.16,
        "logp": 1.19,
        "hbd": 1,
        "hba": 4,
        "tpsa": 63.6,
        "rotatable_bonds": 3,
        "aromatic_rings": 1,
        "lipinski_violations": 0,
        "drug_likeness_score": 1.0
      },
      "toxicity": {
        "toxicity_score": 0.0,
        "risk_level": "low",
        "detected_toxicophores": [],
        "warnings": []
      },
      "binding_affinity_score": 0.58,
      "binding_confidence": 0.8,
      "composite_score": 0.72,
      "rank": 1,
      "ai_analysis": "This molecule shows promising...",
      "structure_2d_svg": "<svg>...</svg>"
    }
  ],
  "metadata": {
    "targets_found": 10,
    "molecules_analyzed": 245,
    "api_version": "0.1.0"
  },
  "warnings": [],
  "disclaimer": "MEDICAL DISCLAIMER: This platform is for research..."
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid input (e.g., disease name too short/long)
- `422` - Validation error
- `429` - Rate limit exceeded (>100 requests/minute)
- `500` - Internal server error

#### GET /health

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

For complete API documentation with all endpoints, schemas, and examples, visit the interactive docs at `/docs`.

## Architecture Overview

### Pipeline Flow

```
User Query → FastAPI → Discovery Pipeline
                ↓
        ┌───────┴───────┐
        ↓               ↓
   Open Targets    Cache Layer (Redis)
        ↓               ↓
   Targets Found   24-hour TTL
        ↓
   ┌────┴────┐
   ↓         ↓
AlphaFold  ChEMBL
   ↓         ↓
Structures Molecules
   ↓         ↓
   └────┬────┘
        ↓
   RDKit Analyzer
        ↓
   Properties + Toxicity
        ↓
   Scoring Engine
        ↓
   Ranked Candidates
        ↓
   BioMistral AI (Top 20)
        ↓
   Final Results
```

### Key Components

1. **Discovery Pipeline** (`discovery_pipeline.py`)
   - Orchestrates the complete workflow
   - Handles concurrent API calls (5 per API)
   - Implements graceful degradation

2. **API Clients**
   - `open_targets_client.py` - Disease-target associations
   - `chembl_client.py` - Bioactive molecules
   - `alphafold_client.py` - Protein structures
   - Retry logic with exponential backoff

3. **RDKit Analyzer** (`rdkit_analyzer.py`)
   - SMILES parsing and validation
   - Molecular property calculations
   - Lipinski Rule evaluation
   - Toxicophore detection (10 patterns)

4. **Scoring Engine** (`scoring_engine.py`)
   - Binding affinity normalization
   - Drug-likeness scoring
   - Toxicity assessment
   - Composite score calculation (40% binding + 30% drug-likeness + 20% safety + 10% novelty)

5. **BioMistral AI** (`biomistral_engine.py`)
   - AI-powered analysis via Ollama
   - Limited to top 20 candidates
   - 5-second timeout per candidate

6. **Cache Layer** (`cache.py`)
   - Redis-based caching
   - 24-hour TTL for all external API responses
   - Reduces latency from ~60s to <100ms for cached queries

### Performance Characteristics

- **First Query**: 8-10 seconds (cold cache)
- **Cached Query**: <100ms (warm cache)
- **Concurrent Processing**: Up to 5 requests per external API
- **Rate Limiting**: 100 requests/minute per IP
- **Cache Hit Rate**: >80% for common diseases

## Troubleshooting

### RDKit Installation Issues

If RDKit fails to install via pip, try using conda:

```bash
conda install -c conda-forge rdkit
```

### Redis Connection Errors

Ensure Redis is running and accessible:

```bash
redis-cli ping
# Should return: PONG
```

### Ollama Connection Issues

Check if Ollama is running:

```bash
curl http://localhost:11434/api/tags
```

## License

This project is for research and educational purposes only. See medical disclaimer in the application.


## Development Guidelines

### Code Style

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

### Testing Requirements

The platform uses a dual testing approach:

**Unit Tests**: Verify specific examples and edge cases
- Test with known molecules (aspirin, caffeine)
- Test error conditions and edge cases
- Test integration points between components

**Property-Based Tests**: Verify universal properties across all inputs
- Use Hypothesis to generate random test data
- Run 100+ iterations per property
- Test invariants that must hold for all inputs

Both approaches are complementary and required for comprehensive coverage.

### Adding New Features

1. Update requirements document if adding new functionality
2. Update design document with architecture changes
3. Implement the feature with type hints and docstrings
4. Write unit tests for specific cases
5. Write property tests for universal behaviors
6. Update API documentation if adding endpoints
7. Run full test suite: `pytest`
8. Check coverage: `pytest --cov=app`

### Commit Message Format

Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `test:` Adding or updating tests
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `chore:` Maintenance tasks

Example: `feat: add support for custom scoring weights`

### Code Review Checklist

- [ ] Type hints on all function signatures
- [ ] Docstrings for public functions/classes
- [ ] Unit tests for new functionality
- [ ] Property tests for invariants
- [ ] Error handling with appropriate exceptions
- [ ] Logging for important operations
- [ ] Updated documentation
- [ ] No hardcoded values (use config)
- [ ] Security considerations addressed
