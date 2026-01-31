"""Development server runner script.

This script starts the FastAPI development server with hot reload enabled.
"""

import uvicorn
from config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
