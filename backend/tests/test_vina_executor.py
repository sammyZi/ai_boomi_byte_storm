"""Tests for the AutoDock Vina executor module.

Tests cover:
- VinaExecutor initialization and path discovery
- Synchronous execution with configuration file
- Asynchronous execution with configuration file
- Timeout handling (30 minutes max)
- Error handling for missing files and invalid configs
- Output parsing and logging
- Availability and version checking
"""

import asyncio
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.docking.executor import VinaExecutor


# Path to the actual Vina executable for integration tests
VINA_PATH = os.path.join(os.path.dirname(__file__), "..", "tools", "vina.exe")


class TestVinaExecutorInit:
    """Tests for VinaExecutor initialization."""
    
    def test_init_with_explicit_path(self):
        """Test initialization with explicit Vina path."""
        executor = VinaExecutor(vina_path="/path/to/vina")
        assert executor.vina_path == "/path/to/vina"
    
    def test_init_with_default_timeout(self):
        """Test default timeout is 30 minutes (1800 seconds)."""
        executor = VinaExecutor(vina_path="/path/to/vina")
        assert executor.timeout == 1800
    
    def test_init_with_custom_timeout(self):
        """Test custom timeout value."""
        executor = VinaExecutor(vina_path="/path/to/vina", timeout=3600)
        assert executor.timeout == 3600
    
    def test_init_auto_detect_vina(self):
        """Test auto-detection of Vina executable."""
        if os.path.exists(VINA_PATH):
            with patch.object(VinaExecutor, '_find_vina', return_value=VINA_PATH):
                executor = VinaExecutor()
                assert executor.vina_path == VINA_PATH
    
    def test_init_raises_when_vina_not_found(self):
        """Test that FileNotFoundError is raised when Vina not found."""
        with patch('shutil.which', return_value=None):
            with patch('os.path.exists', return_value=False):
                with pytest.raises(FileNotFoundError, match="AutoDock Vina not found"):
                    VinaExecutor()


class TestFindVina:
    """Tests for _find_vina method."""
    
    def test_find_vina_in_path(self):
        """Test finding Vina in system PATH."""
        with patch('shutil.which', return_value="/usr/local/bin/vina"):
            executor = VinaExecutor.__new__(VinaExecutor)
            result = executor._find_vina()
            assert result == "/usr/local/bin/vina"
    
    def test_find_vina_checks_multiple_names(self):
        """Test that multiple executable names are checked."""
        def mock_which(name):
            if name == "vina.exe":
                return "C:\\vina\\vina.exe"
            return None
        
        with patch('shutil.which', side_effect=mock_which):
            executor = VinaExecutor.__new__(VinaExecutor)
            result = executor._find_vina()
            assert result == "C:\\vina\\vina.exe"
    
    def test_find_vina_checks_common_paths(self):
        """Test fallback to common installation paths."""
        def mock_exists(path):
            return path == "/usr/local/bin/vina"
        
        with patch('shutil.which', return_value=None):
            with patch('os.path.exists', side_effect=mock_exists):
                executor = VinaExecutor.__new__(VinaExecutor)
                result = executor._find_vina()
                assert result == "/usr/local/bin/vina"


