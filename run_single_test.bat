@echo off
echo =============================================
echo Python-Selve Run Single Test
echo =============================================
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
%PYTHON_CMD% -m pip install pytest pytest-asyncio pytest-cov

:: Display available test files
echo.
echo Available test files:
echo.
echo Unit Tests:
dir /b tests\unit\*.py
echo.
echo Integration Tests:
dir /b tests\integration\*.py
echo.
echo Root Tests:
dir /b tests\*.py
echo.

:: Ask which test to run
set /p TEST_FILE=Enter test file name to run (e.g., test_util.py): 

:: Find the test file
if exist tests\unit\%TEST_FILE% (
    set FULL_PATH=tests\unit\%TEST_FILE%
) else if exist tests\integration\%TEST_FILE% (
    set FULL_PATH=tests\integration\%TEST_FILE%
) else if exist tests\%TEST_FILE% (
    set FULL_PATH=tests\%TEST_FILE%
) else (
    echo Test file not found. Please check the name and try again.
    exit /b 1
)

:: Run the specified test
echo.
echo Running test %FULL_PATH%...
%PYTHON_CMD% -m pytest %FULL_PATH% -v

:: Deactivate virtual environment
echo.
echo Deactivating virtual environment...
call venv\Scripts\deactivate

echo.
echo Test completed.
echo.
