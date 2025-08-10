@echo off
echo Running integration tests...
python -m pytest tests/integration/test_device_integration.py -v
if %ERRORLEVEL% NEQ 0 (
    echo Integration tests failed!
    exit /b %ERRORLEVEL%
)
echo Integration tests completed successfully!
