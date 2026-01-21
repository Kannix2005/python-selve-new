@echo off
echo =============================================
echo Python-Selve Hardware Test Runner
echo =============================================
echo WARNING: These tests require actual Selve hardware connected!
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
%PYTHON_CMD% -m pip install pytest pytest-asyncio

echo.
echo Running hardware tests...
set ENABLE_HARDWARE_TESTS=1
%PYTHON_CMD% -m pytest tests\integration\test_selve_hardware.py -v

:: Deactivate virtual environment
echo.
echo Deactivating virtual environment...
call venv\Scripts\deactivate

echo.
echo Hardware tests completed.
echo.
