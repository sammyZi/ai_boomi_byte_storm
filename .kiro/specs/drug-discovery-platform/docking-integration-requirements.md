# Requirements Document: Docking Integration

## Introduction

The Docking Integration feature extends the AI-Powered Drug Discovery Platform by enabling researchers to export protein-ligand pairs for molecular docking validation using AutoDock Vina. This feature bridges the gap between computational drug discovery and structural validation by automatically generating all necessary files and configurations for docking simulations.

## Glossary

- **System**: The AI-Powered Drug Discovery Platform
- **Docking**: Computational method to predict binding poses and affinity of small molecules to protein targets
- **AutoDock_Vina**: Open-source molecular docking software
- **PDBQT**: Protein Data Bank, Partial Charge (Q), & Atom Type (T) file format required by AutoDock Vina
- **Ligand**: Small molecule (drug candidate) that binds to a protein target
- **Receptor**: Protein target structure that binds to ligands
- **Grid_Box**: 3D rectangular region defining the search space for docking
- **Binding_Site**: Region on protein where ligand binds
- **PDB**: Protein Data Bank format for 3D molecular structures
- **Exhaustiveness**: Search thoroughness parameter for AutoDock Vina (higher = more thorough)
- **Energy_Range**: Maximum energy difference between best and worst binding modes (kcal/mol)
- **Docking_Configuration**: Configuration file specifying docking parameters for AutoDock Vina

## Requirements

### Requirement 1: Protein-Ligand Pair Selection

**User Story:** As a researcher, I want to select specific drug candidates for docking validation, so that I can verify predicted binding interactions.

#### Acceptance Criteria

1. WHEN viewing drug candidate results, THE System SHALL display a "Prepare for Docking" button for each candidate
2. WHEN a user clicks "Prepare for Docking", THE System SHALL mark that protein-ligand pair for export
3. WHEN multiple candidates share the same target, THE System SHALL group them by target protein
4. THE System SHALL allow selection of up to 50 protein-ligand pairs per export
5. WHEN a user selects more than 50 pairs, THE System SHALL display a warning message
6. THE System SHALL display a counter showing the number of selected pairs

### Requirement 2: PDBQT File Generation for Receptors

**User Story:** As a researcher, I want protein structures automatically converted to PDBQT format, so that I can use them directly in AutoDock Vina.

#### Acceptance Criteria

1. WHEN a protein structure is available from AlphaFold, THE System SHALL convert the PDB format to PDBQT format
2. WHEN converting to PDBQT, THE System SHALL add hydrogen atoms to the protein structure
3. WHEN converting to PDBQT, THE System SHALL assign Gasteiger partial charges to all atoms
4. WHEN converting to PDBQT, THE System SHALL merge non-polar hydrogens
5. WHEN converting to PDBQT, THE System SHALL detect and preserve metal ions and cofactors
6. WHEN a protein structure is not available, THE System SHALL provide instructions to obtain the structure manually
7. THE System SHALL validate that the generated PDBQT file contains valid atom types and charges

### Requirement 3: PDBQT File Generation for Ligands

**User Story:** As a researcher, I want ligand molecules automatically converted to PDBQT format, so that I can dock them without manual preparation.

#### Acceptance Criteria

1. WHEN a ligand SMILES string is available, THE System SHALL generate a 3D structure using RDKit
2. WHEN generating 3D structure, THE System SHALL use MMFF94 force field for energy minimization
3. WHEN converting ligand to PDBQT, THE System SHALL add hydrogen atoms
4. WHEN converting ligand to PDBQT, THE System SHALL assign Gasteiger partial charges
5. WHEN converting ligand to PDBQT, THE System SHALL detect and mark rotatable bonds
6. WHEN converting ligand to PDBQT, THE System SHALL set the root atom for torsion tree
7. THE System SHALL validate that the generated PDBQT file contains valid atom types and rotatable bonds
8. WHEN 3D structure generation fails, THE System SHALL log the error and exclude that ligand from export

### Requirement 4: Grid Box Coordinate Calculation

**User Story:** As a researcher, I want automatic calculation of grid box coordinates centered on binding sites, so that I don't have to manually determine search spaces.

#### Acceptance Criteria

1. WHEN a protein structure is available, THE System SHALL calculate the geometric center of the protein
2. WHEN calculating grid box, THE System SHALL set the center coordinates to the protein geometric center
3. WHEN calculating grid box, THE System SHALL set default dimensions to 25 Å × 25 Å × 25 Å
4. WHEN a known binding site is available, THE System SHALL center the grid box on the binding site instead of geometric center
5. THE System SHALL provide grid box coordinates in Angstroms with 2 decimal places
6. THE System SHALL validate that grid box dimensions are between 10 Å and 50 Å per axis
7. WHEN grid box calculation fails, THE System SHALL use default center (0, 0, 0) and log a warning

### Requirement 5: Docking Configuration File Generation

**User Story:** As a researcher, I want pre-configured docking configuration files, so that I can run AutoDock Vina immediately without manual setup.

