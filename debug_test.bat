@echo off
echo =============================================
echo Python-Selve Debug Test with Real Hardware
echo =============================================
echo WARNING: This test requires actual Selve hardware connected!
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

:: Ask for COM port
echo.
set /p COM_PORT=Enter COM port number (e.g., '16' for COM16): 

:: Edit the test_com16.py file to use the specified COM port
echo.
echo Setting up test for COM%COM_PORT%...
powershell -Command "(Get-Content test_com16.py) | ForEach-Object { $_ -replace 'COM\d+', 'COM%COM_PORT%' } | Set-Content test_com16.py"

:: Run the debug test
echo.
echo Running debug test with COM%COM_PORT%...
%PYTHON_CMD% test_com16.py

:: Deactivate virtual environment
echo.
echo Deactivating virtual environment...
call venv\Scripts\deactivate

echo.
echo Debug test completed.
echo.
pause
