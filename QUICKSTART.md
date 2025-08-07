# Python Selve Project - Quick Start Guide

## Automated Setup and Testing

This project includes fully automated setup and testing for the python-selve library.

### Quick Start (Windows)

1. **Automated Setup**:
   ```cmd
   setup.bat
   ```
   This will:
   - Create a virtual environment
   - Install all dependencies
   - Run the complete test suite

2. **Manual Testing**:
   ```cmd
   python run_tests.py
   ```

3. **Alternative Setup**:
   ```cmd
   python setup_and_test_de.py
   ```

### What Gets Tested

- **74 Software Tests**: All pass reliably without hardware
- **13 Hardware Tests**: Require physical Selve hardware

### Test Categories

- **Unit Tests** (25): Core functionality, error handling
- **Integration Tests** (10): Component interaction, workflows  
- **Structure Tests** (26): Data validation, XML processing
- **Advanced Tests** (13): Edge cases, boundary conditions
- **Hardware Tests** (13): Physical device interaction

### Requirements

- Python 3.7+
- Windows (primary support)
- Optional: Selve Gateway hardware for hardware tests

### Project Structure

```
python-selve-new/
├── setup.bat                 # Automated Windows setup
├── setup_and_test_de.py     # Python setup script
├── run_tests.py             # Test runner
├── TEST_RESULTS.md          # Detailed test documentation
├── tests/
│   ├── requirements.txt     # Test dependencies
│   ├── conftest.py         # Test configuration
│   ├── test_selve_unit.py      # Unit tests
│   ├── test_selve_integration.py # Integration tests
│   ├── test_selve_structure.py  # Structure tests
│   ├── test_selve_advanced.py   # Advanced tests
│   └── test_selve_hardware.py   # Hardware tests
└── selve/                   # Main library code
```

### Expected Results

✅ **All software tests pass** (74/74)  
⚠️ **Hardware tests require hardware** (0/13 without hardware)  
ℹ️ **Minor warnings acceptable** (3 AsyncMock warnings)

The project is ready for development, testing, and production use!
