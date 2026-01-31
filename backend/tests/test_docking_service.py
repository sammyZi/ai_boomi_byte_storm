"""Unit tests for the DockingService class.

Tests cover job submission, status retrieval, results retrieval,
job cancellation, and job limits.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base
from app.docking.service import (
    DockingService,
    JobSubmissionResult,
    JobStatusInfo,
    JobResults,
    DockingServiceError,
    JobNotFoundError,
    JobLimitExceededError,
    InvalidJobStateError,
    MAX_QUEUED_JOBS_PER_USER,
    ESTIMATED_TIME_PER_JOB_SECONDS,
)
from app.docking.models import (
    DockingJobStatus,
    DockingParams,
    GridBoxParams,
    DockingResult,
)
from app.docking.db_models import DockingJobDB, DockingResultDB


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
async def service(async_session):
    """Create a DockingService instance for testing."""
    return DockingService(async_session)


class TestSubmitDockingJob:
    """Tests for job submission."""
    
    @pytest.mark.asyncio
    async def test_submit_job_minimal(self, service: DockingService):
        """Test submitting a job with minimal parameters."""
        result = await service.submit_docking_job(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
        )
        
        assert result.job_id is not None
        assert result.status == DockingJobStatus.QUEUED
        assert result.queue_position >= 1
        assert result.estimated_time_seconds >= 0
    
    @pytest.mark.asyncio
    async def test_submit_job_with_all_params(self, service: DockingService):
        """Test submitting a job with all parameters."""
        grid_params = GridBoxParams(
            center_x=10.0,
            center_y=20.0,
            center_z=30.0,
            size_x=25.0,
            size_y=25.0,
            size_z=25.0,
        )
        docking_params = DockingParams(
            exhaustiveness=16,
            num_modes=10,
            energy_range=4.0,
        )
        
        result = await service.submit_docking_job(
            candidate_id="CHEMBL456",
            target_uniprot_id="Q67890",
            disease_name="Cancer",
            user_id="user_123",
            grid_params=grid_params,
            docking_params=docking_params,
        )
        
        assert result.job_id is not None
        assert result.status == DockingJobStatus.QUEUED
        
        # Verify job was saved with parameters
        job = await service.get_job_by_id(result.job_id)
        assert job is not None
        assert job.candidate_id == "CHEMBL456"
        assert job.target_uniprot_id == "Q67890"
        assert job.disease_name == "Cancer"
        assert job.user_id == "user_123"
        assert job.grid_params is not None
        assert job.grid_params.center_x == 10.0
        assert job.docking_params is not None
        assert job.docking_params.exhaustiveness == 16
    
    @pytest.mark.asyncio
    async def test_submit_job_increments_queue_position(self, service: DockingService):
        """Test that queue position increases with each submission."""
        result1 = await service.submit_docking_job(
            candidate_id="CHEMBL001",
            target_uniprot_id="P12345",
        )
        result2 = await service.submit_docking_job(
            candidate_id="CHEMBL002",
            target_uniprot_id="P12345",
        )
        result3 = await service.submit_docking_job(
            candidate_id="CHEMBL003",
            target_uniprot_id="P12345",
        )
        
        # Queue positions should be sequential
        assert result1.queue_position == 1
        assert result2.queue_position == 2
        assert result3.queue_position == 3
    
    @pytest.mark.asyncio
    async def test_submit_job_user_limit_exceeded(self, service: DockingService, async_session: AsyncSession):
        """Test that job limit is enforced."""
        user_id = "limited_user"
        
        # Create MAX_QUEUED_JOBS_PER_USER jobs directly in DB
        for i in range(MAX_QUEUED_JOBS_PER_USER):
            job = DockingJobDB(
                candidate_id=f"CHEMBL{i:03d}",
                target_uniprot_id="P12345",
                user_id=user_id,
                status=DockingJobStatus.QUEUED.value,
            )
            async_session.add(job)
        await async_session.flush()
        
        # Now try to submit one more
        with pytest.raises(JobLimitExceededError) as exc_info:
            await service.submit_docking_job(
                candidate_id="CHEMBL999",
                target_uniprot_id="P12345",
                user_id=user_id,
            )
        
        assert "Maximum is" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_job_no_limit_without_user_id(self, service: DockingService):
        """Test that job limit is not enforced without user_id."""
        # Submit many jobs without user_id
        for i in range(10):
            result = await service.submit_docking_job(
                candidate_id=f"CHEMBL{i:03d}",
                target_uniprot_id="P12345",
            )
            assert result.job_id is not None


class TestSubmitBatchJobs:
    """Tests for batch job submission."""
    
    @pytest.mark.asyncio
    async def test_submit_batch_jobs(self, service: DockingService):
        """Test submitting multiple jobs at once."""
        candidate_ids = ["CHEMBL001", "CHEMBL002", "CHEMBL003"]
        
        results = await service.submit_batch_jobs(
            candidate_ids=candidate_ids,
            target_uniprot_id="P12345",
            disease_name="Cancer",
            user_id="batch_user",
        )
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.job_id is not None
            assert result.status == DockingJobStatus.QUEUED
    
    @pytest.mark.asyncio
    async def test_submit_batch_exceeds_limit(self, service: DockingService, async_session: AsyncSession):
        """Test that batch submission respects job limits."""
        user_id = "batch_limit_user"
        
        # Create 95 jobs
        for i in range(95):
            job = DockingJobDB(
                candidate_id=f"CHEMBL{i:03d}",
                target_uniprot_id="P12345",
                user_id=user_id,
                status=DockingJobStatus.QUEUED.value,
            )
            async_session.add(job)
        await async_session.flush()
        
        # Try to submit 10 more (would exceed 100 limit)
        with pytest.raises(JobLimitExceededError):
            await service.submit_batch_jobs(
                candidate_ids=[f"NEW{i}" for i in range(10)],
                target_uniprot_id="P12345",
                user_id=user_id,
            )


class TestGetJobStatus:
    """Tests for job status retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_status_queued_job(self, service: DockingService):
        """Test getting status of a queued job."""
        result = await service.submit_docking_job(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
        )
        
        status = await service.get_job_status(result.job_id)
        
        assert status.job_id == result.job_id
        assert status.status == DockingJobStatus.QUEUED
        assert status.progress_percent == 0
        assert status.queue_position is not None
        assert status.queue_position >= 1
        assert status.estimated_time_remaining is not None
    
    @pytest.mark.asyncio
    async def test_get_status_running_job(self, service: DockingService, async_session: AsyncSession):
        """Test getting status of a running job."""
        # Create a running job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.RUNNING.value,
            started_at=datetime.utcnow() - timedelta(seconds=60),
        )
        async_session.add(job)
        await async_session.flush()
        
        status = await service.get_job_status(job.id)
        
        assert status.status == DockingJobStatus.RUNNING
        assert status.progress_percent > 0
        assert status.queue_position is None
    
    @pytest.mark.asyncio
    async def test_get_status_completed_job(self, service: DockingService, async_session: AsyncSession):
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
        await async_session.flush()
        
        status = await service.get_job_status(job.id)
        
        assert status.status == DockingJobStatus.COMPLETED
        assert status.progress_percent == 100
        assert status.queue_position is None
    
    @pytest.mark.asyncio
    async def test_get_status_failed_job(self, service: DockingService, async_session: AsyncSession):
        """Test getting status of a failed job."""
        # Create a failed job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.FAILED.value,
            error_message="Docking execution failed",
            completed_at=datetime.utcnow(),
        )
        async_session.add(job)
        await async_session.flush()
        
        status = await service.get_job_status(job.id)
        
        assert status.status == DockingJobStatus.FAILED
        assert status.progress_percent == 100
        assert status.error_message == "Docking execution failed"
    
    @pytest.mark.asyncio
    async def test_get_status_not_found(self, service: DockingService):
        """Test getting status of a non-existent job."""
        with pytest.raises(JobNotFoundError):
            await service.get_job_status("nonexistent-job-id")


