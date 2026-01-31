# Implementation Plan: Docking Integration (Server-Side Execution)

## Overview

This implementation plan adds molecular docking capabilities to the drug discovery platform. The system will run AutoDock Vina on the backend server, allowing users to validate binding predictions without installing software. Results are displayed in an interactive 3D viewer integrated with the existing UI.

**Key Integration Points:**
- Extends existing candidate results page with "Run Docking" button
- Reuses existing 3D visualization components (ProteinViewer3D, MoleculeViewer3D)
- Integrates docking scores with existing composite scoring system
- Uses existing Redis cache infrastructure for job queue

## Tasks

- [x] 1. Set up infrastructure and dependencies
  - Install AutoDock Vina on backend server
  - Install Celery and Redis for job queue
  - Install Open Babel and Meeko for PDBQT conversion
  - Add new backend modules: `app/docking/`, `app/docking/tasks.py`, `app/docking/executor.py`
  - Configure Celery workers and Redis connection
  - Create database tables for docking jobs and results
  - _Requirements: 6.1, 11.1, 11.2_

- [x] 2. Implement PDBQT Converter for Proteins
  - [x] 2.1 Create PDBQTConverter class with protein conversion method
    - Parse PDB data from existing AlphaFold structures
    - Add hydrogen atoms using Open Babel
    - Assign Gasteiger partial charges
    - Merge non-polar hydrogens
    - Detect and preserve metal ions and cofactors
    - Write PDBQT format output
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 2.2 Write property test for protein PDBQT conversion
    - **Property 5: PDB to PDBQT Conversion**
    - **Validates: Requirements 2.1, 2.7**

  - [x] 2.3 Write unit tests for protein conversion
    - Test with sample protein structures from existing AlphaFold data
    - Test error handling for invalid PDB data
    - Test metal ion detection and preservation
    - _Requirements: 2.1, 2.5, 2.6_

- [x] 3. Implement PDBQT Converter for Ligands
  - [x] 3.1 Add ligand conversion method to PDBQTConverter
    - Parse SMILES from existing Molecule data (reuse RDKit from current app)
    - Generate 3D conformer using ETKDG algorithm
    - Optimize geometry with MMFF94 force field
    - Convert to PDB format
    - Use Meeko to convert PDB to PDBQT
    - Detect and mark rotatable bonds
    - Set root atom for torsion tree
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 3.2 Write property test for SMILES to 3D generation
    - **Property 9: SMILES to 3D Structure Generation**
    - **Validates: Requirements 3.1**

  - [x] 3.3 Write unit tests for ligand conversion
    - Test with molecules from existing ChEMBL data
    - Test with complex molecules (multiple rings, stereocenters)
    - Test error handling for invalid SMILES
    - _Requirements: 3.1, 3.8_

- [x] 4. Checkpoint - Ensure PDBQT conversion tests pass
  - All 54 PDBQT tests passing (26 protein + 28 ligand)

- [x] 5. Implement Grid Box Calculator
  - [x] 5.1 Create GridBoxCalculator class
    - Parse PDB data to extract atom coordinates
    - Calculate geometric center (mean of all coordinates)
    - Set default grid box dimensions (25 Å × 25 Å × 25 Å)
    - Format coordinates with 2 decimal places
    - Validate dimensions are within 10-50 Å range
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6_

  - [x] 5.2 Write property test for geometric center calculation
    - **Property 14: Geometric Center Calculation**
    - **Validates: Requirements 4.1, 4.2**

  - [x] 5.3 Write unit tests for grid box calculator
    - 30 tests covering initialization, PDB calculation, binding site, coordinates, errors, property-based tests
    - Test edge cases (very small/large proteins)
    - Test error handling and fallback to defaults
    - _Requirements: 4.1, 4.7_

