"""Tests for the configuration file generator module.

Tests cover:
- Configuration file generation with all required fields
- Default and custom docking parameters
- Path validation for receptor and ligand files
- Configuration file validation (Property 17)
- Error handling for missing files
- Optional seed parameter handling
"""

import os
import tempfile
import pytest

from app.docking.config_generator import ConfigFileGenerator
from app.docking.models import GridBoxParams, DockingParams


# Sample grid box parameters
SAMPLE_GRID_PARAMS = GridBoxParams(
    center_x=10.0,
    center_y=20.0,
    center_z=30.0,
    size_x=25.0,
    size_y=25.0,
    size_z=25.0
)


class TestConfigGeneratorInit:
    """Tests for ConfigFileGenerator initialization."""
    
    def test_init_creates_work_dir(self):
        """Test that work directory is created on initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = os.path.join(tmpdir, "config_test")
            generator = ConfigFileGenerator(work_dir)
            
            assert os.path.exists(work_dir)
            assert generator.work_dir == work_dir
    
    def test_init_with_existing_dir(self):
        """Test initialization with existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConfigFileGenerator(tmpdir)
            assert generator.work_dir == tmpdir


class TestGenerateConfig:
    """Tests for generate_config method."""
    
    def test_generate_config_creates_file(self):
        """Test that configuration file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock receptor and ligand files
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS,
                job_id="test_job"
            )
            
            assert os.path.exists(config_path)
            assert config_path.endswith("test_job_config.txt")
    
    def test_config_contains_receptor_path(self):
        """Test that config contains receptor path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert f"receptor = {receptor_path}" in content
    
    def test_config_contains_ligand_path(self):
        """Test that config contains ligand path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert f"ligand = {ligand_path}" in content
    
    def test_config_contains_output_path(self):
        """Test that config contains output path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert f"out = {output_path}" in content
    
    def test_config_contains_grid_center(self):
        """Test that config contains grid box center coordinates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "center_x = 10.00" in content
            assert "center_y = 20.00" in content
            assert "center_z = 30.00" in content
    
    def test_config_contains_grid_size(self):
        """Test that config contains grid box dimensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "size_x = 25.00" in content
            assert "size_y = 25.00" in content
            assert "size_z = 25.00" in content


class TestDefaultDockingParams:
    """Tests for default docking parameter values."""
    
    def test_default_exhaustiveness(self):
        """Test default exhaustiveness is 8."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "exhaustiveness = 8" in content
    
    def test_default_num_modes(self):
        """Test default num_modes is 9."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "num_modes = 9" in content
    
    def test_default_energy_range(self):
        """Test default energy_range is 3.0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "energy_range = 3.0" in content


class TestCustomDockingParams:
    """Tests for custom docking parameters."""
    
    def test_custom_exhaustiveness(self):
        """Test custom exhaustiveness value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            custom_params = DockingParams(exhaustiveness=16)
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS,
                docking_params=custom_params
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "exhaustiveness = 16" in content
    
    def test_custom_num_modes(self):
        """Test custom num_modes value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            custom_params = DockingParams(num_modes=20)
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS,
                docking_params=custom_params
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "num_modes = 20" in content
    
    def test_custom_energy_range(self):
        """Test custom energy_range value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            custom_params = DockingParams(energy_range=5.0)
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS,
                docking_params=custom_params
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "energy_range = 5.0" in content
    
    def test_seed_not_included_by_default(self):
        """Test that seed is not included when not specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "seed =" not in content
    
    def test_seed_included_when_specified(self):
        """Test that seed is included when specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            custom_params = DockingParams(seed=42)
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS,
                docking_params=custom_params
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "seed = 42" in content


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_missing_receptor_raises_error(self):
        """Test that missing receptor file raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "nonexistent_receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            
            with pytest.raises(ValueError, match="Receptor file not found"):
                generator.generate_config(
                    receptor_path=receptor_path,
                    ligand_path=ligand_path,
                    output_path=output_path,
                    grid_params=SAMPLE_GRID_PARAMS
                )
    
    def test_missing_ligand_raises_error(self):
        """Test that missing ligand file raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "nonexistent_ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            
            generator = ConfigFileGenerator(tmpdir)
            
            with pytest.raises(ValueError, match="Ligand file not found"):
                generator.generate_config(
                    receptor_path=receptor_path,
                    ligand_path=ligand_path,
                    output_path=output_path,
                    grid_params=SAMPLE_GRID_PARAMS
                )


