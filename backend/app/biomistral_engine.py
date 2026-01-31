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
            
            # Validate the response is a proper analysis
            if not self._is_valid_analysis(response, molecule.name):
                return None
            
            return response
            
        except asyncio.TimeoutError:
            # Graceful degradation on timeout
            return None
        except Exception:
            # Graceful degradation on any error
            return None
    
    def _is_valid_analysis(self, response: str, molecule_name: str) -> bool:
        """Validate that the AI response is a proper drug candidate analysis.
        
        Detects generic/unhelpful responses like greetings or irrelevant text.
        
        Args:
            response: The AI-generated response text
            molecule_name: Name of the molecule being analyzed
        
        Returns:
            True if response appears to be a valid analysis, False otherwise
        """
        if not response or len(response.strip()) < 50:
            return False
        
        response_lower = response.lower()
        
        # List of phrases that indicate a generic/unhelpful response
        invalid_phrases = [
            "good evening",
            "good morning", 
            "good afternoon",
            "how can i assist",
            "how can i help",
            "hello",
            "hi there",
            "what can i do for you",
            "i'm here to help",
            "i am here to help",
            "please provide",
            "could you provide",
            "i need more information",
            "can you tell me more",
            "what would you like",
            "i don't have enough information",
            "i cannot provide",
            "as an ai",
            "as a language model",
        ]
        
        for phrase in invalid_phrases:
            if phrase in response_lower:
                return False
        
        # Check that the response contains some relevant content
        # It should mention at least one of these drug-related terms
        relevant_terms = [
            "binding", "affinity", "molecule", "drug", "target", "protein",
            "lipinski", "toxicity", "risk", "molecular", "weight", "logp",
            "therapeutic", "treatment", "efficacy", "safety", "pharmacokinetic",
            "bioavailability", "solubility", "metabolism", molecule_name.lower()
        ]
        
        has_relevant_content = any(term in response_lower for term in relevant_terms)
        
        return has_relevant_content
    
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
        prompt = f"""Analyze the following drug candidate:

Molecule: {molecule.name} ({molecule.chembl_id})
Target: {target.protein_name} ({target.gene_symbol})
Disease: {target.disease_association}

Key Data:
- Binding Affinity (pChEMBL): {molecule.pchembl_value:.2f}
- Molecular Weight: {properties.molecular_weight:.2f} Da
- LogP: {properties.logp:.2f}
- Drug-Likeness (QED): {properties.drug_likeness_score:.2f}
- Lipinski Violations: {properties.lipinski_violations}
- Toxicity Risk: {toxicity.risk_level}
- Toxicity Score: {toxicity.toxicity_score:.2f}

Analysis:"""
        
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
            "system": "You are an expert pharmaceutical scientist providing drug candidate analysis. Always provide direct, detailed analysis based on the data given. Never ask for more information.",
            "options": {
                "temperature": 0.7,  # More creative but still focused
                "num_predict": 600,  # Max tokens for detailed analysis
                "top_p": 0.9
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