- [x] 6. Implement Configuration File Generator
- [x] 6.1 Create ConfigFileGenerator class
    - Generate AutoDock Vina configuration file format
    - Include all required fields (receptor, ligand, center, size, parameters)
    - Set default docking parameters (exhaustiveness=8, num_modes=9, energy_range=3)
    - Validate configuration completeness
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

  - [x] 6.2 Write property test for configuration completeness
    - **Property 17: Configuration File Completeness**
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.9_

  - [x] 6.3 Write unit tests for configuration generator
    - 28 tests covering init, generate_config, default/custom params, error handling, validation, format, completeness
    - Test with custom parameters
    - Test file path formatting
    - _Requirements: 5.1, 5.10_

- [x] 7. Checkpoint - Ensure utility components tests pass
  - All 112 tests passing (54 PDBQT + 30 grid calculator + 28 config generator)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement AutoDock Vina Executor
  - [x] 8.1 Create VinaExecutor class
    - Execute AutoDock Vina subprocess with configuration file
    - Capture stdout and stderr output
    - Parse Vina output to extract binding affinity scores
    - Parse output PDBQT file to extract binding poses
    - Handle execution timeouts (30 minutes max)
    - Handle execution errors and return detailed error messages
    - _Requirements: 6.1, 6.5, 6.6, 6.7, 12.4, 12.5_

  - [x] 8.2 Write unit tests for Vina executor
    - 32 tests covering init, path discovery, sync/async execution, timeout, errors, output parsing
    - Test timeout handling
    - Test error handling (invalid files, Vina not installed)
    - Test output parsing
    - _Requirements: 6.1, 6.9, 12.4_

- [x] 9. Implement Docking Results Parser
  - [x] 9.1 Create DockingResultsParser class
    - Parse AutoDock Vina output PDBQT file
    - Extract binding affinity scores for all poses
    - Extract RMSD values between poses
    - Extract atomic coordinates for each pose
    - Identify best binding pose (most negative affinity)
    - Generate summary statistics
    - _Requirements: 6.7, 9.1, 9.2, 9.3, 9.4_

  - [x] 9.2 Write unit tests for results parser
    - 41 tests covering stdout parsing, PDBQT parsing, best pose, summary stats, combined parsing, edge cases
    - Test with multiple poses
    - Test edge cases (single pose, failed docking)
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 10. Implement Celery Task for Docking Jobs
  - [x] 10.1 Create Celery task for async docking execution
    - Define Celery task `run_docking_job(candidate_id, params)`
    - Retrieve candidate data from existing database
    - Convert protein and ligand to PDBQT (use PDBQTConverter)
    - Calculate grid box (use GridBoxCalculator)
    - Generate config file (use ConfigFileGenerator)
    - Execute AutoDock Vina (use VinaExecutor)
    - Parse results (use DockingResultsParser)
    - Store results in database
    - Update job status throughout execution
    - Clean up temporary files on completion
    - _Requirements: 6.1, 6.2, 6.3, 6.8, 11.1, 11.2_

  - [x] 10.2 Implement job retry logic
    - Retry failed jobs up to 2 times
    - Use exponential backoff (1 min, 5 min)
    - Log retry attempts
    - _Requirements: 11.5_

  - [x] 10.3 Implement concurrency limits
    - Limit to 3 concurrent docking jobs
    - Queue additional jobs when limit reached
    - _Requirements: 6.3, 11.3_

  - [x] 10.4 Write unit tests for Celery task
    - Test successful docking workflow
    - Test error handling at each stage
    - Test retry logic
    - Test cleanup on success and failure
    - _Requirements: 6.1, 6.9, 11.5_

