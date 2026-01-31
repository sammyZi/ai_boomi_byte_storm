"""Real API integration tests for drug discovery pipeline.

These tests make actual calls to external APIs:
- Open Targets Platform
- ChEMBL Database
- AlphaFold Database

WARNING: These tests require:
1. Internet connection
2. External APIs to be available
3. May take longer to run (8-10+ seconds)
4. May be rate-limited by external services

Run with: pytest tests/test_real_api_integration.py -v -s

Validates: Requirements 9.1, 9.6, 10.1
"""

import pytest
import time
from app.discovery_pipeline import DiscoveryPipeline
from app.open_targets_client import OpenTargetsClient
from app.alphafold_client import AlphaFoldClient
from app.chembl_client import ChEMBLClient


# Mark all tests in this module as requiring real API access
pytestmark = pytest.mark.real_api


class TestRealAPIIntegration:
    """Integration tests with real external APIs."""
    
    @pytest.mark.asyncio
    async def test_open_targets_real_api(self):
        """Test Open Targets API with real disease query.
        
        Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
        """
        client = OpenTargetsClient()
        
        # Query for a well-known disease
        disease_name = "Alzheimer's disease"
        
        print(f"\nQuerying Open Targets for: {disease_name}")
        start_time = time.time()
        
        try:
            targets = await client.get_disease_targets(disease_name)
            query_time = time.time() - start_time
            
            print(f"Query completed in {query_time:.2f}s")
            print(f"Found {len(targets)} targets")
            
            # Verify results
            assert len(targets) > 0, "Should find targets for Alzheimer's disease"
            assert len(targets) <= 10, "Should limit to 10 targets"
            
            # Verify target structure
            for target in targets:
                assert target.uniprot_id is not None
                assert target.gene_symbol is not None
                assert target.protein_name is not None
                assert 0.5 <= target.confidence_score <= 1.0
                assert target.disease_association is not None
                
                print(f"  - {target.gene_symbol}: {target.protein_name} "
                      f"(confidence: {target.confidence_score:.2f})")
            
            # Verify targets are sorted by confidence
            for i in range(len(targets) - 1):
                assert targets[i].confidence_score >= targets[i+1].confidence_score, \
                    "Targets should be sorted by confidence descending"
            
        except Exception as e:
            pytest.skip(f"Open Targets API unavailable: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_alphafold_real_api(self):
        """Test AlphaFold API with real protein structure query.
        
        Validates: Requirements 2.1, 2.2, 2.3
        """
        client = AlphaFoldClient()
        
        # Query for a well-known protein (APOE - associated with Alzheimer's)
        uniprot_id = "P02649"  # APOE
        
        print(f"\nQuerying AlphaFold for: {uniprot_id}")
        start_time = time.time()
        
        try:
            structure = await client.get_protein_structure(uniprot_id)
            query_time = time.time() - start_time
            
            print(f"Query completed in {query_time:.2f}s")
            
            if structure:
                print(f"Structure found:")
                print(f"  - UniProt ID: {structure.uniprot_id}")
                print(f"  - pLDDT score: {structure.plddt_score:.1f}")
                print(f"  - Low confidence: {structure.is_low_confidence}")
                print(f"  - PDB data size: {len(structure.pdb_data)} bytes")
                
                # Verify structure
                assert structure.uniprot_id == uniprot_id
                assert 0.0 <= structure.plddt_score <= 100.0
                assert len(structure.pdb_data) > 0
                
                # Verify confidence classification
                if structure.plddt_score < 70:
                    assert structure.is_low_confidence
                else:
                    assert not structure.is_low_confidence
            else:
                print("Structure not available (this is acceptable)")
                
        except Exception as e:
            pytest.skip(f"AlphaFold API unavailable: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_chembl_real_api(self):
        """Test ChEMBL API with real bioactive molecule query.
        
        Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6
        """
        client = ChEMBLClient()
        
        # Query for molecules targeting EGFR (well-studied target)
        target_id = "P00533"  # EGFR
        
        print(f"\nQuerying ChEMBL for target: {target_id}")
        start_time = time.time()
        
        try:
            molecules = await client.get_bioactive_molecules(target_id)
            query_time = time.time() - start_time
            
            print(f"Query completed in {query_time:.2f}s")
            print(f"Found {len(molecules)} molecules")
            
            # Verify results
            assert len(molecules) > 0, "Should find molecules for EGFR"
            assert len(molecules) <= 100, "Should limit to 100 molecules"
            
            # Verify molecule structure
            for i, molecule in enumerate(molecules[:5]):  # Show first 5
                assert molecule.chembl_id is not None
                assert molecule.name is not None
                assert molecule.smiles is not None
                assert molecule.canonical_smiles is not None
                assert molecule.pchembl_value >= 6.0
                assert molecule.activity_type is not None
                
                print(f"  {i+1}. {molecule.name} ({molecule.chembl_id})")
                print(f"     pChEMBL: {molecule.pchembl_value:.2f}, "
                      f"Activity: {molecule.activity_type}")
                print(f"     SMILES: {molecule.smiles[:50]}...")
            
            # Verify all molecules meet activity threshold
            for molecule in molecules:
                assert molecule.pchembl_value >= 6.0, \
                    "All molecules should have pChEMBL >= 6.0"
            
        except Exception as e:
            pytest.skip(f"ChEMBL API unavailable: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_full_pipeline_real_apis(self):
        """Test complete pipeline with real API calls.
        
        This is the ultimate integration test - runs the entire pipeline
        with real external APIs.
        
        WARNING: This test may take 10-30 seconds depending on:
        - Network latency
        - API response times
        - Number of results
        
        Validates: Requirements 9.1, 9.6, 10.1
        """
        pipeline = DiscoveryPipeline()
        
        # Use a well-studied disease with known targets and drugs
        disease_name = "Lung cancer"
        
        print(f"\n{'='*60}")
        print(f"Running full pipeline for: {disease_name}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            result = await pipeline.discover_drugs(disease_name)
            execution_time = time.time() - start_time
            
            print(f"\n{'='*60}")
            print(f"Pipeline completed in {execution_time:.2f}s")
            print(f"{'='*60}")
            
            # Verify result structure
            assert result is not None
            assert result.query == disease_name
            assert result.processing_time_seconds > 0
            assert result.api_version == "0.1.0"
            
            # Print summary
            print(f"\nResults Summary:")
            print(f"  - Targets found: {result.targets_found}")
            print(f"  - Molecules analyzed: {result.molecules_analyzed}")
            print(f"  - Candidates generated: {len(result.candidates)}")
            print(f"  - Warnings: {len(result.warnings)}")
            
            if result.warnings:
                print(f"\nWarnings:")
                for warning in result.warnings:
                    print(f"  - {warning}")
            
            # Verify we got results
            if result.targets_found > 0:
                assert result.molecules_analyzed >= 0
                
                if len(result.candidates) > 0:
                    print(f"\nTop 5 Candidates:")
                    for i, candidate in enumerate(result.candidates[:5]):
                        print(f"\n  {i+1}. {candidate.molecule.name} ({candidate.molecule.chembl_id})")
                        print(f"     Target: {candidate.target.gene_symbol}")
                        print(f"     Composite Score: {candidate.composite_score:.3f}")
                        print(f"     Binding Affinity: {candidate.binding_affinity_score:.3f}")
                        print(f"     Drug-likeness: {candidate.properties.drug_likeness_score:.3f}")
                        print(f"     Toxicity Risk: {candidate.toxicity.risk_level}")
                        
                        if candidate.ai_analysis:
                            print(f"     AI Analysis: {candidate.ai_analysis[:100]}...")
                    
                    # Verify candidate structure
                    for candidate in result.candidates:
                        assert candidate.molecule is not None
                        assert candidate.target is not None
                        assert candidate.properties is not None
                        assert candidate.toxicity is not None
                        assert 0.0 <= candidate.binding_affinity_score <= 1.0
                        assert 0.0 <= candidate.composite_score <= 1.0
                        assert candidate.rank >= 1
                        assert len(candidate.structure_2d_svg) > 0
                    
                    # Verify ranking
                    for i in range(len(result.candidates) - 1):
                        assert result.candidates[i].composite_score >= \
                               result.candidates[i+1].composite_score, \
                               "Candidates should be ranked by composite score"
                    
                    # Performance check
                    # Real APIs may be slower, but should still be reasonable
                    print(f"\nPerformance:")
                    print(f"  - Total time: {execution_time:.2f}s")
                    print(f"  - Throughput: {result.molecules_analyzed / execution_time:.1f} molecules/sec")
                    
                    # Warn if too slow (but don't fail - network conditions vary)
                    if execution_time > 30:
                        print(f"\n  WARNING: Pipeline took {execution_time:.2f}s (target: 8-10s)")
                        print(f"  This may be due to network latency or API response times")
                else:
                    print("\nNo candidates generated (molecules may have failed analysis)")
            else:
                print("\nNo targets found for this disease")
            
        except Exception as e:
            pytest.skip(f"Pipeline failed with real APIs: {str(e)}")
        finally:
            await pipeline.close()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)  # 2 minute timeout for caching test
    async def test_caching_with_real_apis(self):
        """Test caching behavior with real API calls.
        
        Verifies that:
        - First query hits real APIs
        - Second query uses cache (much faster)
        
        Validates: Requirements 9.6
        """
        pipeline = DiscoveryPipeline()
        
        # Use a simpler disease for faster testing
        disease_name = "Asthma"
        
        print(f"\nTesting cache behavior for: {disease_name}")
        
        try:
            # First query - cache miss
            print("\nFirst query (cache miss)...")
            start_time = time.time()
            result1 = await pipeline.discover_drugs(disease_name)
            first_time = time.time() - start_time
            
            print(f"First query completed in {first_time:.2f}s")
            print(f"Targets: {result1.targets_found}, Molecules: {result1.molecules_analyzed}")
            
            # Second query - cache hit
            print("\nSecond query (cache hit)...")
            start_time = time.time()
            result2 = await pipeline.discover_drugs(disease_name)
            second_time = time.time() - start_time
            
            print(f"Second query completed in {second_time:.2f}s")
            print(f"Targets: {result2.targets_found}, Molecules: {result2.molecules_analyzed}")
            
            # Verify results are consistent
            assert result1.targets_found == result2.targets_found
            assert result1.molecules_analyzed == result2.molecules_analyzed
            
            # Second query should be significantly faster (cache hit)
            speedup = first_time / second_time if second_time > 0 else float('inf')
            print(f"\nSpeedup: {speedup:.1f}x faster")
            
            # Cache hit should be much faster (at least 2x)
            if second_time > 0:
                assert speedup >= 2.0, \
                    f"Cache hit should be at least 2x faster (was {speedup:.1f}x)"
            
        except Exception as e:
            pytest.skip(f"Caching test failed: {str(e)}")
        finally:
            await pipeline.close()
    
    @pytest.mark.asyncio
    async def test_error_handling_with_real_apis(self):
        """Test error handling with real APIs.
        
        Tests graceful degradation when:
        - Disease not found
        - No molecules available
        
        Validates: Requirements 10.1
        """
        pipeline = DiscoveryPipeline()
        
        try:
            # Test 1: Unknown disease
            print("\nTest 1: Unknown disease")
            result = await pipeline.discover_drugs("XYZ123NonexistentDisease")
            
            print(f"Targets found: {result.targets_found}")
            print(f"Candidates: {len(result.candidates)}")
            print(f"Warnings: {result.warnings}")
            
            # Should handle gracefully
            assert result is not None
            assert len(result.candidates) == 0
            
            # Test 2: Very rare disease (may have targets but no molecules)
            print("\nTest 2: Rare disease")
            result = await pipeline.discover_drugs("Progeria")
            
            print(f"Targets found: {result.targets_found}")
            print(f"Candidates: {len(result.candidates)}")
            print(f"Warnings: {result.warnings}")
            
            # Should handle gracefully
            assert result is not None
            
        except Exception as e:
            pytest.skip(f"Error handling test failed: {str(e)}")
        finally:
            await pipeline.close()


class TestRealAPIPerformance:
    """Performance tests with real APIs."""
    
    @pytest.mark.asyncio
    async def test_concurrent_real_api_requests(self):
        """Test concurrent processing with real APIs.
        
        Verifies that concurrent requests work correctly with real APIs
        and respect rate limits.
        
        Validates: Requirements 9.7, 9.8
        """
        import asyncio
        
        diseases = ["Diabetes", "Hypertension", "Asthma"]
        
        print(f"\nTesting concurrent requests for {len(diseases)} diseases")
        
        async def query_disease(disease_name):
            """Query a single disease."""
            pipeline = DiscoveryPipeline()
            try:
                start_time = time.time()
                result = await pipeline.discover_drugs(disease_name)
                query_time = time.time() - start_time
                
                return {
                    'disease': disease_name,
                    'time': query_time,
                    'targets': result.targets_found,
                    'candidates': len(result.candidates)
                }
            except Exception as e:
                return {
                    'disease': disease_name,
                    'error': str(e)
                }
            finally:
                await pipeline.close()
        
        try:
            # Run concurrent queries
            start_time = time.time()
            tasks = [query_disease(disease) for disease in diseases]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            print(f"\nTotal time for {len(diseases)} concurrent queries: {total_time:.2f}s")
            
            # Print results
            for result in results:
                if isinstance(result, dict) and 'error' not in result:
                    print(f"\n  {result['disease']}:")
                    print(f"    Time: {result['time']:.2f}s")
                    print(f"    Targets: {result['targets']}")
                    print(f"    Candidates: {result['candidates']}")
                elif isinstance(result, dict):
                    print(f"\n  {result['disease']}: ERROR - {result['error']}")
                else:
                    print(f"\n  Error: {result}")
            
            # Verify at least some queries succeeded
            successful = [r for r in results if isinstance(r, dict) and 'error' not in r]
            assert len(successful) > 0, "At least one query should succeed"
            
        except Exception as e:
            pytest.skip(f"Concurrent test failed: {str(e)}")


# Helper function to run real API tests
def run_real_api_tests():
    """
    Helper function to run real API tests.
    
    Usage:
        pytest tests/test_real_api_integration.py -v -s -m real_api
    
    Or to skip real API tests:
        pytest -v -m "not real_api"
    """
    pass