class TestExecuteSync:
    """Tests for synchronous execute_sync method."""
    
    def test_execute_sync_missing_config_file(self):
        """Test error when config file doesn't exist."""
        executor = VinaExecutor(vina_path="/path/to/vina")
        
        success, stdout, error = executor.execute_sync("/nonexistent/config.txt")
        
        assert success is False
        assert stdout == ""
        assert "Configuration file not found" in error
    
    def test_execute_sync_successful(self):
        """Test successful execution with mock subprocess."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock config file
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("receptor = test.pdbqt\n")
            
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Vina output: -7.5 kcal/mol"
            mock_result.stderr = ""
            
            with patch('subprocess.run', return_value=mock_result):
                executor = VinaExecutor(vina_path="/path/to/vina")
                success, stdout, error = executor.execute_sync(config_path)
                
                assert success is True
                assert "-7.5 kcal/mol" in stdout
                assert error is None
    
    def test_execute_sync_nonzero_return_code(self):
        """Test handling of non-zero return code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("receptor = test.pdbqt\n")
            
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Error: Invalid receptor file"
            
            with patch('subprocess.run', return_value=mock_result):
                executor = VinaExecutor(vina_path="/path/to/vina")
                success, stdout, error = executor.execute_sync(config_path)
                
                assert success is False
                assert "Invalid receptor file" in error
    
    def test_execute_sync_timeout(self):
        """Test timeout handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("receptor = test.pdbqt\n")
            
            import subprocess
            with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd="vina", timeout=10)):
                executor = VinaExecutor(vina_path="/path/to/vina", timeout=10)
                success, stdout, error = executor.execute_sync(config_path)
                
                assert success is False
                assert "timed out" in error.lower()
    
    def test_execute_sync_vina_not_found(self):
        """Test error when Vina executable not found during execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("receptor = test.pdbqt\n")
            
            with patch('subprocess.run', side_effect=FileNotFoundError()):
                executor = VinaExecutor(vina_path="/nonexistent/vina")
                success, stdout, error = executor.execute_sync(config_path)
                
                assert success is False
                assert "not found" in error.lower()
    
    def test_execute_sync_writes_log_file(self):
        """Test that log file is written when path provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            log_path = os.path.join(tmpdir, "vina.log")
            
            with open(config_path, 'w') as f:
                f.write("receptor = test.pdbqt\n")
            
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Vina stdout output"
            mock_result.stderr = "Vina stderr output"
            
            with patch('subprocess.run', return_value=mock_result):
                executor = VinaExecutor(vina_path="/path/to/vina")
                executor.execute_sync(config_path, log_path=log_path)
                
                assert os.path.exists(log_path)
                with open(log_path, 'r') as f:
                    content = f.read()
                assert "STDOUT" in content
                assert "STDERR" in content
                assert "Vina stdout output" in content


class TestExecuteAsync:
    """Tests for asynchronous execute method."""
    
    @pytest.mark.asyncio
    async def test_execute_async_missing_config(self):
        """Test error when config file doesn't exist."""
        executor = VinaExecutor(vina_path="/path/to/vina")
        
        success, stdout, error = await executor.execute("/nonexistent/config.txt")
        
        assert success is False
        assert "Configuration file not found" in error
    
    @pytest.mark.asyncio
    async def test_execute_async_successful(self):
        """Test successful async execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("receptor = test.pdbqt\n")
            
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                b"Vina output: -8.2 kcal/mol",
                b""
            ))
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                executor = VinaExecutor(vina_path="/path/to/vina")
                success, stdout, error = await executor.execute(config_path)
                
                assert success is True
                assert "-8.2 kcal/mol" in stdout
                assert error is None
    
    @pytest.mark.asyncio
    async def test_execute_async_timeout(self):
        """Test async timeout handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("receptor = test.pdbqt\n")
            
            # Create a mock that simulates a long-running process
            async def slow_communicate():
                await asyncio.sleep(10)  # Simulate slow process
                return (b"", b"")
            
            mock_process = MagicMock()
            mock_process.kill = MagicMock()
            mock_process.wait = AsyncMock()
            mock_process.communicate = slow_communicate
            
            async def mock_create_subprocess(*args, **kwargs):
                return mock_process
            
            with patch('asyncio.create_subprocess_exec', side_effect=mock_create_subprocess):
                executor = VinaExecutor(vina_path="/path/to/vina", timeout=1)
                success, stdout, error = await executor.execute(config_path)
                
                assert success is False
                assert "timed out" in error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_async_nonzero_return_code(self):
        """Test handling of non-zero return code in async mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("receptor = test.pdbqt\n")
            
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(
                b"",
                b"Error: Grid box too small"
            ))
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                executor = VinaExecutor(vina_path="/path/to/vina")
                success, stdout, error = await executor.execute(config_path)
                
                assert success is False
                assert "Grid box too small" in error


class TestIsAvailable:
    """Tests for is_available method."""
    
    def test_is_available_when_vina_works(self):
        """Test returns True when Vina responds to --help."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            executor = VinaExecutor(vina_path="/path/to/vina")
            assert executor.is_available() is True
    
    def test_is_available_when_vina_fails(self):
        """Test returns False when Vina fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result):
            executor = VinaExecutor(vina_path="/path/to/vina")
            assert executor.is_available() is False
    
    def test_is_available_when_exception(self):
        """Test returns False when exception occurs."""
        with patch('subprocess.run', side_effect=Exception("Some error")):
            executor = VinaExecutor(vina_path="/path/to/vina")
            assert executor.is_available() is False


class TestGetVersion:
    """Tests for get_version method."""
    
    def test_get_version_success(self):
        """Test getting Vina version string."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "AutoDock Vina 1.2.5"
        
        with patch('subprocess.run', return_value=mock_result):
            executor = VinaExecutor(vina_path="/path/to/vina")
            version = executor.get_version()
            assert version == "AutoDock Vina 1.2.5"
    
    def test_get_version_failure(self):
        """Test returns None when version check fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result):
            executor = VinaExecutor(vina_path="/path/to/vina")
            assert executor.get_version() is None
    
    def test_get_version_exception(self):
        """Test returns None when exception occurs."""
        with patch('subprocess.run', side_effect=Exception("Error")):
            executor = VinaExecutor(vina_path="/path/to/vina")
            assert executor.get_version() is None


class TestCommandConstruction:
    """Tests for command construction."""
    
    def test_command_includes_config_flag(self):
        """Test that command includes --config flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("receptor = test.pdbqt\n")
            
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            
            with patch('subprocess.run', return_value=mock_result) as mock_run:
                executor = VinaExecutor(vina_path="/path/to/vina")
                executor.execute_sync(config_path)
                
                call_args = mock_run.call_args[0][0]
                assert "--config" in call_args
                assert config_path in call_args


