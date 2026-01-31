# Docking Integration Spec - Updated for Server-Side Execution

## What Changed

The spec has been updated from **export-only** to **full server-side docking execution** based on your requirement to run AutoDock Vina on the backend and show complete results to users.

## Key Changes

### Before (Export-Only)
- ❌ Users download ZIP files
- ❌ Users install AutoDock Vina locally
- ❌ Users run docking themselves
- ❌ Users interpret raw results

### After (Server-Side Execution)
- ✅ Backend runs AutoDock Vina automatically
- ✅ Users see results in web interface
- ✅ 3D visualization of binding poses
- ✅ Analyzed and ranked results
- ✅ No software installation needed

## New Requirements Added

### Requirement 6: Server-Side Docking Execution
- Run AutoDock Vina on backend
- Async job processing (5-30 minutes per job)
- Max 3 concurrent docking jobs
- 30-minute timeout per job
- Results stored for 7 days

### Requirement 7: Job Status and Progress Tracking
- Real-time status updates (queued, running, completed, failed)
- Progress percentage and time estimates
- Job cancellation support
- Job history tracking
- Optional notifications

### Requirement 8: Docking Results Visualization
- 3D protein-ligand complex visualization
- Multiple binding poses (up to 9)
- Interactive 3D viewer (rotate, zoom, pan)
- Binding affinity scores displayed
- Hydrogen bonds and interactions highlighted

### Requirement 9: Results Analysis and Ranking
- Extract binding affinity scores
- Rank poses by affinity
- Calculate RMSD between poses
- Integrate with existing candidate rankings
- Export results in CSV/JSON

### Requirement 10: Docking API Endpoints
- POST /api/docking/submit - Submit docking jobs
- GET /api/docking/jobs/{job_id}/status - Check status
- GET /api/docking/jobs/{job_id}/results - Get results
- DELETE /api/docking/jobs/{job_id} - Cancel job

### Requirement 11: Job Queue and Worker Management
- Celery or RQ for async processing
- Worker health monitoring
- Job retry logic (up to 2 retries)
- Graceful shutdown support
- Admin endpoints for monitoring

### Requirement 14: Results Storage and Retrieval
- Database storage for job metadata
- File storage for PDBQT results
- Results history page
- Filter and compare results
- Auto-delete after 7 days

## Technical Requirements

### New Backend Dependencies
```python
celery==5.3.4           # Job queue
redis==5.0.1            # Message broker for Celery
autodock-vina==1.2.5    # Docking software (or system install)
openbabel==3.1.1        # PDBQT conversion
meeko==0.4.0            # Ligand preparation
```

### System Requirements
- **AutoDock Vina**: Must be installed on backend server
- **Redis**: For Celery message broker and result backend
- **CPU**: Multi-core recommended (Vina uses multithreading)
- **Disk**: ~1 GB per 100 docking jobs (temporary files)
- **Memory**: 4-8 GB recommended

### Infrastructure Changes
- **Job Queue**: Celery workers running in background
- **Message Broker**: Redis for job queue
- **File Storage**: Persistent storage for docking results
- **Database**: New tables for job tracking and results

## User Experience Flow

### Old Flow (Export-Only)
1. User selects candidates
2. User clicks "Export for Docking"
3. User downloads ZIP file
4. User installs AutoDock Vina
5. User runs docking locally
6. User interprets results manually

### New Flow (Server-Side)
1. User selects candidates
2. User clicks "Run Docking"
3. System queues docking job
4. User sees progress updates
5. System runs AutoDock Vina
6. User sees 3D visualization of results
7. User reviews analyzed binding scores
8. User downloads results if needed

## Performance Expectations

- **Single docking job**: 5-15 minutes
- **Concurrent jobs**: Max 3 at a time
- **Queue capacity**: 100 jobs per user
- **Results retention**: 7 days
- **Status polling**: Every 5 seconds

## Next Steps

The requirements document has been updated. Next, I need to update:

1. ✅ **Requirements** - DONE
2. ⏳ **Design Document** - Need to add:
   - Docking executor component
   - Job queue architecture
   - Results storage design
   - 3D visualization component
3. ⏳ **Tasks Document** - Need to add:
   - AutoDock Vina integration tasks
   - Celery setup tasks
   - Job queue implementation tasks
   - Results visualization tasks

Would you like me to proceed with updating the design and tasks documents?
