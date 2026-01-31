#!/bin/bash
# Bash script to set test environment variables
# Run this script before running tests if you encounter environment variable issues
# Usage: source set_test_env.sh

echo "Setting test environment variables..."

export LOG_LEVEL="INFO"
export ENFORCE_HTTPS="false"
export ENVIRONMENT="development"
export API_PORT="8000"
export API_HOST="0.0.0.0"
export CORS_ORIGINS="http://localhost:3000"
export OPEN_TARGETS_API_URL="https://api.platform.opentargets.org/api/v4"
export CHEMBL_API_URL="https://www.ebi.ac.uk/chembl/api/data"
export ALPHAFOLD_API_URL="https://alphafold.ebi.ac.uk/api"
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="biomistral:7b"
export OLLAMA_TIMEOUT="5"
export REDIS_URL="redis://localhost:6379"
export CACHE_TTL="86400"
export RATE_LIMIT_PER_MINUTE="100"

echo "Environment variables set successfully!"
echo ""
echo "You can now run tests with:"
echo "  python -m pytest tests/"
