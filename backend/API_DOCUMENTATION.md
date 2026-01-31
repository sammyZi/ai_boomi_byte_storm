# API Documentation - AI-Powered Drug Discovery Platform

Complete API reference for the Drug Discovery Platform backend.

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Endpoints](#endpoints)
  - [GET /](#get-)
  - [GET /health](#get-health)
  - [POST /api/discover](#post-apidiscover)
- [Request/Response Formats](#requestresponse-formats)
- [Error Codes](#error-codes)
- [Code Examples](#code-examples)
- [Interactive Documentation](#interactive-documentation)

## Overview

The Drug Discovery Platform API provides a single endpoint for transforming disease queries into ranked drug candidates. The API orchestrates multiple biomedical databases and AI analysis to deliver comprehensive results in 8-10 seconds.

**Key Features:**
- Disease-to-drug candidate pipeline
- Molecular property calculations
- Toxicity screening
- AI-powered analysis
- 24-hour result caching
- Rate limiting protection

**API Version:** 0.1.0

## Base URL

**Development:**
```
http://localhost:8000
```

**Production:**
```
https://api.yourdomain.com
```

All endpoints are relative to the base URL.

## Authentication

Currently, the API does not require authentication. Access is controlled through:
- **CORS**: Requests must originate from allowed domains
- **Rate Limiting**: 100 requests per minute per IP address

Future versions may include API key authentication.

## Rate Limiting

**Limits:**
- 100 requests per minute per IP address
- Burst allowance: 20 requests

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1643723400
```

**Rate Limit Exceeded Response:**
```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded. Maximum 100 requests per minute.",
  "timestamp": "2026-01-31T12:34:56.789Z"
}
```

**Status Code:** `429 Too Many Requests`

## Endpoints

### GET /

Root endpoint returning API information.

**Request:**
```http
GET / HTTP/1.1
Host: api.yourdomain.com
```

**Response:**
```json
{
  "name": "AI-Powered Drug Discovery Platform",
  "version": "0.1.0",
  "status": "operational",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

**Status Code:** `200 OK`

---

### GET /health

Health check endpoint for monitoring and load balancers.

**Request:**
```http
GET /health HTTP/1.1
Host: api.yourdomain.com
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

**Status Code:** `200 OK`

**Use Cases:**
- Load balancer health checks
- Monitoring system probes
- Deployment verification

---

### POST /api/discover

**Primary endpoint for drug discovery.**

Transforms a disease query into ranked drug candidates through a complete proteome-to-cure pipeline.

#### Request

**HTTP Method:** `POST`

**Endpoint:** `/api/discover`

**Content-Type:** `application/json`

**Request Body Schema:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `disease_name` | string | Yes | 2-200 characters | Disease name to search for drug candidates |

**Example Request:**
```http
POST /api/discover HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json

{
  "disease_name": "Alzheimer's disease"
}
```

**cURL Example:**
```bash
curl -X POST https://api.yourdomain.com/api/discover \
  -H "Content-Type: application/json" \
  -d '{"disease_name": "Alzheimer'\''s disease"}'
```

#### Response

**Status Code:** `200 OK`

**Content-Type:** `application/json`

**Response Body Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Original disease query |
| `timestamp` | string | Query execution timestamp (ISO 8601) |
| `processing_time_seconds` | number | Total processing time in seconds |
| `candidates` | array | Ranked list of drug candidates |
| `metadata` | object | Additional metadata |
| `warnings` | array | Warnings about partial failures |
| `disclaimer` | string | Medical disclaimer |

**Candidate Object Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `molecule` | object | Molecule information |
| `target` | object | Primary target information |
| `properties` | object | Molecular properties |
| `toxicity` | object | Toxicity assessment |
| `binding_affinity_score` | number | Normalized binding score (0-1) |
| `binding_confidence` | number | Confidence in measurement (0.6-0.9) |
| `composite_score` | number | Final ranking score (0-1) |
| `rank` | integer | Rank position (1-based) |
| `ai_analysis` | string | AI-generated analysis (optional) |
| `structure_2d_svg` | string | 2D molecular structure as SVG |

**Example Response:**
```json
{
  "query": "Alzheimer's disease",
  "timestamp": "2026-01-31T12:34:56.789Z",
  "processing_time_seconds": 8.45,
  "candidates": [
    {
      "molecule": {
        "chembl_id": "CHEMBL1234",
        "name": "Example Compound",
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
        "disease_association": "Amyloid-beta production in Alzheimer's disease"
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
      "ai_analysis": "This molecule shows promising binding affinity to BACE1...",
      "structure_2d_svg": "<svg xmlns=\"http://www.w3.org/2000/svg\">...</svg>"
    }
  ],
  "metadata": {
    "targets_found": 10,
    "molecules_analyzed": 245,
    "api_version": "0.1.0"
  },
  "warnings": [
    "AlphaFold structure unavailable for 2 targets"
  ],
  "disclaimer": "MEDICAL DISCLAIMER: This platform is for research and educational purposes only..."
}
```

#### Error Responses

**400 Bad Request - Invalid Input**

Returned when the disease name is invalid.

```json
{
  "error_code": "INVALID_INPUT",
  "message": "Disease name must be at least 2 characters long",
  "timestamp": "2026-01-31T12:34:56.789Z"
}
```

**422 Unprocessable Entity - Validation Error**

Returned when request body fails validation.

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": {
    "field": "disease_name",
    "error": "field required"
  },
  "timestamp": "2026-01-31T12:34:56.789Z"
}
```

**429 Too Many Requests - Rate Limit Exceeded**

Returned when rate limit is exceeded.

```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded. Maximum 100 requests per minute.",
  "timestamp": "2026-01-31T12:34:56.789Z"
}
```

**500 Internal Server Error**

Returned when an unexpected error occurs.

```json
{
  "error_code": "INTERNAL_ERROR",
  "message": "An internal error occurred during drug discovery",
  "details": {
    "error": "Connection timeout to external API"
  },
  "timestamp": "2026-01-31T12:34:56.789Z"
}
```

#### Pipeline Stages

The `/api/discover` endpoint executes the following stages:

1. **Target Identification** (1-2s)
   - Query Open Targets Platform for disease-target associations
   - Filter targets with confidence ≥ 0.5
   - Limit to top 10 targets

2. **Structure Retrieval** (1-2s)
   - Query AlphaFold Database for protein structures
   - Retrieve PDB format with confidence scores
   - Flag low confidence structures (pLDDT < 70)

3. **Molecule Search** (2-3s)
   - Query ChEMBL Database for bioactive molecules
   - Filter by activity (pChEMBL ≥ 6.0)
   - Deduplicate across targets
   - Validate SMILES strings

4. **Property Calculation** (1-2s)
   - Calculate molecular properties (MW, LogP, HBD, HBA, TPSA)
   - Evaluate Lipinski's Rule of Five
   - Calculate drug-likeness score

5. **Toxicity Screening** (1s)
   - Detect toxic substructures (10 toxicophore patterns)
   - Calculate toxicity score
   - Classify risk level (low/medium/high)

6. **Scoring and Ranking** (<1s)
   - Normalize binding affinity scores
   - Calculate composite scores
   - Rank candidates by composite score

7. **AI Analysis** (2-3s)
   - Generate analysis for top 20 candidates
   - Use BioMistral-7B via Ollama
   - 5-second timeout per candidate

**Total Time:** 8-10 seconds (first query), <100ms (cached)

#### Caching Behavior

Results are cached for 24 hours based on the disease name:

- **Cache Hit:** Response time <100ms
- **Cache Miss:** Full pipeline execution (8-10s)
- **Cache Key:** Normalized disease name (lowercase, trimmed)

**Cache Headers:**
```
X-Cache-Status: HIT | MISS
X-Cache-TTL: 86400
```

## Request/Response Formats

### Content Types

**Request:**
- `application/json` (required)

**Response:**
- `application/json`
- Gzip compression enabled for responses >1KB

### Date/Time Format

All timestamps use ISO 8601 format:
```
2026-01-31T12:34:56.789Z
```

### Number Precision

All scores are formatted with 2 decimal places:
```json
{
  "binding_affinity_score": 0.58,
  "composite_score": 0.72
}
```

### SMILES Notation

Molecules are represented using SMILES (Simplified Molecular Input Line Entry System):

**Example:**
```
Aspirin: CC(=O)Oc1ccccc1C(=O)O
Caffeine: CN1C=NC2=C1C(=O)N(C(=O)N2C)C
```

Both standard and canonical SMILES are provided in responses.

## Error Codes

Complete list of error codes returned by the API:

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `INVALID_INPUT` | 400 | Disease name validation failed |
| `VALIDATION_ERROR` | 422 | Request body validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded (>100 req/min) |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `EXTERNAL_API_ERROR` | 500 | External API failure |
| `CACHE_ERROR` | 500 | Redis cache error |
| `AI_MODEL_ERROR` | 500 | Ollama/BioMistral error |
| `HTTPS_REQUIRED` | 301 | HTTPS enforcement redirect |

### Error Response Format

All errors follow a consistent format:

```json
{
  "error_code": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "additional": "context"
  },
  "timestamp": "2026-01-31T12:34:56.789Z"
}
```

**Validates: Requirement 15.5**

## Code Examples

### Python

```python
import requests

# Make request
response = requests.post(
    "https://api.yourdomain.com/api/discover",
    json={"disease_name": "Alzheimer's disease"},
    headers={"Content-Type": "application/json"}
)

# Check status
if response.status_code == 200:
    result = response.json()
    print(f"Found {len(result['candidates'])} candidates")
    print(f"Processing time: {result['processing_time_seconds']}s")
    
    # Print top candidate
    if result['candidates']:
        top = result['candidates'][0]
        print(f"\nTop Candidate:")
        print(f"  Name: {top['molecule']['name']}")
        print(f"  ChEMBL ID: {top['molecule']['chembl_id']}")
        print(f"  Composite Score: {top['composite_score']}")
        print(f"  Risk Level: {top['toxicity']['risk_level']}")
elif response.status_code == 429:
    print("Rate limit exceeded. Please wait and try again.")
else:
    error = response.json()
    print(f"Error: {error['message']}")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

async function discoverDrugs(diseaseName) {
  try {
    const response = await axios.post(
      'https://api.yourdomain.com/api/discover',
      { disease_name: diseaseName },
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    const result = response.data;
    console.log(`Found ${result.candidates.length} candidates`);
    console.log(`Processing time: ${result.processing_time_seconds}s`);
    
    // Print top candidate
    if (result.candidates.length > 0) {
      const top = result.candidates[0];
      console.log('\nTop Candidate:');
      console.log(`  Name: ${top.molecule.name}`);
      console.log(`  ChEMBL ID: ${top.molecule.chembl_id}`);
      console.log(`  Composite Score: ${top.composite_score}`);
      console.log(`  Risk Level: ${top.toxicity.risk_level}`);
    }
    
    return result;
  } catch (error) {
    if (error.response) {
      console.error(`Error ${error.response.status}: ${error.response.data.message}`);
    } else {
      console.error(`Request failed: ${error.message}`);
    }
    throw error;
  }
}

// Usage
discoverDrugs("Alzheimer's disease");
```

### JavaScript (Browser/Fetch)

```javascript
async function discoverDrugs(diseaseName) {
  try {
    const response = await fetch('https://api.yourdomain.com/api/discover', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ disease_name: diseaseName }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message);
    }
    
    const result = await response.json();
    console.log(`Found ${result.candidates.length} candidates`);
    
    return result;
  } catch (error) {
    console.error('Discovery failed:', error.message);
    throw error;
  }
}

// Usage
discoverDrugs("Alzheimer's disease")
  .then(result => {
    // Process results
    console.log('Discovery complete!');
  })
  .catch(error => {
    // Handle error
    console.error('Error:', error);
  });
```

### cURL

```bash
# Basic request
curl -X POST https://api.yourdomain.com/api/discover \
  -H "Content-Type: application/json" \
  -d '{"disease_name": "Alzheimer'\''s disease"}'

# Pretty-print JSON response
curl -X POST https://api.yourdomain.com/api/discover \
  -H "Content-Type: application/json" \
  -d '{"disease_name": "Alzheimer'\''s disease"}' \
  | jq '.'

# Save response to file
curl -X POST https://api.yourdomain.com/api/discover \
  -H "Content-Type: application/json" \
  -d '{"disease_name": "Alzheimer'\''s disease"}' \
  -o results.json

# Include response headers
curl -i -X POST https://api.yourdomain.com/api/discover \
  -H "Content-Type: application/json" \
  -d '{"disease_name": "Alzheimer'\''s disease"}'

# Measure response time
curl -w "\nTime: %{time_total}s\n" \
  -X POST https://api.yourdomain.com/api/discover \
  -H "Content-Type: application/json" \
  -d '{"disease_name": "Alzheimer'\''s disease"}'
```

### TypeScript

```typescript
interface DiscoveryRequest {
  disease_name: string;
}

interface DiscoveryResponse {
  query: string;
  timestamp: string;
  processing_time_seconds: number;
  candidates: DrugCandidate[];
  metadata: {
    targets_found: number;
    molecules_analyzed: number;
    api_version: string;
  };
  warnings: string[];
  disclaimer: string;
}

interface DrugCandidate {
  molecule: {
    chembl_id: string;
    name: string;
    smiles: string;
    canonical_smiles: string;
    pchembl_value: number;
    activity_type: string;
    target_ids: string[];
  };
  target: {
    uniprot_id: string;
    gene_symbol: string;
    protein_name: string;
    confidence_score: number;
    disease_association: string;
  };
  properties: {
    molecular_weight: number;
    logp: number;
    hbd: number;
    hba: number;
    tpsa: number;
    rotatable_bonds: number;
    aromatic_rings: number;
    lipinski_violations: number;
    drug_likeness_score: number;
  };
  toxicity: {
    toxicity_score: number;
    risk_level: 'low' | 'medium' | 'high';
    detected_toxicophores: string[];
    warnings: string[];
  };
  binding_affinity_score: number;
  binding_confidence: number;
  composite_score: number;
  rank: number;
  ai_analysis: string | null;
  structure_2d_svg: string;
}

async function discoverDrugs(
  diseaseName: string
): Promise<DiscoveryResponse> {
  const response = await fetch('https://api.yourdomain.com/api/discover', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ disease_name: diseaseName }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message);
  }
  
  return response.json();
}

// Usage
discoverDrugs("Alzheimer's disease")
  .then((result) => {
    console.log(`Found ${result.candidates.length} candidates`);
    result.candidates.forEach((candidate) => {
      console.log(`${candidate.rank}. ${candidate.molecule.name}`);
      console.log(`   Score: ${candidate.composite_score}`);
      console.log(`   Risk: ${candidate.toxicity.risk_level}`);
    });
  })
  .catch((error) => {
    console.error('Error:', error.message);
  });
```

## Interactive Documentation

The API provides interactive documentation where you can test endpoints directly in your browser:

### Swagger UI

**URL:** `https://api.yourdomain.com/docs`

Features:
- Try out API endpoints with custom inputs
- View detailed request/response schemas
- See example requests and responses
- Download OpenAPI specification

### ReDoc

**URL:** `https://api.yourdomain.com/redoc`

Features:
- Clean, readable documentation
- Detailed schema information
- Searchable endpoint list
- Code samples in multiple languages

### OpenAPI Specification

**URL:** `https://api.yourdomain.com/openapi.json`

Download the complete OpenAPI 3.0 specification for:
- API client generation
- Testing automation
- Documentation generation
- Integration with API tools

## Best Practices

### 1. Handle Rate Limits

```python
import time

def discover_with_retry(disease_name, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, json={"disease_name": disease_name})
        
        if response.status_code == 429:
            # Rate limited - wait and retry
            wait_time = 60  # Wait 1 minute
            print(f"Rate limited. Waiting {wait_time}s...")
            time.sleep(wait_time)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

### 2. Use Caching

```python
# Cache results on client side
cache = {}

def discover_cached(disease_name):
    if disease_name in cache:
        return cache[disease_name]
    
    response = requests.post(url, json={"disease_name": disease_name})
    result = response.json()
    cache[disease_name] = result
    return result
```

### 3. Handle Errors Gracefully

```python
def discover_safe(disease_name):
    try:
        response = requests.post(
            url,
            json={"disease_name": disease_name},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("Request timed out")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e.response.status_code}")
        print(e.response.json()['message'])
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    
    return None
```

### 4. Validate Input

```python
def validate_disease_name(name):
    if len(name) < 2:
        raise ValueError("Disease name too short (min 2 characters)")
    if len(name) > 200:
        raise ValueError("Disease name too long (max 200 characters)")
    
    # Check for invalid characters
    invalid_chars = ['<', '>', ';', '`', '$', '{', '}', '[', ']', '\\', '|', '&']
    if any(char in name for char in invalid_chars):
        raise ValueError("Disease name contains invalid characters")
    
    return name.strip()
```

### 5. Process Results Efficiently

```python
def process_results(result):
    # Extract top candidates
    top_candidates = result['candidates'][:10]
    
    # Filter by risk level
    low_risk = [c for c in top_candidates if c['toxicity']['risk_level'] == 'low']
    
    # Sort by specific criteria
    by_binding = sorted(top_candidates, key=lambda c: c['binding_affinity_score'], reverse=True)
    
    return {
        'top_10': top_candidates,
        'low_risk': low_risk,
        'best_binding': by_binding[0] if by_binding else None
    }
```

## Changelog

### Version 0.1.0 (2026-01-31)

Initial release:
- Drug discovery pipeline endpoint
- Support for 10 protein targets per query
- Molecular property calculations
- Toxicity screening (10 toxicophore patterns)
- AI-powered analysis (BioMistral-7B)
- 24-hour result caching
- Rate limiting (100 req/min)

## Support

For API support:
- Check interactive documentation: `/docs`
- Review error messages and codes
- Verify request format and parameters
- Check rate limit headers
- Test with health endpoint: `/health`

---

**Requirements Validated:**
- 11.1: OpenAPI/Swagger documentation at /docs
- 11.2: ReDoc documentation at /redoc
- 11.3: All endpoints with request/response schemas
- 11.6: Example requests and responses included