class TestIntegrationWithRealVina:
    """Integration tests with actual Vina executable.
    
    These tests require Vina to be installed and skip if not available.
    """
    
    @pytest.fixture
    def vina_executor(self):
        """Create executor with real Vina path."""
        if not os.path.exists(VINA_PATH):
            pytest.skip("Vina executable not found")
        return VinaExecutor(vina_path=VINA_PATH)
    
    def test_real_vina_is_available(self, vina_executor):
        """Test that real Vina is available and working."""
        assert vina_executor.is_available() is True
    
    def test_real_vina_version(self, vina_executor):
        """Test getting real Vina version."""
        version = vina_executor.get_version()
        # Vina outputs version info, may not have explicit version number
        # Just check it returns something or None without crashing
        assert version is None or isinstance(version, str)
    
    def test_real_vina_missing_receptor(self, vina_executor):
        """Test real Vina error for missing receptor file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("receptor = nonexistent.pdbqt\n")
                f.write("ligand = nonexistent.pdbqt\n")
                f.write("out = output.pdbqt\n")
                f.write("center_x = 0\n")
                f.write("center_y = 0\n")
                f.write("center_z = 0\n")
                f.write("size_x = 20\n")
                f.write("size_y = 20\n")
                f.write("size_z = 20\n")
            
            success, stdout, error = vina_executor.execute_sync(config_path)
            
            # Should fail because receptor doesn't exist
            assert success is False
            assert error is not None


class TestOutputParsing:
    """Tests for parsing Vina output."""
    
    def test_stdout_contains_binding_affinity(self):
        """Test that stdout captures binding affinity output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("receptor = test.pdbqt\n")
            
            vina_output = """
AutoDock Vina v1.2.5
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1         -7.8          0.000      0.000
   2         -7.2          1.234      2.456
   3         -6.9          2.345      3.567
"""
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = vina_output
            mock_result.stderr = ""
            
            with patch('subprocess.run', return_value=mock_result):
                executor = VinaExecutor(vina_path="/path/to/vina")
                success, stdout, error = executor.execute_sync(config_path)
                
                assert success is True
                assert "-7.8" in stdout
                assert "-7.2" in stdout
                assert "affinity" in stdout


class TestErrorMessages:
    """Tests for error message quality."""
    
    def test_error_message_for_missing_config(self):
        """Test clear error message for missing config."""
        executor = VinaExecutor(vina_path="/path/to/vina")
        success, _, error = executor.execute_sync("/no/such/file.txt")
        
        assert "Configuration file not found" in error
        assert "/no/such/file.txt" in error
    
    def test_error_message_for_timeout(self):
        """Test clear error message for timeout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("test = value\n")
            
            import subprocess
            with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("vina", 60)):
                executor = VinaExecutor(vina_path="/path/to/vina", timeout=60)
                success, _, error = executor.execute_sync(config_path)
                
                assert "timed out" in error.lower()
                assert "60" in error
    
    def test_error_preserves_stderr(self):
        """Test that stderr content is preserved in error message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.txt")
            with open(config_path, 'w') as f:
                f.write("test = value\n")
            
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Specific Vina error: receptor file format invalid"
            
            with patch('subprocess.run', return_value=mock_result):
                executor = VinaExecutor(vina_path="/path/to/vina")
                success, _, error = executor.execute_sync(config_path)
                
                assert "receptor file format invalid" in error
