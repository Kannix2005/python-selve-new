#!/usr/bin/env python3
"""
Automated Setup and Test Runner for python-selve

This script automatically:
1. Checks Python version compatibility
2. Sets up virtual environment (optional)
3. Installs all dependencies
4. Detects hardware automatically
5. Runs appropriate test suites
6. Generates reports

Usage:
    python setup_and_test.py [options]

Examples:
    python setup_and_test.py                    # Full auto setup and test
    python setup_and_test.py --no-venv          # Skip virtual environment
    python setup_and_test.py --quick            # Quick setup and unit tests only
    python setup_and_test.py --force-hardware   # Force hardware tests even if none detected
"""

import argparse
import sys
import os
import subprocess
import logging
import tempfile
import shutil
import time
from pathlib import Path
from typing import Optional, List, Tuple

# Configuration
MIN_PYTHON_VERSION = (3, 8)
PROJECT_NAME = "python-selve"
VENV_NAME = "venv"

# Colors for console output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    @staticmethod
    def colorize(text: str, color: str) -> str:
        """Add color to text if terminal supports it"""
        if os.name == 'nt':  # Windows
            return text  # Windows console might not support colors
        return f"{color}{text}{Colors.END}"

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(Colors.colorize(f" {title} ", Colors.BOLD + Colors.CYAN))
    print("=" * 60)

def print_step(step: str):
    """Print a step indicator"""
    print(f"\n{Colors.colorize('→', Colors.BLUE)} {step}")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.colorize('✓', Colors.GREEN)} {message}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.colorize('⚠', Colors.YELLOW)} {message}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.colorize('✗', Colors.RED)} {message}")

def print_info(message: str):
    """Print info message"""
    print(f"{Colors.colorize('ℹ', Colors.BLUE)} {message}")

class EnvironmentManager:
    """Manages Python environment setup and dependencies"""
    
    def __init__(self, project_root: Path, use_venv: bool = True):
        self.project_root = project_root
        self.use_venv = use_venv
        self.venv_path = project_root / VENV_NAME
        self.python_exe = self._get_python_executable()
        
    def _get_python_executable(self) -> str:
        """Get the Python executable path"""
        if self.use_venv and self.venv_path.exists():
            if os.name == 'nt':  # Windows
                return str(self.venv_path / "Scripts" / "python.exe")
            else:  # Unix-like
                return str(self.venv_path / "bin" / "python")
        return sys.executable
    
    def check_python_version(self) -> bool:
        """Check if Python version meets requirements"""
        print_step("Checking Python version...")
        
        version = sys.version_info
        required = MIN_PYTHON_VERSION
        
        if version >= required:
            print_success(f"Python {version.major}.{version.minor}.{version.micro} ✓")
            return True
        else:
            print_error(f"Python {required[0]}.{required[1]}+ required, got {version.major}.{version.minor}.{version.micro}")
            return False
    
    def create_virtual_environment(self) -> bool:
        """Create virtual environment if requested"""
        if not self.use_venv:
            print_info("Skipping virtual environment creation")
            return True
            
        print_step("Setting up virtual environment...")
        
        if self.venv_path.exists():
            print_warning(f"Virtual environment already exists at {self.venv_path}")
            response = input("Do you want to recreate it? (y/N): ").strip().lower()
            if response == 'y':
                print_info("Removing existing virtual environment...")
                shutil.rmtree(self.venv_path)
            else:
                print_info("Using existing virtual environment")
                return True
        
        try:
            # Create virtual environment
            subprocess.run([
                sys.executable, "-m", "venv", str(self.venv_path)
            ], check=True, capture_output=True)
            
            print_success(f"Virtual environment created at {self.venv_path}")
            
            # Update python executable path
            self.python_exe = self._get_python_executable()
            
            # Upgrade pip
            self._run_pip_command(["install", "--upgrade", "pip"])
            
            return True
            
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to create virtual environment: {e}")
            return False
    
    def _run_pip_command(self, args: List[str]) -> bool:
        """Run a pip command"""
        try:
            cmd = [self.python_exe, "-m", "pip"] + args
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Pip command failed: {e}")
            if e.stdout:
                print(f"STDOUT: {e.stdout}")
            if e.stderr:
                print(f"STDERR: {e.stderr}")
            return False
    
    def install_dependencies(self) -> bool:
        """Install project dependencies"""
        print_step("Installing dependencies...")
        
        # Core dependencies
        core_deps = [
            "pyserial>=3.5",
            "untangle>=1.1.1",
        ]
        
        # Test dependencies
        test_deps = [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "pytest-cov>=4.0.0",
            "psutil>=5.9.0",
        ]
        
        # Development dependencies
        dev_deps = [
            "black",
            "flake8",
            "mypy",
        ]
        
        # Install core dependencies
        print_info("Installing core dependencies...")
        if not self._run_pip_command(["install"] + core_deps):
            return False
        print_success("Core dependencies installed")
        
        # Install test dependencies
        print_info("Installing test dependencies...")
        if not self._run_pip_command(["install"] + test_deps):
            print_warning("Some test dependencies failed to install")
        else:
            print_success("Test dependencies installed")
        
        # Install development dependencies (optional)
        print_info("Installing development dependencies...")
        if not self._run_pip_command(["install"] + dev_deps):
            print_warning("Some development dependencies failed to install (optional)")
        else:
            print_success("Development dependencies installed")
        
        return True
    
    def verify_installation(self) -> bool:
        """Verify that key dependencies are installed"""
        print_step("Verifying installation...")
        
        required_modules = [
            "serial",
            "untangle", 
            "pytest",
            "pytest_asyncio"
        ]
        
        all_good = True
        for module in required_modules:
            try:
                subprocess.run([
                    self.python_exe, "-c", f"import {module}"
                ], check=True, capture_output=True)
                print_success(f"{module} ✓")
            except subprocess.CalledProcessError:
                print_error(f"{module} ✗")
                all_good = False
        
        return all_good

