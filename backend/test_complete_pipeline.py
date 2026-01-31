"""Complete pipeline test with real APIs.

This script runs the full drug discovery pipeline and displays detailed results
including all API responses and final drug candidates.
"""

import asyncio
import sys
from app.discovery_pipeline import DiscoveryPipeline


async def test_complete_pipeline():
    """Run complete pipeline with detailed output."""
    
    # Choose a well-studied disease
    disease_name = "COVID-19"  # Well-studied with many known drugs
    
    print("="*80)
    print(f"AI-POWERED DRUG DISCOVERY PLATFORM")
    print("="*80)
    print(f"\nDisease Query: {disease_name}")
    print("\n" + "="*80)
    
    pipeline = DiscoveryPipeline()
    
    try:
        # Run the pipeline
        print("\n[STEP 1] Querying Open Targets for disease-target associations...")
        print("-"*80)
        
        result = await pipeline.discover_drugs(disease_name)
        
        # Display results
        print(f"\n[OK] Pipeline completed in {result.processing_time_seconds:.2f} seconds")
        print("\n" + "="*80)
        print("PIPELINE RESULTS SUMMARY")
        print("="*80)
        print(f"  Query: {result.query}")
        print(f"  Timestamp: {result.timestamp}")
        print(f"  Processing Time: {result.processing_time_seconds:.2f}s")
        print(f"  API Version: {result.api_version}")
        print(f"\n  Targets Found: {result.targets_found}")
        print(f"  Molecules Analyzed: {result.molecules_analyzed}")
        print(f"  Drug Candidates Generated: {len(result.candidates)}")
        
        if result.warnings:
            print(f"\n  Warnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"    [!] {warning}")
        
        # Display candidates
        if len(result.candidates) > 0:
            print("\n" + "="*80)
            print("TOP DRUG CANDIDATES")
            print("="*80)
            
            # Show top 10 candidates
            for i, candidate in enumerate(result.candidates[:10], 1):
                print(f"\n{'-'*80}")
                print(f"RANK #{i}: {candidate.molecule.name}")
                print(f"{'-'*80}")
                
                # Molecule information
                print(f"\n  Molecule Details:")
                print(f"    ChEMBL ID: {candidate.molecule.chembl_id}")
                print(f"    SMILES: {candidate.molecule.smiles[:60]}...")
                print(f"    Activity: {candidate.molecule.activity_type}")
                print(f"    pChEMBL Value: {candidate.molecule.pchembl_value:.2f}")
                
                # Target information
                print(f"\n  Target Information:")
                print(f"    Gene: {candidate.target.gene_symbol}")
                print(f"    Protein: {candidate.target.protein_name}")
                print(f"    UniProt ID: {candidate.target.uniprot_id}")
                print(f"    Confidence: {candidate.target.confidence_score:.2f}")
                
                # Scores
                print(f"\n  Scoring:")
                print(f"    * Composite Score: {candidate.composite_score:.3f}")
                print(f"    - Binding Affinity: {candidate.binding_affinity_score:.3f} (confidence: {candidate.binding_confidence:.2f})")
                print(f"    - Drug-likeness: {candidate.properties.drug_likeness_score:.3f}")
                print(f"    - Toxicity Score: {candidate.toxicity.toxicity_score:.3f} ({candidate.toxicity.risk_level} risk)")
                
                # Molecular properties
                print(f"\n  Molecular Properties:")
                print(f"    Molecular Weight: {candidate.properties.molecular_weight:.2f} Da")
                print(f"    LogP: {candidate.properties.logp:.2f}")
                print(f"    H-Bond Donors: {candidate.properties.hbd}")
                print(f"    H-Bond Acceptors: {candidate.properties.hba}")
                print(f"    TPSA: {candidate.properties.tpsa:.2f} A^2")
                print(f"    Rotatable Bonds: {candidate.properties.rotatable_bonds}")
                print(f"    Aromatic Rings: {candidate.properties.aromatic_rings}")
                print(f"    Lipinski Violations: {candidate.properties.lipinski_violations}")
                
                # Toxicity assessment
                if candidate.toxicity.detected_toxicophores:
                    print(f"\n  Toxicity Warnings:")
                    for toxicophore in candidate.toxicity.detected_toxicophores:
                        print(f"    [!] {toxicophore}")
                else:
                    print(f"\n  Toxicity: No toxic substructures detected [OK]")
                
                # AI analysis
                if candidate.ai_analysis:
                    print(f"\n  AI Analysis:")
                    # Wrap text at 76 characters
                    analysis = candidate.ai_analysis
                    words = analysis.split()
                    line = "    "
                    for word in words:
                        if len(line) + len(word) + 1 > 76:
                            print(line)
                            line = "    " + word
                        else:
                            line += " " + word if line != "    " else word
                    if line.strip():
                        print(line)
            
            # Summary statistics
            print("\n" + "="*80)
            print("CANDIDATE STATISTICS")
            print("="*80)
            
            avg_composite = sum(c.composite_score for c in result.candidates) / len(result.candidates)
            avg_binding = sum(c.binding_affinity_score for c in result.candidates) / len(result.candidates)
            avg_drug_likeness = sum(c.properties.drug_likeness_score for c in result.candidates) / len(result.candidates)
            avg_toxicity = sum(c.toxicity.toxicity_score for c in result.candidates) / len(result.candidates)
            
            print(f"\n  Average Scores:")
            print(f"    Composite: {avg_composite:.3f}")
            print(f"    Binding Affinity: {avg_binding:.3f}")
            print(f"    Drug-likeness: {avg_drug_likeness:.3f}")
            print(f"    Toxicity: {avg_toxicity:.3f}")
            
            # Risk distribution
            risk_counts = {"low": 0, "medium": 0, "high": 0}
            for candidate in result.candidates:
                risk_counts[candidate.toxicity.risk_level] += 1
            
            print(f"\n  Risk Distribution:")
            print(f"    Low Risk: {risk_counts['low']} ({risk_counts['low']/len(result.candidates)*100:.1f}%)")
            print(f"    Medium Risk: {risk_counts['medium']} ({risk_counts['medium']/len(result.candidates)*100:.1f}%)")
            print(f"    High Risk: {risk_counts['high']} ({risk_counts['high']/len(result.candidates)*100:.1f}%)")
            
            # Lipinski compliance
            compliant = sum(1 for c in result.candidates if c.properties.lipinski_violations == 0)
            print(f"\n  Lipinski Rule Compliance:")
            print(f"    Fully Compliant: {compliant} ({compliant/len(result.candidates)*100:.1f}%)")
            print(f"    With Violations: {len(result.candidates) - compliant} ({(len(result.candidates) - compliant)/len(result.candidates)*100:.1f}%)")
            
        else:
            print("\n" + "="*80)
            print("NO CANDIDATES FOUND")
            print("="*80)
            print("\nPossible reasons:")
            print("  • No bioactive molecules found in ChEMBL for the identified targets")
            print("  • All molecules failed SMILES validation")
            print("  • All molecules failed drug-likeness criteria")
            
        print("\n" + "="*80)
        print("PIPELINE COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await pipeline.close()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_complete_pipeline())
    sys.exit(exit_code)

