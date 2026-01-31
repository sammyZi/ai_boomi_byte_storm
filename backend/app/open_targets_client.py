"""Open Targets API client for disease-target association queries.

This module provides a client for querying the Open Targets Platform API
to retrieve protein targets associated with diseases.
"""

import asyncio
import httpx
from typing import List, Optional
from app.models import Target
from config.settings import settings


class OpenTargetsClient:
    """Client for querying the Open Targets Platform API.
    
    Retrieves disease-target associations with confidence scores,
    implements retry logic with exponential backoff, and filters/ranks results.
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """Initialize the Open Targets client.
        
        Args:
            base_url: Base URL for the Open Targets API (defaults to settings)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.open_targets_api_url
        self.timeout = timeout
        self.max_retries = 3
        self.retry_delays = [1.0, 2.0, 4.0]  # Exponential backoff delays
    
    async def get_disease_targets(
        self, 
        disease_name: str,
        min_confidence: float = 0.5,
        max_targets: int = 10
    ) -> List[Target]:
        """Retrieve protein targets associated with a disease.
        
        Queries the Open Targets Platform API for disease-target associations,
        filters by confidence score, and returns the top-ranked targets.
        
        Args:
            disease_name: Name of the disease to search for
            min_confidence: Minimum confidence score (default: 0.5)
            max_targets: Maximum number of targets to return (default: 10)
        
        Returns:
            List of Target objects sorted by confidence (descending)
        
        Raises:
            httpx.HTTPError: If all retry attempts fail
            ValueError: If disease_name is empty or invalid
        """
        if not disease_name or not disease_name.strip():
            raise ValueError("Disease name cannot be empty")
        
        # Search for disease first to get disease ID
        disease_id = await self._search_disease(disease_name)
        if not disease_id:
            return []
        
        # Get targets for the disease
        targets = await self._get_targets_for_disease(disease_id)
        
        # Filter and rank targets
        filtered_targets = self._filter_and_rank_targets(
            targets, 
            min_confidence, 
            max_targets
        )
        
        return filtered_targets
    
    async def _search_disease(self, disease_name: str) -> Optional[str]:
        """Search for a disease by name and return its ID.
        
        Args:
            disease_name: Name of the disease to search for
        
        Returns:
            Disease ID (EFO ID) or None if not found
        """
        # GraphQL query to search for disease
        query = """
        query SearchDisease($queryString: String!) {
          search(queryString: $queryString, entityNames: ["disease"], page: {size: 1}) {
            hits {
              id
              name
              entity
            }
          }
        }
        """
        
        variables = {"queryString": disease_name}
        
        response_data = await self._make_request_with_retry(
            method="POST",
            endpoint="/graphql",
            json_data={"query": query, "variables": variables}
        )
        
        # Extract disease ID from response
        hits = response_data.get("data", {}).get("search", {}).get("hits", [])
        if hits:
            return hits[0].get("id")
        
        return None
    
    async def _get_targets_for_disease(self, disease_id: str) -> List[dict]:
        """Get protein targets associated with a disease.
        
        Args:
            disease_id: EFO disease identifier
        
        Returns:
            List of target dictionaries with association data
        """
        # GraphQL query to get disease-target associations
        query = """
        query DiseaseTargets($diseaseId: String!) {
          disease(efoId: $diseaseId) {
            associatedTargets(page: {size: 50}) {
              rows {
                target {
                  id
                  approvedSymbol
                  approvedName
                }
                score
                datatypeScores {
                  id
                  score
                }
              }
            }
          }
        }
        """
        
        variables = {"diseaseId": disease_id}
        
        response_data = await self._make_request_with_retry(
            method="POST",
            endpoint="/graphql",
            json_data={"query": query, "variables": variables}
        )
        
        # Extract targets from response
        rows = (
            response_data.get("data", {})
            .get("disease", {})
            .get("associatedTargets", {})
            .get("rows", [])
        )
        
        return rows
    
    def _filter_and_rank_targets(
        self, 
        targets: List[dict], 
        min_confidence: float,
        max_targets: int
    ) -> List[Target]:
        """Filter targets by confidence and rank them.
        
        Implements requirements 1.3, 1.4, 1.5:
        - Filter targets with confidence >= min_confidence
        - Sort by confidence descending
        - Limit to max_targets
        
        Args:
            targets: List of target dictionaries from API
            min_confidence: Minimum confidence threshold
            max_targets: Maximum number of targets to return
        
        Returns:
            List of Target objects, filtered and ranked
        """
        target_objects = []
        
        for row in targets:
            target_data = row.get("target", {})
            score = row.get("score", 0.0)
            
            # Filter by confidence threshold (must be at least 0.5 per Target model validation)
            # and user-specified min_confidence
            effective_min_confidence = max(min_confidence, 0.5)
            if score < effective_min_confidence:
                continue
            
            # Create Target object
            target = Target(
                uniprot_id=target_data.get("id", ""),
                gene_symbol=target_data.get("approvedSymbol", ""),
                protein_name=target_data.get("approvedName", ""),
                confidence_score=score,
                disease_association=f"Association score: {score:.3f}"
            )
            
            target_objects.append(target)
        
        # Sort by confidence descending
        target_objects.sort(key=lambda t: t.confidence_score, reverse=True)
        
        # Limit to max_targets
        return target_objects[:max_targets]
    
    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None
    ) -> dict:
        """Make an HTTP request with exponential backoff retry logic.
        
        Implements requirement 1.6: Retry up to 3 times with exponential backoff.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json_data: JSON payload for POST requests
            params: Query parameters
        
        Returns:
            Response JSON data
        
        Raises:
            httpx.HTTPError: If all retry attempts fail
        """
        url = f"{self.base_url}{endpoint}"
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "POST":
                        response = await client.post(url, json=json_data, params=params)
                    else:
                        response = await client.get(url, params=params)
                    
                    response.raise_for_status()
                    return response.json()
            
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_exception = e
                
                # If this is not the last attempt, wait before retrying
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    await asyncio.sleep(delay)
                    continue
        
        # All retries failed, raise the last exception
        raise last_exception
