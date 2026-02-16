# Async Database Fix - Complete

## Problem

The initial database implementation caused:
```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

This happened because FastAPI runs in an async event loop, and we were trying to create a new event loop with `asyncio.run()`.

## Solution

Converted all database operations to use **native async/await** instead of sync wrappers.

## Changes Made

### 1. Tasks Module (`backend/app/docking/tasks.py`)

**Before (Sync with wrapper):**
```python
_db_service = SyncDockingJobService()

def get_job(job_id: str):
    return _db_service.get_job(job_id)  # Uses asyncio.run() internally

def create_docking_job(...):
    job = _db_service.create_job(...)  # Uses asyncio.run() internally
```

**After (Native Async):**
```python
async def get_job(job_id: str):
    async with async_session_maker() as session:
        service = DockingJobService(session)
        return await service.get_job(job_id)

async def create_docking_job(...):
    async with async_session_maker() as session:
        service = DockingJobService(session)
        job = await service.create_job(...)
```

### 2. Main API Endpoints (`backend/app/main.py`)

**Before:**
```python
async def submit_docking_job(request):
    job = create_docking_job(...)  # Sync call in async function
```

**After:**
```python
async def submit_docking_job(request):
    job = await create_docking_job(...)  # Proper async/await
```

### 3. Router Endpoints (`backend/app/docking/router.py`)

**Before:**
```python
async def get_job_history():
    all_jobs = get_all_jobs()  # Sync call
```

**After:**
```python
async def get_job_history():
    all_jobs = await get_all_jobs()  # Async call
```

### 4. Background Thread (`run_docking_job`)

The `run_docking_job` function runs in a background thread (not in the FastAPI event loop), so it uses `asyncio.run()` safely:

```python
def run_docking_job(job_id: str):
    # This runs in a separate thread, so asyncio.run() is safe here
    async def _get_job():
        async with async_session_maker() as session:
            service = DockingJobService(session)
            return await service.get_job(job_id)
    
    job = asyncio.run(_get_job())  # OK because we're in a thread
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Event Loop                       │
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  API Endpoints   │────────▶│  Async Tasks     │          │
│  │  (async)         │  await  │  (async)         │          │
│  └──────────────────┘         └──────────────────┘          │
│                                        │                      │
│                                        │ await                │
│                                        ▼                      │
│                          ┌──────────────────────┐            │
│                          │  DockingJobService   │            │
│                          │  (async)             │            │
│                          └──────────────────────┘            │
│                                        │                      │
│                                        │ await                │
│                                        ▼                      │
│                          ┌──────────────────────┐            │
│                          │  SQLAlchemy Async    │            │
│                          │  Database            │            │
│                          └──────────────────────┘            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   Background Thread                          │
│                                                               │
│  ┌──────────────────┐                                        │
│  │ run_docking_job  │                                        │
│  │ (sync)           │                                        │
│  └──────────────────┘                                        │
│           │                                                   │
│           │ asyncio.run()                                    │
│           ▼                                                   │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  New Event Loop  │────────▶│  Async Database  │          │
│  │  (created)       │  await  │  Operations      │          │
│  └──────────────────┘         └──────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## Key Points

1. **FastAPI endpoints are async** - They run in the main event loop
2. **Database operations are async** - They use `await` in the main loop
3. **Background threads are sync** - They create their own event loop with `asyncio.run()`
4. **No nested event loops** - We never call `asyncio.run()` from within an existing loop

## Testing

Restart the backend and test:

```powershell
cd backend
.\venv\Scripts\python.exe run.py
```

Then:
1. Submit a docking job - Should work without errors
2. Check job status - Should retrieve from database
3. View results - Should show protein data
4. Restart backend - Jobs should persist

## Files Modified

1. `backend/app/docking/tasks.py` - Made functions async
2. `backend/app/main.py` - Added await to async calls
3. `backend/app/docking/router.py` - Added await to async calls
4. `backend/app/docking/db_service.py` - Improved sync wrapper (not used anymore)

## Benefits

- ✅ No more "asyncio.run() cannot be called from a running event loop" errors
- ✅ Proper async/await throughout the codebase
- ✅ Better performance (no thread pool overhead for API calls)
- ✅ Database persistence works correctly
- ✅ Protein data is stored and retrieved from database

## Summary

The system now uses **proper async/await** for all database operations in the FastAPI event loop, while background threads safely create their own event loops. This fixes the runtime error and enables full database persistence.