class TestConfigValidation:
    """Tests for configuration validation (Property 17)."""
    
    def test_validate_complete_config(self):
        """Test that validate_config returns True for complete config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            assert generator.validate_config(config_path) is True
    
    def test_validate_incomplete_config(self):
        """Test that validate_config returns False for incomplete config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create incomplete config manually
            config_path = os.path.join(tmpdir, "incomplete.txt")
            with open(config_path, 'w') as f:
                f.write("receptor = test.pdbqt\n")
                f.write("ligand = test.pdbqt\n")
                # Missing: out, center_x, center_y, center_z, etc.
            
            generator = ConfigFileGenerator(tmpdir)
            assert generator.validate_config(config_path) is False
    
    def test_validate_nonexistent_config(self):
        """Test that validate_config returns False for nonexistent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConfigFileGenerator(tmpdir)
            assert generator.validate_config("nonexistent.txt") is False


class TestConfigFormat:
    """Tests for configuration file format."""
    
    def test_config_contains_comments(self):
        """Test that config contains section comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "# AutoDock Vina Configuration File" in content
            assert "# Input files" in content
            assert "# Output file" in content
            assert "# Grid box center" in content
            assert "# Grid box size" in content
            assert "# Docking parameters" in content
    
    def test_config_contains_job_id(self):
        """Test that config contains job ID in header."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS,
                job_id="unique_job_123"
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "unique_job_123" in content
    
    def test_config_file_uses_job_id_in_name(self):
        """Test that config filename includes job ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS,
                job_id="my_docking_job"
            )
            
            assert "my_docking_job_config.txt" in config_path


class TestCustomGridParams:
    """Tests for custom grid box parameters."""
    
    def test_custom_center_coordinates(self):
        """Test custom center coordinates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            custom_grid = GridBoxParams(
                center_x=-15.5,
                center_y=42.3,
                center_z=0.0,
                size_x=30.0,
                size_y=35.0,
                size_z=40.0
            )
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=custom_grid
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "center_x = -15.50" in content
            assert "center_y = 42.30" in content
            assert "center_z = 0.00" in content
            assert "size_x = 30.00" in content
            assert "size_y = 35.00" in content
            assert "size_z = 40.00" in content
    
    def test_cpu_parameter(self):
        """Test that CPU parameter is included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            custom_params = DockingParams(cpu=8)
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS,
                docking_params=custom_params
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            assert "cpu = 8" in content


class TestConfigurationCompleteness:
    """Tests for Property 17: Configuration file completeness."""
    
    def test_all_required_fields_present(self):
        """Test that all required Vina fields are present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            required_fields = [
                'receptor',
                'ligand',
                'out',
                'center_x',
                'center_y',
                'center_z',
                'size_x',
                'size_y',
                'size_z',
                'exhaustiveness',
                'num_modes',
                'energy_range',
                'cpu'
            ]
            
            for field in required_fields:
                assert f"{field} =" in content, f"Missing field: {field}"
    
    def test_config_is_valid_vina_format(self):
        """Test that config can be parsed as Vina format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            receptor_path = os.path.join(tmpdir, "receptor.pdbqt")
            ligand_path = os.path.join(tmpdir, "ligand.pdbqt")
            output_path = os.path.join(tmpdir, "output.pdbqt")
            
            with open(receptor_path, 'w') as f:
                f.write("ATOM mock receptor")
            with open(ligand_path, 'w') as f:
                f.write("ATOM mock ligand")
            
            generator = ConfigFileGenerator(tmpdir)
            config_path = generator.generate_config(
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                output_path=output_path,
                grid_params=SAMPLE_GRID_PARAMS
            )
            
            # Parse config to verify format
            config_dict = {}
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config_dict[key.strip()] = value.strip()
            
            # Verify numeric values can be parsed
            assert float(config_dict['center_x']) == 10.0
            assert float(config_dict['center_y']) == 20.0
            assert float(config_dict['center_z']) == 30.0
            assert int(config_dict['exhaustiveness']) == 8
            assert int(config_dict['num_modes']) == 9
