"""BioMistral AI engine for drug candidate analysis.

This module provides AI-powered analysis of drug candidates using the
BioMistral-7B language model via Ollama. It generates detailed biomedical
analysis including molecular property interpretation, binding affinity
assessment, safety evaluation, and mechanism of action.
"""

import asyncio
import httpx
from typing import Optional
from config.settings import settings
from app.models import (
    Molecule,
    Target,
    MolecularProperties,
    ToxicityAssessment,
    DrugCandidate
)


class BioMistralEngine:
    """AI engine for generating biomedical analysis of drug candidates.
    
    Uses BioMistral-7B via Ollama to provide detailed analysis of molecular
    properties, binding affinity, drug-likeness, safety profiles, and
    mechanisms of action.
    """
    
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: int = None
    ):
        """Initialize the BioMistral engine.
        
        Args:
            base_url: Ollama API base URL (defaults to settings)
            model: Model name (defaults to settings)
            timeout: Timeout in seconds per candidate (defaults to settings)
        """
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    async def analyze_candidate(
        self,
        molecule: Molecule,
        target: Target,
        properties: MolecularProperties,
        toxicity: ToxicityAssessment
    ) -> Optional[str]:
        """Generate detailed AI analysis for a drug candidate.
        
        Analyzes molecular properties, binding affinity, drug-likeness,
        safety profile, and mechanism of action. Returns None if analysis
        fails (graceful degradation).
        
        Args:
            molecule: Molecule information with SMILES and activity data
            target: Target protein information
            properties: Calculated molecular properties
            toxicity: Toxicity assessment results
        
        Returns:
            AI-generated analysis text, or None if analysis fails
        """
        try:
            # Generate structured prompt
            prompt = self._generate_prompt(molecule, target, properties, toxicity)
            
            # Call Ollama API with timeout
            response = await asyncio.wait_for(
                self._call_ollama(prompt),
                timeout=self.timeout
            )
            
            return response
            
        except asyncio.TimeoutError:
            # Graceful degradation on timeout
            return None
        except Exception:
            # Graceful degradation on any error
            return None
    
    def _generate_prompt(
        self,
        molecule: Molecule,
        target: Target,
        properties: MolecularProperties,
        toxicity: ToxicityAssessment
    ) -> str:
        """Generate structured prompt for BioMistral analysis.
        
        Creates a detailed prompt with molecular data, scores, and context
        to guide the AI analysis.
        
        Args:
            molecule: Molecule information
            target: Target protein information
            properties: Molecular properties
            toxicity: Toxicity assessment
        
        Returns:
            Formatted prompt string
        """
        prompt = f"""Analyze this drug candidate for {target.disease_association}:

MOLECULE INFORMATION:
- Name: {molecule.name}
- ChEMBL ID: {molecule.chembl_id}
- SMILES: {molecule.smiles}

TARGET INFORMATION:
- Protein: {target.protein_name} ({target.gene_symbol})
- UniProt ID: {target.uniprot_id}
- Disease Association: {target.disease_association}
- Confidence: {target.confidence_score:.2f}

BINDING AFFINITY:
- pChEMBL Value: {molecule.pchembl_value:.2f}
- Activity Type: {molecule.activity_type}

MOLECULAR PROPERTIES:
- Molecular Weight: {properties.molecular_weight:.2f} Da
- LogP: {properties.logp:.2f}
- H-Bond Donors: {properties.hbd}
- H-Bond Acceptors: {properties.hba}
- TPSA: {properties.tpsa:.2f} Ų
- Rotatable Bonds: {properties.rotatable_bonds}
- Aromatic Rings: {properties.aromatic_rings}

DRUG-LIKENESS:
- Lipinski Violations: {properties.lipinski_violations}
- Drug-Likeness Score: {properties.drug_likeness_score:.2f}

TOXICITY ASSESSMENT:
- Toxicity Score: {toxicity.toxicity_score:.2f}
- Risk Level: {toxicity.risk_level}
- Detected Toxicophores: {', '.join(toxicity.detected_toxicophores) if toxicity.detected_toxicophores else 'None'}

Provide a concise analysis covering:
1. Molecular properties and their clinical implications
2. Binding affinity and therapeutic potential
3. Drug-likeness assessment and bioavailability
4. Safety profile and toxicity concerns
5. Mechanism of action for target modulation
6. Comparison to existing approved drugs if applicable

Keep the analysis under 500 words and focus on actionable insights."""
        
        return prompt
    
    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API to generate analysis.
        
        Args:
            prompt: Formatted prompt for analysis
        
        Returns:
            Generated analysis text
        
        Raises:
            Exception: If API call fails
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Focused, deterministic output
                "num_predict": 500   # Max tokens
            }
        }
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "")
    
    async def analyze_candidates(
        self,
        candidates: list[DrugCandidate],
        max_candidates: int = 20
    ) -> list[DrugCandidate]:
        """Analyze multiple candidates with AI, limiting to top N.
        
        Generates AI analysis for the top-ranked candidates only to
        optimize performance. Updates candidates in-place with analysis.
        
        Args:
            candidates: List of drug candidates (should be pre-ranked)
            max_candidates: Maximum number of candidates to analyze (default: 20)
        
        Returns:
            List of candidates with AI analysis added to top N
        """
        # Limit analysis to top N candidates
        candidates_to_analyze = candidates[:max_candidates]
        
        # Analyze each candidate
        for candidate in candidates_to_analyze:
            analysis = await self.analyze_candidate(
                candidate.molecule,
                candidate.target,
                candidate.properties,
                candidate.toxicity
            )
            candidate.ai_analysis = analysis
        
        return candidates
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
