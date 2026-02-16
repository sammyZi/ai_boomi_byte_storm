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
from app.alphafold_client import AlphaFoldClient
from app.rate_limiter import RateLimiter, RateLimitMiddleware
from app.security import anonymize_ip, get_client_ip
from app.disease_resolver import get_disease_resolver, DiseaseMatch, SuggestionResponse, ConfidenceLevel
from app.docking.models import (
    DockingJobRequest,
    DockingJobResponse,
    DockingStatusResponse,
    DockingJob,
    DockingJobStatus
)
from app.docking.tasks import (
    create_docking_job,
    run_docking_job,
    get_job,
    cancel_docking_job,
    get_queue_position
)
from app.docking.router import router as docking_router


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

# Include the docking router for job history and other endpoints
app.include_router(docking_router)

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


# ==================== Disease Resolution API ====================

@app.get(
    "/api/diseases/suggest",
    summary="Get intelligent disease suggestions",
    description="""
    Intelligent disease resolution with 5-layer architecture:
    
    **Layer 1 - Input Normalization:**
    - Typo correction (Levenshtein distance < 2)
    - Abbreviation expansion (AD → Alzheimer's disease)
    - Common misspelling fixes
    
    **Layer 2 - Multi-Ontology Lookup:**
    - EFO (Experimental Factor Ontology) with 20K+ terms
    - Cross-references to Disease Ontology, MeSH
    
    **Layer 3 - Hierarchical Expansion:**
    - Walks up ontology tree if specific disease has no targets
    - Suggests broader parent diseases
    
    **Layer 4 - NLP Semantic Matching:**
    - Cosine similarity matching
    - Medical term weighting
    
    **Layer 5 - Smart Fallbacks:**
    - Symptom detection → disease suggestions
    - Category-based browsing
    
    Returns ranked suggestions with confidence scores and target counts.
    """,
    responses={
        200: {
            "description": "Disease suggestions with confidence scores",
            "content": {
                "application/json": {
                    "example": {
                        "query": "alzheimers",
                        "suggestions": [
                            {
                                "disease_id": "EFO_0000249",
                                "disease_name": "Alzheimer's disease",
                                "match_type": "typo_corrected",
                                "confidence": 0.92,
                                "confidence_level": "high",
                                "target_count": 1847,
                                "correction_applied": "Corrected: alzheimers → Alzheimer's"
                            }
                        ],
                        "confidence_level": "high",
                        "message": "Did you mean: Alzheimer's disease?",
                        "processing_time_ms": 145
                    }
                }
            }
        },
        400: {"description": "Invalid query", "model": ErrorResponse}
    },
    tags=["Disease Resolution"]
)
async def get_disease_suggestions(
    q: str,
    max_results: int = 10
):
    """
    Get intelligent disease suggestions based on user query.
    
    Args:
        q: Search query (minimum 2 characters)
        max_results: Maximum number of suggestions to return (default: 10)
    
    Returns:
        SuggestionResponse with ranked disease matches
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_QUERY",
                "message": "Query must be at least 2 characters",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    if len(q) > 200:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "QUERY_TOO_LONG",
                "message": "Query must not exceed 200 characters",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    resolver = get_disease_resolver()
    result = await resolver.resolve(q, max_suggestions=max_results)
    
    # Convert to dict for JSON response
    return {
        "query": result.query,
        "suggestions": [
            {
                "disease_id": s.disease_id,
                "disease_name": s.disease_name,
                "match_type": s.match_type.value,
                "confidence": round(s.confidence, 3),
                "confidence_level": s.confidence_level.value,
                "target_count": s.target_count,
                "synonyms": s.synonyms[:5] if s.synonyms else [],
                "description": s.description[:200] if s.description else "",
                "correction_applied": s.correction_applied,
                "parent_diseases": s.parent_diseases[:3] if s.parent_diseases else []
            }
            for s in result.suggestions
        ],
        "confidence_level": result.confidence_level.value,
        "message": result.message,
        "processing_time_ms": result.processing_time_ms
    }


@app.get(
    "/api/diseases/{disease_id}/details",
    summary="Get detailed disease information",
    description="Get comprehensive details about a disease including target count, synonyms, and parent diseases.",
    responses={
        200: {
            "description": "Disease details",
            "content": {
                "application/json": {
                    "example": {
                        "disease_id": "EFO_0000249",
                        "disease_name": "Alzheimer's disease",
                        "description": "A progressive neurodegenerative disease...",
                        "synonyms": ["AD", "Alzheimer disease", "Alzheimer dementia"],
                        "parent_diseases": ["neurodegenerative disease", "dementia"],
                        "target_count": 1847
                    }
                }
            }
        },
        404: {"description": "Disease not found", "model": ErrorResponse}
    },
    tags=["Disease Resolution"]
)
async def get_disease_details(disease_id: str):
    """
    Get detailed information about a specific disease.
    
    Args:
        disease_id: EFO disease identifier
    
    Returns:
        Detailed disease information
    """
    resolver = get_disease_resolver()
    details = await resolver.ontology.get_disease_details(disease_id)
    
    if not details:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "DISEASE_NOT_FOUND",
                "message": f"Disease with ID '{disease_id}' not found",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    return details


@app.get(
    "/api/protein/{uniprot_id}/structure",
    summary="Get protein structure from AlphaFold",
    description="Retrieve 3D protein structure in PDB format with pLDDT confidence scores. Uses caching with 24-hour TTL.",
    responses={
        200: {
            "description": "Protein structure data",
            "content": {
                "application/json": {
                    "example": {
                        "uniprot_id": "Q5S007",
                        "pdb_data": "ATOM 1 N ALA A 1 ...",
                        "plddt_score": 77.5,
                        "is_low_confidence": False,
                        "metadata": {
                            "sequence_length": 2527,
                            "gene": "LRRK2",
                            "organism": "Homo sapiens"
                        }
                    }
                }
            }
        },
        404: {"description": "Protein structure not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_protein_structure(uniprot_id: str):
    """Get protein structure from AlphaFold Database.
    
    Fetches protein structure by UniProt ID from AlphaFold, handling
    different model versions automatically. Results are cached for 24 hours.
    
    Args:
        uniprot_id: UniProt identifier (e.g., Q5S007, P12345)
    
    Returns:
        Protein structure with PDB data and confidence metrics
    """
    try:
        # Validate UniProt ID format
        uniprot_id = uniprot_id.strip().upper()
        if not uniprot_id or len(uniprot_id) < 4 or len(uniprot_id) > 15:
            raise HTTPException(
                status_code=400,
                detail="Invalid UniProt ID format"
            )
        
        # Fetch structure using AlphaFold client
        client = AlphaFoldClient()
        structure = await client.get_protein_structure(uniprot_id)
        
        if not structure:
            raise HTTPException(
                status_code=404,
                detail=f"No structure found for UniProt ID: {uniprot_id}"
            )
        
        # Return structure with additional metadata
        return {
            "uniprot_id": structure.uniprot_id,
            "pdb_data": structure.pdb_data,
            "plddt_score": structure.plddt_score,
            "is_low_confidence": structure.is_low_confidence,
            "confidence_category": (
                "very_high" if structure.plddt_score >= 90 else
                "high" if structure.plddt_score >= 70 else
                "low" if structure.plddt_score >= 50 else
                "very_low"
            )
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching protein structure for {uniprot_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch protein structure"
        )


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


# ============================================================================
# MOLECULAR DOCKING ENDPOINTS
# ============================================================================

@app.post(
    "/api/docking/submit",
    response_model=DockingJobResponse,
    responses={
        200: {
            "description": "Docking job submitted successfully",
            "model": DockingJobResponse
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
    summary="Submit a molecular docking job",
    description="""
    Submit a new molecular docking job to validate protein-ligand binding.
    
    The job will be queued and processed asynchronously. Use the returned
    job_id to check status and retrieve results.
    
    Required data:
    - candidate_id: ChEMBL ID of the drug candidate
    - target_uniprot_id: UniProt ID of the target protein  
    - disease_name: Disease being treated
    - smiles: SMILES string of the ligand molecule
    
    Optional parameters:
    - grid_params: Custom grid box parameters (auto-calculated if not provided)
    - docking_params: Custom docking parameters (uses defaults if not provided)
    """
)
async def submit_docking_job(request: DockingJobRequest) -> DockingJobResponse:
    """Submit a new molecular docking job.
    
    Args:
        request: DockingJobRequest with candidate and docking parameters
    
    Returns:
        DockingJobResponse with job_id for tracking
    """
    try:
        # Fetch protein structure from AlphaFold
        from app.alphafold_client import AlphaFoldClient
        
        alphafold = AlphaFoldClient()
        structure = await alphafold.get_protein_structure(request.target_uniprot_id)
        
        if not structure:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "STRUCTURE_NOT_FOUND",
                    "message": f"No protein structure found for {request.target_uniprot_id}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Create docking job
        job = await create_docking_job(
            candidate_id=request.candidate_id,
            target_uniprot_id=request.target_uniprot_id,
            disease_name=request.disease_name,
            smiles=request.smiles,
            pdb_data=structure.pdb_data,
            grid_params=request.grid_params,
            docking_params=request.docking_params
        )
        
        # Run docking synchronously for now (in production, use Celery)
        # For async execution, uncomment: celery_app.send_task('run_docking', args=[job.id])
        import threading
        thread = threading.Thread(target=run_docking_job, args=(job.id,))
        thread.start()
        
        return DockingJobResponse(
            job_id=job.id,
            status=job.status,
            message="Docking job submitted successfully. Progress will be tracked in real-time.",
            estimated_time_seconds=180  # ~3 minutes typical with OpenBabel conversion
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Docking submission error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DOCKING_SUBMISSION_ERROR",
                "message": f"Failed to submit docking job: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@app.get(
    "/api/docking/status/{job_id}",
    response_model=DockingStatusResponse,
    responses={
        200: {
            "description": "Docking job status",
            "model": DockingStatusResponse
        },
        404: {
            "description": "Job not found",
            "model": ErrorResponse
        }
    },
    summary="Get docking job status",
    description="Get the current status and results of a docking job."
)
async def get_docking_status(job_id: str) -> DockingStatusResponse:
    """Get status and results of a docking job.
    
    Args:
        job_id: The job identifier returned from submit
    
    Returns:
        DockingStatusResponse with job details and results
    """
    job = await get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": f"Docking job not found: {job_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    queue_pos = await get_queue_position(job_id) if job.status == DockingJobStatus.QUEUED else None
    
    # Calculate estimated time based on progress
    estimated_remaining = None
    if job.status == DockingJobStatus.QUEUED:
        # 2 minutes per queued job ahead
        estimated_remaining = (queue_pos or 1) * 120
    elif job.status == DockingJobStatus.RUNNING and job.started_at:
        # Estimate based on progress
        elapsed = (datetime.utcnow() - job.started_at.replace(tzinfo=None)).total_seconds()
        if job.progress_percent > 0:
            total_estimate = elapsed / (job.progress_percent / 100)
            estimated_remaining = max(0, int(total_estimate - elapsed))
        else:
            estimated_remaining = 180  # 3 minutes default
    
    return DockingStatusResponse(
        job=job,
        queue_position=queue_pos
    )


@app.get(
    "/api/docking/jobs/{job_id}/results",
    responses={
        200: {
            "description": "Docking results retrieved"
        },
        400: {
            "description": "Job not completed",
            "model": ErrorResponse
        },
        404: {
            "description": "Job not found",
            "model": ErrorResponse
        }
    },
    summary="Get docking job results",
    description="Get the results of a completed docking job including all poses and binding affinities."
)
async def get_docking_results(job_id: str):
    """Get docking results for a completed job.
    
    Args:
        job_id: The job identifier
    
    Returns:
        Docking results with poses and binding affinities
    """
    job = await get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": f"Docking job not found: {job_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    if job.status not in [DockingJobStatus.COMPLETED, DockingJobStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "JOB_NOT_COMPLETE",
                "message": f"Job {job_id} is not complete (status: {job.status})",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    # Build results response
    poses = []
    if job.results:
        for i, result in enumerate(job.results):
            poses.append({
                "pose_number": result.pose_number,
                "binding_affinity": result.binding_affinity,
                "rmsd_lb": result.rmsd_lb,
                "rmsd_ub": result.rmsd_ub,
                "pdbqt_data": result.pdbqt_data
            })
    
    # Calculate execution time
    execution_time = None
    if job.started_at and job.completed_at:
        execution_time = (job.completed_at - job.started_at).total_seconds()
    
    # Load protein PDBQT data if not in memory but file path exists
    protein_pdbqt_data = job.protein_pdbqt_data
    logger.info(f"[{job_id}] Initial protein_pdbqt_data from job object: {len(protein_pdbqt_data) if protein_pdbqt_data else 0} bytes")
    logger.info(f"[{job_id}] Protein PDBQT path: {job.protein_pdbqt_path}")
    
    if not protein_pdbqt_data and job.protein_pdbqt_path:
        try:
            import os
            logger.info(f"[{job_id}] Attempting to load protein from file: {job.protein_pdbqt_path}")
            if os.path.exists(job.protein_pdbqt_path):
                with open(job.protein_pdbqt_path, 'r') as f:
                    protein_pdbqt_data = f.read()
                logger.info(f"[{job_id}] Loaded protein PDBQT from file: {len(protein_pdbqt_data)} bytes")
            else:
                logger.warning(f"[{job_id}] Protein PDBQT file does not exist: {job.protein_pdbqt_path}")
        except Exception as e:
            logger.warning(f"[{job_id}] Could not load protein PDBQT from file: {e}")
    
    # Debug: Log protein data status
    logger.info(f"[{job_id}] Returning results - protein_pdbqt_data length: {len(protein_pdbqt_data) if protein_pdbqt_data else 0} bytes")
    logger.info(f"[{job_id}] Returning results - num poses: {len(poses)}")
    
    return {
        "job_id": job.id,
        "candidate_id": job.candidate_id,
        "target_uniprot_id": job.target_uniprot_id,
        "status": job.status.value if hasattr(job.status, 'value') else job.status,
        "best_affinity": job.best_affinity,
        "num_poses": len(poses),
        "poses": poses,
        "protein_pdbqt": protein_pdbqt_data,  # Include protein structure for visualization
        "console_output": job.console_output,
        "execution_time_seconds": execution_time,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None
    }


@app.delete(
    "/api/docking/cancel/{job_id}",
    responses={
        200: {
            "description": "Job cancelled successfully"
        },
        400: {
            "description": "Job cannot be cancelled",
            "model": ErrorResponse
        },
        404: {
            "description": "Job not found",
            "model": ErrorResponse
        }
    },
    summary="Cancel a docking job",
    description="Cancel a queued docking job. Running jobs cannot be cancelled."
)
async def cancel_docking(job_id: str):
    """Cancel a queued docking job.
    
    Args:
        job_id: The job identifier to cancel
    
    Returns:
        Success message or error
    """
    job = await get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": f"Docking job not found: {job_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    if await cancel_docking_job(job_id):
        return {"message": "Docking job cancelled successfully", "job_id": job_id}
    else:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "CANNOT_CANCEL",
                "message": f"Job {job_id} cannot be cancelled (status: {job.status})",
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
