"""Test script to verify AI analysis is working."""
import asyncio
from app.biomistral_engine import BioMistralEngine
from app.models import Molecule, Target, MolecularProperties, ToxicityAssessment

async def test_ai_analysis():
    """Test AI analysis with sample data."""
    engine = BioMistralEngine()
    
    # Create sample data
    molecule = Molecule(
        chembl_id="CHEMBL25",
        name="Aspirin",
        smiles="CC(=O)Oc1ccccc1C(=O)O",
        canonical_smiles="CC(=O)Oc1ccccc1C(=O)O",
        pchembl_value=7.5,
        activity_type="IC50",
        target_ids=["P23219"]
    )
    
    target = Target(
        uniprot_id="P23219",
        gene_symbol="PTGS1",
        protein_name="Prostaglandin G/H synthase 1",
        confidence_score=0.95,
        disease_association="Inflammation and pain pathways"
    )
    
    properties = MolecularProperties(
        molecular_weight=180.16,
        logp=1.19,
        hbd=1,
        hba=4,
        tpsa=63.6,
        rotatable_bonds=3,
        aromatic_rings=1,
        lipinski_violations=0,
        drug_likeness_score=0.72
    )
    
    toxicity = ToxicityAssessment(
        toxicity_score=0.25,
        risk_level="low",
        detected_toxicophores=[]
    )
    
    print("Testing AI analysis...")
    print(f"Ollama URL: {engine.base_url}")
    print(f"Model: {engine.model}")
    print(f"Timeout: {engine.timeout}s")
    print()
    
    try:
        analysis = await engine.analyze_candidate(
            molecule, target, properties, toxicity
        )
        
        if analysis:
            print("✓ AI Analysis generated successfully!")
            print()
            print("Analysis:")
            print("-" * 80)
            print(analysis)
            print("-" * 80)
        else:
            print("✗ AI Analysis returned None (timeout or error)")
            
    except Exception as e:
        print(f"✗ Error during analysis: {e}")
    finally:
        await engine.close()

if __name__ == "__main__":
    asyncio.run(test_ai_analysis())
