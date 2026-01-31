"""Unit tests for the docking API endpoints.

Tests cover all docking API endpoints including submission,
status, results, cancellation, and history.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base, get_db
from app.docking.router import router
from app.docking.models import DockingJobStatus, GridBoxParams, DockingParams
from app.docking.db_models import DockingJobDB, DockingResultDB
from app.docking.service import DockingService


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_engine():
    """Create an async test engine with in-memory SQLite."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Create an async session for testing."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def app(async_session):
    """Create a test FastAPI app with the docking router."""
    test_app = FastAPI()
    test_app.include_router(router)
    
    # Override the database dependency
    async def override_get_db():
        yield async_session
    
    test_app.dependency_overrides[get_db] = override_get_db
    
    return test_app


@pytest.fixture
async def client(app):
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


class TestSubmitEndpoint:
    """Tests for POST /api/docking/submit."""
    
    @pytest.mark.asyncio
    async def test_submit_single_job(self, client: AsyncClient):
        """Test submitting a single docking job."""
        response = await client.post(
            "/api/docking/submit",
            json={
                "candidate_ids": ["CHEMBL123"],
                "target_uniprot_id": "P12345",
                "disease_name": "Cancer",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["job_ids"]) == 1
        assert data["total_jobs"] == 1
        assert data["message"] == "Successfully submitted 1 docking jobs"
        assert data["estimated_time_seconds"] > 0
    
    @pytest.mark.asyncio
    async def test_submit_multiple_jobs(self, client: AsyncClient):
        """Test submitting multiple docking jobs."""
        response = await client.post(
            "/api/docking/submit",
            json={
                "candidate_ids": ["CHEMBL001", "CHEMBL002", "CHEMBL003"],
                "target_uniprot_id": "P12345",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["job_ids"]) == 3
        assert data["total_jobs"] == 3
    
    @pytest.mark.asyncio
    async def test_submit_with_custom_params(self, client: AsyncClient):
        """Test submitting with custom grid and docking parameters."""
        response = await client.post(
            "/api/docking/submit",
            json={
                "candidate_ids": ["CHEMBL123"],
                "target_uniprot_id": "P12345",
                "grid_params": {
                    "center_x": 10.0,
                    "center_y": 20.0,
                    "center_z": 30.0,
                    "size_x": 25.0,
                    "size_y": 25.0,
                    "size_z": 25.0,
                },
                "docking_params": {
                    "exhaustiveness": 16,
                    "num_modes": 10,
                    "energy_range": 4.0,
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["job_ids"]) == 1
    
    @pytest.mark.asyncio
    async def test_submit_empty_candidates_fails(self, client: AsyncClient):
        """Test that submitting with empty candidates fails."""
        response = await client.post(
            "/api/docking/submit",
            json={
                "candidate_ids": [],
                "target_uniprot_id": "P12345",
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_submit_too_many_candidates_fails(self, client: AsyncClient):
        """Test that submitting more than 20 candidates fails."""
        response = await client.post(
            "/api/docking/submit",
            json={
                "candidate_ids": [f"CHEMBL{i:03d}" for i in range(25)],
                "target_uniprot_id": "P12345",
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_submit_missing_target_fails(self, client: AsyncClient):
        """Test that missing target_uniprot_id fails."""
        response = await client.post(
            "/api/docking/submit",
            json={
                "candidate_ids": ["CHEMBL123"],
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestStatusEndpoint:
    """Tests for GET /api/docking/jobs/{job_id}/status."""
    
    @pytest.mark.asyncio
    async def test_get_status_queued_job(self, client: AsyncClient, async_session: AsyncSession):
        """Test getting status of a queued job."""
        # Create a job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.QUEUED.value,
        )
        async_session.add(job)
        await async_session.commit()
        await async_session.refresh(job)
        
        response = await client.get(f"/api/docking/jobs/{job.id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job.id
        assert data["status"] == "queued"
        assert data["progress_percent"] == 0
        assert data["queue_position"] is not None
    
    @pytest.mark.asyncio
    async def test_get_status_running_job(self, client: AsyncClient, async_session: AsyncSession):
        """Test getting status of a running job."""
        # Create a running job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.RUNNING.value,
            started_at=datetime.utcnow() - timedelta(seconds=60),
        )
        async_session.add(job)
        await async_session.commit()
        await async_session.refresh(job)
        
        response = await client.get(f"/api/docking/jobs/{job.id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["progress_percent"] > 0
    
    @pytest.mark.asyncio
    async def test_get_status_completed_job(self, client: AsyncClient, async_session: AsyncSession):
        """Test getting status of a completed job."""
        # Create a completed job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.COMPLETED.value,
            started_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow(),
            best_affinity=-8.5,
        )
        async_session.add(job)
        await async_session.commit()
        await async_session.refresh(job)
        
        response = await client.get(f"/api/docking/jobs/{job.id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress_percent"] == 100
    
    @pytest.mark.asyncio
    async def test_get_status_not_found(self, client: AsyncClient):
        """Test getting status of non-existent job."""
        response = await client.get("/api/docking/jobs/nonexistent-id/status")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "JOB_NOT_FOUND"


class TestResultsEndpoint:
    """Tests for GET /api/docking/jobs/{job_id}/results."""
    
    @pytest.mark.asyncio
    async def test_get_results_completed_job(self, client: AsyncClient, async_session: AsyncSession):
        """Test getting results of a completed job."""
        # Create a completed job with results
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.COMPLETED.value,
            completed_at=datetime.utcnow(),
            best_affinity=-8.5,
        )
        async_session.add(job)
        await async_session.flush()
        
        # Add results
        for i in range(3):
            result = DockingResultDB(
                job_id=job.id,
                pose_number=i + 1,
                binding_affinity=-8.5 + i * 0.5,
                rmsd_lb=0.0 if i == 0 else i * 1.5,
                rmsd_ub=0.0 if i == 0 else i * 2.0,
            )
            async_session.add(result)
        await async_session.commit()
        await async_session.refresh(job)
        
        response = await client.get(f"/api/docking/jobs/{job.id}/results")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job.id
        assert data["status"] == "completed"
        assert data["best_affinity"] == -8.5
        assert data["num_poses"] == 3
        assert len(data["poses"]) == 3
        assert data["poses"][0]["binding_affinity"] == -8.5
    
    @pytest.mark.asyncio
    async def test_get_results_not_completed(self, client: AsyncClient, async_session: AsyncSession):
        """Test that getting results of unfinished job fails."""
        # Create a queued job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.QUEUED.value,
        )
        async_session.add(job)
        await async_session.commit()
        await async_session.refresh(job)
        
        response = await client.get(f"/api/docking/jobs/{job.id}/results")
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "JOB_NOT_COMPLETED"
    
    @pytest.mark.asyncio
    async def test_get_results_failed_job(self, client: AsyncClient, async_session: AsyncSession):
        """Test getting results of a failed job."""
        # Create a failed job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.FAILED.value,
            completed_at=datetime.utcnow(),
            error_message="Docking failed",
        )
        async_session.add(job)
        await async_session.commit()
        await async_session.refresh(job)
        
        response = await client.get(f"/api/docking/jobs/{job.id}/results")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Docking failed"
        assert data["num_poses"] == 0
    
    @pytest.mark.asyncio
    async def test_get_results_not_found(self, client: AsyncClient):
        """Test getting results of non-existent job."""
        response = await client.get("/api/docking/jobs/nonexistent-id/results")
        
        assert response.status_code == 404


class TestCancelEndpoint:
    """Tests for DELETE /api/docking/jobs/{job_id}."""
    
    @pytest.mark.asyncio
    async def test_cancel_queued_job(self, client: AsyncClient, async_session: AsyncSession):
        """Test cancelling a queued job."""
        # Create a queued job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.QUEUED.value,
        )
        async_session.add(job)
        await async_session.commit()
        await async_session.refresh(job)
        
        response = await client.delete(f"/api/docking/jobs/{job.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job.id
        assert data["status"] == "cancelled"
        assert "cancelled" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_cancel_running_job(self, client: AsyncClient, async_session: AsyncSession):
        """Test cancelling a running job."""
        # Create a running job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )
        async_session.add(job)
        await async_session.commit()
        await async_session.refresh(job)
        
        response = await client.delete(f"/api/docking/jobs/{job.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_cancel_completed_job_fails(self, client: AsyncClient, async_session: AsyncSession):
        """Test that cancelling a completed job fails."""
        # Create a completed job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.COMPLETED.value,
            completed_at=datetime.utcnow(),
        )
        async_session.add(job)
        await async_session.commit()
        await async_session.refresh(job)
        
        response = await client.delete(f"/api/docking/jobs/{job.id}")
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "CANNOT_CANCEL"
    
    @pytest.mark.asyncio
    async def test_cancel_not_found(self, client: AsyncClient):
        """Test cancelling a non-existent job."""
        response = await client.delete("/api/docking/jobs/nonexistent-id")
        
        assert response.status_code == 404


class TestHistoryEndpoint:
    """Tests for GET /api/docking/jobs."""
    
    @pytest.mark.asyncio
    async def test_get_history_empty(self, client: AsyncClient):
        """Test getting history with no jobs."""
        response = await client.get("/api/docking/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_history_with_user_id(self, client: AsyncClient, async_session: AsyncSession, app: FastAPI):
        """Test getting history for a specific user."""
        user_id = "test_user"
        
        # Create jobs for the user
        for i in range(5):
            job = DockingJobDB(
                candidate_id=f"CHEMBL{i:03d}",
                target_uniprot_id="P12345",
                user_id=user_id,
                status=DockingJobStatus.COMPLETED.value,
            )
            async_session.add(job)
        await async_session.commit()
        
        # Note: In real tests, user_id would come from auth
        # For this test, we need to mock the endpoint behavior
        response = await client.get(f"/api/docking/jobs?page=1&page_size=10")
        
        # Without auth, should return empty
        assert response.status_code == 200
        data = response.json()
        # User ID is not passed, so returns empty
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_history_pagination(self, client: AsyncClient):
        """Test pagination parameters."""
        response = await client.get("/api/docking/jobs?page=2&page_size=5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 5
    
    @pytest.mark.asyncio
    async def test_get_history_filter_by_status(self, client: AsyncClient):
        """Test filtering by status."""
        response = await client.get("/api/docking/jobs?status=completed")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_history_filter_by_target(self, client: AsyncClient):
        """Test filtering by target protein."""
        response = await client.get("/api/docking/jobs?target_uniprot_id=P12345")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_history_invalid_page_size(self, client: AsyncClient):
        """Test that invalid page_size is rejected."""
        response = await client.get("/api/docking/jobs?page_size=200")
        
        assert response.status_code == 422  # Validation error


class TestValidation:
    """Tests for request validation."""
    
    @pytest.mark.asyncio
    async def test_invalid_grid_params(self, client: AsyncClient):
        """Test that invalid grid params are rejected."""
        response = await client.post(
            "/api/docking/submit",
            json={
                "candidate_ids": ["CHEMBL123"],
                "target_uniprot_id": "P12345",
                "grid_params": {
                    "center_x": 10.0,
                    "center_y": 20.0,
                    "center_z": 30.0,
                    "size_x": 100.0,  # Too large (max 50)
                    "size_y": 25.0,
                    "size_z": 25.0,
                }
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_invalid_docking_params(self, client: AsyncClient):
        """Test that invalid docking params are rejected."""
        response = await client.post(
            "/api/docking/submit",
            json={
                "candidate_ids": ["CHEMBL123"],
                "target_uniprot_id": "P12345",
                "docking_params": {
                    "exhaustiveness": 100,  # Too high (max 32)
                    "num_modes": 9,
                    "energy_range": 3.0,
                }
            }
        )
        
        assert response.status_code == 422


class TestErrorResponses:
    """Tests for error response formats."""
    
    @pytest.mark.asyncio
    async def test_404_error_format(self, client: AsyncClient):
        """Test 404 error response format."""
        response = await client.get("/api/docking/jobs/nonexistent/status")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "error_code" in data["detail"]
        assert "message" in data["detail"]
        assert "timestamp" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_400_error_format(self, client: AsyncClient, async_session: AsyncSession):
        """Test 400 error response format."""
        # Create a completed job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.COMPLETED.value,
        )
        async_session.add(job)
        await async_session.commit()
        await async_session.refresh(job)
        
        response = await client.delete(f"/api/docking/jobs/{job.id}")
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "error_code" in data["detail"]
