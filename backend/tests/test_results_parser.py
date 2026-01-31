"""Tests for the docking results parser module.

Tests cover:
- Parsing binding affinity from Vina stdout output
- Parsing poses from output PDBQT file
- Extracting RMSD values
- Identifying best binding pose
- Generating summary statistics
- Combined parsing from stdout and PDBQT
- Edge cases (single pose, empty results, failed docking)
"""

import os
import tempfile
import pytest

from app.docking.results_parser import DockingResultsParser
from app.docking.models import DockingResult


# Sample Vina stdout output
SAMPLE_VINA_STDOUT = """
AutoDock Vina v1.2.5
Computing Vina grid ... done.
Performing docking (random seed: 12345) ... done.

mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1         -8.5      0.000      0.000
   2         -7.9      1.234      2.456
   3         -7.2      2.345      3.567
   4         -6.8      3.456      4.678
   5         -6.5      4.567      5.789

Writing output ... done.
"""

SAMPLE_VINA_STDOUT_SINGLE_POSE = """
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1         -9.2      0.000      0.000

Writing output ... done.
"""

SAMPLE_VINA_STDOUT_NO_RESULTS = """
AutoDock Vina v1.2.5
Computing Vina grid ... error.
"""

# Sample PDBQT output content
SAMPLE_PDBQT_OUTPUT = """MODEL 1
REMARK VINA RESULT:    -8.5      0.000      0.000
ATOM      1  C   LIG     1       0.000   0.000   0.000  1.00  0.00     0.001 C 
ATOM      2  N   LIG     1       1.500   0.000   0.000  1.00  0.00    -0.350 N 
ATOM      3  O   LIG     1       0.000   1.500   0.000  1.00  0.00    -0.400 O 
ENDMDL
MODEL 2
REMARK VINA RESULT:    -7.9      1.234      2.456
ATOM      1  C   LIG     1       0.100   0.100   0.100  1.00  0.00     0.001 C 
ATOM      2  N   LIG     1       1.600   0.100   0.100  1.00  0.00    -0.350 N 
ATOM      3  O   LIG     1       0.100   1.600   0.100  1.00  0.00    -0.400 O 
ENDMDL
MODEL 3
REMARK VINA RESULT:    -7.2      2.345      3.567
ATOM      1  C   LIG     1       0.200   0.200   0.200  1.00  0.00     0.001 C 
ATOM      2  N   LIG     1       1.700   0.200   0.200  1.00  0.00    -0.350 N 
ATOM      3  O   LIG     1       0.200   1.700   0.200  1.00  0.00    -0.400 O 
ENDMDL
"""

SAMPLE_PDBQT_SINGLE_POSE = """MODEL 1
REMARK VINA RESULT:    -9.2      0.000      0.000
ATOM      1  C   LIG     1       0.000   0.000   0.000  1.00  0.00     0.001 C 
ENDMDL
"""


def write_temp_file(content: str, suffix: str = '.pdbqt') -> str:
    """Create a temp file with content in a Windows-compatible way."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        os.write(fd, content.encode('utf-8'))
    finally:
        os.close(fd)
    return path


def safe_unlink(path: str):
    """Safely remove a file, ignoring errors."""
    try:
        os.unlink(path)
    except (OSError, PermissionError):
        pass


class TestParseStdout:
    """Tests for parse_stdout method."""
    
    def test_parse_multiple_poses(self):
        """Test parsing stdout with multiple poses."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        assert len(results) == 5
    
    def test_parse_binding_affinities(self):
        """Test that binding affinities are extracted correctly."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        assert results[0].binding_affinity == -8.5
        assert results[1].binding_affinity == -7.9
        assert results[2].binding_affinity == -7.2
        assert results[3].binding_affinity == -6.8
        assert results[4].binding_affinity == -6.5
    
    def test_parse_pose_numbers(self):
        """Test that pose numbers are extracted correctly."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        assert results[0].pose_number == 1
        assert results[1].pose_number == 2
        assert results[4].pose_number == 5
    
    def test_parse_rmsd_values(self):
        """Test that RMSD values are extracted correctly."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        # First pose always has RMSD of 0
        assert results[0].rmsd_lb == 0.0
        assert results[0].rmsd_ub == 0.0
        
        # Second pose
        assert results[1].rmsd_lb == 1.234
        assert results[1].rmsd_ub == 2.456
    
    def test_parse_single_pose(self):
        """Test parsing stdout with single pose."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT_SINGLE_POSE)
        
        assert len(results) == 1
        assert results[0].binding_affinity == -9.2
        assert results[0].pose_number == 1
    
    def test_parse_empty_stdout(self):
        """Test parsing empty stdout."""
        parser = DockingResultsParser()
        results = parser.parse_stdout("")
        
        assert len(results) == 0
    
    def test_parse_no_results(self):
        """Test parsing stdout with no results table."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT_NO_RESULTS)
        
        assert len(results) == 0
    
    def test_returns_docking_result_objects(self):
        """Test that results are DockingResult objects."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        for result in results:
            assert isinstance(result, DockingResult)