class HardwareDetector:
    """Detects and manages hardware for testing"""
    
    def __init__(self):
        self.detected_ports: List[Tuple[str, str]] = []
        self.selve_port: Optional[str] = None
    
    def detect_serial_ports(self) -> bool:
        """Detect available serial ports"""
        print_step("Detecting serial ports...")
        
        try:
            # Try to import serial tools
            import serial.tools.list_ports as list_ports
            
            ports = list_ports.comports()
            self.detected_ports = [(port.device, port.description) for port in ports]
            
            if not self.detected_ports:
                print_warning("No serial ports detected")
                return False
            
            print_info(f"Found {len(self.detected_ports)} serial port(s):")
            for device, description in self.detected_ports:
                print(f"  {device}: {description}")
            
            return True
            
        except ImportError:
            print_error("pyserial not installed - cannot detect hardware")
            return False
        except Exception as e:
            print_error(f"Error detecting serial ports: {e}")
            return False
    
    def detect_selve_hardware(self) -> Optional[str]:
        """Detect Selve Gateway hardware specifically"""
        print_step("Detecting Selve Gateway hardware...")
        
        if not self.detected_ports:
            self.detect_serial_ports()
        
        # Keywords that might indicate Selve Gateway or compatible hardware
        selve_keywords = [
            'usb', 'serial', 'cp210', 'ftdi', 'ch340', 'prolific', 'pl2303'
        ]
        
        candidates = []
        for device, description in self.detected_ports:
            desc_lower = description.lower()
            if any(keyword in desc_lower for keyword in selve_keywords):
                candidates.append((device, description))
        
        if not candidates:
            print_warning("No potential Selve Gateway hardware detected")
            return None
        
        if len(candidates) == 1:
            device, description = candidates[0]
            print_success(f"Potential Selve Gateway detected: {device} ({description})")
            self.selve_port = device
            return device
        
        # Multiple candidates - let user choose
        print_info(f"Multiple potential devices found:")
        for i, (device, description) in enumerate(candidates, 1):
            print(f"  {i}. {device}: {description}")
        
        while True:
            try:
                choice = input(f"Select device (1-{len(candidates)}, or 0 to skip): ").strip()
                if choice == '0':
                    print_info("Skipping hardware selection")
                    return None
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(candidates):
                    device, description = candidates[choice_idx]
                    print_success(f"Selected: {device} ({description})")
                    self.selve_port = device
                    return device
                else:
                    print_error("Invalid choice")
            except (ValueError, KeyboardInterrupt):
                print_info("Skipping hardware selection")
                return None
    
    def test_hardware_connection(self, port: str) -> bool:
        """Test if we can connect to the hardware"""
        print_step(f"Testing connection to {port}...")
        
        try:
            import serial
            
            # Try to open the port
            with serial.Serial(port, 115200, timeout=1) as ser:
                print_success(f"Successfully opened {port}")
                return True
                
        except Exception as e:
            print_warning(f"Could not connect to {port}: {e}")
            return False