#### Acceptance Criteria

1. WHEN exporting docking files, THE System SHALL generate a configuration file for each protein-ligand pair
2. THE System SHALL include receptor PDBQT file path in the configuration
3. THE System SHALL include ligand PDBQT file path in the configuration
4. THE System SHALL include grid box center coordinates (center_x, center_y, center_z) in the configuration
5. THE System SHALL include grid box dimensions (size_x, size_y, size_z) in the configuration
6. THE System SHALL set exhaustiveness parameter to 8 by default
7. THE System SHALL set num_modes parameter to 9 by default
8. THE System SHALL set energy_range parameter to 3 kcal/mol by default
9. THE System SHALL include output file path for docking results in the configuration
10. THE System SHALL format the configuration file according to AutoDock Vina specification

### Requirement 6: Server-Side Docking Execution

**User Story:** As a researcher, I want the system to run molecular docking automatically, so that I can see binding predictions without installing software.

#### Acceptance Criteria

1. WHEN a user initiates docking, THE System SHALL execute AutoDock Vina on the backend server
2. THE System SHALL run docking jobs asynchronously using a job queue
3. THE System SHALL process multiple docking jobs concurrently with a maximum of 3 concurrent jobs
4. WHEN a docking job is submitted, THE System SHALL return a job ID to track progress
5. THE System SHALL execute AutoDock Vina with the generated configuration files
6. THE System SHALL capture AutoDock Vina output including binding affinity scores
7. THE System SHALL parse docking results to extract binding poses and scores
8. WHEN docking completes successfully, THE System SHALL store results for 7 days
9. WHEN docking fails, THE System SHALL log the error and mark the job as failed
10. THE System SHALL enforce a timeout of 30 minutes per docking job

### Requirement 7: Docking Job Status and Progress Tracking

**User Story:** As a researcher, I want to track docking job progress, so that I know when results will be ready.

#### Acceptance Criteria

1. WHEN a docking job is running, THE System SHALL provide real-time status updates
2. THE System SHALL report job status as: queued, running, completed, or failed
3. WHEN a job is queued, THE System SHALL display estimated wait time based on queue length
4. WHEN a job is running, THE System SHALL display progress percentage
5. WHEN a job is running, THE System SHALL display estimated time remaining
6. THE System SHALL allow users to cancel queued or running jobs
7. WHEN a job is cancelled, THE System SHALL clean up temporary files and stop execution
8. THE System SHALL send notifications when docking jobs complete (optional email/webhook)
9. THE System SHALL maintain a job history for each user showing past docking runs
10. THE System SHALL allow users to re-run failed docking jobs

### Requirement 8: Docking Results Visualization

**User Story:** As a researcher, I want to visualize docking results in 3D, so that I can understand binding poses and interactions.

#### Acceptance Criteria

1. WHEN docking completes, THE Frontend SHALL display a 3D visualization of the protein-ligand complex
2. THE Frontend SHALL render the protein structure in cartoon representation
3. THE Frontend SHALL render the ligand in stick representation with atom colors
4. THE Frontend SHALL highlight the binding site region
5. THE Frontend SHALL allow users to rotate, zoom, and pan the 3D view
6. THE Frontend SHALL display multiple binding poses (up to 9 modes)
7. THE Frontend SHALL allow users to switch between different binding poses
8. THE Frontend SHALL display binding affinity score for each pose
9. THE Frontend SHALL highlight key interactions (hydrogen bonds, hydrophobic contacts)
10. THE Frontend SHALL provide a download button for the docking result files

### Requirement 9: Docking Results Analysis and Ranking

**User Story:** As a researcher, I want docking results analyzed and ranked, so that I can identify the best binding candidates.

#### Acceptance Criteria

1. WHEN docking completes, THE System SHALL extract binding affinity scores from AutoDock Vina output
2. THE System SHALL rank binding poses by binding affinity (most negative = best)
3. THE System SHALL calculate RMSD (root mean square deviation) between poses
4. THE System SHALL identify the best binding pose for each ligand
5. THE System SHALL compare docking scores across multiple ligands for the same target
6. THE System SHALL integrate docking scores with existing composite scores
7. THE System SHALL update candidate rankings based on actual docking results
8. THE System SHALL flag poses with poor binding affinity (> -5 kcal/mol)
9. THE System SHALL provide a summary table of all docking results
10. THE System SHALL allow export of docking results in CSV and JSON formats

### Requirement 10: Docking API Endpoints

**User Story:** As a developer, I want well-defined API endpoints for docking operations, so that I can integrate docking functionality programmatically.

#### Acceptance Criteria