class TestParseOutputPDBQT:
    """Tests for parse_output_pdbqt method."""
    
    def test_parse_pdbqt_multiple_models(self):
        """Test parsing PDBQT with multiple models."""
        path = write_temp_file(SAMPLE_PDBQT_OUTPUT)
        try:
            parser = DockingResultsParser()
            results = parser.parse_output_pdbqt(path)
            assert len(results) == 3
        finally:
            safe_unlink(path)
    
    def test_parse_pdbqt_affinities(self):
        """Test that affinities are extracted from PDBQT."""
        path = write_temp_file(SAMPLE_PDBQT_OUTPUT)
        try:
            parser = DockingResultsParser()
            results = parser.parse_output_pdbqt(path)
            
            assert results[0].binding_affinity == -8.5
            assert results[1].binding_affinity == -7.9
            assert results[2].binding_affinity == -7.2
        finally:
            safe_unlink(path)
    
    def test_parse_pdbqt_rmsd_values(self):
        """Test that RMSD values are extracted from PDBQT."""
        path = write_temp_file(SAMPLE_PDBQT_OUTPUT)
        try:
            parser = DockingResultsParser()
            results = parser.parse_output_pdbqt(path)
            
            assert results[0].rmsd_lb == 0.0
            assert results[1].rmsd_lb == 1.234
            assert results[1].rmsd_ub == 2.456
        finally:
            safe_unlink(path)
    
    def test_parse_pdbqt_contains_coordinates(self):
        """Test that pdbqt_data contains atomic coordinates."""
        path = write_temp_file(SAMPLE_PDBQT_OUTPUT)
        try:
            parser = DockingResultsParser()
            results = parser.parse_output_pdbqt(path)
            
            assert results[0].pdbqt_data is not None
            assert "ATOM" in results[0].pdbqt_data
            assert "MODEL 1" in results[0].pdbqt_data
        finally:
            safe_unlink(path)
    
    def test_parse_pdbqt_single_model(self):
        """Test parsing PDBQT with single model."""
        path = write_temp_file(SAMPLE_PDBQT_SINGLE_POSE)
        try:
            parser = DockingResultsParser()
            results = parser.parse_output_pdbqt(path)
            
            assert len(results) == 1
            assert results[0].binding_affinity == -9.2
        finally:
            safe_unlink(path)
    
    def test_parse_pdbqt_file_not_found(self):
        """Test handling of missing PDBQT file."""
        parser = DockingResultsParser()
        results = parser.parse_output_pdbqt("/nonexistent/file.pdbqt")
        
        assert len(results) == 0
    
    def test_parse_pdbqt_empty_file(self):
        """Test handling of empty PDBQT file."""
        path = write_temp_file("")
        try:
            parser = DockingResultsParser()
            results = parser.parse_output_pdbqt(path)
            assert len(results) == 0
        finally:
            safe_unlink(path)


class TestGetBestPose:
    """Tests for get_best_pose method."""
    
    def test_get_best_pose_returns_most_negative(self):
        """Test that best pose is the most negative affinity."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        best = parser.get_best_pose(results)
        
        assert best is not None
        assert best.binding_affinity == -8.5
        assert best.pose_number == 1
    
    def test_get_best_pose_single_result(self):
        """Test best pose with single result."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT_SINGLE_POSE)
        
        best = parser.get_best_pose(results)
        
        assert best is not None
        assert best.binding_affinity == -9.2
    
    def test_get_best_pose_empty_list(self):
        """Test best pose with empty results list."""
        parser = DockingResultsParser()
        
        best = parser.get_best_pose([])
        
        assert best is None
    
    def test_get_best_pose_custom_results(self):
        """Test best pose with custom results."""
        results = [
            DockingResult(pose_number=1, binding_affinity=-5.0),
            DockingResult(pose_number=2, binding_affinity=-9.0),
            DockingResult(pose_number=3, binding_affinity=-7.0),
        ]
        
        parser = DockingResultsParser()
        best = parser.get_best_pose(results)
        
        assert best.binding_affinity == -9.0
        assert best.pose_number == 2


