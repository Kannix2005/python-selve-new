@echo off
echo Running Mock-based Tests for the Selve Gateway Library...

:: Setup environment if needed
echo Checking for virtual environment...
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install dependencies if needed
pip install -e .

echo.
echo Running mock tests for devices, groups, and gateway scenarios...
echo --------------------------------------------------------------

:: Running all mock tests
echo Running Gateway Configuration Issue Tests...
python -m pytest tests\unit\test_gateway_configuration_issues.py -v

echo.
echo Running Mock Devices and Groups Tests...
python -m pytest tests\unit\test_mock_devices_and_groups.py -v

echo.
echo Running Mock Sensors and Senders Tests...
python -m pytest tests\unit\test_mock_sensors_and_senders.py -v

echo.
echo Running Service Command Error Tests...
python -m pytest tests\unit\test_service_command_errors.py -v

echo.
echo Running Existing Mock Command Tests...
python -m pytest tests\unit\test_mock_commands.py -v

echo.
echo Running Gateway Error Handling Tests...
python -m pytest tests\unit\test_gateway_error_handling_fixed.py -v

echo.
echo Running Missing Components Tests...
python -m pytest tests\unit\test_missing_components.py -v

echo.
echo All mock tests completed.

:: Deactivate virtual environment
call venv\Scripts\deactivate.bat