- [x] 11. Checkpoint - Ensure docking execution tests pass ✅ 117 tests passing
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement Docking Job Database Models ✅ 26 tests passing
  - [x] 12.1 Create DockingJob model
    - Fields: id, candidate_id, user_id, status, created_at, started_at, completed_at
    - Fields: grid_params, docking_params, error_message
    - Status enum: queued, running, completed, failed, cancelled
    - Relationships: belongs to candidate, has many results
    - _Requirements: 7.2, 14.1, 14.2_

  - [x] 12.2 Create DockingResult model
    - Fields: id, job_id, pose_number, binding_affinity, rmsd
    - Fields: pdbqt_file_path, created_at
    - Relationships: belongs to job
    - _Requirements: 9.1, 14.3, 14.4_

  - [x] 12.3 Create database migrations
    - Create tables for DockingJob and DockingResult
    - Add indexes for efficient querying
    - _Requirements: 14.1_

  - [x] 12.4 Write unit tests for models
    - Test model creation and validation
    - Test relationships
    - Test queries
    - _Requirements: 14.1, 14.2_

- [ ] 13. Implement Docking Service Layer
  - [ ] 13.1 Create DockingService class
    - Method: submit_docking_job(candidate_ids, params) -> job_ids
    - Method: get_job_status(job_id) -> status_info
    - Method: get_job_results(job_id) -> results
    - Method: cancel_job(job_id) -> success
    - Method: get_user_job_history(user_id) -> jobs
    - Validate candidate IDs exist in database
    - Enforce user job limits (max 100 queued jobs)
    - Queue Celery tasks for execution
    - _Requirements: 1.4, 7.1, 7.6, 7.9, 15.6_

  - [ ] 13.2 Write unit tests for docking service
    - Test job submission
    - Test status retrieval
    - Test results retrieval
    - Test cancellation
    - Test job limits
    - _Requirements: 1.4, 7.6, 15.6_

- [ ] 14. Implement Docking API Endpoints
  - [ ] 14.1 Create API endpoint POST /api/docking/submit
    - Define request schema (candidate_ids, grid_params, docking_params)
    - Define response schema (job_ids, estimated_time)
    - Validate request payload
    - Call DockingService.submit_docking_job()
    - Return job IDs and queue position
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [ ] 14.2 Create API endpoint GET /api/docking/jobs/{job_id}/status
    - Return job status (queued, running, completed, failed)
    - Return progress percentage
    - Return estimated time remaining
    - Return error message if failed
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 10.8_

  - [ ] 14.3 Create API endpoint GET /api/docking/jobs/{job_id}/results
    - Validate job is completed
    - Return binding affinity scores for all poses
    - Return PDBQT file URLs for download
    - Return summary statistics
    - _Requirements: 9.1, 9.5, 9.9, 10.9_

  - [ ] 14.4 Create API endpoint DELETE /api/docking/jobs/{job_id}
    - Cancel running or queued job
    - Clean up temporary files
    - Update job status to cancelled
    - _Requirements: 7.6, 7.7, 10.10_

  - [ ] 14.5 Create API endpoint GET /api/docking/jobs
    - Return user's job history
    - Support filtering by status, date, target
    - Support pagination
    - _Requirements: 7.9, 14.6, 14.7_

  - [ ] 14.6 Write unit tests for API endpoints
    - Test valid requests
    - Test invalid requests (validation errors)
    - Test authentication and authorization
    - Test error scenarios
    - _Requirements: 10.1, 10.2, 10.10_

- [ ] 15. Checkpoint - Ensure backend API tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Implement Frontend Docking Button Component
  - [ ] 16.1 Add "Run Docking" button to CandidateCard component
    - Add button to existing CandidateCard.tsx
    - Show button only when protein structure is available
    - Handle button click to open docking modal
    - Integrate with existing UI styling
    - _Requirements: 1.1, 13.1_

  - [ ] 16.2 Write unit tests for docking button
    - Test button rendering
    - Test button click handler
    - Test conditional display
    - _Requirements: 13.1_