class TestGetSummaryStatistics:
    """Tests for get_summary_statistics method."""
    
    def test_summary_num_poses(self):
        """Test that num_poses is correct."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        stats = parser.get_summary_statistics(results)
        
        assert stats['num_poses'] == 5
    
    def test_summary_best_affinity(self):
        """Test that best_affinity is correct."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        stats = parser.get_summary_statistics(results)
        
        assert stats['best_affinity'] == -8.5
    
    def test_summary_worst_affinity(self):
        """Test that worst_affinity is correct."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        stats = parser.get_summary_statistics(results)
        
        assert stats['worst_affinity'] == -6.5
    
    def test_summary_mean_affinity(self):
        """Test that mean_affinity is calculated correctly."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        stats = parser.get_summary_statistics(results)
        
        # Mean of -8.5, -7.9, -7.2, -6.8, -6.5 = -36.9/5 = -7.38
        assert abs(stats['mean_affinity'] - (-7.38)) < 0.01
    
    def test_summary_affinity_range(self):
        """Test that affinity_range is calculated correctly."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        stats = parser.get_summary_statistics(results)
        
        # Range: -6.5 - (-8.5) = 2.0
        assert stats['affinity_range'] == 2.0
    
    def test_summary_empty_results(self):
        """Test summary with empty results."""
        parser = DockingResultsParser()
        
        stats = parser.get_summary_statistics([])
        
        assert stats['num_poses'] == 0
        assert stats['best_affinity'] is None
        assert stats['worst_affinity'] is None
        assert stats['mean_affinity'] is None
        assert stats['affinity_range'] is None
    
    def test_summary_single_pose(self):
        """Test summary with single pose."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT_SINGLE_POSE)
        
        stats = parser.get_summary_statistics(results)
        
        assert stats['num_poses'] == 1
        assert stats['best_affinity'] == -9.2
        assert stats['worst_affinity'] == -9.2
        assert stats['mean_affinity'] == -9.2
        assert stats['affinity_range'] == 0.0


