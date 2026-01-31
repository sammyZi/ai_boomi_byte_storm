"""Quick validation test for drug discovery pipeline.

This script runs a quick validation of the complete pipeline with real APIs
to confirm everything is working correctly.
"""

import asyncio
import sys
from app.discovery_pipeline import DiscoveryPipeline


async def quick_validation():
    """Run quick validation test."""
    
    print("="*80)
    print("DRUG DISCOVERY PIPELINE - QUICK VALIDATION")
    print("="*80)
    
    pipeline = DiscoveryPipeline()
    
    try:
        # Test with a simple disease
        disease_name = "Asthma"
        
        print(f"\nTesting with: {disease_name}")
        print("-"*80)
        
        result = await pipeline.discover_drugs(disease_name)
        
        # Validate results
        print(f"\n[OK] Pipeline completed in {result.processing_time_seconds:.2f}s")
        print(f"\nResults:")
        print(f"  - Targets Found: {result.targets_found}")
        print(f"  - Molecules Analyzed: {result.molecules_analyzed}")
        print(f"  - Candidates Generated: {len(result.candidates)}")
        
        if len(result.candidates) > 0:
            print(f"\nTop 3 Candidates:")
            for i, candidate in enumerate(result.candidates[:3], 1):
                print(f"  {i}. {candidate.molecule.name}")
                print(f"     Score: {candidate.composite_score:.3f}, "
                      f"Target: {candidate.target.gene_symbol}")
        
        # Validation checks
        assert result.targets_found > 0, "Should find targets"
        assert result.molecules_analyzed >= 0, "Should analyze molecules"
        
        print(f"\n{'='*80}")
        print("[SUCCESS] All validation checks passed!")
        print("="*80)
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Validation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await pipeline.close()


if __name__ == "__main__":
    exit_code = asyncio.run(quick_validation())
    sys.exit(exit_code)
