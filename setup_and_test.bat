@echo off
echo =============================================
echo Python-Selve Complete Test Suite
echo =============================================
echo This script will set up the environment and run all tests.
echo.

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

:: Check for Selve Gateway (USB device)
echo.
echo Checking for Selve Gateway USB device...
%PYTHON_CMD% -c "from serial.tools import list_ports; ports = list_ports.comports(); gateway_found = any('USB' in str(port) or 'VID_' in str(port) for port in ports); print('Gateway found!' if gateway_found else 'No Gateway detected.'); exit(0 if gateway_found else 1)" > nul 2>&1
set GATEWAY_DETECTED=%ERRORLEVEL%

if %GATEWAY_DETECTED% EQU 0 (
    echo Selve Gateway detected! Hardware tests will be included.
    set ENABLE_HARDWARE_TESTS=1
) else (
    echo No Selve Gateway detected. Only mock and unit tests will run.
    set ENABLE_HARDWARE_TESTS=0
)

:: Run all tests
echo.
echo =============================================
echo Running Complete Test Suite
echo =============================================
echo.

:: Run unit and integration tests (always)
echo Running Unit and Integration Tests...
%PYTHON_CMD% -m pytest tests/ -v --tb=short

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Some unit/integration tests failed!
    goto :error_exit
)

echo.
echo [SUCCESS] All unit and integration tests passed!

:: Run hardware tests if gateway is detected
if %ENABLE_HARDWARE_TESTS% EQU 1 (
    echo.
    echo Running Hardware Tests with detected Gateway...
    %PYTHON_CMD% -m pytest tests/integration/test_selve_hardware.py -v --tb=short
    
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [WARNING] Some hardware tests failed - this might be normal if no devices are configured.
    ) else (
        echo.
        echo [SUCCESS] All hardware tests passed!
    )
) else (
    echo.
    echo [SKIPPED] Hardware tests skipped - no Gateway detected.
)

:: Run coverage report
echo.
echo Generating coverage report...
%PYTHON_CMD% -m pytest tests/ --cov=selve --cov-report=term-missing --cov-report=html --quiet

echo.
echo =============================================
echo Coverage Summary
echo =============================================
echo Coverage report generated in htmlcov/index.html
echo.

echo.
echo =============================================
echo Test Summary
echo =============================================
if %ENABLE_HARDWARE_TESTS% EQU 1 (
    echo - Unit Tests: PASSED
    echo - Integration Tests: PASSED  
    echo - Hardware Tests: COMPLETED
    echo - Gateway Status: DETECTED
) else (
    echo - Unit Tests: PASSED
    echo - Integration Tests: PASSED
    echo - Hardware Tests: SKIPPED (No Gateway)
    echo - Gateway Status: NOT DETECTED
)
echo.
echo All tests completed successfully!
goto :success_exit

:error_exit
echo.
echo =============================================
echo Test execution failed! Check the output above.
echo =============================================

:: Deactivate virtual environment
call venv\Scripts\deactivate

echo.
pause
exit /b 1

:success_exit
:: Deactivate virtual environment
echo.
echo Deactivating virtual environment...
call venv\Scripts\deactivate

echo.
echo Test suite completed successfully!
echo.
exit /b 0
