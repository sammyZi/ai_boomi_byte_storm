"""Unit tests for scoring engine.

Tests specific examples and edge cases for the scoring and ranking engine.

Feature: drug-discovery-platform
"""

import pytest
from app.scoring_engine import ScoringEngine
from app.models import DrugCandidate, Molecule, Target, MolecularProperties, ToxicityAssessment


class TestBindingAffinityNormalization:
    """Unit tests for binding affinity normalization."""
    
    def test_normalize_below_minimum(self):
        """Test pChEMBL values below 4 map to 0."""
        assert ScoringEngine.normalize_binding_affinity(0.0) == 0.0
        assert ScoringEngine.normalize_binding_affinity(2.5) == 0.0
        assert ScoringEngine.normalize_binding_affinity(3.9) == 0.0
    
    def test_normalize_above_maximum(self):
        """Test pChEMBL values above 10 map to 1."""
        assert ScoringEngine.normalize_binding_affinity(10.1) == 1.0
        assert ScoringEngine.normalize_binding_affinity(12.0) == 1.0
        assert ScoringEngine.normalize_binding_affinity(15.0) == 1.0
    
    def test_normalize_at_boundaries(self):
        """Test pChEMBL values at boundaries."""
        assert ScoringEngine.normalize_binding_affinity(4.0) == 0.0
        assert ScoringEngine.normalize_binding_affinity(10.0) == 1.0
    
    def test_normalize_midpoint(self):
        """Test pChEMBL value at midpoint (7.0)."""
        score = ScoringEngine.normalize_binding_affinity(7.0)
        expected = (7.0 - 4.0) / (10.0 - 4.0)  # 0.5
        assert abs(score - expected) < 0.001
        assert abs(score - 0.5) < 0.001
    
    def test_normalize_specific_values(self):
        """Test specific pChEMBL values."""
        # pChEMBL 6.0 (IC50 = 1 µM)
        score = ScoringEngine.normalize_binding_affinity(6.0)
        expected = (6.0 - 4.0) / 6.0  # 0.333...
        assert abs(score - expected) < 0.001
        
        # pChEMBL 8.0 (IC50 = 10 nM)
        score = ScoringEngine.normalize_binding_affinity(8.0)
        expected = (8.0 - 4.0) / 6.0  # 0.666...
        assert abs(score - expected) < 0.001


class TestMaximumActivitySelection:
    """Unit tests for maximum activity selection."""
    
    def test_select_single_activity(self):
        """Test selection with single activity."""
        activities = [(6.5, 'IC50')]
        max_pchembl, activity_type = ScoringEngine.select_maximum_activity(activities)
        assert max_pchembl == 6.5
        assert activity_type == 'IC50'
    
    def test_select_from_multiple_activities(self):
        """Test selection from multiple activities."""
        activities = [
            (6.0, 'IC50'),
            (8.5, 'Ki'),
            (7.2, 'Kd'),
            (5.5, 'EC50')
        ]
        max_pchembl, activity_type = ScoringEngine.select_maximum_activity(activities)
        assert max_pchembl == 8.5
        assert activity_type == 'Ki'
    
    def test_select_with_duplicate_max(self):
        """Test selection when multiple activities have same max value."""
        activities = [
            (7.0, 'IC50'),
            (8.0, 'Ki'),
            (8.0, 'Kd'),
            (6.0, 'EC50')
        ]
        max_pchembl, activity_type = ScoringEngine.select_maximum_activity(activities)
        assert max_pchembl == 8.0
        assert activity_type in ['Ki', 'Kd']  # Either is valid
    
    def test_empty_activities_raises_error(self):
        """Test that empty activities list raises error."""
        with pytest.raises(ValueError, match="Activities list cannot be empty"):
            ScoringEngine.select_maximum_activity([])