class TestGetJobResults:
    """Tests for job results retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_results_completed_job(self, service: DockingService, async_session: AsyncSession):
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
        await async_session.flush()
        
        results = await service.get_job_results(job.id)
        
        assert results.job_id == job.id
        assert results.status == DockingJobStatus.COMPLETED
        assert results.best_affinity == -8.5
        assert len(results.poses) == 3
        assert results.poses[0].pose_number == 1
        assert results.poses[0].binding_affinity == -8.5
    
    @pytest.mark.asyncio
    async def test_get_results_failed_job(self, service: DockingService, async_session: AsyncSession):
        """Test getting results of a failed job."""
        # Create a failed job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.FAILED.value,
            error_message="Docking failed",
            completed_at=datetime.utcnow(),
        )
        async_session.add(job)
        await async_session.flush()
        
        results = await service.get_job_results(job.id)
        
        assert results.status == DockingJobStatus.FAILED
        assert results.error_message == "Docking failed"
        assert len(results.poses) == 0
    
    @pytest.mark.asyncio
    async def test_get_results_not_finished(self, service: DockingService):
        """Test that getting results of unfinished job raises error."""
        result = await service.submit_docking_job(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
        )
        
        with pytest.raises(InvalidJobStateError) as exc_info:
            await service.get_job_results(result.job_id)
        
        assert "not finished" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_get_results_not_found(self, service: DockingService):
        """Test getting results of a non-existent job."""
        with pytest.raises(JobNotFoundError):
            await service.get_job_results("nonexistent-job-id")


class TestCancelJob:
    """Tests for job cancellation."""
    
    @pytest.mark.asyncio
    async def test_cancel_queued_job(self, service: DockingService):
        """Test cancelling a queued job."""
        result = await service.submit_docking_job(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            user_id="user_123",
        )
        
        success = await service.cancel_job(result.job_id)
        
        assert success is True
        
        status = await service.get_job_status(result.job_id)
        assert status.status == DockingJobStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_cancel_running_job(self, service: DockingService, async_session: AsyncSession):
        """Test cancelling a running job."""
        # Create a running job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )
        async_session.add(job)
        await async_session.flush()
        
        success = await service.cancel_job(job.id)
        
        assert success is True
        
        status = await service.get_job_status(job.id)
        assert status.status == DockingJobStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_cancel_completed_job_fails(self, service: DockingService, async_session: AsyncSession):
        """Test that cancelling a completed job fails."""
        # Create a completed job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.COMPLETED.value,
            completed_at=datetime.utcnow(),
        )
        async_session.add(job)
        await async_session.flush()
        
        with pytest.raises(InvalidJobStateError):
            await service.cancel_job(job.id)
    
    @pytest.mark.asyncio
    async def test_cancel_wrong_user(self, service: DockingService, async_session: AsyncSession):
        """Test that users can only cancel their own jobs."""
        # Create a job owned by user_1
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            user_id="user_1",
            status=DockingJobStatus.QUEUED.value,
        )
        async_session.add(job)
        await async_session.flush()
        
        # Try to cancel as user_2
        with pytest.raises(JobNotFoundError):
            await service.cancel_job(job.id, user_id="user_2")
    
    @pytest.mark.asyncio
    async def test_cancel_not_found(self, service: DockingService):
        """Test cancelling a non-existent job."""
        with pytest.raises(JobNotFoundError):
            await service.cancel_job("nonexistent-job-id")


class TestGetUserJobHistory:
    """Tests for user job history retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_user_history(self, service: DockingService, async_session: AsyncSession):
        """Test getting a user's job history."""
        user_id = "history_user"
        
        # Create jobs for the user
        for i in range(5):
            job = DockingJobDB(
                candidate_id=f"CHEMBL{i:03d}",
                target_uniprot_id="P12345",
                user_id=user_id,
                status=DockingJobStatus.COMPLETED.value if i % 2 == 0 else DockingJobStatus.QUEUED.value,
            )
            async_session.add(job)
        await async_session.flush()
        
        jobs, total = await service.get_user_job_history(user_id)
        
        assert total == 5
        assert len(jobs) == 5
    
    @pytest.mark.asyncio
    async def test_get_user_history_with_status_filter(self, service: DockingService, async_session: AsyncSession):
        """Test filtering job history by status."""
        user_id = "filter_user"
        
        # Create 3 completed and 2 queued jobs
        for i in range(5):
            job = DockingJobDB(
                candidate_id=f"CHEMBL{i:03d}",
                target_uniprot_id="P12345",
                user_id=user_id,
                status=DockingJobStatus.COMPLETED.value if i < 3 else DockingJobStatus.QUEUED.value,
            )
            async_session.add(job)
        await async_session.flush()
        
        jobs, total = await service.get_user_job_history(
            user_id,
            status=DockingJobStatus.COMPLETED,
        )
        
        assert total == 3
        assert len(jobs) == 3
        for job in jobs:
            assert job.status == DockingJobStatus.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_get_user_history_with_target_filter(self, service: DockingService, async_session: AsyncSession):
        """Test filtering job history by target protein."""
        user_id = "target_filter_user"
        
        # Create jobs for different targets
        for i in range(5):
            job = DockingJobDB(
                candidate_id=f"CHEMBL{i:03d}",
                target_uniprot_id="P12345" if i < 3 else "Q67890",
                user_id=user_id,
                status=DockingJobStatus.COMPLETED.value,
            )
            async_session.add(job)
        await async_session.flush()
        
        jobs, total = await service.get_user_job_history(
            user_id,
            target_uniprot_id="P12345",
        )
        
        assert total == 3
        assert len(jobs) == 3
    
    @pytest.mark.asyncio
    async def test_get_user_history_with_date_filter(self, service: DockingService, async_session: AsyncSession):
        """Test filtering job history by date."""
        user_id = "date_filter_user"
        
        # Create old and new jobs
        old_time = datetime.utcnow() - timedelta(days=7)
        new_time = datetime.utcnow() - timedelta(hours=1)
        
        job_old = DockingJobDB(
            candidate_id="CHEMBL_OLD",
            target_uniprot_id="P12345",
            user_id=user_id,
            status=DockingJobStatus.COMPLETED.value,
            created_at=old_time,
        )
        job_new = DockingJobDB(
            candidate_id="CHEMBL_NEW",
            target_uniprot_id="P12345",
            user_id=user_id,
            status=DockingJobStatus.COMPLETED.value,
            created_at=new_time,
        )
        async_session.add(job_old)
        async_session.add(job_new)
        await async_session.flush()
        
        # Get jobs since yesterday
        since = datetime.utcnow() - timedelta(days=1)
        jobs, total = await service.get_user_job_history(user_id, since=since)
        
        assert total == 1
        assert jobs[0].candidate_id == "CHEMBL_NEW"
    
    @pytest.mark.asyncio
    async def test_get_user_history_pagination(self, service: DockingService, async_session: AsyncSession):
        """Test pagination of job history."""
        user_id = "pagination_user"
        
        # Create 15 jobs
        for i in range(15):
            job = DockingJobDB(
                candidate_id=f"CHEMBL{i:03d}",
                target_uniprot_id="P12345",
                user_id=user_id,
                status=DockingJobStatus.COMPLETED.value,
            )
            async_session.add(job)
        await async_session.flush()
        
        # Get first page
        jobs, total = await service.get_user_job_history(user_id, limit=5, offset=0)
        assert total == 15
        assert len(jobs) == 5
        
        # Get second page
        jobs, total = await service.get_user_job_history(user_id, limit=5, offset=5)
        assert total == 15
        assert len(jobs) == 5
        
        # Get last page
        jobs, total = await service.get_user_job_history(user_id, limit=5, offset=10)
        assert total == 15
        assert len(jobs) == 5
    
    @pytest.mark.asyncio
    async def test_get_user_history_empty(self, service: DockingService):
        """Test getting history for user with no jobs."""
        jobs, total = await service.get_user_job_history("no_jobs_user")
        
        assert total == 0
        assert len(jobs) == 0


