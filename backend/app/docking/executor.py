"""AutoDock Vina executor for molecular docking.

This module handles execution of AutoDock Vina subprocess with proper
timeout handling, error capture, and output parsing.
"""

import asyncio
import logging
import os
import subprocess
import shutil
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class VinaExecutor:
    """Executor for AutoDock Vina docking calculations.
    
    Handles subprocess execution with timeout, captures output,
    and manages errors gracefully.
    """
    
    DEFAULT_TIMEOUT = 1800  # 30 minutes
    
    def __init__(
        self,
        vina_path: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """Initialize the Vina executor.
        
        Args:
            vina_path: Path to Vina executable (auto-detected if None)
            timeout: Maximum execution time in seconds
        """
        self.vina_path = vina_path or self._find_vina()
        self.timeout = timeout
    
    def _find_vina(self) -> str:
        """Find AutoDock Vina executable in system PATH.
        
        Returns:
            Path to vina executable
        
        Raises:
            FileNotFoundError: If Vina is not installed
        """
        # Check common names and paths
        vina_names = ['vina', 'vina_1.2.5_linux_x86_64', 'vina.exe', 'autodock_vina']
        
        for name in vina_names:
            path = shutil.which(name)
            if path:
                logger.info(f"Found Vina at: {path}")
                return path
        
        # Check backend tools folder first
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        tools_path = os.path.join(backend_dir, 'tools', 'vina.exe')
        if os.path.exists(tools_path):
            logger.info(f"Found Vina at: {tools_path}")
            return tools_path
        
        # Check common installation directories
        common_paths = [
            '/usr/local/bin/vina',
            '/usr/bin/vina',
            'C:\\Program Files\\Vina\\vina.exe',
            os.path.expanduser('~/bin/vina'),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                logger.info(f"Found Vina at: {path}")
                return path
        
        raise FileNotFoundError(
            "AutoDock Vina not found. Please install it and ensure it's in PATH."
        )
    
    async def execute(
        self,
        config_path: str,
        log_path: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """Execute AutoDock Vina with configuration file.
        
        Args:
            config_path: Path to Vina configuration file
            log_path: Optional path for log file output
        
        Returns:
            Tuple of (success, stdout_output, error_message)
        """
        if not os.path.exists(config_path):
            return False, "", f"Configuration file not found: {config_path}"
        
        start_time = datetime.utcnow()
        logger.info(f"Starting Vina execution with config: {config_path}")
        
        try:
            # Build command
            cmd = [self.vina_path, '--config', config_path]
            
            # Execute with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return False, "", f"Docking timed out after {self.timeout} seconds"
            
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')
            
            # Log output if requested
            if log_path:
                with open(log_path, 'w') as f:
                    f.write(f"=== STDOUT ===\n{stdout_text}\n")
                    f.write(f"=== STDERR ===\n{stderr_text}\n")
            
            # Check return code
            if process.returncode != 0:
                error_msg = stderr_text or f"Vina exited with code {process.returncode}"
                logger.error(f"Vina failed: {error_msg}")
                return False, stdout_text, error_msg
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Vina completed in {elapsed:.1f} seconds")
            
            return True, stdout_text, None
            
        except FileNotFoundError:
            return False, "", f"Vina executable not found at: {self.vina_path}"
        except Exception as e:
            logger.error(f"Vina execution error: {str(e)}")
            return False, "", str(e)
    
    def execute_sync(
        self,
        config_path: str,
        log_path: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """Synchronous version of execute for use in Celery tasks.
        
        Args:
            config_path: Path to Vina configuration file
            log_path: Optional path for log file output
        
        Returns:
            Tuple of (success, stdout_output, error_message)
        """
        if not os.path.exists(config_path):
            return False, "", f"Configuration file not found: {config_path}"
        
        start_time = datetime.utcnow()
        logger.info(f"Starting Vina execution with config: {config_path}")
        
        try:
            cmd = [self.vina_path, '--config', config_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            stdout_text = result.stdout
            stderr_text = result.stderr
            
            if log_path:
                with open(log_path, 'w') as f:
                    f.write(f"=== STDOUT ===\n{stdout_text}\n")
                    f.write(f"=== STDERR ===\n{stderr_text}\n")
            
            if result.returncode != 0:
                error_msg = stderr_text or f"Vina exited with code {result.returncode}"
                logger.error(f"Vina failed: {error_msg}")
                return False, stdout_text, error_msg
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Vina completed in {elapsed:.1f} seconds")
            
            return True, stdout_text, None
            
        except subprocess.TimeoutExpired:
            return False, "", f"Docking timed out after {self.timeout} seconds"
        except FileNotFoundError:
            return False, "", f"Vina executable not found at: {self.vina_path}"
        except Exception as e:
            logger.error(f"Vina execution error: {str(e)}")
            return False, "", str(e)
    
    def is_available(self) -> bool:
        """Check if AutoDock Vina is available and working.
        
        Returns:
            True if Vina can be executed
        """
        try:
            result = subprocess.run(
                [self.vina_path, '--help'],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_version(self) -> Optional[str]:
        """Get AutoDock Vina version string.
        
        Returns:
            Version string or None if not available
        """
        try:
            result = subprocess.run(
                [self.vina_path, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
