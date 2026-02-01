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
        job = create_docking_job(
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
            message="Docking job submitted successfully",
            estimated_time_seconds=300  # ~5 minutes typical
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
    job = get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": f"Docking job not found: {job_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    queue_pos = get_queue_position(job_id) if job.status == DockingJobStatus.QUEUED else None
    
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
    job = get_job(job_id)
    
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
                "pose_number": i + 1,
                "binding_affinity": result.binding_affinity,
                "rmsd_lb": result.rmsd_lb,
                "rmsd_ub": result.rmsd_ub,
                "pdbqt_data": result.pdbqt_data
            })
    
    return {
        "job_id": job.id,
        "candidate_id": job.candidate_id,
        "target_uniprot_id": job.target_uniprot_id,
        "status": job.status.value,
        "best_affinity": job.best_affinity,
        "num_poses": len(poses),
        "poses": poses,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
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
    job = get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": f"Docking job not found: {job_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    if cancel_docking_job(job_id):
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
