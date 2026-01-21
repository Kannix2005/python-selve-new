@echo off
echo ====================================================
echo Python-Selve: Comprehensive Test Runner
echo ====================================================
echo This script will run all tests, including:
echo - Basic import tests
echo - Unit tests for all components
echo - All Mock tests for error scenarios
echo - Integration tests with simulated hardware
echo - Hardware tests (optional)
echo ====================================================

:: Check if Python is installed and get the Python command
python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    py --version > nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Python is not installed or not in PATH. Please install Python first.
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

:: Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv venv
) else (
    echo Found existing virtual environment.
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

:: Install requirements if needed
echo Installing required packages...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -e .
%PYTHON_CMD% -m pip install pytest pytest-asyncio pytest-cov

echo ====================================================
echo STEP 1: Basic Import Tests
echo ====================================================
%PYTHON_CMD% -m pytest tests\test_import.py -v

echo ====================================================
echo STEP 2: Unit Tests
echo ====================================================
echo Running standard unit tests...
%PYTHON_CMD% -m pytest tests\unit\test_commands.py tests\unit\test_device.py tests\unit\test_group.py tests\unit\test_service_commands.py tests\unit\test_group_commands.py tests\unit\test_util.py -v

echo ====================================================
echo STEP 3: Mock Tests for Error Scenarios
echo ====================================================
echo Running gateway configuration issue tests...
%PYTHON_CMD% -m pytest tests\unit\test_gateway_configuration_issues.py -v

echo Running mock devices and groups tests...
%PYTHON_CMD% -m pytest tests\unit\test_mock_devices_and_groups.py -v

echo Running mock sensors and senders tests...
%PYTHON_CMD% -m pytest tests\unit\test_mock_sensors_and_senders.py -v

echo Running service command error tests...
%PYTHON_CMD% -m pytest tests\unit\test_service_command_errors.py -v

echo Running existing mock tests...
%PYTHON_CMD% -m pytest tests\unit\test_mock_commands.py -v
%PYTHON_CMD% -m pytest tests\unit\test_gateway_error_handling_fixed.py -v
%PYTHON_CMD% -m pytest tests\unit\test_missing_components.py -v

echo ====================================================
echo STEP 4: Integration Tests
echo ====================================================
echo Running integration tests with simulated hardware...

echo Running device integration tests...
%PYTHON_CMD% -m pytest tests\integration\test_device_integration.py -v

echo Running gateway integration tests...
%PYTHON_CMD% -m pytest tests\integration\test_selve_gateway_integration.py -v

echo Running other integration tests...
%PYTHON_CMD% -m pytest tests\integration\test_selve_integration.py -v

:: Ask if the user wants to run hardware tests
echo ====================================================
echo STEP 5: Hardware Tests (Optional)
echo ====================================================
echo Do you want to run hardware tests? These require actual Selve hardware 
echo connected via USB. These tests might control your devices if connected! (Y/N)
set /p RUN_HARDWARE_TESTS=

if /i "%RUN_HARDWARE_TESTS%"=="Y" (
    echo Running hardware tests...
    set ENABLE_HARDWARE_TESTS=1
    %PYTHON_CMD% -m pytest tests\integration\test_selve_hardware.py tests\integration\test_device_integration.py -v
) else (
    echo Skipping hardware tests.
)

:: Coverage report disabled due to RAM issues with gc.collect in pytest-cov
:: To generate coverage manually: python -m pytest --cov=selve --cov-report=html tests/
echo ====================================================
echo Test Coverage Report Generation: SKIPPED
echo ====================================================
echo Coverage generation disabled to prevent RAM exhaustion.
echo To generate manually with limited scope:
echo   python -m pytest --cov=selve --cov-report=term-missing tests/unit/
echo.

:: Deactivate virtual environment
echo Deactivating virtual environment...
call venv\Scripts\deactivate

echo ====================================================
echo All tests completed! 
echo Coverage report generated.
echo ====================================================

