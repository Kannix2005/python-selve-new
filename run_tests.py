 #!/usr/bin/env python3
"""
Test runner script for python-selve

This script provides an easy way to run different types of tests:
- Unit tests (default): Fast tests with mocks
- Hardware tests: Tests requiring actual Selve Gateway hardware
- Integration tests: Tests that verify component interactions
- Performance tests: Tests that measure performance characteristics
- All tests: Complete test suite

Usage:
    python run_tests.py [--type TYPE] [--verbose] [--coverage] [--hardware-port PORT]

Examples:
    python run_tests.py                    # Run unit tests only
    python run_tests.py --type hardware    # Run hardware tests (requires hardware)
    python run_tests.py --type all         # Run all tests
    python run_tests.py --coverage         # Run with coverage report
"""

import argparse
import sys
import os
import subprocess
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging(verbose=False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def check_dependencies():
    """Check if test dependencies are installed"""
    try:
        import pytest
        import pytest_asyncio
        return True
    except ImportError as e:
        print(f"Missing test dependencies: {e}")
        print("Install test dependencies with:")
        print("  pip install -r tests/requirements.txt")
        return False

def detect_hardware():
    """Detect if Selve Gateway hardware is available"""
    try:
        from serial.tools import list_ports
        
        ports = list_ports.comports()
        for port in ports:
            if any(keyword in port.description.lower() for keyword in 
                   ['usb', 'serial', 'cp210', 'ftdi', 'ch340']):
                print(f"Potential hardware detected on {port.device}: {port.description}")
                return port.device
    except Exception:
        pass
    
    print("No Selve Gateway hardware detected")
    return None

def run_tests(test_type="unit", verbose=False, coverage=False, hardware_port=None):
    """Run the specified type of tests"""
    
    if not check_dependencies():
        return False
    
    # Determine Python executable
    python_cmd = "python"
    if os.path.exists("venv/Scripts/python.exe"):
        python_cmd = "venv/Scripts/python.exe"
    elif os.path.exists("venv\\Scripts\\python.exe"):
        python_cmd = "venv\\Scripts\\python.exe"
    
    # Base pytest command
    cmd = [python_cmd, "-m", "pytest"]
    
    # Add verbosity
    if verbose:
        cmd.extend(["-v", "-s"])
    else:
        cmd.append("-q")
    
    # Add coverage
    if coverage:
        cmd.extend(["--cov=selve", "--cov-report=html", "--cov-report=term"])
    
    # Select tests based on type
    if test_type == "unit":
        cmd.extend(["-m", "not hardware and not stress"])
        cmd.append("tests/test_selve_unit.py")
        cmd.append("tests/test_selve_structure.py")
        
    elif test_type == "hardware":
        hardware_detected = detect_hardware()
        if not hardware_detected and not hardware_port:
            print("No hardware detected. Skipping hardware tests.")
            print("Use --hardware-port PORT to specify a port manually.")
            return True
        
        cmd.extend(["-m", "hardware"])
        cmd.append("tests/test_selve_hardware.py")
        
        if hardware_port:
            os.environ['SELVE_TEST_PORT'] = hardware_port
            
    elif test_type == "integration":
        cmd.extend(["-m", "not hardware and not stress"])
        cmd.append("tests/test_selve_integration.py")
        
    elif test_type == "performance":
        cmd.extend(["-m", "not hardware"])
        cmd.append("tests/test_selve_advanced.py")
        
    elif test_type == "stress":
        hardware_detected = detect_hardware()
        if not hardware_detected:
            print("No hardware detected. Skipping stress tests.")
            return True
            
        cmd.extend(["-m", "stress"])
        cmd.append("tests/test_selve_hardware.py")
        
    elif test_type == "all":
        cmd.append("tests/")
        
    else:
        print(f"Unknown test type: {test_type}")
        return False
    
    # Run the tests
    print(f"Running {test_type} tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return False
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Test runner for python-selve",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test types:
  unit         Unit tests with mocks (default, fast)
  hardware     Hardware integration tests (requires Selve Gateway)
  integration  Integration tests with mocks
  performance  Performance and memory tests
  stress       Stress tests (requires hardware, slow)
  all          All tests

Examples:
  python run_tests.py                           # Run unit tests (default)
  python run_tests.py --unit                    # Run unit tests
  python run_tests.py --hardware                # Run hardware tests
  python run_tests.py --integration             # Run integration tests
  python run_tests.py --all                     # Run all tests
  python run_tests.py --all --coverage          # All tests with coverage
  python run_tests.py --hardware-port COM3      # Specify hardware port
        """
    )
    
    parser.add_argument(
        "--type", "-t",
        choices=["unit", "hardware", "integration", "performance", "stress", "all"],
        default="unit",
        help="Type of tests to run (default: unit)"
    )
    
    parser.add_argument(
        "--all",
        action="store_const",
        const="all",
        dest="type",
        help="Run all tests (same as --type all)"
    )
    
    parser.add_argument(
        "--unit",
        action="store_const",
        const="unit",
        dest="type",
        help="Run unit tests only (same as --type unit)"
    )
    
    parser.add_argument(
        "--hardware",
        action="store_const",
        const="hardware",
        dest="type",
        help="Run hardware tests only (same as --type hardware)"
    )
    
    parser.add_argument(
        "--integration",
        action="store_const",
        const="integration",
        dest="type",
        help="Run integration tests only (same as --type integration)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--hardware-port",
        help="Specify hardware port manually (e.g., COM3, /dev/ttyUSB0)"
    )
    
    parser.add_argument(
        "--list-hardware",
        action="store_true",
        help="List available serial ports and exit"
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if args.list_hardware:
        print("Available serial ports:")
        try:
            from serial.tools import list_ports
            ports = list_ports.comports()
            if not ports:
                print("  No serial ports found")
            else:
                for port in ports:
                    print(f"  {port.device}: {port.description}")
        except ImportError:
            print("  pyserial not installed")
        return
    
    # Print test configuration
    print("Python Selve Test Runner")
    print("=" * 40)
    print(f"Test type: {args.type}")
    print(f"Verbose: {args.verbose}")
    print(f"Coverage: {args.coverage}")
    if args.hardware_port:
        print(f"Hardware port: {args.hardware_port}")
    print()
    
    # Run tests
    success = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        hardware_port=args.hardware_port
    )
    
    if success:
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        if args.coverage:
            print("Coverage report generated in htmlcov/index.html")
    else:
        print("\n" + "=" * 60)
        print("Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