1. THE Backend SHALL provide a POST endpoint at /api/docking/submit
2. WHEN the endpoint receives a request, THE Backend SHALL validate the request payload
3. THE Backend SHALL accept a list of candidate IDs to dock
4. THE Backend SHALL accept optional grid box parameters (center, size)
5. THE Backend SHALL accept optional docking parameters (exhaustiveness, num_modes, energy_range)
6. WHEN validation succeeds, THE Backend SHALL queue docking jobs asynchronously
7. WHEN jobs are queued, THE Backend SHALL return job IDs for tracking
8. THE Backend SHALL provide a GET endpoint at /api/docking/jobs/{job_id}/status
9. THE Backend SHALL provide a GET endpoint at /api/docking/jobs/{job_id}/results
10. THE Backend SHALL provide a DELETE endpoint at /api/docking/jobs/{job_id} for cancellation

### Requirement 11: Job Queue and Worker Management

**User Story:** As a system administrator, I want efficient job queue management, so that docking jobs are processed reliably and resources are used optimally.

#### Acceptance Criteria

1. THE System SHALL use a job queue system (Celery or RQ) for async docking execution
2. THE System SHALL configure worker processes to handle docking jobs
3. THE System SHALL limit concurrent docking jobs to 3 to prevent resource exhaustion
4. THE System SHALL prioritize jobs based on submission time (FIFO)
5. THE System SHALL retry failed jobs up to 2 times with exponential backoff
6. THE System SHALL monitor worker health and restart failed workers
7. THE System SHALL log all job events (queued, started, completed, failed)
8. THE System SHALL clean up completed job data after 7 days
9. THE System SHALL provide admin endpoints to view queue status and worker metrics
10. THE System SHALL support graceful shutdown of workers without losing jobs

### Requirement 12: Validation and Error Handling

**User Story:** As a researcher, I want clear error messages when docking export fails, so that I can understand and resolve issues.

#### Acceptance Criteria

1. WHEN a protein structure is missing, THE System SHALL provide a clear error message and skip that candidate
2. WHEN SMILES conversion fails, THE System SHALL provide the molecule name and error reason
3. WHEN PDBQT generation fails, THE System SHALL log detailed error information and skip that candidate
4. WHEN AutoDock Vina execution fails, THE System SHALL capture stderr output and mark job as failed
5. WHEN a docking job times out after 30 minutes, THE System SHALL terminate the process and mark as failed
6. THE System SHALL validate that AutoDock Vina is installed before accepting docking jobs
7. WHEN AutoDock Vina is not installed, THE System SHALL return HTTP 503 with installation instructions
8. THE System SHALL validate file permissions before writing files
9. WHEN file write fails, THE System SHALL return a clear error message
10. THE System SHALL log all errors with context for debugging

### Requirement 13: Frontend Docking Interface

**User Story:** As a researcher, I want an intuitive interface for initiating docking and viewing results, so that I can easily validate binding predictions.

#### Acceptance Criteria

1. WHEN viewing candidate details, THE Frontend SHALL display a "Run Docking" button
2. WHEN candidates are selected, THE Frontend SHALL display a batch docking option
3. WHEN the docking button is clicked, THE Frontend SHALL display a confirmation modal
4. WHEN the modal opens, THE Frontend SHALL show estimated docking time
5. WHEN the modal opens, THE Frontend SHALL display advanced options (grid box, docking parameters)
6. WHEN the user confirms docking, THE Frontend SHALL call the docking API
7. WHEN docking is submitted, THE Frontend SHALL display a job tracking interface
8. WHEN docking is running, THE Frontend SHALL poll for status updates every 5 seconds
9. WHEN docking completes, THE Frontend SHALL display results with 3D visualization
10. WHEN docking fails, THE Frontend SHALL display an error message with details

### Requirement 14: Docking Results Storage and Retrieval

**User Story:** As a researcher, I want my docking results saved, so that I can review them later without re-running docking.

#### Acceptance Criteria

1. THE System SHALL store docking results in a database with job metadata
2. THE System SHALL store PDBQT result files on disk with unique identifiers
3. THE System SHALL associate docking results with the original drug candidates
4. THE System SHALL store binding affinity scores for all poses
5. THE System SHALL store timestamps for job submission and completion
6. THE System SHALL provide a results history page showing past docking jobs
7. THE System SHALL allow users to filter results by date, target, or status
8. THE System SHALL allow users to compare results across multiple docking runs
9. THE System SHALL automatically delete results older than 7 days
10. THE System SHALL provide an option to download raw docking output files

### Requirement 15: Performance and Scalability

**User Story:** As a researcher, I want reasonable docking performance, so that I can get results in a timely manner.

#### Acceptance Criteria

1. THE System SHALL complete docking for a single protein-ligand pair in 5-15 minutes
2. THE System SHALL process multiple docking jobs concurrently (max 3 concurrent)
3. THE System SHALL queue additional jobs when concurrent limit is reached
4. THE System SHALL provide accurate time estimates based on queue length and job complexity
5. THE System SHALL use efficient file I/O to minimize disk usage
6. THE System SHALL limit maximum number of queued jobs to 100 per user
7. WHEN queue limit is reached, THE System SHALL return an error suggesting to wait
8. THE System SHALL clean up temporary files immediately after job completion
9. THE System SHALL monitor system resources (CPU, memory, disk) and throttle if needed
10. THE System SHALL log performance metrics for each docking job