class TestRunner:
    """Runs tests based on available hardware and configuration"""
    
    def __init__(self, env_manager: EnvironmentManager, hardware_detector: HardwareDetector):
        self.env_manager = env_manager
        self.hardware_detector = hardware_detector
        self.project_root = env_manager.project_root
    
    def run_tests(self, test_types: List[str], force_hardware: bool = False) -> bool:
        """Run specified test types"""
        print_header("Running Tests")
        
        # Determine what tests to run
        if "auto" in test_types:
            test_types = self._determine_auto_tests(force_hardware)
        
        all_passed = True
        
        for test_type in test_types:
            if not self._run_single_test_type(test_type, force_hardware):
                all_passed = False
        
        return all_passed
    
    def _determine_auto_tests(self, force_hardware: bool) -> List[str]:
        """Automatically determine which tests to run"""
        tests = ["unit", "structure", "integration"]
        
        # Add hardware tests if hardware available or forced
        if self.hardware_detector.selve_port or force_hardware:
            tests.append("hardware")
        
        # Add performance tests
        tests.append("performance")
        
        return tests
    
    def _run_single_test_type(self, test_type: str, force_hardware: bool = False) -> bool:
        """Run a single type of test"""
        print_step(f"Running {test_type} tests...")
        
        cmd = [self.env_manager.python_exe, "-m", "pytest"]
        
        # Configure based on test type
        if test_type == "unit":
            cmd.extend(["-m", "not hardware and not stress"])
            cmd.extend(["tests/test_selve_unit.py", "tests/test_selve_structure.py"])
            
        elif test_type == "structure":
            cmd.extend(["tests/test_selve_structure.py"])
            
        elif test_type == "integration":
            cmd.extend(["-m", "not hardware and not stress"])
            cmd.extend(["tests/test_selve_integration.py"])
            
        elif test_type == "performance":
            cmd.extend(["-m", "not hardware and not stress"])
            cmd.extend(["tests/test_selve_advanced.py"])
            
        elif test_type == "hardware":
            if not self.hardware_detector.selve_port and not force_hardware:
                print_warning("No hardware detected, skipping hardware tests")
                return True
            
            cmd.extend(["-m", "hardware"])
            cmd.extend(["tests/test_selve_hardware.py"])
            
            # Set hardware port environment variable
            if self.hardware_detector.selve_port:
                os.environ['SELVE_TEST_PORT'] = self.hardware_detector.selve_port
            
        elif test_type == "all":
            cmd.extend(["tests/"])
            
        else:
            print_error(f"Unknown test type: {test_type}")
            return False
        
        # Add common options
        cmd.extend(["-v", "--tb=short"])
        
        # Add coverage for comprehensive tests
        if test_type in ["all", "unit"]:
            cmd.extend(["--cov=selve", "--cov-report=term-missing"])
        
        # Run the test
        try:
            print_info(f"Command: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=self.project_root)
            
            if result.returncode == 0:
                print_success(f"{test_type} tests passed!")
                return True
            else:
                print_error(f"{test_type} tests failed!")
                return False
                
        except Exception as e:
            print_error(f"Error running {test_type} tests: {e}")
            return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Automated setup and test runner for python-selve",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_and_test.py                     # Full auto setup and test
  python setup_and_test.py --quick             # Quick setup and unit tests only
  python setup_and_test.py --no-venv           # Skip virtual environment
  python setup_and_test.py --force-hardware    # Force hardware tests
  python setup_and_test.py --tests unit        # Only unit tests
        """
    )
    
    parser.add_argument(
        "--no-venv",
        action="store_true",
        help="Skip virtual environment creation"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick setup: only install essentials and run unit tests"
    )
    
    parser.add_argument(
        "--force-hardware",
        action="store_true",
        help="Force hardware tests even if no hardware detected"
    )
    
    parser.add_argument(
        "--tests",
        nargs="+",
        choices=["unit", "structure", "integration", "performance", "hardware", "all", "auto"],
        default=["auto"],
        help="Specify which tests to run (default: auto)"
    )
    
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip dependency installation"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Get project root
    project_root = Path(__file__).parent
    
    print_header(f"Python Selve - Automated Setup & Test")
    print_info(f"Project root: {project_root}")
    print_info(f"Python: {sys.executable}")
    
    # Initialize managers
    env_manager = EnvironmentManager(project_root, use_venv=not args.no_venv)
    hardware_detector = HardwareDetector()
    test_runner = TestRunner(env_manager, hardware_detector)
    
    success = True
    
    try:
        # Step 1: Check Python version
        if not env_manager.check_python_version():
            print_error("Python version check failed")
            return 1
        
        # Step 2: Setup virtual environment
        if not args.quick and not env_manager.create_virtual_environment():
            print_error("Virtual environment setup failed")
            return 1
        
        # Step 3: Install dependencies
        if not args.skip_install:
            if not env_manager.install_dependencies():
                print_error("Dependency installation failed")
                return 1
            
            if not env_manager.verify_installation():
                print_error("Installation verification failed")
                return 1
        
        # Step 4: Detect hardware
        hardware_detector.detect_selve_hardware()
        
        # Step 5: Test hardware connection if available
        if hardware_detector.selve_port:
            hardware_detector.test_hardware_connection(hardware_detector.selve_port)
        
        # Step 6: Run tests
        test_types = ["unit"] if args.quick else args.tests
        if not test_runner.run_tests(test_types, args.force_hardware):
            success = False
        
        # Final summary
        print_header("Setup and Test Summary")
        
        if success:
            print_success("All operations completed successfully!")
            print_info("Your python-selve environment is ready!")
            
            if hardware_detector.selve_port:
                print_info(f"Hardware detected on: {hardware_detector.selve_port}")
                print_info("You can run hardware tests with: python run_tests.py --type hardware")
            else:
                print_info("No hardware detected - unit tests available")
                print_info("Connect Selve Gateway and run: python run_tests.py --type hardware")
                
        else:
            print_error("Some operations failed - check output above")
            return 1
            
    except KeyboardInterrupt:
        print_warning("\nSetup interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
