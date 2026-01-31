"""Scoring and ranking engine for drug candidates.

This module implements the scoring logic for drug discovery, including:
- Binding affinity normalization
- Maximum activity selection
- Measurement type confidence mapping
- Composite score calculation
- Candidate ranking
"""

from typing import List, Dict, Tuple
from app.models import Molecule, Target, MolecularProperties, ToxicityAssessment, DrugCandidate


class ScoringEngine:
    """Engine for scoring and ranking drug candidates.
    
    Implements the complete scoring pipeline from raw bioactivity data
    to ranked drug candidates with composite scores.
    """
    
    # Confidence weights by measurement type
    CONFIDENCE_WEIGHTS = {
        'Ki': 0.9,
        'Kd': 0.9,
        'IC50': 0.8,
        'EC50': 0.8,
    }
    DEFAULT_CONFIDENCE = 0.6
    
    # Composite score weights
    BINDING_WEIGHT = 0.40
    DRUG_LIKENESS_WEIGHT = 0.30
    SAFETY_WEIGHT = 0.20
    NOVELTY_WEIGHT = 0.10
    
    @staticmethod
    def normalize_binding_affinity(pchembl_value: float) -> float:
        """Normalize pChEMBL value to 0-1 scale.
        
        Formula: (pChEMBL - 4) / (10 - 4), clamped to [0, 1]
        
        Args:
            pchembl_value: pChEMBL value (typically 4-10 range)
            
        Returns:
            Normalized binding affinity score (0-1)
            
        Validates: Requirements 4.1, 4.2, 4.3, 4.4
        """
        # Clamp values below 4 to 0
        if pchembl_value < 4.0:
            return 0.0
        
        # Clamp values above 10 to 1
        if pchembl_value > 10.0:
            return 1.0
        
        # Normalize values in range [4, 10] to [0, 1]
        normalized = (pchembl_value - 4.0) / (10.0 - 4.0)
        return normalized
    
    @staticmethod
    def select_maximum_activity(activities: List[Tuple[float, str]]) -> Tuple[float, str]:
        """Select the highest pChEMBL value from multiple measurements.
        
        When multiple activity measurements exist for the same molecule-target pair,
        use the highest pChEMBL value.
        
        Args:
            activities: List of (pchembl_value, activity_type) tuples
            
        Returns:
            Tuple of (max_pchembl, activity_type) for the highest activity
            
        Validates: Requirements 4.5
        """
        if not activities:
            raise ValueError("Activities list cannot be empty")
        
        # Find the activity with maximum pChEMBL value
        max_activity = max(activities, key=lambda x: x[0])
        return max_activity
    
    @staticmethod
    def get_measurement_confidence(activity_type: str) -> float:
        """Map measurement type to confidence score.
        
        Confidence scores by measurement type:
        - Ki/Kd: 0.9 (direct binding measurements)
        - IC50/EC50: 0.8 (functional assays)
        - Other: 0.6 (less reliable measurements)
        
        Args:
            activity_type: Type of activity measurement (Ki, Kd, IC50, EC50, etc.)
            
        Returns:
            Confidence score (0.6-0.9)
            
        Validates: Requirements 4.6
        """
        return ScoringEngine.CONFIDENCE_WEIGHTS.get(
            activity_type,
            ScoringEngine.DEFAULT_CONFIDENCE
        )
    
    @staticmethod
    def calculate_composite_score(
        binding_affinity: float,
        drug_likeness: float,
        toxicity_score: float,
        novelty_score: float = 0.5
    ) -> float:
        """Calculate composite ranking score.
        
        Formula: 0.40×binding + 0.30×drug_likeness + 0.20×(1-toxicity) + 0.10×novelty
        
        Args:
            binding_affinity: Normalized binding affinity score (0-1)
            drug_likeness: Drug-likeness score (0-1)
            toxicity_score: Toxicity score (0-1, higher is worse)
            novelty_score: Novelty score (0-1), defaults to 0.5
            
        Returns:
            Composite score (0-1)
            
        Validates: Requirements 7.8
        """
        # Validate input ranges
        if not (0.0 <= binding_affinity <= 1.0):
            raise ValueError(f"Binding affinity must be in [0, 1], got {binding_affinity}")
        if not (0.0 <= drug_likeness <= 1.0):
            raise ValueError(f"Drug likeness must be in [0, 1], got {drug_likeness}")
        if not (0.0 <= toxicity_score <= 1.0):
            raise ValueError(f"Toxicity score must be in [0, 1], got {toxicity_score}")
        if not (0.0 <= novelty_score <= 1.0):
            raise ValueError(f"Novelty score must be in [0, 1], got {novelty_score}")
        
        # Calculate weighted composite score
        composite = (
            ScoringEngine.BINDING_WEIGHT * binding_affinity +
            ScoringEngine.DRUG_LIKENESS_WEIGHT * drug_likeness +
            ScoringEngine.SAFETY_WEIGHT * (1.0 - toxicity_score) +
            ScoringEngine.NOVELTY_WEIGHT * novelty_score
        )
        
        return composite
    
    @staticmethod
    def rank_candidates(candidates: List[DrugCandidate]) -> List[DrugCandidate]:
        """Rank drug candidates by composite score in descending order.
        
        Sorts candidates by composite_score (highest first) and assigns
        rank positions (1-based indexing).
        
        Args:
            candidates: List of drug candidates to rank
            
        Returns:
            Sorted list of candidates with updated rank field
            
        Validates: Requirements 7.9
        """
        if not candidates:
            return []
        
        # Sort by composite score descending
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.composite_score,
            reverse=True
        )
        
        # Assign ranks (1-based)
        for i, candidate in enumerate(sorted_candidates, start=1):
            candidate.rank = i
        
        return sorted_candidates
