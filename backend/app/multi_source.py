"""Multi-source data fetcher with automatic fallback.

This module provides unified access to multiple data sources for:
- Protein structures: AlphaFold → PDB → ESMFold → UniProt
- Molecule data: ChEMBL → PubChem → DrugBank
- Disease-target associations: Open Targets → DisGeNET

If one source fails, automatically tries the next available source.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
import httpx

from app.models import ProteinStructure
from app.cache import cache
from config.settings import settings

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Available data sources."""
    # Protein structure sources
    ALPHAFOLD = "AlphaFold"
    PDB = "PDB"
    ESMFOLD = "ESMFold"
    UNIPROT = "UniProt"
    
    # Molecule data sources
    CHEMBL = "ChEMBL"
    PUBCHEM = "PubChem"
    DRUGBANK = "DrugBank"
    
    # Disease-target sources
    OPEN_TARGETS = "OpenTargets"
    DISGENET = "DisGeNET"


@dataclass
class FetchResult:
    """Result from a data fetch operation."""
    success: bool
    data: Optional[Any]
    source: Optional[DataSource]
    sources_tried: List[str] = field(default_factory=list)
    error: Optional[str] = None
    cached: bool = False
    fetch_time_ms: float = 0


class MultiSourceFetcher:
    """Multi-source data fetcher with automatic fallback."""
    
    # Protein structure sources in order of preference
    PROTEIN_SOURCES = [
        DataSource.ALPHAFOLD,
        DataSource.PDB,
        DataSource.ESMFOLD,
    ]
    
    # Molecule data sources
    MOLECULE_SOURCES = [
        DataSource.CHEMBL,
        DataSource.PUBCHEM,
    ]
    
    def __init__(self, timeout: float = 10.0):
        """Initialize the multi-source fetcher.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.cache_ttl = 86400  # 24 hours
        
        # API endpoints
        self.endpoints = {
            DataSource.ALPHAFOLD: "https://alphafold.ebi.ac.uk/api",
            DataSource.PDB: "https://data.rcsb.org/rest/v1",
            DataSource.ESMFOLD: "https://api.esmatlas.com",
            DataSource.CHEMBL: "https://www.ebi.ac.uk/chembl/api/data",
            DataSource.PUBCHEM: "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
            DataSource.OPEN_TARGETS: "https://api.platform.opentargets.org/api/v4",
            DataSource.DISGENET: "https://www.disgenet.org/api",
        }
    
    async def get_protein_structure(
        self, 
        uniprot_id: str,
        preferred_sources: Optional[List[DataSource]] = None
    ) -> FetchResult:
        """Fetch protein structure from multiple sources with fallback.
        
        Tries sources in order: AlphaFold → PDB → ESMFold
        
        Args:
            uniprot_id: UniProt identifier
            preferred_sources: Optional list of sources to try (in order)
            
        Returns:
            FetchResult with protein structure data
        """
        start_time = datetime.now(timezone.utc)
        sources = preferred_sources or self.PROTEIN_SOURCES
        sources_tried = []
        
        # Check cache first
        cache_key = f"multi:protein:{uniprot_id}"
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"[{uniprot_id}] Protein structure found in cache")
            return FetchResult(
                success=True,
                data=ProteinStructure(**cached),
                source=DataSource(cached.get('_source', 'AlphaFold')),
                sources_tried=['cache'],
                cached=True,
                fetch_time_ms=0
            )
        
        for source in sources:
            sources_tried.append(source.value)
            logger.info(f"[{uniprot_id}] Trying {source.value}...")
            
            try:
                if source == DataSource.ALPHAFOLD:
                    result = await self._fetch_alphafold(uniprot_id)
                elif source == DataSource.PDB:
                    result = await self._fetch_pdb(uniprot_id)
                elif source == DataSource.ESMFOLD:
                    result = await self._fetch_esmfold(uniprot_id)
                else:
                    continue
                
                if result:
                    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    
                    # Cache the result with source info
                    cache_data = result.model_dump()
                    cache_data['_source'] = source.value
                    await cache.set(cache_key, cache_data, ttl=self.cache_ttl)
                    
                    logger.info(f"[{uniprot_id}] Successfully fetched from {source.value}")
                    return FetchResult(
                        success=True,
                        data=result,
                        source=source,
                        sources_tried=sources_tried,
                        fetch_time_ms=elapsed
                    )
                    
            except Exception as e:
                logger.warning(f"[{uniprot_id}] {source.value} failed: {str(e)}")
                continue
        
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        return FetchResult(
            success=False,
            data=None,
            source=None,
            sources_tried=sources_tried,
            error=f"All sources failed for {uniprot_id}",
            fetch_time_ms=elapsed
        )
    
    async def _fetch_alphafold(self, uniprot_id: str) -> Optional[ProteinStructure]:
        """Fetch from AlphaFold Database."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Get PDB structure
            pdb_url = f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb"
            response = await client.get(pdb_url)
            
            if response.status_code != 200:
                return None
            
            pdb_data = response.text
            plddt_score = self._parse_plddt_from_pdb(pdb_data)
            
            return ProteinStructure(
                uniprot_id=uniprot_id,
                pdb_data=pdb_data,
                plddt_score=plddt_score,
                is_low_confidence=plddt_score < 70.0
            )
    
    async def _fetch_pdb(self, uniprot_id: str) -> Optional[ProteinStructure]:
        """Fetch from RCSB PDB Database.
        
        First maps UniProt ID to PDB ID, then fetches structure.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Search for PDB entries with this UniProt ID
            search_url = "https://search.rcsb.org/rcsbsearch/v2/query"
            search_query = {
                "query": {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                        "operator": "exact_match",
                        "value": uniprot_id
                    }
                },
                "return_type": "entry",
                "request_options": {
                    "results_content_type": ["experimental"],
                    "sort": [{"sort_by": "score", "direction": "desc"}],
                    "pager": {"start": 0, "rows": 1}
                }
            }
            
            response = await client.post(search_url, json=search_query)
            if response.status_code != 200:
                return None
            
            results = response.json()
            if not results.get('result_set'):
                return None
            
            pdb_id = results['result_set'][0]['identifier']
            
            # Fetch PDB structure
            pdb_url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
            pdb_response = await client.get(pdb_url)
            
            if pdb_response.status_code != 200:
                return None
            
            pdb_data = pdb_response.text
            
            return ProteinStructure(
                uniprot_id=uniprot_id,
                pdb_data=pdb_data,
                plddt_score=85.0,  # Experimental structures are high quality
                is_low_confidence=False
            )
    
    async def _fetch_esmfold(self, uniprot_id: str) -> Optional[ProteinStructure]:
        """Fetch from ESMFold API.
        
        ESMFold can predict structures from sequence on-the-fly.
        First needs to get sequence from UniProt.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:  # Longer timeout for prediction
            # Get sequence from UniProt
            uniprot_url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.fasta"
            seq_response = await client.get(uniprot_url)
            
            if seq_response.status_code != 200:
                return None
            
            # Parse FASTA
            lines = seq_response.text.strip().split('\n')
            sequence = ''.join(lines[1:])  # Skip header line
            
            if len(sequence) > 400:
                # ESMFold has sequence length limits
                logger.warning(f"[{uniprot_id}] Sequence too long for ESMFold ({len(sequence)} aa)")
                return None
            
            # Request structure prediction
            esmfold_url = "https://api.esmatlas.com/foldSequence/v1/pdb/"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            pred_response = await client.post(
                esmfold_url,
                content=sequence,
                headers=headers
            )
            
            if pred_response.status_code != 200:
                return None
            
            pdb_data = pred_response.text
            plddt_score = self._parse_plddt_from_pdb(pdb_data)
            
            return ProteinStructure(
                uniprot_id=uniprot_id,
                pdb_data=pdb_data,
                plddt_score=plddt_score,
                is_low_confidence=plddt_score < 70.0
            )
    
    def _parse_plddt_from_pdb(self, pdb_data: str) -> float:
        """Parse average pLDDT score from B-factor column in PDB.
        
        In AlphaFold PDB files, pLDDT scores are stored in the B-factor column
        (columns 61-66 of ATOM records).
        """
        plddt_scores = []
        
        for line in pdb_data.split('\n'):
            if line.startswith('ATOM'):
                try:
                    # B-factor is columns 61-66 (0-indexed: 60:66)
                    b_factor = float(line[60:66].strip())
                    plddt_scores.append(b_factor)
                except (ValueError, IndexError):
                    continue
        
        if plddt_scores:
            return sum(plddt_scores) / len(plddt_scores)
        return 0.0
    
    async def get_molecule_data(
        self,
        chembl_id: Optional[str] = None,
        smiles: Optional[str] = None,
        inchi_key: Optional[str] = None
    ) -> FetchResult:
        """Fetch molecule data from multiple sources.
        
        Tries sources in order: ChEMBL → PubChem
        
        Args:
            chembl_id: ChEMBL molecule identifier
            smiles: SMILES string
            inchi_key: InChI Key identifier
            
        Returns:
            FetchResult with molecule data
        """
        start_time = datetime.now(timezone.utc)
        sources_tried = []
        
        identifier = chembl_id or smiles or inchi_key
        if not identifier:
            return FetchResult(
                success=False,
                data=None,
                source=None,
                sources_tried=[],
                error="No identifier provided"
            )
        
        # Check cache
        cache_key = f"multi:molecule:{identifier}"
        cached = await cache.get(cache_key)
        if cached:
            return FetchResult(
                success=True,
                data=cached,
                source=DataSource(cached.get('_source', 'ChEMBL')),
                sources_tried=['cache'],
                cached=True
            )
        
        for source in self.MOLECULE_SOURCES:
            sources_tried.append(source.value)
            
            try:
                if source == DataSource.CHEMBL and chembl_id:
                    result = await self._fetch_chembl_molecule(chembl_id)
                elif source == DataSource.PUBCHEM:
                    result = await self._fetch_pubchem_molecule(smiles or inchi_key)
                else:
                    continue
                
                if result:
                    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    
                    result['_source'] = source.value
                    await cache.set(cache_key, result, ttl=self.cache_ttl)
                    
                    return FetchResult(
                        success=True,
                        data=result,
                        source=source,
                        sources_tried=sources_tried,
                        fetch_time_ms=elapsed
                    )
                    
            except Exception as e:
                logger.warning(f"[{identifier}] {source.value} failed: {str(e)}")
                continue
        
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        return FetchResult(
            success=False,
            data=None,
            source=None,
            sources_tried=sources_tried,
            error=f"All sources failed for molecule",
            fetch_time_ms=elapsed
        )
    
    async def _fetch_chembl_molecule(self, chembl_id: str) -> Optional[Dict[str, Any]]:
        """Fetch molecule data from ChEMBL."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/{chembl_id}.json"
            response = await client.get(url)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            return {
                'chembl_id': chembl_id,
                'name': data.get('pref_name'),
                'smiles': data.get('molecule_structures', {}).get('canonical_smiles'),
                'molecular_weight': data.get('molecule_properties', {}).get('full_mwt'),
                'max_phase': data.get('max_phase'),
                'molecule_type': data.get('molecule_type')
            }
    
    async def _fetch_pubchem_molecule(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Fetch molecule data from PubChem."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Try SMILES search
            search_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{identifier}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName/JSON"
            response = await client.get(search_url)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            properties = data.get('PropertyTable', {}).get('Properties', [{}])[0]
            
            return {
                'cid': properties.get('CID'),
                'name': properties.get('IUPACName'),
                'smiles': properties.get('CanonicalSMILES'),
                'molecular_weight': properties.get('MolecularWeight'),
                'formula': properties.get('MolecularFormula')
            }


# Singleton instance
multi_source = MultiSourceFetcher()