- [ ] 17. Implement Docking Submission Modal
  - [ ] 17.1 Create DockingSubmissionModal component
    - Display candidate summary (molecule name, target, scores)
    - Show estimated docking time (5-15 minutes)
    - Add collapsible advanced options section
    - Add grid box parameter inputs (optional)
    - Add docking parameter inputs (optional)
    - Add "Run Docking" and "Cancel" buttons
    - _Requirements: 13.3, 13.4, 13.5, 13.6_

  - [ ] 17.2 Implement modal submission logic
    - Call docking API on submit
    - Handle API errors
    - Close modal on success
    - Open job tracking interface
    - _Requirements: 13.6, 13.7_

  - [ ] 17.3 Write unit tests for docking modal
    - Test modal rendering
    - Test parameter inputs
    - Test submission
    - Test error handling
    - _Requirements: 13.3, 13.10_

- [ ] 18. Implement Docking Job Tracking Interface
  - [ ] 18.1 Create DockingJobTracker component
    - Display job status (queued, running, completed, failed)
    - Display progress bar with percentage
    - Display current step description
    - Display estimated time remaining
    - Poll API for status updates every 5 seconds
    - Add cancel button for queued/running jobs
    - Redirect to results page when completed
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 13.8_

  - [ ] 18.2 Write unit tests for job tracker
    - Test status display
    - Test progress updates
    - Test polling logic
    - Test cancellation
    - _Requirements: 7.1, 7.5, 13.8_

- [ ] 19. Implement Docking Results Visualization
  - [ ] 19.1 Create DockingResultsViewer component
    - Reuse existing ProteinViewer3D component for protein structure
    - Overlay ligand poses on protein structure
    - Display protein in cartoon representation
    - Display ligand in stick representation with atom colors
    - Highlight binding site region
    - Add pose selector dropdown (switch between poses)
    - Display binding affinity score for selected pose
    - Add rotation, zoom, pan controls (reuse existing)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [ ] 19.2 Add interaction highlighting
    - Detect and display hydrogen bonds
    - Detect and display hydrophobic contacts
    - Add toggle to show/hide interactions
    - _Requirements: 8.9_

  - [ ] 19.3 Add download button for results
    - Download PDBQT files
    - Download summary CSV
    - _Requirements: 8.10_

  - [ ] 19.4 Write unit tests for results viewer
    - Test component rendering
    - Test pose switching
    - Test interaction display
    - Test download functionality
    - _Requirements: 8.1, 8.7, 8.10_

- [ ] 20. Implement Docking Results Analysis Panel
  - [ ] 20.1 Create DockingResultsAnalysis component
    - Display summary table of all poses
    - Show binding affinity scores ranked
    - Show RMSD values
    - Highlight best pose
    - Compare with predicted binding affinity from existing pipeline
    - Show improvement/difference from prediction
    - _Requirements: 9.1, 9.2, 9.4, 9.5, 9.6_

  - [ ] 20.2 Integrate docking scores with candidate ranking
    - Update composite score calculation to include docking score
    - Re-rank candidates based on actual docking results
    - Show before/after ranking comparison
    - _Requirements: 9.6, 9.7_

  - [ ] 20.3 Write unit tests for results analysis
    - Test table rendering
    - Test score calculations
    - Test ranking updates
    - _Requirements: 9.1, 9.5, 9.7_

- [ ] 21. Implement Docking Job History Page
  - [ ] 21.1 Create DockingJobHistory page component
    - Display table of past docking jobs
    - Show job ID, candidate, target, status, date
    - Add filters (status, date range, target)
    - Add pagination
    - Add "View Results" button for completed jobs
    - Add "Re-run" button for failed jobs
    - _Requirements: 7.9, 14.6, 14.7, 14.8, 14.10_

  - [ ] 21.2 Write unit tests for job history page
    - Test table rendering
    - Test filtering
    - Test pagination
    - Test navigation to results
    - _Requirements: 14.6, 14.7_

- [ ] 22. Integrate Docking into Existing Candidate Details Page
  - [ ] 22.1 Update candidate details page (candidates/[id]/page.tsx)
    - Add "Docking Results" tab if docking has been run
    - Display DockingResultsViewer in tab
    - Display DockingResultsAnalysis in tab
    - Show "Run Docking" button if not yet run
    - Show job tracker if docking is in progress
    - _Requirements: 13.1, 13.7, 13.9_

  - [ ] 22.2 Write integration tests for candidate page
    - Test docking button display
    - Test job tracker display
    - Test results display
    - Test tab navigation
    - _Requirements: 13.1, 13.9_