class TestMeasurementConfidence:
    """Unit tests for measurement type confidence mapping."""
    
    def test_ki_confidence(self):
        """Test Ki measurement confidence."""
        assert ScoringEngine.get_measurement_confidence('Ki') == 0.9
    
    def test_kd_confidence(self):
        """Test Kd measurement confidence."""
        assert ScoringEngine.get_measurement_confidence('Kd') == 0.9
    
    def test_ic50_confidence(self):
        """Test IC50 measurement confidence."""
        assert ScoringEngine.get_measurement_confidence('IC50') == 0.8
    
    def test_ec50_confidence(self):
        """Test EC50 measurement confidence."""
        assert ScoringEngine.get_measurement_confidence('EC50') == 0.8
    
    def test_other_measurement_confidence(self):
        """Test other measurement types default to 0.6."""
        assert ScoringEngine.get_measurement_confidence('GI50') == 0.6
        assert ScoringEngine.get_measurement_confidence('AC50') == 0.6
        assert ScoringEngine.get_measurement_confidence('Potency') == 0.6
        assert ScoringEngine.get_measurement_confidence('Unknown') == 0.6


class TestCompositeScoreCalculation:
    """Unit tests for composite score calculation."""
    
    def test_all_zeros(self):
        """Test composite score with all zeros."""
        score = ScoringEngine.calculate_composite_score(0.0, 0.0, 0.0, 0.0)
        # With toxicity=0, safety component = 0.20 * (1-0) = 0.20
        expected = 0.0 + 0.0 + 0.20 + 0.0
        assert abs(score - expected) < 0.001
        assert abs(score - 0.20) < 0.001
    
    def test_all_ones(self):
        """Test composite score with all ones."""
        score = ScoringEngine.calculate_composite_score(1.0, 1.0, 1.0, 1.0)
        # With toxicity=1, safety component = 0.20 * (1-1) = 0.0
        expected = 0.40 + 0.30 + 0.0 + 0.10
        assert abs(score - expected) < 0.001
        assert abs(score - 0.80) < 0.001
    
    def test_perfect_candidate(self):
        """Test perfect candidate (high binding, drug-like, safe, novel)."""
        score = ScoringEngine.calculate_composite_score(1.0, 1.0, 0.0, 1.0)
        # binding=1.0, drug_likeness=1.0, toxicity=0.0, novelty=1.0
        expected = 0.40 * 1.0 + 0.30 * 1.0 + 0.20 * 1.0 + 0.10 * 1.0
        assert abs(score - expected) < 0.001
        assert abs(score - 1.0) < 0.001
    
    def test_worst_candidate(self):
        """Test worst candidate (low binding, not drug-like, toxic, not novel)."""
        score = ScoringEngine.calculate_composite_score(0.0, 0.0, 1.0, 0.0)
        # binding=0.0, drug_likeness=0.0, toxicity=1.0, novelty=0.0
        expected = 0.40 * 0.0 + 0.30 * 0.0 + 0.20 * 0.0 + 0.10 * 0.0
        assert abs(score - expected) < 0.001
        assert abs(score - 0.0) < 0.001
    
    def test_typical_candidate(self):
        """Test typical candidate with moderate scores."""
        score = ScoringEngine.calculate_composite_score(0.7, 0.8, 0.2, 0.5)
        # binding=0.7, drug_likeness=0.8, toxicity=0.2, novelty=0.5
        expected = 0.40 * 0.7 + 0.30 * 0.8 + 0.20 * 0.8 + 0.10 * 0.5
        assert abs(score - expected) < 0.001
    
    def test_invalid_binding_raises_error(self):
        """Test that invalid binding affinity raises error."""
        with pytest.raises(ValueError, match="Binding affinity must be in"):
            ScoringEngine.calculate_composite_score(-0.1, 0.5, 0.5, 0.5)
        with pytest.raises(ValueError, match="Binding affinity must be in"):
            ScoringEngine.calculate_composite_score(1.1, 0.5, 0.5, 0.5)
    
    def test_invalid_drug_likeness_raises_error(self):
        """Test that invalid drug likeness raises error."""
        with pytest.raises(ValueError, match="Drug likeness must be in"):
            ScoringEngine.calculate_composite_score(0.5, -0.1, 0.5, 0.5)
        with pytest.raises(ValueError, match="Drug likeness must be in"):
            ScoringEngine.calculate_composite_score(0.5, 1.1, 0.5, 0.5)
    
    def test_invalid_toxicity_raises_error(self):
        """Test that invalid toxicity score raises error."""
        with pytest.raises(ValueError, match="Toxicity score must be in"):
            ScoringEngine.calculate_composite_score(0.5, 0.5, -0.1, 0.5)
        with pytest.raises(ValueError, match="Toxicity score must be in"):
            ScoringEngine.calculate_composite_score(0.5, 0.5, 1.1, 0.5)
    
    def test_invalid_novelty_raises_error(self):
        """Test that invalid novelty score raises error."""
        with pytest.raises(ValueError, match="Novelty score must be in"):
            ScoringEngine.calculate_composite_score(0.5, 0.5, 0.5, -0.1)
        with pytest.raises(ValueError, match="Novelty score must be in"):
            ScoringEngine.calculate_composite_score(0.5, 0.5, 0.5, 1.1)


