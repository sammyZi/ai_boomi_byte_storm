# AI-Powered Drug Discovery Platform - Backend

Backend API for the AI-Powered Drug Discovery Platform that transforms disease queries into ranked drug candidates in 8-10 seconds.

## Technology Stack

- **Framework**: FastAPI with async/await
- **Python**: 3.11+
- **Caching**: Redis
- **AI**: BioMistral-7B via Ollama
- **Cheminformatics**: RDKit
- **Testing**: Hypothesis (property-based), pytest (unit tests)

## Project Structure

```
backend/
├── app/                    # Application code
│   ├── __init__.py
│   ├── main.py            # FastAPI application entry point
│   ├── models/            # Data models and schemas
│   ├── services/          # Business logic and API clients
│   ├── api/               # API endpoints
│   └── utils/             # Utility functions
├── config/                # Configuration management
│   └── __init__.py
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── unit/             # Unit tests
│   ├── property/         # Property-based tests
│   └── integration/      # Integration tests
├── requirements.txt       # Python dependencies
├── pytest.ini            # Pytest configuration
├── .env.example          # Example environment variables
└── README.md             # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.11 or higher
- Redis server
- Ollama with BioMistral-7B model (for AI analysis)

### 2. Create Virtual Environment

```bash
cd backend
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Copy the example environment file and configure it:

```bash
copy .env.example .env  # Windows
cp .env.example .env    # macOS/Linux
```

Edit `.env` and set the required values:

```env
# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
CORS_ORIGINS=http://localhost:3000

# External APIs
OPEN_TARGETS_API_URL=https://api.platform.opentargets.org/api/v4
CHEMBL_API_URL=https://www.ebi.ac.uk/chembl/api/data
ALPHAFOLD_API_URL=https://alphafold.ebi.ac.uk/api

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=biomistral:7b
OLLAMA_TIMEOUT=5

# Cache Configuration
REDIS_URL=redis://localhost:6379
CACHE_TTL=86400

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# Logging
LOG_LEVEL=INFO
```

### 6. Start Redis

Make sure Redis is running:

```bash
redis-server
```

### 7. Start Ollama (Optional for AI Analysis)

Install and start Ollama with BioMistral-7B:

```bash
ollama pull biomistral:7b
ollama serve
```

## Running the Application

### Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Types

```bash
# Unit tests only
pytest -m unit

# Property-based tests only
pytest -m property

# Integration tests only
pytest -m integration

# Run with coverage report
pytest --cov=app --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/unit/test_rdkit_analyzer.py
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Development Guidelines

### Code Style

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose

### Testing

- Write both unit tests and property-based tests
- Unit tests verify specific examples and edge cases
- Property tests verify universal properties across all inputs
- Aim for >80% code coverage
- Tag tests with appropriate markers (unit, property, integration)

### Commit Messages

Follow conventional commits format:
- `feat:` New features
- `fix:` Bug fixes
- `test:` Adding or updating tests
- `docs:` Documentation changes
- `refactor:` Code refactoring

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