- [ ] 23. Implement Docking API Client
  - [ ] 23.1 Create docking API client module (lib/docking-api.ts)
    - Function: submitDockingJob(candidateIds, params)
    - Function: getDockingJobStatus(jobId)
    - Function: getDockingJobResults(jobId)
    - Function: cancelDockingJob(jobId)
    - Function: getDockingJobHistory(filters)
    - Handle API errors
    - Handle authentication
    - _Requirements: 10.1, 10.8, 10.9, 10.10_

  - [ ] 23.2 Write unit tests for API client
    - Test API request formatting
    - Test response parsing
    - Test error handling
    - _Requirements: 10.1, 10.10_

- [ ] 24. Checkpoint - Ensure frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 25. Implement Background Job Cleanup
  - [ ] 25.1 Create cleanup Celery task
    - Delete docking results older than 7 days
    - Delete temporary files
    - Update database records
    - Run daily via Celery beat
    - _Requirements: 14.9, 15.8_

  - [ ] 25.2 Write unit tests for cleanup task
    - Test old result deletion
    - Test file cleanup
    - Test database updates
    - _Requirements: 14.9_

- [ ] 26. Implement Admin Monitoring Endpoints
  - [ ] 26.1 Create admin API endpoints
    - GET /api/admin/docking/queue-status - View queue length and worker status
    - GET /api/admin/docking/metrics - View performance metrics
    - POST /api/admin/docking/workers/restart - Restart workers
    - Require admin authentication
    - _Requirements: 11.9_

  - [ ] 26.2 Write unit tests for admin endpoints
    - Test authentication
    - Test metrics retrieval
    - Test worker management
    - _Requirements: 11.9_

- [ ] 27. End-to-End Integration Testing
  - [ ] 27.1 Write end-to-end integration tests
    - Test complete workflow: select candidate → submit docking → track progress → view results
    - Test with various candidates from existing data
    - Test error scenarios (missing structure, timeout, cancellation)
    - Test concurrent job execution
    - Validate results accuracy
    - _Requirements: 6.1, 7.1, 8.1, 13.1_

- [ ] 28. Performance Testing and Optimization
  - [ ] 28.1 Benchmark docking performance
    - Measure time for single docking job
    - Measure concurrent job throughput
    - Measure queue processing time
    - _Requirements: 15.1, 15.2, 15.10_

  - [ ] 28.2 Optimize resource usage
    - Monitor CPU and memory usage
    - Implement throttling if needed
    - Optimize file I/O
    - _Requirements: 15.5, 15.9_

- [ ] 29. Documentation and Deployment Preparation
  - [ ] 29.1 Update API documentation
    - Add docking endpoints to OpenAPI/Swagger docs
    - Include request/response schemas
    - Include example requests
    - _Requirements: 10.1_

  - [ ] 29.2 Update deployment documentation
    - Document AutoDock Vina installation
    - Document Celery worker setup
    - Document Redis configuration
    - Document environment variables
    - Document performance expectations
    - _Requirements: 6.1, 11.1, 15.1_

  - [ ] 29.3 Create user guide
    - Document how to run docking
    - Document how to interpret results
    - Document how to compare with predictions
    - Include troubleshooting tips
    - _Requirements: 13.1, 8.1, 9.1_

- [ ] 30. Final Checkpoint - Complete validation
  - Run full test suite (unit + integration + e2e)
  - Validate performance benchmarks
  - Validate all requirements are met
  - Test with real user workflow
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation integrates with existing components (ProteinViewer3D, CandidateCard, etc.)
- All docking execution happens on the backend - users only interact with the web UI
- Results are stored for 7 days and automatically cleaned up
- Maximum 3 concurrent docking jobs to prevent resource exhaustion