class TestUpdateJobStatus:
    """Tests for updating job status."""
    
    @pytest.mark.asyncio
    async def test_update_to_running(self, service: DockingService):
        """Test updating job status to running."""
        result = await service.submit_docking_job(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
        )
        
        job = await service.update_job_status(
            result.job_id,
            DockingJobStatus.RUNNING,
        )
        
        assert job.status == DockingJobStatus.RUNNING.value
        assert job.started_at is not None
    
    @pytest.mark.asyncio
    async def test_update_to_completed(self, service: DockingService, async_session: AsyncSession):
        """Test updating job status to completed."""
        # Create a running job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )
        async_session.add(job)
        await async_session.flush()
        
        updated = await service.update_job_status(
            job.id,
            DockingJobStatus.COMPLETED,
            best_affinity=-8.5,
        )
        
        assert updated.status == DockingJobStatus.COMPLETED.value
        assert updated.completed_at is not None
        assert updated.best_affinity == -8.5
    
    @pytest.mark.asyncio
    async def test_update_to_failed(self, service: DockingService, async_session: AsyncSession):
        """Test updating job status to failed."""
        # Create a running job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )
        async_session.add(job)
        await async_session.flush()
        
        updated = await service.update_job_status(
            job.id,
            DockingJobStatus.FAILED,
            error_message="Vina execution failed",
        )
        
        assert updated.status == DockingJobStatus.FAILED.value
        assert updated.completed_at is not None
        assert updated.error_message == "Vina execution failed"


