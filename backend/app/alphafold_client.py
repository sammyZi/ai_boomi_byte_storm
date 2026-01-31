"""AlphaFold API client for protein structure retrieval.

This module provides a client for querying the AlphaFold Database API
to retrieve 3D protein structures with confidence scores.
"""

import asyncio
import httpx
from typing import Optional
from app.models import ProteinStructure
from app.cache import cache
from config.settings import settings


class AlphaFoldClient:
    """Client for querying the AlphaFold Database API.
    
    Retrieves 3D protein structures in PDB format with pLDDT confidence scores,
    implements caching with 24-hour TTL, and handles missing structures gracefully.
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0):
        """Initialize the AlphaFold client.
        
        Args:
            base_url: Base URL for the AlphaFold API (defaults to settings)
            timeout: Request timeout in seconds (default: 10.0)
        """
        self.base_url = base_url or settings.alphafold_api_url
        self.timeout = timeout
        self.cache_ttl = 86400  # 24 hours in seconds
    
    async def get_protein_structure(self, uniprot_id: str) -> Optional[ProteinStructure]:
        """Retrieve 3D protein structure from AlphaFold Database.
        
        Queries the AlphaFold Database for a protein structure by UniProt ID,
        parses the PDB format with pLDDT confidence scores, and flags low
        confidence structures (pLDDT < 70).
        
        Implements requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6:
        - Query by UniProt ID
        - Parse PDB format with pLDDT scores
        - Flag structures with pLDDT < 70 as low confidence
        - Cache for 24 hours
        - Continue pipeline if structure unavailable
        - Handle 10-second timeout
        
        Args:
            uniprot_id: UniProt identifier for the protein
        
        Returns:
            ProteinStructure object or None if unavailable
        """
        if not uniprot_id or not uniprot_id.strip():
            return None
        
        # Check cache first (requirement 2.4)
        cache_key = f"af:structure:{uniprot_id}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            return ProteinStructure(**cached_data)
        
        try:
            # Fetch PDB structure from AlphaFold API
            pdb_data = await self._fetch_pdb_structure(uniprot_id)
            if not pdb_data:
                return None
            
            # Parse pLDDT scores from PDB data
            plddt_score = self._parse_plddt_from_pdb(pdb_data)
            
            # Classify confidence (requirement 2.3)
            is_low_confidence = plddt_score < 70.0
            
            # Create ProteinStructure object
            structure = ProteinStructure(
                uniprot_id=uniprot_id,
                pdb_data=pdb_data,
                plddt_score=plddt_score,
                is_low_confidence=is_low_confidence
            )
            
            # Cache the structure (requirement 2.4)
            await cache.set(cache_key, structure.model_dump(), ttl=self.cache_ttl)
            
            return structure
        
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            # Gracefully handle missing structures (requirement 2.5)
            # Log but don't raise - allow pipeline to continue
            return None
    
    async def _fetch_pdb_structure(self, uniprot_id: str) -> Optional[str]:
        """Fetch PDB structure file from AlphaFold API.
        
        Args:
            uniprot_id: UniProt identifier
        
        Returns:
            PDB file content as string, or None if not found
        
        Raises:
            httpx.TimeoutException: If request exceeds 10-second timeout
        """
        # AlphaFold API endpoint for PDB files
        url = f"{self.base_url}/prediction/{uniprot_id}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # First, check if the structure exists via the prediction endpoint
                response = await client.get(url)
                
                if response.status_code == 404:
                    # Structure not available
                    return None
                
                response.raise_for_status()
                prediction_data = response.json()
                
                # Get the PDB file URL from the prediction data
                pdb_url = prediction_data[0].get("pdbUrl") if prediction_data else None
                if not pdb_url:
                    return None
                
                # Fetch the actual PDB file
                pdb_response = await client.get(pdb_url)
                pdb_response.raise_for_status()
                
                return pdb_response.text
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Structure not found - this is expected for some proteins
                return None
            raise
    
    def _parse_plddt_from_pdb(self, pdb_data: str) -> float:
        """Parse average pLDDT confidence score from PDB file.
        
        The pLDDT (predicted Local Distance Difference Test) score is stored
        in the B-factor column of the PDB file. This method calculates the
        average pLDDT across all residues.
        
        Args:
            pdb_data: PDB file content as string
        
        Returns:
            Average pLDDT score (0-100)
        """
        plddt_scores = []
        
        for line in pdb_data.split('\n'):
            # ATOM records contain the B-factor (pLDDT) in columns 61-66
            if line.startswith('ATOM'):
                try:
                    # Extract B-factor value (pLDDT score)
                    b_factor_str = line[60:66].strip()
                    if b_factor_str:
                        plddt_scores.append(float(b_factor_str))
                except (ValueError, IndexError):
                    continue
        
        # Calculate average pLDDT
        if plddt_scores:
            return sum(plddt_scores) / len(plddt_scores)
        
        # Default to 0 if no scores found
        return 0.0

