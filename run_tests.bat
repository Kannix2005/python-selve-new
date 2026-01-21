@echo off
echo ==========================::: Run the tests without hardware tests by default
echo.
echo Running unit tests...
%PYTHON_CMD% -m pytest tests\unit -v

echo.
echo Running mock tests for gateway configuration issues...
%PYTHON_CMD% -m pytest tests\unit\test_gateway_configuration_issues.py -v
%PYTHON_CMD% -m pytest tests\unit\test_mock_devices_and_groups.py -v
%PYTHON_CMD% -m pytest tests\unit\test_mock_sensors_and_senders.py -v
%PYTHON_CMD% -m pytest tests\unit\test_service_command_errors.py -v
%PYTHON_CMD% -m pytest tests\unit\test_gateway_error_handling.py -v
%PYTHON_CMD% -m pytest tests\unit\test_missing_components.py -v

echo.
echo Running integration tests with simulated hardware...
%PYTHON_CMD% -m pytest tests\integration -v===========
echo Python-Selve Test Runner
echo =============================================

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

:: Run the basic import test first to make sure everything is working
echo.
echo Running basic import test...
%PYTHON_CMD% -m pytest tests\test_import.py -v

:: Run the tests without hardware tests by default
echo.
echo Running unit tests...
%PYTHON_CMD% -m pytest tests\unit -v

echo.
echo Running integration tests with simulated hardware...
%PYTHON_CMD% -m pytest tests\integration -v

:: Ask if the user wants to run hardware tests
echo.
echo Do you want to run hardware tests? These require actual Selve hardware connected. (Y/N)
set /p RUN_HARDWARE_TESTS=
if /i "%RUN_HARDWARE_TESTS%"=="Y" (
    echo.
    echo Running hardware tests...
    set ENABLE_HARDWARE_TESTS=1
    %PYTHON_CMD% -m pytest tests\integration\test_selve_hardware.py -v
) else (
    echo Skipping hardware tests.
)

:: Generate coverage report
echo.
echo Generating coverage report...
%PYTHON_CMD% -m pytest --cov=selve tests\

:: Deactivate virtual environment
echo.
echo Deactivating virtual environment...
call venv\Scripts\deactivate

echo.
echo Tests completed.
echo.
