"""RDKit-based molecular analysis module.

This module provides cheminformatics analysis using RDKit, including:
- SMILES parsing and validation
- Molecular property calculations
- Drug-likeness assessment (Lipinski's Rule of Five)
- Toxicity screening via toxicophore detection
- 2D structure generation
"""

from typing import Optional, List, Tuple
from dataclasses import dataclass
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, AllChem, Draw
from rdkit.Chem.Draw import rdMolDraw2D
from app.models import MolecularProperties, ToxicityAssessment


class RDKitAnalyzer:
    """Cheminformatics analyzer using RDKit.
    
    Provides methods for parsing SMILES, calculating molecular properties,
    assessing drug-likeness, and screening for toxicophores.
    """
    
    # SMARTS patterns for toxicophore detection
    TOXICOPHORE_PATTERNS = {
        'azide': '[N-]=[N+]=[N-]',
        'nitro_group': '[N+](=O)[O-]',
        'acyl_chloride': 'C(=O)Cl',
        'epoxide': 'C1OC1',
        'peroxide': 'OO',
        'hydrazine': 'NN',
        'sulfonyl_chloride': 'S(=O)(=O)Cl',
        'isocyanate': 'N=C=O',
        'diazo_compound': 'C=[N+]=[N-]',
        'nitroso_group': 'N=O'
    }
    
    def parse_smiles(self, smiles: str) -> Optional[Chem.Mol]:
        """Parse and validate a SMILES string.
        
        Args:
            smiles: SMILES notation string
            
        Returns:
            RDKit Mol object if valid, None if invalid
            
        Validates:
            - SMILES syntax is correct
            - Molecule contains at least 1 atom
            - Molecule does not exceed 200 atoms (reasonable drug size limit)
        """
        if not smiles or not smiles.strip():
            return None
        
        try:
            mol = Chem.MolFromSmiles(smiles)
            
            if mol is None:
                return None
            
            # Validate atom count
            atom_count = mol.GetNumAtoms()
            if atom_count < 1 or atom_count > 200:
                return None
            
            return mol
            
        except Exception:
            return None
    
    def get_canonical_smiles(self, mol: Chem.Mol) -> str:
        """Generate canonical SMILES representation.
        
        Args:
            mol: RDKit Mol object
            
        Returns:
            Canonical SMILES string
        """
        return Chem.MolToSmiles(mol)
    
    def calculate_properties(self, mol: Chem.Mol) -> MolecularProperties:
        """Calculate molecular properties for drug-likeness assessment.
        
        Args:
            mol: RDKit Mol object
            
        Returns:
            MolecularProperties object with calculated values
            
        Calculates:
            - Molecular weight
            - LogP (lipophilicity)
            - Hydrogen bond donors (HBD)
            - Hydrogen bond acceptors (HBA)
            - Topological polar surface area (TPSA)
            - Rotatable bonds
            - Aromatic rings
            - Lipinski violations
            - Drug-likeness score
        """
        # Calculate basic properties
        mw = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd = Descriptors.NumHDonors(mol)
        hba = Descriptors.NumHAcceptors(mol)
        tpsa = Descriptors.TPSA(mol)
        rotatable_bonds = Descriptors.NumRotatableBonds(mol)
        aromatic_rings = Descriptors.NumAromaticRings(mol)
        
        # Evaluate Lipinski's Rule of Five
        violations = 0
        if mw > 500:
            violations += 1
        if logp > 5:
            violations += 1
        if hbd > 5:
            violations += 1
        if hba > 10:
            violations += 1
        
        # Calculate drug-likeness score
        drug_likeness_score = 1.0 - (0.25 * violations)
        drug_likeness_score = max(0.0, min(1.0, drug_likeness_score))
        
        return MolecularProperties(
            molecular_weight=mw,
            logp=logp,
            hbd=hbd,
            hba=hba,
            tpsa=tpsa,
            rotatable_bonds=rotatable_bonds,
            aromatic_rings=aromatic_rings,
            lipinski_violations=violations,
            drug_likeness_score=drug_likeness_score
        )
    
    def assess_toxicity(self, mol: Chem.Mol) -> ToxicityAssessment:
        """Screen molecule for toxic substructures (toxicophores).
        
        Args:
            mol: RDKit Mol object
            
        Returns:
            ToxicityAssessment with score, risk level, and detected toxicophores
            
        Screens for 10 toxicophore patterns using SMARTS matching.
        Calculates toxicity score as min(0.15 × count, 1.0).
        Classifies risk as: low (0-0.3), medium (0.3-0.6), high (>0.6).
        """
        detected_toxicophores = []
        warnings = []
        
        # Perform SMARTS pattern matching for each toxicophore
        for name, smarts in self.TOXICOPHORE_PATTERNS.items():
            pattern = Chem.MolFromSmarts(smarts)
            if pattern and mol.HasSubstructMatch(pattern):
                detected_toxicophores.append(name)
                warnings.append(f"Contains {name.replace('_', ' ')}")
        
        # Calculate toxicity score
        toxicity_score = min(0.15 * len(detected_toxicophores), 1.0)
        
        # Classify risk level
        if toxicity_score < 0.3:
            risk_level = "low"
        elif toxicity_score < 0.6:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        return ToxicityAssessment(
            toxicity_score=toxicity_score,
            risk_level=risk_level,
            detected_toxicophores=detected_toxicophores,
            warnings=warnings
        )
    
    def generate_2d_structure(self, mol: Chem.Mol, width: int = 300, height: int = 300) -> str:
        """Generate 2D SVG representation of molecule.
        
        Args:
            mol: RDKit Mol object
            width: Image width in pixels
            height: Image height in pixels
            
        Returns:
            SVG string representation of the molecule
        """
        # Generate 2D coordinates if not present
        AllChem.Compute2DCoords(mol)
        
        # Create drawer
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        
        return drawer.GetDrawingText()