class TestCandidateRanking:
    """Unit tests for candidate ranking."""
    
    def _create_candidate(self, chembl_id: str, composite_score: float) -> DrugCandidate:
        """Helper to create a drug candidate with specific score."""
        return DrugCandidate(
            molecule=Molecule(
                chembl_id=chembl_id,
                name=f"Molecule {chembl_id}",
                smiles="CCO",
                canonical_smiles="CCO",
                pchembl_value=6.0,
                activity_type="IC50",
                target_ids=["P12345"]
            ),
            target=Target(
                uniprot_id="P12345",
                gene_symbol="TEST",
                protein_name="Test Protein",
                confidence_score=0.8,
                disease_association="Test disease"
            ),
            properties=MolecularProperties(
                molecular_weight=200.0,
                logp=2.0,
                hbd=2,
                hba=3,
                tpsa=40.0,
                rotatable_bonds=2,
                aromatic_rings=1,
                lipinski_violations=0,
                drug_likeness_score=1.0
            ),
            toxicity=ToxicityAssessment(
                toxicity_score=0.0,
                risk_level="low",
                detected_toxicophores=[],
                warnings=[]
            ),
            binding_affinity_score=0.5,
            binding_confidence=0.8,
            composite_score=composite_score,
            rank=1,
            ai_analysis=None,
            structure_2d_svg="<svg></svg>"
        )
    
    def test_rank_empty_list(self):
        """Test ranking empty list returns empty list."""
        ranked = ScoringEngine.rank_candidates([])
        assert ranked == []
    
    def test_rank_single_candidate(self):
        """Test ranking single candidate."""
        candidates = [self._create_candidate("CHEMBL001", 0.75)]
        ranked = ScoringEngine.rank_candidates(candidates)
        assert len(ranked) == 1
        assert ranked[0].rank == 1
    
    def test_rank_multiple_candidates(self):
        """Test ranking multiple candidates in descending order."""
        candidates = [
            self._create_candidate("CHEMBL001", 0.50),
            self._create_candidate("CHEMBL002", 0.85),
            self._create_candidate("CHEMBL003", 0.65),
            self._create_candidate("CHEMBL004", 0.90),
            self._create_candidate("CHEMBL005", 0.40)
        ]
        
        ranked = ScoringEngine.rank_candidates(candidates)
        
        # Check correct order
        assert ranked[0].molecule.chembl_id == "CHEMBL004"  # 0.90
        assert ranked[1].molecule.chembl_id == "CHEMBL002"  # 0.85
        assert ranked[2].molecule.chembl_id == "CHEMBL003"  # 0.65
        assert ranked[3].molecule.chembl_id == "CHEMBL001"  # 0.50
        assert ranked[4].molecule.chembl_id == "CHEMBL005"  # 0.40
        
        # Check ranks
        for i, candidate in enumerate(ranked, start=1):
            assert candidate.rank == i
    
    def test_rank_with_equal_scores(self):
        """Test ranking with equal composite scores."""
        candidates = [
            self._create_candidate("CHEMBL001", 0.75),
            self._create_candidate("CHEMBL002", 0.75),
            self._create_candidate("CHEMBL003", 0.80)
        ]
        
        ranked = ScoringEngine.rank_candidates(candidates)
        
        # Highest score should be first
        assert ranked[0].molecule.chembl_id == "CHEMBL003"
        assert ranked[0].rank == 1
        
        # Equal scores should be ranked 2 and 3
        assert ranked[1].rank == 2
        assert ranked[2].rank == 3
        assert ranked[1].composite_score == ranked[2].composite_score == 0.75
