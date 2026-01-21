@echo off
echo =============================================
echo Python-Selve Direct Hardware Test
echo =============================================
echo This script will run a direct hardware test with interactive controls.
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

:: Port selection (non-interactive). Set SELVE_PORT or COM_PORT to skip auto-discovery.
echo.
if defined SELVE_PORT set "COM_PORT=%SELVE_PORT%"
if defined COM_PORT (
    echo Running direct hardware test with %COM_PORT%...
    %PYTHON_CMD% direct_hardware_test.py --port %COM_PORT% --verbose
) else (
    echo Running direct hardware test with auto-discovery...
    %PYTHON_CMD% direct_hardware_test.py --discover --verbose
)

:: Deactivate virtual environment
echo.
echo Deactivating virtual environment...
call venv\Scripts\deactivate

echo.
echo Test completed.
echo.