class TestParseCombined:
    """Tests for parse_combined method."""
    
    def test_combined_stdout_only(self):
        """Test combined parsing with stdout only."""
        parser = DockingResultsParser()
        
        results = parser.parse_combined(SAMPLE_VINA_STDOUT)
        
        assert len(results) == 5
        assert results[0].pdbqt_data is None
    
    def test_combined_with_pdbqt(self):
        """Test combined parsing with both stdout and PDBQT."""
        # Use matching stdout (same affinities for first 3 poses)
        stdout = """
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1         -8.5      0.000      0.000
   2         -7.9      1.234      2.456
   3         -7.2      2.345      3.567
"""
        path = write_temp_file(SAMPLE_PDBQT_OUTPUT)
        try:
            parser = DockingResultsParser()
            results = parser.parse_combined(stdout, path)
            
            assert len(results) == 3
            assert results[0].pdbqt_data is not None
            assert "ATOM" in results[0].pdbqt_data
        finally:
            safe_unlink(path)
    
    def test_combined_merges_pdbqt_data(self):
        """Test that pdbqt_data is merged into stdout results."""
        path = write_temp_file(SAMPLE_PDBQT_SINGLE_POSE)
        try:
            parser = DockingResultsParser()
            stdout = SAMPLE_VINA_STDOUT_SINGLE_POSE
            
            results = parser.parse_combined(stdout, path)
            
            assert len(results) == 1
            assert results[0].binding_affinity == -9.2
            assert results[0].pdbqt_data is not None
        finally:
            safe_unlink(path)


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_parse_positive_affinity(self):
        """Test handling of unusual positive affinity values."""
        stdout = """
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1          0.5      0.000      0.000
"""
        parser = DockingResultsParser()
        results = parser.parse_stdout(stdout)
        
        assert len(results) == 1
        assert results[0].binding_affinity == 0.5
    
    def test_parse_very_negative_affinity(self):
        """Test handling of very negative affinity values."""
        stdout = """
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1        -15.2      0.000      0.000
"""
        parser = DockingResultsParser()
        results = parser.parse_stdout(stdout)
        
        assert len(results) == 1
        assert results[0].binding_affinity == -15.2
    
    def test_parse_high_rmsd_values(self):
        """Test handling of high RMSD values."""
        stdout = """
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1         -8.0      0.000      0.000
   2         -7.5     12.345     15.678
"""
        parser = DockingResultsParser()
        results = parser.parse_stdout(stdout)
        
        assert results[1].rmsd_lb == 12.345
        assert results[1].rmsd_ub == 15.678
    
    def test_parse_malformed_line_skipped(self):
        """Test that malformed lines after separator are handled."""
        stdout = """
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1         -8.5      0.000      0.000

Writing output ... done.
"""
        parser = DockingResultsParser()
        results = parser.parse_stdout(stdout)
        
        # Should parse valid line before empty line
        assert len(results) == 1
        assert results[0].binding_affinity == -8.5
    
    def test_pdbqt_missing_remark_line(self):
        """Test PDBQT with model missing REMARK line."""
        pdbqt_content = """MODEL 1
ATOM      1  C   LIG     1       0.000   0.000   0.000  1.00  0.00     0.001 C 
ENDMDL
MODEL 2
REMARK VINA RESULT:    -7.5      0.000      0.000
ATOM      1  C   LIG     1       0.100   0.100   0.100  1.00  0.00     0.001 C 
ENDMDL
"""
        path = write_temp_file(pdbqt_content)
        try:
            parser = DockingResultsParser()
            results = parser.parse_output_pdbqt(path)
            
            # Only model 2 has valid REMARK line
            assert len(results) == 1
            assert results[0].binding_affinity == -7.5
        finally:
            safe_unlink(path)
    
    def test_whitespace_variations_in_stdout(self):
        """Test parsing with different whitespace in stdout."""
        stdout = """
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
  1        -8.5     0.000     0.000
   2         -7.9      1.234      2.456
    3          -7.2       2.345       3.567
"""
        parser = DockingResultsParser()
        results = parser.parse_stdout(stdout)
        
        assert len(results) == 3
        assert results[0].binding_affinity == -8.5
        assert results[2].binding_affinity == -7.2


class TestDockingResultModel:
    """Tests for DockingResult model integration."""
    
    def test_result_has_required_fields(self):
        """Test that parsed results have all required fields."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        for result in results:
            assert hasattr(result, 'pose_number')
            assert hasattr(result, 'binding_affinity')
            assert hasattr(result, 'rmsd_lb')
            assert hasattr(result, 'rmsd_ub')
            assert hasattr(result, 'pdbqt_data')
    
    def test_result_default_pdbqt_data_is_none(self):
        """Test that pdbqt_data defaults to None from stdout parsing."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        for result in results:
            assert result.pdbqt_data is None
    
    def test_result_pose_number_starts_at_one(self):
        """Test that pose numbers start at 1."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        assert results[0].pose_number == 1
    
    def test_result_affinities_are_floats(self):
        """Test that affinities are float values."""
        parser = DockingResultsParser()
        results = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        
        for result in results:
            assert isinstance(result.binding_affinity, float)


class TestParserReusability:
    """Tests for parser instance reusability."""
    
    def test_parser_can_parse_multiple_outputs(self):
        """Test that same parser instance can parse multiple outputs."""
        parser = DockingResultsParser()
        
        results1 = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        results2 = parser.parse_stdout(SAMPLE_VINA_STDOUT_SINGLE_POSE)
        
        assert len(results1) == 5
        assert len(results2) == 1
    
    def test_parser_results_are_independent(self):
        """Test that results from different parses are independent."""
        parser = DockingResultsParser()
        
        results1 = parser.parse_stdout(SAMPLE_VINA_STDOUT)
        results2 = parser.parse_stdout(SAMPLE_VINA_STDOUT_SINGLE_POSE)
        
        # Modifying one shouldn't affect the other
        results1.clear()
        assert len(results2) == 1
