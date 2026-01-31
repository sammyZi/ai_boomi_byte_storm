# PowerShell script to set test environment variables
# Run this script before running tests if you encounter environment variable issues

Write-Host "Setting test environment variables..." -ForegroundColor Green

$env:LOG_LEVEL = "INFO"
$env:ENFORCE_HTTPS = "false"
$env:ENVIRONMENT = "development"
$env:API_PORT = "8000"
$env:API_HOST = "0.0.0.0"
$env:CORS_ORIGINS = "http://localhost:3000"
$env:OPEN_TARGETS_API_URL = "https://api.platform.opentargets.org/api/v4"
$env:CHEMBL_API_URL = "https://www.ebi.ac.uk/chembl/api/data"
$env:ALPHAFOLD_API_URL = "https://alphafold.ebi.ac.uk/api"
$env:OLLAMA_BASE_URL = "http://localhost:11434"
$env:OLLAMA_MODEL = "biomistral:7b"
$env:OLLAMA_TIMEOUT = "5"
$env:REDIS_URL = "redis://localhost:6379"
$env:CACHE_TTL = "86400"
$env:RATE_LIMIT_PER_MINUTE = "100"

Write-Host "Environment variables set successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run tests with:" -ForegroundColor Yellow
Write-Host "  python -m pytest tests/" -ForegroundColor Cyan
