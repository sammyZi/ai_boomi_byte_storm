"""ChEMBL API client for bioactive molecule retrieval.

This module provides a client for querying the ChEMBL Database API
to retrieve bioactive molecules tested against protein targets.
"""

import asyncio
import httpx
from typing import List, Optional, Dict, Set
from app.models import Molecule
from app.cache import cache
from app.rdkit_analyzer import RDKitAnalyzer
from config.settings import settings


class ChEMBLClient:
    """Client for querying the ChEMBL Database API.
    
    Retrieves bioactive molecules with activity data, filters by pChEMBL values,
    validates SMILES strings, and implements caching with 24-hour TTL.
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """Initialize the ChEMBL client.
        
        Args:
            base_url: Base URL for the ChEMBL API (defaults to settings)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.chembl_api_url
        self.timeout = timeout
        self.cache_ttl = 86400  # 24 hours in seconds
        self.rdkit_analyzer = RDKitAnalyzer()
    
    async def get_bioactive_molecules(
        self,
        target_id: str,
        min_pchembl: float = 6.0,
        max_molecules: int = 100
    ) -> List[Molecule]:
        """Retrieve bioactive molecules for a protein target.
        
        Queries the ChEMBL Database for molecules with bioactivity data against
        the specified target, filters by pChEMBL value, validates SMILES strings,
        and returns up to max_molecules results.
        
        Implements requirements 3.1, 3.2, 3.3, 3.5, 3.6, 3.7:
        - Query ChEMBL for bioactive molecules
        - Filter by pChEMBL >= min_pchembl
        - Limit to max_molecules per target
        - Validate SMILES using RDKit
        - Exclude invalid SMILES
        - Cache with 24-hour TTL
        
        Args:
            target_id: UniProt ID or ChEMBL target ID
            min_pchembl: Minimum pChEMBL value (default: 6.0)
            max_molecules: Maximum number of molecules to return (default: 100)
        
        Returns:
            List of Molecule objects with validated SMILES
        """
        if not target_id or not target_id.strip():
            return []
        
        # Check cache first (requirement 3.7)
        cache_key = f"chembl:molecules:{target_id}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            # Deserialize cached molecules
            return [Molecule(**mol_data) for mol_data in cached_data]
        
        try:
            # Fetch activities from ChEMBL API
            activities = await self._fetch_activities(target_id)
            
            # Filter and process molecules
            molecules = self._process_activities(
                activities,
                target_id,
                min_pchembl,
                max_molecules
            )
            
            # Cache the results (requirement 3.7)
            if molecules:
                molecules_data = [mol.model_dump() for mol in molecules]
                await cache.set(cache_key, molecules_data, ttl=self.cache_ttl)
            
            return molecules
        
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            # Log error but don't raise - allow pipeline to continue
            return []
    
    async def _fetch_activities(self, target_id: str) -> List[dict]:
        """Fetch bioactivity data from ChEMBL API.
        
        Args:
            target_id: Target identifier (UniProt or ChEMBL ID)
        
        Returns:
            List of activity dictionaries from API
        """
        # ChEMBL API endpoint for activities by target
        # First, we need to get the ChEMBL target ID from UniProt ID
        chembl_target_id = await self._get_chembl_target_id(target_id)
        if not chembl_target_id:
            return []
        
        # Query activities for the target
        url = f"{self.base_url}/activity"
        params = {
            "target_chembl_id": chembl_target_id,
            "pchembl_value__isnull": "false",  # Only activities with pChEMBL values
            "limit": 1000,  # Get more than we need for filtering
            "format": "json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 404:
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Extract activities from response
            activities = data.get("activities", [])
            return activities
    
    async def _get_chembl_target_id(self, uniprot_id: str) -> Optional[str]:
        """Convert UniProt ID to ChEMBL target ID.
        
        Args:
            uniprot_id: UniProt identifier
        
        Returns:
            ChEMBL target ID or None if not found
        """
        # If it's already a ChEMBL ID, return it
        if uniprot_id.startswith("CHEMBL"):
            return uniprot_id
        
        # Query ChEMBL target endpoint by UniProt accession
        url = f"{self.base_url}/target"
        params = {
            "target_components__accession": uniprot_id,
            "limit": 1,
            "format": "json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                targets = data.get("targets", [])
                if targets:
                    return targets[0].get("target_chembl_id")
                
                return None
        except (httpx.HTTPError, httpx.TimeoutException):
            return None
    
    def _process_activities(
        self,
        activities: List[dict],
        target_id: str,
        min_pchembl: float,
        max_molecules: int
    ) -> List[Molecule]:
        """Process activities into Molecule objects with filtering and validation.
        
        Implements requirements 3.2, 3.3, 3.5, 3.6:
        - Filter by pChEMBL >= min_pchembl
        - Limit to max_molecules
        - Validate SMILES using RDKit
        - Exclude invalid SMILES
        
        Args:
            activities: List of activity dictionaries from API
            target_id: Target identifier for association
            min_pchembl: Minimum pChEMBL threshold
            max_molecules: Maximum number of molecules
        
        Returns:
            List of validated Molecule objects
        """
        molecules = []
        seen_chembl_ids = set()
        
        for activity in activities:
            # Extract activity data
            pchembl_value = activity.get("pchembl_value")
            if pchembl_value is None:
                continue
            
            try:
                pchembl_value = float(pchembl_value)
            except (ValueError, TypeError):
                continue
            
            # Filter by pChEMBL threshold (requirement 3.2)
            if pchembl_value < min_pchembl:
                continue
            
            # Extract molecule data
            molecule_data = activity.get("molecule_chembl_id")
            if not molecule_data:
                continue
            
            chembl_id = molecule_data if isinstance(molecule_data, str) else activity.get("molecule_chembl_id")
            if not chembl_id or chembl_id in seen_chembl_ids:
                continue
            
            # Get SMILES
            canonical_smiles = activity.get("canonical_smiles")
            if not canonical_smiles:
                continue
            
            # Validate SMILES using RDKit (requirements 3.5, 3.6)
            mol = self.rdkit_analyzer.parse_smiles(canonical_smiles)
            if mol is None:
                # Invalid SMILES - exclude from results
                continue
            
            # Get canonical SMILES from RDKit
            rdkit_canonical_smiles = self.rdkit_analyzer.get_canonical_smiles(mol)
            if not rdkit_canonical_smiles:
                continue
            
            # Extract additional data
            molecule_name = activity.get("molecule_pref_name", chembl_id)
            activity_type = activity.get("standard_type", "Unknown")
            
            # Create Molecule object
            molecule = Molecule(
                chembl_id=chembl_id,
                name=molecule_name,
                smiles=canonical_smiles,
                canonical_smiles=rdkit_canonical_smiles,
                pchembl_value=pchembl_value,
                activity_type=activity_type,
                target_ids=[target_id]
            )
            
            molecules.append(molecule)
            seen_chembl_ids.add(chembl_id)
            
            # Limit to max_molecules (requirement 3.3)
            if len(molecules) >= max_molecules:
                break
        
        return molecules
    
    def deduplicate_molecules(
        self,
        molecule_lists: List[List[Molecule]]
    ) -> List[Molecule]:
        """Deduplicate molecules across multiple targets.
        
        Implements requirement 3.4:
        - Deduplicate by ChEMBL ID across targets
        - Associate molecules with all relevant targets
        
        Args:
            molecule_lists: List of molecule lists from different targets
        
        Returns:
            Deduplicated list of molecules with all target associations
        """
        molecule_map: Dict[str, Molecule] = {}
        
        for molecules in molecule_lists:
            for molecule in molecules:
                chembl_id = molecule.chembl_id
                
                if chembl_id in molecule_map:
                    # Molecule already exists - merge target IDs
                    existing = molecule_map[chembl_id]
                    # Add new target IDs that aren't already present
                    for target_id in molecule.target_ids:
                        if target_id not in existing.target_ids:
                            existing.target_ids.append(target_id)
                    
                    # Keep the higher pChEMBL value (requirement 4.5)
                    if molecule.pchembl_value > existing.pchembl_value:
                        existing.pchembl_value = molecule.pchembl_value
                        existing.activity_type = molecule.activity_type
                else:
                    # New molecule - add to map
                    molecule_map[chembl_id] = molecule
        
        return list(molecule_map.values())
