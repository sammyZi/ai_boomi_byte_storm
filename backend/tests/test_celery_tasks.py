"""Tests for the Celery task definitions for docking jobs.

Tests cover:
- run_docking_task: async docking execution workflow
- Retry logic with exponential backoff
- Concurrency configuration validation
- Error handling at each stage
- cleanup_old_jobs: periodic cleanup task
- get_queue_status: queue statistics
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any

from app.docking.celery_tasks import (
    run_docking_task,
    cleanup_old_jobs,
    get_queue_status,
)
from app.docking import tasks
from app.docking.models import (
    DockingJob,
    DockingJobStatus,
    DockingParams,
    GridBoxParams,
    DockingResult,
)


# Sample test data
SAMPLE_CANDIDATE_ID = "CHEMBL12345"
SAMPLE_TARGET_UNIPROT_ID = "P12345"
SAMPLE_DISEASE_NAME = "Test Disease"
SAMPLE_SMILES = "CCO"  # Ethanol
SAMPLE_PDB_DATA = """ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00  0.00           C
END
"""

SAMPLE_GRID_PARAMS = {
    "center_x": 10.0,
    "center_y": 20.0,
    "center_z": 30.0,
    "size_x": 25.0,
    "size_y": 25.0,
    "size_z": 25.0,
}

SAMPLE_DOCKING_PARAMS = {
    "exhaustiveness": 8,
    "num_modes": 9,
    "energy_range": 3.0,
}


@pytest.fixture
def mock_job():
    """Create a mock docking job."""
    return DockingJob(
        id="test-job-id",
        candidate_id=SAMPLE_CANDIDATE_ID,
        target_uniprot_id=SAMPLE_TARGET_UNIPROT_ID,
        disease_name=SAMPLE_DISEASE_NAME,
        status=DockingJobStatus.COMPLETED,
        results=[
            DockingResult(
                pose_number=1,
                binding_affinity=-8.5,
                rmsd_lb=0.0,
                rmsd_ub=0.0,
            ),
            DockingResult(
                pose_number=2,
                binding_affinity=-7.2,
                rmsd_lb=1.5,
                rmsd_ub=2.3,
            ),
        ],
        best_affinity=-8.5,
    )


@pytest.fixture
def clean_jobs_store():
    """Clean the jobs store before and after tests."""
    tasks._jobs_store.clear()
    tasks._job_data.clear()
    yield
    tasks._jobs_store.clear()
    tasks._job_data.clear()


def call_docking_task(candidate_id, target_uniprot_id, disease_name,
                      smiles, pdb_data, grid_params=None, docking_params=None):
    """Helper to call the wrapped docking task."""
    return run_docking_task.__wrapped__(
        candidate_id,
        target_uniprot_id,
        disease_name,
        smiles,
        pdb_data,
        grid_params,
        docking_params,
    )


class TestRunDockingTaskSuccess:
    """Tests for successful docking task execution."""

    def test_run_docking_task_basic(self, mock_job, clean_jobs_store):
        """Test basic docking task execution."""
        with patch.object(tasks, 'create_docking_job', return_value=mock_job) as mock_create, \
             patch.object(tasks, 'run_docking_job', return_value=mock_job) as mock_run:
            
            # Call the underlying function (not the Celery task directly)
            result = call_docking_task(
                SAMPLE_CANDIDATE_ID,
                SAMPLE_TARGET_UNIPROT_ID,
                SAMPLE_DISEASE_NAME,
                SAMPLE_SMILES,
                SAMPLE_PDB_DATA,
            )
            
            assert result["job_id"] == "test-job-id"
            assert result["status"] == "completed"
            assert result["results_count"] == 2
            assert result["best_affinity"] == -8.5
            assert result["error"] is None
            
            mock_create.assert_called_once()
            mock_run.assert_called_once_with(mock_job.id)

    def test_run_docking_task_with_grid_params(self, mock_job, clean_jobs_store):
        """Test docking task with custom grid parameters."""
        with patch.object(tasks, 'create_docking_job', return_value=mock_job), \
             patch.object(tasks, 'run_docking_job', return_value=mock_job):
            
            result = call_docking_task(
                SAMPLE_CANDIDATE_ID,
                SAMPLE_TARGET_UNIPROT_ID,
                SAMPLE_DISEASE_NAME,
                SAMPLE_SMILES,
                SAMPLE_PDB_DATA,
                grid_params=SAMPLE_GRID_PARAMS,
            )
            
            assert result["status"] == "completed"

    def test_run_docking_task_with_docking_params(self, mock_job, clean_jobs_store):
        """Test docking task with custom docking parameters."""
        with patch.object(tasks, 'create_docking_job', return_value=mock_job), \
             patch.object(tasks, 'run_docking_job', return_value=mock_job):
            
            result = call_docking_task(
                SAMPLE_CANDIDATE_ID,
                SAMPLE_TARGET_UNIPROT_ID,
                SAMPLE_DISEASE_NAME,
                SAMPLE_SMILES,
                SAMPLE_PDB_DATA,
                docking_params=SAMPLE_DOCKING_PARAMS,
            )
            
            assert result["status"] == "completed"

    def test_run_docking_task_with_all_params(self, mock_job, clean_jobs_store):
        """Test docking task with both grid and docking parameters."""
        with patch.object(tasks, 'create_docking_job', return_value=mock_job) as mock_create, \
             patch.object(tasks, 'run_docking_job', return_value=mock_job):
            
            result = call_docking_task(
                SAMPLE_CANDIDATE_ID,
                SAMPLE_TARGET_UNIPROT_ID,
                SAMPLE_DISEASE_NAME,
                SAMPLE_SMILES,
                SAMPLE_PDB_DATA,
                grid_params=SAMPLE_GRID_PARAMS,
                docking_params=SAMPLE_DOCKING_PARAMS,
            )
            
            assert result["status"] == "completed"
            
            # Verify parameters were converted to models
            call_kwargs = mock_create.call_args[1]
            assert isinstance(call_kwargs["grid_params"], GridBoxParams)
            assert isinstance(call_kwargs["docking_params"], DockingParams)

    def test_run_docking_task_logs_start(self, mock_job, clean_jobs_store):
        """Test that task logs the start."""
        with patch.object(tasks, 'create_docking_job', return_value=mock_job), \
             patch.object(tasks, 'run_docking_job', return_value=mock_job), \
             patch('app.docking.celery_tasks.logger') as mock_logger:
            
            call_docking_task(
                SAMPLE_CANDIDATE_ID,
                SAMPLE_TARGET_UNIPROT_ID,
                SAMPLE_DISEASE_NAME,
                SAMPLE_SMILES,
                SAMPLE_PDB_DATA,
            )
            
            # Should log the start message
            mock_logger.info.assert_called()


class TestRunDockingTaskFailure:
    """Tests for docking task failure handling."""

    def test_run_docking_task_job_creation_fails(self, clean_jobs_store):
        """Test task when job creation fails."""
        with patch.object(tasks, 'create_docking_job', side_effect=ValueError("Database error")):
            
            with pytest.raises(ValueError, match="Database error"):
                call_docking_task(
                    SAMPLE_CANDIDATE_ID,
                    SAMPLE_TARGET_UNIPROT_ID,
                    SAMPLE_DISEASE_NAME,
                    SAMPLE_SMILES,
                    SAMPLE_PDB_DATA,
                )

    def test_run_docking_task_execution_fails(self, mock_job, clean_jobs_store):
        """Test task when docking execution fails."""
        mock_job.status = DockingJobStatus.FAILED
        mock_job.error_message = "Vina execution failed"
        mock_job.results = []
        
        with patch.object(tasks, 'create_docking_job', return_value=mock_job), \
             patch.object(tasks, 'run_docking_job', return_value=mock_job):
            
            result = call_docking_task(
                SAMPLE_CANDIDATE_ID,
                SAMPLE_TARGET_UNIPROT_ID,
                SAMPLE_DISEASE_NAME,
                SAMPLE_SMILES,
                SAMPLE_PDB_DATA,
            )
            
            assert result["status"] == "failed"
            assert result["error"] == "Vina execution failed"
            assert result["results_count"] == 0
            assert result["best_affinity"] is None

    def test_run_docking_task_run_raises_exception(self, mock_job, clean_jobs_store):
        """Test task when run_docking_job raises an exception."""
        with patch.object(tasks, 'create_docking_job', return_value=mock_job), \
             patch.object(tasks, 'run_docking_job', side_effect=RuntimeError("Unexpected error")):
            
            with pytest.raises(RuntimeError, match="Unexpected error"):
                call_docking_task(
                    SAMPLE_CANDIDATE_ID,
                    SAMPLE_TARGET_UNIPROT_ID,
                    SAMPLE_DISEASE_NAME,
                    SAMPLE_SMILES,
                    SAMPLE_PDB_DATA,
                )

    def test_run_docking_task_logs_error(self, mock_job, clean_jobs_store):
        """Test that task logs errors."""
        with patch.object(tasks, 'create_docking_job', side_effect=ValueError("Test error")), \
             patch('app.docking.celery_tasks.logger') as mock_logger:
            
            with pytest.raises(ValueError):
                call_docking_task(
                    SAMPLE_CANDIDATE_ID,
                    SAMPLE_TARGET_UNIPROT_ID,
                    SAMPLE_DISEASE_NAME,
                    SAMPLE_SMILES,
                    SAMPLE_PDB_DATA,
                )
            
            mock_logger.error.assert_called()
            error_message = mock_logger.error.call_args[0][0]
            assert "Test error" in error_message


class TestRunDockingTaskRetryConfiguration:
    """Tests for retry configuration on the Celery task."""

    def test_task_has_max_retries(self):
        """Test that task is configured with max_retries=2."""
        assert run_docking_task.max_retries == 2

    def test_task_has_retry_backoff(self):
        """Test that task uses exponential backoff."""
        assert run_docking_task.retry_backoff is True

    def test_task_has_retry_backoff_max(self):
        """Test that task has maximum backoff of 5 minutes."""
        assert run_docking_task.retry_backoff_max == 300

    def test_task_has_default_retry_delay(self):
        """Test that task has default retry delay of 60 seconds."""
        assert run_docking_task.default_retry_delay == 60

    def test_task_has_autoretry_for_exceptions(self):
        """Test that task auto-retries on exceptions."""
        assert run_docking_task.autoretry_for == (Exception,)


class TestRunDockingTaskConcurrency:
    """Tests for concurrency configuration validation."""

    def test_task_has_rate_limit_annotation(self):
        """Test that task has rate limit annotation."""
        from app.celery_app import celery_app
        
        annotations = celery_app.conf.task_annotations
        assert "app.docking.celery_tasks.run_docking_task" in annotations

    def test_task_has_correct_name(self):
        """Test that task has correct name."""
        assert run_docking_task.name == "app.docking.celery_tasks.run_docking_task"


class TestCleanupOldJobsSuccess:
    """Tests for successful cleanup_old_jobs task execution."""

    def test_cleanup_old_jobs_removes_old_completed_jobs(self, clean_jobs_store):
        """Test that old completed jobs are cleaned up."""
        # Create an old completed job
        old_job = DockingJob(
            id="old-job-id",
            candidate_id="CHEMBL1",
            target_uniprot_id="P1",
            disease_name="Disease1",
            status=DockingJobStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        tasks._jobs_store["old-job-id"] = old_job
        tasks._job_data["old-job-id"] = {"smiles": "CCO", "pdb_data": "..."}
        
        with patch.object(tasks, 'cleanup_job_files', return_value=True):
            result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        assert result["cleaned_count"] == 1
        assert result["error_count"] == 0
        assert "old-job-id" not in tasks._jobs_store
        assert "old-job-id" not in tasks._job_data

    def test_cleanup_old_jobs_removes_old_failed_jobs(self, clean_jobs_store):
        """Test that old failed jobs are cleaned up."""
        old_job = DockingJob(
            id="failed-job-id",
            candidate_id="CHEMBL1",
            target_uniprot_id="P1",
            disease_name="Disease1",
            status=DockingJobStatus.FAILED,
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        tasks._jobs_store["failed-job-id"] = old_job
        
        with patch.object(tasks, 'cleanup_job_files', return_value=True):
            result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        assert result["cleaned_count"] == 1
        assert "failed-job-id" not in tasks._jobs_store

    def test_cleanup_old_jobs_removes_old_cancelled_jobs(self, clean_jobs_store):
        """Test that old cancelled jobs are cleaned up."""
        old_job = DockingJob(
            id="cancelled-job-id",
            candidate_id="CHEMBL1",
            target_uniprot_id="P1",
            disease_name="Disease1",
            status=DockingJobStatus.CANCELLED,
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        tasks._jobs_store["cancelled-job-id"] = old_job
        
        with patch.object(tasks, 'cleanup_job_files', return_value=True):
            result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        assert result["cleaned_count"] == 1
        assert "cancelled-job-id" not in tasks._jobs_store

    def test_cleanup_old_jobs_keeps_recent_jobs(self, clean_jobs_store):
        """Test that recent jobs are not cleaned up."""
        recent_job = DockingJob(
            id="recent-job-id",
            candidate_id="CHEMBL1",
            target_uniprot_id="P1",
            disease_name="Disease1",
            status=DockingJobStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=3),
        )
        tasks._jobs_store["recent-job-id"] = recent_job
        
        result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        assert result["cleaned_count"] == 0
        assert "recent-job-id" in tasks._jobs_store

    def test_cleanup_old_jobs_keeps_running_jobs(self, clean_jobs_store):
        """Test that old running jobs are not cleaned up."""
        running_job = DockingJob(
            id="running-job-id",
            candidate_id="CHEMBL1",
            target_uniprot_id="P1",
            disease_name="Disease1",
            status=DockingJobStatus.RUNNING,
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        tasks._jobs_store["running-job-id"] = running_job
        
        result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        assert result["cleaned_count"] == 0
        assert "running-job-id" in tasks._jobs_store

    def test_cleanup_old_jobs_keeps_queued_jobs(self, clean_jobs_store):
        """Test that old queued jobs are not cleaned up."""
        queued_job = DockingJob(
            id="queued-job-id",
            candidate_id="CHEMBL1",
            target_uniprot_id="P1",
            disease_name="Disease1",
            status=DockingJobStatus.QUEUED,
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        tasks._jobs_store["queued-job-id"] = queued_job
        
        result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        assert result["cleaned_count"] == 0
        assert "queued-job-id" in tasks._jobs_store

    def test_cleanup_old_jobs_with_custom_days(self, clean_jobs_store):
        """Test cleanup with custom days_old parameter."""
        old_job = DockingJob(
            id="old-job-id",
            candidate_id="CHEMBL1",
            target_uniprot_id="P1",
            disease_name="Disease1",
            status=DockingJobStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=5),
        )
        tasks._jobs_store["old-job-id"] = old_job
        
        # With 7 days, should not be cleaned
        with patch.object(tasks, 'cleanup_job_files', return_value=True):
            result = cleanup_old_jobs.__wrapped__(days_old=7)
        assert result["cleaned_count"] == 0
        
        # With 3 days, should be cleaned
        with patch.object(tasks, 'cleanup_job_files', return_value=True):
            result = cleanup_old_jobs.__wrapped__(days_old=3)
        assert result["cleaned_count"] == 1

    def test_cleanup_old_jobs_multiple_jobs(self, clean_jobs_store):
        """Test cleanup of multiple jobs."""
        # Create multiple jobs with different states and ages
        old_completed = DockingJob(
            id="old-completed",
            candidate_id="CHEMBL1",
            target_uniprot_id="P1",
            disease_name="Disease1",
            status=DockingJobStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        old_failed = DockingJob(
            id="old-failed",
            candidate_id="CHEMBL2",
            target_uniprot_id="P2",
            disease_name="Disease2",
            status=DockingJobStatus.FAILED,
            created_at=datetime.utcnow() - timedelta(days=15),
        )
        recent_completed = DockingJob(
            id="recent-completed",
            candidate_id="CHEMBL3",
            target_uniprot_id="P3",
            disease_name="Disease3",
            status=DockingJobStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=3),
        )
        old_running = DockingJob(
            id="old-running",
            candidate_id="CHEMBL4",
            target_uniprot_id="P4",
            disease_name="Disease4",
            status=DockingJobStatus.RUNNING,
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        
        tasks._jobs_store["old-completed"] = old_completed
        tasks._jobs_store["old-failed"] = old_failed
        tasks._jobs_store["recent-completed"] = recent_completed
        tasks._jobs_store["old-running"] = old_running
        
        with patch.object(tasks, 'cleanup_job_files', return_value=True):
            result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        assert result["cleaned_count"] == 2  # old-completed and old-failed
        assert "old-completed" not in tasks._jobs_store
        assert "old-failed" not in tasks._jobs_store
        assert "recent-completed" in tasks._jobs_store
        assert "old-running" in tasks._jobs_store


class TestCleanupOldJobsError:
    """Tests for error handling in cleanup_old_jobs task."""

    def test_cleanup_old_jobs_handles_cleanup_errors(self, clean_jobs_store):
        """Test that errors during individual job cleanup are handled."""
        old_job = DockingJob(
            id="old-job-id",
            candidate_id="CHEMBL1",
            target_uniprot_id="P1",
            disease_name="Disease1",
            status=DockingJobStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        tasks._jobs_store["old-job-id"] = old_job
        
        with patch.object(tasks, 'cleanup_job_files', side_effect=Exception("Cleanup error")):
            result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        # Job should still be in store because cleanup failed
        assert result["error_count"] == 1
        assert result["cleaned_count"] == 0

    def test_cleanup_old_jobs_continues_after_error(self, clean_jobs_store):
        """Test that cleanup continues processing after an error."""
        # Create two old jobs
        job1 = DockingJob(
            id="job1",
            candidate_id="CHEMBL1",
            target_uniprot_id="P1",
            disease_name="Disease1",
            status=DockingJobStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        job2 = DockingJob(
            id="job2",
            candidate_id="CHEMBL2",
            target_uniprot_id="P2",
            disease_name="Disease2",
            status=DockingJobStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        tasks._jobs_store["job1"] = job1
        tasks._jobs_store["job2"] = job2
        
        call_count = [0]
        
        def mock_cleanup(job_id):
            call_count[0] += 1
            if job_id == "job1":
                raise Exception("Cleanup error for job1")
            return True
        
        with patch.object(tasks, 'cleanup_job_files', side_effect=mock_cleanup):
            result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        # Both jobs should have been attempted
        assert call_count[0] == 2
        # One should fail, one should succeed
        assert result["cleaned_count"] == 1
        assert result["error_count"] == 1

    def test_cleanup_old_jobs_empty_store(self, clean_jobs_store):
        """Test cleanup when there are no jobs."""
        result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        assert result["cleaned_count"] == 0
        assert result["error_count"] == 0

    def test_cleanup_old_jobs_returns_cutoff_date(self, clean_jobs_store):
        """Test that cleanup returns cutoff date in ISO format."""
        result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        assert "cutoff_date" in result
        # Should be a valid ISO date
        cutoff = datetime.fromisoformat(result["cutoff_date"])
        expected_cutoff = datetime.utcnow() - timedelta(days=7)
        # Within a few seconds
        assert abs((cutoff - expected_cutoff).total_seconds()) < 5


class TestCleanupOldJobsConfiguration:
    """Tests for cleanup_old_jobs task configuration."""

    def test_task_has_correct_name(self):
        """Test that task has correct name."""
        assert cleanup_old_jobs.name == "app.docking.celery_tasks.cleanup_old_jobs"

    def test_task_default_days_old(self, clean_jobs_store):
        """Test that default days_old is 7."""
        # The default is specified in the function signature
        import inspect
        sig = inspect.signature(cleanup_old_jobs.__wrapped__)
        days_old_param = sig.parameters.get('days_old')
        assert days_old_param is not None
        assert days_old_param.default == 7


class TestGetQueueStatus:
    """Tests for get_queue_status task."""

    def test_get_queue_status_empty(self, clean_jobs_store):
        """Test queue status with no jobs."""
        result = get_queue_status.__wrapped__()
        
        assert result["total_jobs"] == 0
        assert result["status_counts"]["queued"] == 0
        assert result["status_counts"]["running"] == 0
        assert result["status_counts"]["completed"] == 0
        assert result["status_counts"]["failed"] == 0
        assert result["status_counts"]["cancelled"] == 0

    def test_get_queue_status_with_jobs(self, clean_jobs_store):
        """Test queue status with various job states."""
        # Create jobs with different statuses
        jobs = [
            DockingJob(
                id="queued1",
                candidate_id="C1",
                target_uniprot_id="P1",
                disease_name="D1",
                status=DockingJobStatus.QUEUED,
            ),
            DockingJob(
                id="queued2",
                candidate_id="C2",
                target_uniprot_id="P2",
                disease_name="D2",
                status=DockingJobStatus.QUEUED,
            ),
            DockingJob(
                id="running1",
                candidate_id="C3",
                target_uniprot_id="P3",
                disease_name="D3",
                status=DockingJobStatus.RUNNING,
            ),
            DockingJob(
                id="completed1",
                candidate_id="C4",
                target_uniprot_id="P4",
                disease_name="D4",
                status=DockingJobStatus.COMPLETED,
            ),
            DockingJob(
                id="completed2",
                candidate_id="C5",
                target_uniprot_id="P5",
                disease_name="D5",
                status=DockingJobStatus.COMPLETED,
            ),
            DockingJob(
                id="completed3",
                candidate_id="C6",
                target_uniprot_id="P6",
                disease_name="D6",
                status=DockingJobStatus.COMPLETED,
            ),
            DockingJob(
                id="failed1",
                candidate_id="C7",
                target_uniprot_id="P7",
                disease_name="D7",
                status=DockingJobStatus.FAILED,
            ),
            DockingJob(
                id="cancelled1",
                candidate_id="C8",
                target_uniprot_id="P8",
                disease_name="D8",
                status=DockingJobStatus.CANCELLED,
            ),
        ]
        
        for job in jobs:
            tasks._jobs_store[job.id] = job
        
        result = get_queue_status.__wrapped__()
        
        assert result["total_jobs"] == 8
        assert result["status_counts"]["queued"] == 2
        assert result["status_counts"]["running"] == 1
        assert result["status_counts"]["completed"] == 3
        assert result["status_counts"]["failed"] == 1
        assert result["status_counts"]["cancelled"] == 1

    def test_get_queue_status_includes_timestamp(self, clean_jobs_store):
        """Test that queue status includes timestamp."""
        result = get_queue_status.__wrapped__()
        
        assert "timestamp" in result
        # Should be a valid ISO timestamp
        timestamp = datetime.fromisoformat(result["timestamp"])
        # Should be recent
        assert abs((datetime.utcnow() - timestamp).total_seconds()) < 5


class TestGetQueueStatusConfiguration:
    """Tests for get_queue_status task configuration."""

    def test_task_has_correct_name(self):
        """Test that task has correct name."""
        assert get_queue_status.name == "app.docking.celery_tasks.get_queue_status"


class TestTaskIntegration:
    """Integration tests for task interactions."""

    def test_run_task_then_cleanup(self, mock_job, clean_jobs_store):
        """Test running a task and then cleaning it up."""
        # First run a docking task
        mock_job.created_at = datetime.utcnow() - timedelta(days=10)
        
        with patch.object(tasks, 'create_docking_job', return_value=mock_job), \
             patch.object(tasks, 'run_docking_job', return_value=mock_job):
            
            result = call_docking_task(
                SAMPLE_CANDIDATE_ID,
                SAMPLE_TARGET_UNIPROT_ID,
                SAMPLE_DISEASE_NAME,
                SAMPLE_SMILES,
                SAMPLE_PDB_DATA,
            )
            
            # Manually add to store as mock doesn't do this
            tasks._jobs_store[mock_job.id] = mock_job
        
        # Then verify queue status shows the job
        status = get_queue_status.__wrapped__()
        assert status["total_jobs"] == 1
        assert status["status_counts"]["completed"] == 1
        
        # Then cleanup
        with patch.object(tasks, 'cleanup_job_files', return_value=True):
            cleanup_result = cleanup_old_jobs.__wrapped__(days_old=7)
        
        assert cleanup_result["cleaned_count"] == 1
        
        # Verify job is removed
        final_status = get_queue_status.__wrapped__()
        assert final_status["total_jobs"] == 0

    def test_parameter_conversion_to_models(self, mock_job, clean_jobs_store):
        """Test that dict parameters are correctly converted to Pydantic models."""
        captured_args = {}
        
        def capture_create_job(**kwargs):
            captured_args.update(kwargs)
            return mock_job
        
        with patch.object(tasks, 'create_docking_job', side_effect=capture_create_job), \
             patch.object(tasks, 'run_docking_job', return_value=mock_job):
            
            call_docking_task(
                SAMPLE_CANDIDATE_ID,
                SAMPLE_TARGET_UNIPROT_ID,
                SAMPLE_DISEASE_NAME,
                SAMPLE_SMILES,
                SAMPLE_PDB_DATA,
                grid_params=SAMPLE_GRID_PARAMS,
                docking_params=SAMPLE_DOCKING_PARAMS,
            )
        
        # Check GridBoxParams
        grid = captured_args["grid_params"]
        assert isinstance(grid, GridBoxParams)
        assert grid.center_x == 10.0
        assert grid.center_y == 20.0
        assert grid.center_z == 30.0
        assert grid.size_x == 25.0
        assert grid.size_y == 25.0
        assert grid.size_z == 25.0
        
        # Check DockingParams
        params = captured_args["docking_params"]
        assert isinstance(params, DockingParams)
        assert params.exhaustiveness == 8
        assert params.num_modes == 9
        assert params.energy_range == 3.0

    def test_none_params_handled(self, mock_job, clean_jobs_store):
        """Test that None parameters are passed correctly."""
        captured_args = {}
        
        def capture_create_job(**kwargs):
            captured_args.update(kwargs)
            return mock_job
        
        with patch.object(tasks, 'create_docking_job', side_effect=capture_create_job), \
             patch.object(tasks, 'run_docking_job', return_value=mock_job):
            
            call_docking_task(
                SAMPLE_CANDIDATE_ID,
                SAMPLE_TARGET_UNIPROT_ID,
                SAMPLE_DISEASE_NAME,
                SAMPLE_SMILES,
                SAMPLE_PDB_DATA,
            )
        
        assert captured_args["grid_params"] is None
        assert captured_args["docking_params"] is None


class TestCeleryAppConfiguration:
    """Tests for Celery app configuration related to docking tasks."""

    def test_celery_includes_docking_tasks(self):
        """Test that Celery app includes docking tasks module."""
        from app.celery_app import celery_app
        
        assert "app.docking.celery_tasks" in celery_app.conf.include

    def test_docking_task_route(self):
        """Test that docking task is routed to correct queue."""
        from app.celery_app import celery_app
        
        routes = celery_app.conf.task_routes
        assert "app.docking.celery_tasks.run_docking_task" in routes
        assert routes["app.docking.celery_tasks.run_docking_task"]["queue"] == "docking"

    def test_cleanup_task_route(self):
        """Test that cleanup task is routed to maintenance queue."""
        from app.celery_app import celery_app
        
        routes = celery_app.conf.task_routes
        assert "app.docking.celery_tasks.cleanup_old_jobs" in routes
        assert routes["app.docking.celery_tasks.cleanup_old_jobs"]["queue"] == "maintenance"

    def test_beat_schedule_includes_cleanup(self):
        """Test that Celery beat schedule includes cleanup task."""
        from app.celery_app import celery_app
        
        schedule = celery_app.conf.beat_schedule
        assert "cleanup-old-docking-jobs" in schedule
        assert schedule["cleanup-old-docking-jobs"]["task"] == "app.docking.celery_tasks.cleanup_old_jobs"
        assert schedule["cleanup-old-docking-jobs"]["schedule"] == 86400  # Daily

    def test_result_expiry(self):
        """Test that results are configured to expire."""
        from app.celery_app import celery_app
        
        assert celery_app.conf.result_expires == 86400 * 7  # 7 days


class TestErrorHandlingScenarios:
    """Tests for specific error handling scenarios."""

    def test_job_with_no_results(self, clean_jobs_store):
        """Test task result when job completes with no results."""
        mock_job = DockingJob(
            id="test-job-id",
            candidate_id=SAMPLE_CANDIDATE_ID,
            target_uniprot_id=SAMPLE_TARGET_UNIPROT_ID,
            disease_name=SAMPLE_DISEASE_NAME,
            status=DockingJobStatus.COMPLETED,
            results=[],  # Empty results
        )
        
        with patch.object(tasks, 'create_docking_job', return_value=mock_job), \
             patch.object(tasks, 'run_docking_job', return_value=mock_job):
            
            result = call_docking_task(
                SAMPLE_CANDIDATE_ID,
                SAMPLE_TARGET_UNIPROT_ID,
                SAMPLE_DISEASE_NAME,
                SAMPLE_SMILES,
                SAMPLE_PDB_DATA,
            )
            
            assert result["results_count"] == 0
            assert result["best_affinity"] is None

    def test_job_with_none_results(self, clean_jobs_store):
        """Test task result when job has empty results (failed)."""
        mock_job = DockingJob(
            id="test-job-id",
            candidate_id=SAMPLE_CANDIDATE_ID,
            target_uniprot_id=SAMPLE_TARGET_UNIPROT_ID,
            disease_name=SAMPLE_DISEASE_NAME,
            status=DockingJobStatus.FAILED,
            results=[],  # Empty results
            error_message="Vina failed",
        )
        
        with patch.object(tasks, 'create_docking_job', return_value=mock_job), \
             patch.object(tasks, 'run_docking_job', return_value=mock_job):
            
            result = call_docking_task(
                SAMPLE_CANDIDATE_ID,
                SAMPLE_TARGET_UNIPROT_ID,
                SAMPLE_DISEASE_NAME,
                SAMPLE_SMILES,
                SAMPLE_PDB_DATA,
            )
            
            assert result["results_count"] == 0
            assert result["best_affinity"] is None
            assert result["error"] == "Vina failed"