class TestAddJobResult:
    """Tests for adding job results."""
    
    @pytest.mark.asyncio
    async def test_add_result(self, service: DockingService, async_session: AsyncSession):
        """Test adding a docking result to a job."""
        # Create a job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.RUNNING.value,
        )
        async_session.add(job)
        await async_session.flush()
        
        result = await service.add_job_result(
            job_id=job.id,
            pose_number=1,
            binding_affinity=-8.5,
            rmsd_lb=0.0,
            rmsd_ub=0.0,
            pdbqt_data="ATOM  1  C  LIG  1  0.000  0.000  0.000",
        )
        
        assert result.id is not None
        assert result.job_id == job.id
        assert result.pose_number == 1
        assert result.binding_affinity == -8.5
        assert result.pdbqt_data is not None
    
    @pytest.mark.asyncio
    async def test_add_multiple_results(self, service: DockingService, async_session: AsyncSession):
        """Test adding multiple docking results to a job."""
        # Create a job
        job = DockingJobDB(
            candidate_id="CHEMBL123",
            target_uniprot_id="P12345",
            status=DockingJobStatus.RUNNING.value,
        )
        async_session.add(job)
        await async_session.flush()
        
        # Add 5 poses
        for i in range(5):
            await service.add_job_result(
                job_id=job.id,
                pose_number=i + 1,
                binding_affinity=-8.5 + i * 0.5,
                rmsd_lb=0.0 if i == 0 else i * 1.0,
                rmsd_ub=0.0 if i == 0 else i * 1.5,
            )
        
        # Refresh to get results
        await async_session.refresh(job)
        
        assert len(job.results) == 5


class TestExceptionTypes:
    """Tests for exception types."""
    
    def test_docking_service_error_is_exception(self):
        """Test that DockingServiceError is an Exception."""
        assert issubclass(DockingServiceError, Exception)
    
    def test_job_not_found_error(self):
        """Test JobNotFoundError."""
        error = JobNotFoundError("Job xyz not found")
        assert "xyz" in str(error)
        assert isinstance(error, DockingServiceError)
    
    def test_job_limit_exceeded_error(self):
        """Test JobLimitExceededError."""
        error = JobLimitExceededError("Too many jobs")
        assert "Too many" in str(error)
        assert isinstance(error, DockingServiceError)
    
    def test_invalid_job_state_error(self):
        """Test InvalidJobStateError."""
        error = InvalidJobStateError("Cannot cancel completed job")
        assert "completed" in str(error)
        assert isinstance(error, DockingServiceError)
