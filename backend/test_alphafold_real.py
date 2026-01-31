"""Manual test script to verify AlphaFold API client with real API calls.

This script actually downloads a protein structure from AlphaFold to verify
the client works correctly with the real API.

Run with: python test_alphafold_real.py
"""

import asyncio
import sys
from app.alphafold_client import AlphaFoldClient


async def test_real_download():
    """Test downloading a real protein structure from AlphaFold."""
    
    print("=" * 70)
    print("Testing AlphaFold API Client with REAL API calls")
    print("=" * 70)
    
    client = AlphaFoldClient()
    
    # Test with a well-known protein: Human Insulin (P01308)
    test_proteins = [
        ("P01308", "Human Insulin"),
        ("P04637", "Tumor protein p53"),
        ("P68871", "Hemoglobin subunit beta"),
    ]
    
    for uniprot_id, protein_name in test_proteins:
        print(f"\n📥 Downloading: {protein_name} ({uniprot_id})")
        print("-" * 70)
        
        try:
            # This will make a REAL API call to AlphaFold
            structure = await client.get_protein_structure(uniprot_id)
            
            if structure:
                print(f"✅ SUCCESS!")
                print(f"   UniProt ID: {structure.uniprot_id}")
                print(f"   pLDDT Score: {structure.plddt_score:.2f}")
                print(f"   Confidence: {'LOW ⚠️' if structure.is_low_confidence else 'HIGH ✓'}")
                print(f"   PDB Data Size: {len(structure.pdb_data)} characters")
                
                # Show first few lines of PDB
                pdb_lines = structure.pdb_data.split('\n')[:5]
                print(f"\n   First lines of PDB file:")
                for line in pdb_lines:
                    print(f"   {line}")
                
                # Test caching - second call should be instant
                print(f"\n   Testing cache...")
                import time
                start = time.time()
                cached_structure = await client.get_protein_structure(uniprot_id)
                elapsed = time.time() - start
                
                if cached_structure:
                    print(f"   ✅ Cache hit! Retrieved in {elapsed*1000:.1f}ms")
                    print(f"   Cached data matches: {cached_structure.plddt_score == structure.plddt_score}")
                
            else:
                print(f"❌ FAILED: Structure not found")
                
        except Exception as e:
            print(f"❌ ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70)


async def test_missing_protein():
    """Test handling of non-existent protein."""
    print("\n\n📥 Testing non-existent protein (should handle gracefully)")
    print("-" * 70)
    
    client = AlphaFoldClient()
    
    try:
        structure = await client.get_protein_structure("NOTREAL123")
        
        if structure is None:
            print("✅ Correctly returned None for non-existent protein")
        else:
            print("❌ Unexpected: Got a structure for fake ID")
            
    except Exception as e:
        print(f"❌ ERROR (should have returned None): {e}")


async def test_empty_id():
    """Test handling of empty protein ID."""
    print("\n\n📥 Testing empty protein ID (should handle gracefully)")
    print("-" * 70)
    
    client = AlphaFoldClient()
    
    try:
        structure = await client.get_protein_structure("")
        
        if structure is None:
            print("✅ Correctly returned None for empty ID")
        else:
            print("❌ Unexpected: Got a structure for empty ID")
            
    except Exception as e:
        print(f"❌ ERROR (should have returned None): {e}")


async def main():
    """Run all tests."""
    
    print("\n🧪 ALPHAFOLD API CLIENT - REAL API TEST")
    print("This will download actual protein structures from AlphaFold")
    print("Make sure you have internet connection!\n")
    
    # Run tests
    await test_real_download()
    await test_missing_protein()
    await test_empty_id()
    
    print("\n✨ All tests completed!\n")


if __name__ == "__main__":
    # Check if Redis is needed
    print("⚠️  Note: This test requires Redis to be running for caching.")
    print("   If Redis is not available, caching will be disabled but downloads will still work.\n")
    
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

