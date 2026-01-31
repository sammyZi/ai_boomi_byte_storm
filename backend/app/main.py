"""Main FastAPI application entry point.

This module initializes the FastAPI application with all necessary
middleware, routes, and configuration.
"""

import re
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from config.settings import settings
from app.models import DiscoveryRequest, DiscoveryResponse, ErrorResponse
from app.discovery_pipeline import DiscoveryPipeline
from app.rate_limiter import RateLimiter, RateLimitMiddleware


def sanitize_disease_name(disease_name: str) -> str:
    """Sanitize disease name input to prevent injection attacks.
    
    Validates:
    - Length between 2-200 characters
    - Rejects strings with potentially malicious special characters
    
    Args:
        disease_name: Raw disease name input
    
    Returns:
        Sanitized disease name
    
    Raises:
        ValueError: If input is invalid or contains malicious characters
    
    Validates: Requirements 12.5
    """
    # Check length
    if len(disease_name) < 2:
        raise ValueError("Disease name must be at least 2 characters long")
    if len(disease_name) > 200:
        raise ValueError("Disease name must not exceed 200 characters")
    
    # Strip leading/trailing whitespace
    disease_name = disease_name.strip()
    
    # Check for malicious special characters
    # Allow: letters, numbers, spaces, hyphens, apostrophes, parentheses, commas
    # Reject: SQL injection chars, script tags, shell commands, etc.
    malicious_patterns = [
        r'[<>]',  # HTML/XML tags
        r'[;]',   # SQL/command injection
        r'[\$`]', # Shell command injection
        r'[{}]',  # Code injection
        r'[\[\]]', # Array/object injection
        r'[\\]',  # Escape sequences
        r'[|&]',  # Command chaining
    ]
    
    for pattern in malicious_patterns:
        if re.search(pattern, disease_name):
            raise ValueError(
                f"Disease name contains invalid characters. "
                f"Only letters, numbers, spaces, hyphens, apostrophes, "
                f"parentheses, and commas are allowed."
            )
    
    return disease_name

# Create FastAPI application instance
app = FastAPI(
    title="AI-Powered Drug Discovery Platform",
    description="Backend API for transforming disease queries into ranked drug candidates",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add gzip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add rate limiting middleware
rate_limiter = RateLimiter(requests_per_minute=settings.rate_limit_per_minute)
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

# Initialize pipeline (will be created per request for now)
# In production, consider using dependency injection
pipeline = None


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    global pipeline
    pipeline = DiscoveryPipeline()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global pipeline
    if pipeline:
        await pipeline.close()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler for consistent error responses.
    
    Validates: Requirements 15.5
    """
    # Extract error details from HTTPException
    if isinstance(exc.detail, dict):
        error_response = exc.detail
    else:
        error_response = {
            "error_code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with consistent error format.
    
    Validates: Requirements 15.5
    """
    error_response = {
        "error_code": "INTERNAL_ERROR",
        "message": "An unexpected error occurred",
        "details": {"error": str(exc)},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return JSONResponse(
        status_code=500,
        content=error_response
    )


@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "AI-Powered Drug Discovery Platform",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": "0.1.0"
    }


@app.post(
    "/api/discover",
    response_model=DiscoveryResponse,
    responses={
        200: {
            "description": "Successful drug discovery",
            "model": DiscoveryResponse
        },
        400: {
            "description": "Invalid input",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        },
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    summary="Discover drug candidates for a disease",
    description="""
    Transform a disease query into ranked drug candidates.
    
    This endpoint orchestrates the complete drug discovery pipeline:
    1. Identifies protein targets associated with the disease
    2. Retrieves protein structures from AlphaFold
    3. Finds bioactive molecules from ChEMBL
    4. Calculates molecular properties and toxicity
    5. Scores and ranks candidates
    6. Generates AI analysis for top candidates
    
    Expected processing time: 8-10 seconds for common diseases.
    Results are cached for 24 hours.
    """
)
async def discover_drugs(request: DiscoveryRequest) -> DiscoveryResponse:
    """Discover drug candidates for a disease.
    
    Args:
        request: DiscoveryRequest with disease_name
    
    Returns:
        DiscoveryResponse with ranked candidates
    
    Validates: Requirements 15.1, 15.2
    """
    try:
        # Sanitize input
        sanitized_disease_name = sanitize_disease_name(request.disease_name)
        
        # Run the discovery pipeline
        result = await pipeline.discover_drugs(sanitized_disease_name)
        
        # Format scores to 2 decimal places
        for candidate in result.candidates:
            candidate.binding_affinity_score = round(candidate.binding_affinity_score, 2)
            candidate.binding_confidence = round(candidate.binding_confidence, 2)
            candidate.composite_score = round(candidate.composite_score, 2)
            candidate.properties.drug_likeness_score = round(
                candidate.properties.drug_likeness_score, 2
            )
            candidate.toxicity.toxicity_score = round(candidate.toxicity.toxicity_score, 2)
        
        # Create response
        response = DiscoveryResponse(
            query=result.query,
            timestamp=result.timestamp.isoformat(),
            processing_time_seconds=round(result.processing_time_seconds, 2),
            candidates=result.candidates,
            metadata={
                "targets_found": result.targets_found,
                "molecules_analyzed": result.molecules_analyzed,
                "api_version": result.api_version
            },
            warnings=result.warnings
        )
        
        return response
        
    except ValueError as e:
        # Validation errors
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_INPUT",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        # Internal server errors
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An internal error occurred during drug discovery",
                "details": {"error": str(e)},
                "timestamp": datetime.utcnow().isoformat()
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
