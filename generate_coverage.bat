@echo off
echo ====================================================
echo Python-Selve: Coverage Report Generator
echo ====================================================
echo Generating coverage in smaller batches to avoid RAM issues...
echo ====================================================

:: Check if virtual environment exists
if not exist venv (
    echo Please run setup first to create virtual environment.
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate

:: Install coverage if needed
python -m pip install coverage

:: Remove old coverage data
if exist .coverage del .coverage
if exist htmlcov rmdir /s /q htmlcov

echo.
echo Step 1: Import tests
coverage run -m pytest tests\test_import.py

echo.
echo Step 2: Basic unit tests
coverage run --append -m pytest tests\unit\test_commands.py tests\unit\test_device.py tests\unit\test_group.py

echo.
echo Step 3: Service and group tests
coverage run --append -m pytest tests\unit\test_service_commands.py tests\unit\test_group_commands.py tests\unit\test_util.py

echo.
echo Step 4: Mock configuration tests
coverage run --append -m pytest tests\unit\test_gateway_configuration_issues.py tests\unit\test_mock_devices_and_groups.py

echo.
echo Step 5: Mock sensors and service errors
coverage run --append -m pytest tests\unit\test_mock_sensors_and_senders.py tests\unit\test_service_command_errors.py

echo.
echo Step 6: Mock commands and error handling
coverage run --append -m pytest tests\unit\test_mock_commands.py tests\unit\test_gateway_error_handling_fixed.py tests\unit\test_missing_components.py

echo.
echo Step 7: Integration tests (optional - skip if RAM limited)
set /p RUN_INTEGRATION="Include integration tests in coverage? (Y/N): "
if /i "%RUN_INTEGRATION%"=="Y" (
    coverage run --append -m pytest tests\integration\test_device_integration.py
    coverage run --append -m pytest tests\integration\test_selve_gateway_integration.py
    coverage run --append -m pytest tests\integration\test_selve_integration.py
)

echo.
echo ====================================================
echo Generating Reports
echo ====================================================
echo.
echo Terminal Report:
coverage report -m

echo.
echo Generating HTML Report...
coverage html
echo HTML report generated in: htmlcov\index.html

echo.
echo Generating XML Report...
coverage xml
echo XML report generated: coverage.xml

echo.
echo ====================================================
echo Coverage report generation completed!
echo ====================================================
echo Open htmlcov\index.html in your browser to view the report.
echo.

call venv\Scripts\deactivate
