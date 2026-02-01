"""Unit tests for docking database models.

Tests for DockingJobDB and DockingResultDB SQLAlchemy models.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import asyncio

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from app.database import Base
from app.docking.db_models import DockingJobDB, DockingResultDB
from app.docking.models import DockingJobStatus, GridBoxParams, DockingParams


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def engine():
    """Create a test engine with in-memory SQLite."""
    from sqlalchemy import event as sa_event
    
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    
    # Enable foreign key enforcement in SQLite
    @sa_event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine):
    """Create a test session."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestDockingJobDBModel:
    """Tests for DockingJobDB model."""

    def test_create_docking_job_minimal(self, session: Session):
        """Test creating a docking job with minimal fields."""
        job = DockingJobDB(
            candidate_id="CAND_001",
            target_uniprot_id="P12345",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        assert job.id is not None
        assert job.candidate_id == "CAND_001"
        assert job.target_uniprot_id == "P12345"
        assert job.status == DockingJobStatus.QUEUED.value
        assert job.created_at is not None

    def test_create_docking_job_full(self, session: Session):
        """Test creating a docking job with all fields."""
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

        job = DockingJobDB(
            candidate_id="CAND_002",
            target_uniprot_id="Q67890",
            user_id="user_123",
            status=DockingJobStatus.RUNNING.value,
            grid_params_json=json.dumps(grid_params.model_dump()),
            docking_params_json=json.dumps(docking_params.model_dump()),
            ligand_pdbqt_path="/path/to/ligand.pdbqt",
            protein_pdbqt_path="/path/to/receptor.pdbqt",
            output_pdbqt_path="/path/to/output",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        assert job.id is not None
        assert job.user_id == "user_123"
        assert job.status == DockingJobStatus.RUNNING.value
        assert job.ligand_pdbqt_path == "/path/to/ligand.pdbqt"
        assert job.protein_pdbqt_path == "/path/to/receptor.pdbqt"
        assert job.output_pdbqt_path == "/path/to/output"

    def test_docking_job_status_values(self, session: Session):
        """Test all possible status values."""
        statuses = [
            DockingJobStatus.QUEUED,
            DockingJobStatus.RUNNING,
            DockingJobStatus.COMPLETED,
            DockingJobStatus.FAILED,
        ]

        for status in statuses:
            job = DockingJobDB(
                candidate_id=f"CAND_{status.value}",
                target_uniprot_id="P12345",
                status=status.value,
            )
            session.add(job)

        session.commit()

        # Verify all jobs were created
        jobs = session.execute(select(DockingJobDB)).scalars().all()
        assert len(jobs) == len(statuses)

    def test_docking_job_timestamps_auto_update(self, session: Session):
        """Test that timestamps are automatically set."""
        job = DockingJobDB(
            candidate_id="CAND_TS",
            target_uniprot_id="P12345",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        created = job.created_at
        assert created is not None
        
        # started_at and completed_at should be None initially
        assert job.started_at is None
        assert job.completed_at is None

    def test_grid_params_property(self, session: Session):
        """Test grid_params property getter and setter."""
        grid_params = GridBoxParams(
            center_x=15.5,
            center_y=25.5,
            center_z=35.5,
            size_x=30.0,
            size_y=30.0,
            size_z=30.0,
        )

        job = DockingJobDB(
            candidate_id="CAND_GRID",
            target_uniprot_id="P12345",
        )
        job.grid_params = grid_params
        session.add(job)
        session.commit()
        session.refresh(job)

        # Test getter
        retrieved_params = job.grid_params
        assert retrieved_params is not None
        assert retrieved_params.center_x == 15.5
        assert retrieved_params.center_y == 25.5
        assert retrieved_params.center_z == 35.5
        assert retrieved_params.size_x == 30.0

    def test_docking_params_property(self, session: Session):
        """Test docking_params property getter and setter."""
        docking_params = DockingParams(
            exhaustiveness=32,
            num_modes=20,
            energy_range=5.0,
        )

        job = DockingJobDB(
            candidate_id="CAND_DOCK",
            target_uniprot_id="P12345",
        )
        job.docking_params = docking_params
        session.add(job)
        session.commit()
        session.refresh(job)

        # Test getter
        retrieved_params = job.docking_params
        assert retrieved_params is not None
        assert retrieved_params.exhaustiveness == 32
        assert retrieved_params.num_modes == 20
        assert retrieved_params.energy_range == 5.0

    def test_docking_job_with_error(self, session: Session):
        """Test docking job with error message."""
        job = DockingJobDB(
            candidate_id="CAND_ERR",
            target_uniprot_id="P12345",
            status=DockingJobStatus.FAILED.value,
            error_message="Docking failed: receptor not found",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        assert job.status == DockingJobStatus.FAILED.value
        assert job.error_message == "Docking failed: receptor not found"

    def test_docking_job_best_affinity(self, session: Session):
        """Test best_affinity field."""
        job = DockingJobDB(
            candidate_id="CAND_AFF",
            target_uniprot_id="P12345",
            status=DockingJobStatus.COMPLETED.value,
            best_affinity=-8.5,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        assert job.best_affinity == -8.5

    def test_docking_job_repr(self, session: Session):
        """Test string representation of docking job."""
        job = DockingJobDB(
            candidate_id="CAND_REPR",
            target_uniprot_id="P12345",
            status=DockingJobStatus.QUEUED.value,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        repr_str = repr(job)
        assert "DockingJobDB" in repr_str
        assert str(job.id) in repr_str
        assert "queued" in repr_str


class TestDockingResultDBModel:
    """Tests for DockingResultDB model."""

    def test_create_docking_result(self, session: Session):
        """Test creating a docking result."""
        # First create a job
        job = DockingJobDB(
            candidate_id="CAND_RES",
            target_uniprot_id="P12345",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        # Create a result
        result = DockingResultDB(
            job_id=job.id,
            pose_number=1,
            binding_affinity=-7.5,
            rmsd_lb=0.0,
            rmsd_ub=0.0,
        )
        session.add(result)
        session.commit()
        session.refresh(result)

        assert result.id is not None
        assert result.job_id == job.id
        assert result.pose_number == 1
        assert result.binding_affinity == -7.5
        assert result.rmsd_lb == 0.0
        assert result.rmsd_ub == 0.0
        assert result.created_at is not None

    def test_docking_result_with_pdbqt_data(self, session: Session):
        """Test docking result with PDBQT data."""
        job = DockingJobDB(
            candidate_id="CAND_PDBQT",
            target_uniprot_id="P12345",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        pdbqt_content = """MODEL 1
REMARK VINA RESULT:    -7.5      0.000      0.000
ATOM      1  C   LIG A   1       0.000   0.000   0.000  1.00  0.00    +0.000 C
ENDMDL"""

        result = DockingResultDB(
            job_id=job.id,
            pose_number=1,
            binding_affinity=-7.5,
            rmsd_lb=0.0,
            rmsd_ub=0.0,
            pdbqt_file_path="/path/to/output.pdbqt",
            pdbqt_data=pdbqt_content,
        )
        session.add(result)
        session.commit()
        session.refresh(result)

        assert result.pdbqt_file_path == "/path/to/output.pdbqt"
        assert "MODEL 1" in result.pdbqt_data
        assert "-7.5" in result.pdbqt_data

    def test_docking_result_repr(self, session: Session):
        """Test string representation of docking result."""
        job = DockingJobDB(
            candidate_id="CAND_REPR2",
            target_uniprot_id="P12345",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        result = DockingResultDB(
            job_id=job.id,
            pose_number=3,
            binding_affinity=-6.8,
            rmsd_lb=1.5,
            rmsd_ub=2.3,
        )
        session.add(result)
        session.commit()
        session.refresh(result)

        repr_str = repr(result)
        assert "DockingResultDB" in repr_str
        assert "pose=3" in repr_str
        assert "-6.8" in repr_str


class TestDockingJobResultRelationship:
    """Tests for the relationship between DockingJobDB and DockingResultDB."""

    def test_job_has_many_results(self, session: Session):
        """Test that a job can have multiple results."""
        job = DockingJobDB(
            candidate_id="CAND_MULTI",
            target_uniprot_id="P12345",
            status=DockingJobStatus.COMPLETED.value,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        # Add multiple results
        for i in range(5):
            result = DockingResultDB(
                job_id=job.id,
                pose_number=i + 1,
                binding_affinity=-7.0 + (i * 0.5),  # -7.0, -6.5, -6.0, etc.
                rmsd_lb=float(i),
                rmsd_ub=float(i) + 0.5,
            )
            session.add(result)

        session.commit()
        session.refresh(job)

        assert len(job.results) == 5
        assert job.results[0].binding_affinity == -7.0
        assert job.results[4].binding_affinity == -5.0

    def test_cascade_delete(self, session: Session):
        """Test that deleting a job cascades to results."""
        job = DockingJobDB(
            candidate_id="CAND_CASCADE",
            target_uniprot_id="P12345",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

        # Add results
        for i in range(3):
            result = DockingResultDB(
                job_id=job.id,
                pose_number=i + 1,
                binding_affinity=-7.0,
                rmsd_lb=0.0,
                rmsd_ub=0.0,
            )
            session.add(result)

        session.commit()

        # Verify results exist
        results = session.execute(
            select(DockingResultDB).where(DockingResultDB.job_id == job_id)
        ).scalars().all()
        assert len(results) == 3

        # Delete job
        session.delete(job)
        session.commit()

        # Verify results are also deleted
        results = session.execute(
            select(DockingResultDB).where(DockingResultDB.job_id == job_id)
        ).scalars().all()
        assert len(results) == 0

    def test_result_references_job(self, session: Session):
        """Test that a result references its parent job."""
        job = DockingJobDB(
            candidate_id="CAND_REF",
            target_uniprot_id="P12345",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        result = DockingResultDB(
            job_id=job.id,
            pose_number=1,
            binding_affinity=-8.0,
            rmsd_lb=0.0,
            rmsd_ub=0.0,
        )
        session.add(result)
        session.commit()
        session.refresh(result)

        # Access job through result relationship
        assert result.job is not None
        assert result.job.id == job.id
        assert result.job.candidate_id == "CAND_REF"


class TestDatabaseIndexes:
    """Tests to verify database indexes work correctly."""

    def test_query_by_status(self, session: Session):
        """Test querying jobs by status (uses index)."""
        # Create jobs with different statuses
        for i, status in enumerate([
            DockingJobStatus.QUEUED,
            DockingJobStatus.RUNNING,
            DockingJobStatus.COMPLETED,
            DockingJobStatus.COMPLETED,
        ]):
            job = DockingJobDB(
                candidate_id=f"CAND_IDX_{i}",
                target_uniprot_id="P12345",
                status=status.value,
            )
            session.add(job)

        session.commit()

        # Query by status
        completed_jobs = session.execute(
            select(DockingJobDB).where(
                DockingJobDB.status == DockingJobStatus.COMPLETED.value
            )
        ).scalars().all()

        assert len(completed_jobs) == 2

    def test_query_by_user_and_status(self, session: Session):
        """Test querying jobs by user and status (uses composite index)."""
        # Create jobs for different users
        for user_id in ["user_a", "user_b"]:
            for status in [DockingJobStatus.QUEUED, DockingJobStatus.COMPLETED]:
                job = DockingJobDB(
                    candidate_id=f"CAND_{user_id}_{status.value}",
                    target_uniprot_id="P12345",
                    user_id=user_id,
                    status=status.value,
                )
                session.add(job)

        session.commit()

        # Query by user and status
        user_a_completed = session.execute(
            select(DockingJobDB).where(
                DockingJobDB.user_id == "user_a",
                DockingJobDB.status == DockingJobStatus.COMPLETED.value,
            )
        ).scalars().all()

        assert len(user_a_completed) == 1
        assert user_a_completed[0].user_id == "user_a"

    def test_query_by_candidate_and_target(self, session: Session):
        """Test querying by candidate and target (uses composite index)."""
        job = DockingJobDB(
            candidate_id="CAND_COMBO",
            target_uniprot_id="P99999",
        )
        session.add(job)
        session.commit()

        # Query by combo
        found = session.execute(
            select(DockingJobDB).where(
                DockingJobDB.candidate_id == "CAND_COMBO",
                DockingJobDB.target_uniprot_id == "P99999",
            )
        ).scalars().first()

        assert found is not None
        assert found.candidate_id == "CAND_COMBO"

    def test_query_results_by_job_and_pose(self, session: Session):
        """Test querying results by job and pose number."""
        job = DockingJobDB(
            candidate_id="CAND_POSE",
            target_uniprot_id="P12345",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        # Add multiple poses
        for pose in range(1, 6):
            result = DockingResultDB(
                job_id=job.id,
                pose_number=pose,
                binding_affinity=-7.0 + pose * 0.1,
                rmsd_lb=0.0,
                rmsd_ub=0.0,
            )
            session.add(result)

        session.commit()

        # Query specific pose
        pose_3 = session.execute(
            select(DockingResultDB).where(
                DockingResultDB.job_id == job.id,
                DockingResultDB.pose_number == 3,
            )
        ).scalars().first()

        assert pose_3 is not None
        assert pose_3.pose_number == 3

    def test_query_results_by_affinity(self, session: Session):
        """Test querying results by binding affinity (uses index)."""
        job = DockingJobDB(
            candidate_id="CAND_AFF_IDX",
            target_uniprot_id="P12345",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        # Add results with different affinities
        affinities = [-9.5, -8.0, -7.5, -6.0, -5.0]
        for i, aff in enumerate(affinities):
            result = DockingResultDB(
                job_id=job.id,
                pose_number=i + 1,
                binding_affinity=aff,
                rmsd_lb=0.0,
                rmsd_ub=0.0,
            )
            session.add(result)

        session.commit()

        # Query best results (affinity < -7.0)
        good_results = session.execute(
            select(DockingResultDB)
            .where(DockingResultDB.binding_affinity < -7.0)
            .order_by(DockingResultDB.binding_affinity)
        ).scalars().all()

        assert len(good_results) == 3
        assert good_results[0].binding_affinity == -9.5


class TestModelValidation:
    """Tests for model field validation and constraints."""

    def test_required_fields(self, session: Session):
        """Test that required fields are enforced."""
        # Missing candidate_id should fail
        job = DockingJobDB(target_uniprot_id="P12345")

        with pytest.raises(IntegrityError):
            session.add(job)
            session.commit()

    def test_result_requires_job_id(self, session: Session):
        """Test that result requires valid job_id - FK constraint enforced."""
        result = DockingResultDB(
            job_id="nonexistent-job-id",  # Non-existent job
            pose_number=1,
            binding_affinity=-7.0,
            rmsd_lb=0.0,
            rmsd_ub=0.0,
        )

        with pytest.raises(IntegrityError):
            session.add(result)
            session.commit()

    def test_null_optional_fields(self, session: Session):
        """Test that optional fields can be null."""
        job = DockingJobDB(
            candidate_id="CAND_OPT",
            target_uniprot_id="P12345",
            # All optional fields left as None
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        assert job.user_id is None
        assert job.grid_params_json is None
        assert job.docking_params_json is None
        assert job.error_message is None
        assert job.best_affinity is None
        assert job.ligand_pdbqt_path is None
        assert job.protein_pdbqt_path is None
        assert job.output_pdbqt_path is None


class TestJSONSerialization:
    """Tests for JSON serialization of parameters."""

    def test_grid_params_json_roundtrip(self, session: Session):
        """Test GridBoxParams JSON roundtrip."""
        original = GridBoxParams(
            center_x=1.1,
            center_y=2.2,
            center_z=3.3,
            size_x=10.0,
            size_y=20.0,
            size_z=30.0,
        )

        job = DockingJobDB(
            candidate_id="CAND_JSON1",
            target_uniprot_id="P12345",
        )
        job.grid_params = original
        session.add(job)
        session.commit()

        # Fetch fresh from database
        fetched_job = session.execute(
            select(DockingJobDB).where(DockingJobDB.candidate_id == "CAND_JSON1")
        ).scalars().first()

        restored = fetched_job.grid_params
        assert restored.center_x == original.center_x
        assert restored.center_y == original.center_y
        assert restored.center_z == original.center_z
        assert restored.size_x == original.size_x
        assert restored.size_y == original.size_y
        assert restored.size_z == original.size_z

    def test_docking_params_json_roundtrip(self, session: Session):
        """Test DockingParams JSON roundtrip."""
        original = DockingParams(
            exhaustiveness=32,
            num_modes=15,
            energy_range=3.5,
        )

        job = DockingJobDB(
            candidate_id="CAND_JSON2",
            target_uniprot_id="P12345",
        )
        job.docking_params = original
        session.add(job)
        session.commit()

        # Fetch fresh from database
        fetched_job = session.execute(
            select(DockingJobDB).where(DockingJobDB.candidate_id == "CAND_JSON2")
        ).scalars().first()

        restored = fetched_job.docking_params
        assert restored.exhaustiveness == original.exhaustiveness
        assert restored.num_modes == original.num_modes
        assert restored.energy_range == original.energy_range

    def test_null_json_params_returns_none(self, session: Session):
        """Test that null JSON params return None."""
        job = DockingJobDB(
            candidate_id="CAND_NULL",
            target_uniprot_id="P12345",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        assert job.grid_params is None
        assert job.docking_params is None
