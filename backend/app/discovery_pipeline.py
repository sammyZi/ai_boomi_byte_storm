"""Discovery pipeline orchestrator for drug discovery workflow.

This module orchestrates the complete drug discovery pipeline, coordinating
multiple API clients, analysis engines, and scoring components to transform
disease queries into ranked drug candidates.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Set, Optional
from app.models import (
    Target,
    ProteinStructure,
    Molecule,
    MolecularProperties,
    ToxicityAssessment,
    DrugCandidate,
    DiscoveryResult
)
from app.open_targets_client import OpenTargetsClient
from app.alphafold_client import AlphaFoldClient
from app.chembl_client import ChEMBLClient
from app.rdkit_analyzer import RDKitAnalyzer
from app.scoring_engine import ScoringEngine
from app.biomistral_engine import BioMistralEngine


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiscoveryPipeline:
    """Orchestrator for the complete drug discovery pipeline.
    
    Coordinates the workflow:
    1. Query Open Targets for disease-target associations
    2. Fetch AlphaFold structures for targets (concurrent)
    3. Query ChEMBL for bioactive molecules per target (concurrent)
    4. Calculate molecular properties and toxicity
    5. Score and rank candidates
    6. Generate AI analysis for top candidates
    7. Return ranked results with metadata
    
    Implements graceful degradation: continues processing when non-critical
    components fail, adding warnings to results.
    """
    
    def __init__(
        self,
        open_targets_client: Optional[OpenTargetsClient] = None,
        alphafold_client: Optional[AlphaFoldClient] = None,
        chembl_client: Optional[ChEMBLClient] = None,
        rdkit_analyzer: Optional[RDKitAnalyzer] = None,
        scoring_engine: Optional[ScoringEngine] = None,
        biomistral_engine: Optional[BioMistralEngine] = None,
        max_concurrent_requests: int = 5
    ):
        """Initialize the discovery pipeline.
        
        Args:
            open_targets_client: Client for disease-target queries
            alphafold_client: Client for protein structure retrieval
            chembl_client: Client for bioactive molecule queries
            rdkit_analyzer: Analyzer for molecular properties
            scoring_engine: Engine for scoring and ranking
            biomistral_engine: AI engine for candidate analysis
            max_concurrent_requests: Maximum concurrent requests per API (default: 5)
        """
        self.open_targets_client = open_targets_client or OpenTargetsClient()
        self.alphafold_client = alphafold_client or AlphaFoldClient()
        self.chembl_client = chembl_client or ChEMBLClient()
        self.rdkit_analyzer = rdkit_analyzer or RDKitAnalyzer()
        self.scoring_engine = scoring_engine or ScoringEngine()
        self.biomistral_engine = biomistral_engine or BioMistralEngine()
        self.max_concurrent_requests = max_concurrent_requests
        self.warnings: List[str] = []
    
    async def discover_drugs(self, disease_name: str) -> DiscoveryResult:
        """Main entry point for drug discovery pipeline.
        
        Orchestrates the complete workflow from disease query to ranked
        drug candidates with AI analysis.
        
        Args:
            disease_name: Name of the disease to search for
        
        Returns:
            DiscoveryResult with ranked candidates and metadata
        
        Validates: Requirements 9.1
        """
        start_time = datetime.utcnow()
        self.warnings = []  # Reset warnings for new query
        targets_found = 0  # Track targets for result
        
        try:
            # Step 1: Get disease-target associations
            logger.info(f"Querying Open Targets for disease: {disease_name}")
            targets = await self._get_targets(disease_name)
            targets_found = len(targets)
            
            if not targets:
                logger.warning(f"No targets found for disease: {disease_name}")
                return self._create_empty_result(disease_name, start_time, targets_found)
            
            logger.info(f"Found {len(targets)} targets")
            
            # Step 2: Fetch protein structures concurrently (non-critical)
            logger.info("Fetching protein structures from AlphaFold")
            structures = await self._fetch_structures_concurrent(targets)
            
            # Step 3: Fetch bioactive molecules concurrently
            logger.info("Fetching bioactive molecules from ChEMBL")
            molecules = await self._fetch_molecules_concurrent(targets)
            
            if not molecules:
                logger.warning("No bioactive molecules found")
                return self._create_empty_result(disease_name, start_time, targets_found)
            
            logger.info(f"Found {len(molecules)} unique molecules")
            
            # Step 4: Analyze molecules (properties + toxicity)
            logger.info("Analyzing molecular properties and toxicity")
            analyzed_molecules = await self._analyze_molecules(molecules)
            
            # Step 5: Create and score drug candidates
            logger.info("Creating and scoring drug candidates")
            candidates = await self._create_candidates(
                analyzed_molecules,
                targets,
                structures
            )
            
            if not candidates:
                logger.warning("No valid candidates after analysis")
                return self._create_empty_result(disease_name, start_time, targets_found)
            
            # Step 6: Rank candidates
            logger.info(f"Ranking {len(candidates)} candidates")
            ranked_candidates = self.scoring_engine.rank_candidates(candidates)
            
            # Step 7: Generate AI analysis for top candidates
            logger.info("Generating AI analysis for top candidates")
            await self._add_ai_analysis(ranked_candidates)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            # Ensure minimum processing time to satisfy validation (gt=0.0)
            processing_time = max(processing_time, 0.001)
            
            # Create result
            result = DiscoveryResult(
                query=disease_name,
                timestamp=start_time,
                processing_time_seconds=processing_time,
                candidates=ranked_candidates,
                targets_found=len(targets),
                molecules_analyzed=len(molecules),
                api_version="0.1.0",
                warnings=self.warnings
            )
            
            logger.info(f"Pipeline completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            # Return empty result with error warning
            self.warnings.append(f"Pipeline error: {str(e)}")
            return self._create_empty_result(disease_name, start_time, targets_found)
    
    async def _get_targets(self, disease_name: str) -> List[Target]:
        """Get disease-target associations from Open Targets.
        
        Args:
            disease_name: Disease to search for
        
        Returns:
            List of Target objects
        """
        try:
            targets = await self.open_targets_client.get_disease_targets(disease_name)
            return targets
        except Exception as e:
            logger.error(f"Error fetching targets: {str(e)}")
            self.warnings.append(f"Failed to fetch targets: {str(e)}")
            return []
    
    async def _fetch_structures_concurrent(
        self,
        targets: List[Target]
    ) -> Dict[str, ProteinStructure]:
        """Fetch protein structures concurrently with rate limiting.
        
        Implements graceful degradation: continues if structures unavailable.
        
        Args:
            targets: List of targets to fetch structures for
        
        Returns:
            Dictionary mapping UniProt ID to ProteinStructure
        
        Validates: Requirements 9.7, 9.8, 10.1
        """
        structures = {}
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def fetch_with_limit(target: Target):
            async with semaphore:
                try:
                    structure = await self.alphafold_client.get_protein_structure(
                        target.uniprot_id
                    )
                    if structure:
                        if structure.is_low_confidence:
                            self.warnings.append(
                                f"Low confidence structure for {target.gene_symbol} "
                                f"(pLDDT: {structure.plddt_score:.1f})"
                            )
                        return target.uniprot_id, structure
                except Exception as e:
                    logger.warning(f"Failed to fetch structure for {target.uniprot_id}: {e}")
                    # Graceful degradation - continue without structure
                return None
        
        # Fetch all structures concurrently
        tasks = [fetch_with_limit(target) for target in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful results
        for result in results:
            if result and not isinstance(result, Exception):
                uniprot_id, structure = result
                structures[uniprot_id] = structure
        
        if len(structures) < len(targets):
            missing = len(targets) - len(structures)
            self.warnings.append(f"{missing} protein structures unavailable")
        
        return structures
    
    async def _fetch_molecules_concurrent(
        self,
        targets: List[Target]
    ) -> List[Molecule]:
        """Fetch bioactive molecules concurrently with rate limiting.
        
        Deduplicates molecules across targets and associates with all
        relevant targets.
        
        Args:
            targets: List of targets to fetch molecules for
        
        Returns:
            List of unique Molecule objects
        
        Validates: Requirements 9.7, 9.8, 3.4
        """
        all_molecules: Dict[str, Molecule] = {}  # ChEMBL ID -> Molecule
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def fetch_with_limit(target: Target):
            async with semaphore:
                try:
                    molecules = await self.chembl_client.get_bioactive_molecules(
                        target.uniprot_id
                    )
                    return target.uniprot_id, molecules
                except Exception as e:
                    logger.warning(f"Failed to fetch molecules for {target.uniprot_id}: {e}")
                    return target.uniprot_id, []
        
        # Fetch all molecules concurrently
        tasks = [fetch_with_limit(target) for target in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Deduplicate and associate with targets
        for result in results:
            if result and not isinstance(result, Exception):
                target_id, molecules = result
                for molecule in molecules:
                    if molecule.chembl_id in all_molecules:
                        # Add this target to existing molecule
                        if target_id not in all_molecules[molecule.chembl_id].target_ids:
                            all_molecules[molecule.chembl_id].target_ids.append(target_id)
                    else:
                        # New molecule
                        molecule.target_ids = [target_id]
                        all_molecules[molecule.chembl_id] = molecule
        
        return list(all_molecules.values())
    
    async def _analyze_molecules(
        self,
        molecules: List[Molecule]
    ) -> List[Dict]:
        """Analyze molecules for properties and toxicity.
        
        Args:
            molecules: List of molecules to analyze
        
        Returns:
            List of dicts with molecule, properties, and toxicity
        """
        analyzed = []
        
        for molecule in molecules:
            try:
                # Parse SMILES
                mol = self.rdkit_analyzer.parse_smiles(molecule.smiles)
                if not mol:
                    logger.warning(f"Invalid SMILES for {molecule.chembl_id}")
                    continue
                
                # Calculate properties
                properties = self.rdkit_analyzer.calculate_properties(mol)
                
                # Assess toxicity
                toxicity = self.rdkit_analyzer.assess_toxicity(mol)
                
                # Generate 2D structure
                structure_svg = self.rdkit_analyzer.generate_2d_structure(mol)
                
                analyzed.append({
                    'molecule': molecule,
                    'properties': properties,
                    'toxicity': toxicity,
                    'structure_svg': structure_svg
                })
                
            except Exception as e:
                logger.warning(f"Failed to analyze {molecule.chembl_id}: {e}")
                # Graceful degradation - skip this molecule
                continue
        
        if len(analyzed) < len(molecules):
            failed = len(molecules) - len(analyzed)
            self.warnings.append(f"{failed} molecules failed analysis")
        
        return analyzed
    
    async def _create_candidates(
        self,
        analyzed_molecules: List[Dict],
        targets: List[Target],
        structures: Dict[str, ProteinStructure]
    ) -> List[DrugCandidate]:
        """Create drug candidates with scores.
        
        Args:
            analyzed_molecules: List of analyzed molecule dicts
            targets: List of targets
            structures: Dict of protein structures
        
        Returns:
            List of DrugCandidate objects with scores
        """
        candidates = []
        target_map = {t.uniprot_id: t for t in targets}
        
        for analysis in analyzed_molecules:
            molecule = analysis['molecule']
            properties = analysis['properties']
            toxicity = analysis['toxicity']
            structure_svg = analysis['structure_svg']
            
            # Create candidate for each target this molecule is active against
            for target_id in molecule.target_ids:
                if target_id not in target_map:
                    continue
                
                target = target_map[target_id]
                
                try:
                    # Calculate binding affinity score
                    binding_score = self.scoring_engine.normalize_binding_affinity(
                        molecule.pchembl_value
                    )
                    
                    # Get measurement confidence
                    binding_confidence = self.scoring_engine.get_measurement_confidence(
                        molecule.activity_type
                    )
                    
                    # Calculate composite score
                    # Note: novelty_score is set to 0.5 as a placeholder
                    # In a real system, this would be calculated based on
                    # similarity to known drugs
                    novelty_score = 0.5
                    
                    composite_score = self.scoring_engine.calculate_composite_score(
                        binding_score,
                        properties.drug_likeness_score,
                        toxicity.toxicity_score,
                        novelty_score
                    )
                    
                    # Create candidate
                    candidate = DrugCandidate(
                        molecule=molecule,
                        target=target,
                        properties=properties,
                        toxicity=toxicity,
                        binding_affinity_score=binding_score,
                        binding_confidence=binding_confidence,
                        composite_score=composite_score,
                        rank=1,  # Temporary rank, will be set during ranking
                        ai_analysis=None,  # Will be added later
                        structure_2d_svg=structure_svg
                    )
                    
                    candidates.append(candidate)
                    
                except Exception as e:
                    logger.warning(f"Failed to create candidate for {molecule.chembl_id}: {e}")
                    continue
        
        return candidates
    
    async def _add_ai_analysis(self, candidates: List[DrugCandidate]):
        """Add AI analysis to top candidates.
        
        Args:
            candidates: List of ranked candidates (modified in-place)
        
        Validates: Requirements 7.11, 7.10
        """
        try:
            await self.biomistral_engine.analyze_candidates(
                candidates,
                max_candidates=20
            )
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
            self.warnings.append("AI analysis unavailable")
            # Graceful degradation - continue without AI analysis
    
    def _create_empty_result(
        self,
        disease_name: str,
        start_time: datetime,
        targets_found: int = 0
    ) -> DiscoveryResult:
        """Create an empty result for failed queries.
        
        Args:
            disease_name: Original query
            start_time: Query start time
            targets_found: Number of targets found (default: 0)
        
        Returns:
            Empty DiscoveryResult with warnings
        """
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        # Ensure minimum processing time to satisfy validation (gt=0.0)
        processing_time = max(processing_time, 0.001)
        
        return DiscoveryResult(
            query=disease_name,
            timestamp=start_time,
            processing_time_seconds=processing_time,
            candidates=[],
            targets_found=targets_found,
            molecules_analyzed=0,
            api_version="0.1.0",
            warnings=self.warnings
        )
    
    async def close(self):
        """Close all clients and engines."""
        await self.biomistral_engine.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
