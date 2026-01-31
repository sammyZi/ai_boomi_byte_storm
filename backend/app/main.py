"""Main FastAPI application entry point.

This module initializes the FastAPI application with all necessary
middleware, routes, and configuration.
"""

import re
import time
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from config.settings import settings
from app.models import DiscoveryRequest, DiscoveryResponse, ErrorResponse, AnalyzeCandidateRequest, AnalyzeCandidateResponse
from app.discovery_pipeline import DiscoveryPipeline
from app.biomistral_engine import BioMistralEngine
from app.rate_limiter import RateLimiter, RateLimitMiddleware
from app.security import anonymize_ip, get_client_ip


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce HTTPS in production.
    
    Validates: Requirement 12.1
    """
    
    async def dispatch(self, request: Request, call_next):
        """Redirect HTTP requests to HTTPS in production."""
        if settings.enforce_https:
            # Check if request is not HTTPS
            if request.url.scheme != "https":
                # Check for X-Forwarded-Proto header (common in reverse proxy setups)
                forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
                if forwarded_proto != "https":
                    # Redirect to HTTPS
                    url = request.url.replace(scheme="https")
                    return JSONResponse(
                        status_code=301,
                        content={
                            "error_code": "HTTPS_REQUIRED",
                            "message": "HTTPS is required for this endpoint",
                            "redirect_url": str(url)
                        },
                        headers={"Location": str(url)}
                    )
        
        response = await call_next(request)
        
        # Add security headers
        if settings.enforce_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests with anonymized IP addresses.
    
    Validates: Requirement 12.8
    """
    
    async def dispatch(self, request: Request, call_next):
        """Log request with anonymized IP."""
        start_time = time.time()
        
        # Get and anonymize client IP
        client_ip = get_client_ip(request)
        anonymized_ip = anonymize_ip(client_ip)
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} from {anonymized_ip}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} for {request.method} {request.url.path} "
                f"from {anonymized_ip} (took {process_time:.2f}s)"
            )
            
            return response
        except Exception as e:
            # Log error with anonymized IP
            logger.error(
                f"Error processing request {request.method} {request.url.path} "
                f"from {anonymized_ip}: {str(e)}"
            )
            raise


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

# Add HTTPS enforcement middleware (must be first)
app.add_middleware(HTTPSRedirectMiddleware)

# Add logging middleware with IP anonymization
app.add_middleware(LoggingMiddleware)

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
        
        # Format scores to 2 decimal places and limit to top 20
        top_candidates = result.candidates[:20]
        for candidate in top_candidates:
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
            candidates=top_candidates,
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


@app.post(
    "/api/analyze-candidate",
    response_model=AnalyzeCandidateResponse,
    responses={
        200: {
            "description": "AI analysis generated successfully",
            "model": AnalyzeCandidateResponse
        },
        400: {
            "description": "Invalid input",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    summary="Generate AI analysis for a single drug candidate",
    description="""
    Generate AI-powered analysis for a single drug candidate on-demand.
    
    This endpoint allows lazy loading of AI analysis when a user views
    a specific candidate, rather than generating analysis for all candidates
    upfront during the discovery process.
    
    The analysis includes:
    - Molecular property interpretation
    - Binding affinity assessment
    - Drug-likeness evaluation
    - Safety profile analysis
    - Mechanism of action insights
    """
)
async def analyze_candidate(request: AnalyzeCandidateRequest) -> AnalyzeCandidateResponse:
    """Generate AI analysis for a single drug candidate.
    
    Args:
        request: AnalyzeCandidateRequest with molecule, target, properties, and toxicity
    
    Returns:
        AnalyzeCandidateResponse with AI analysis text
    """
    try:
        # Create BioMistral engine instance
        biomistral = BioMistralEngine()
        
        try:
            # Generate AI analysis
            analysis = await biomistral.analyze_candidate(
                request.molecule,
                request.target,
                request.properties,
                request.toxicity
            )
            
            if analysis:
                return AnalyzeCandidateResponse(
                    ai_analysis=analysis,
                    success=True,
                    message="AI analysis generated successfully"
                )
            else:
                return AnalyzeCandidateResponse(
                    ai_analysis=None,
                    success=False,
                    message="AI analysis unavailable - service may be offline"
                )
        finally:
            await biomistral.close()
        
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}", exc_info=True)
        return AnalyzeCandidateResponse(
            ai_analysis=None,
            success=False,
            message=f"AI analysis failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
