@echo off
setlocal enabledelayedexpansion

echo Python Selve - Hardware Tests
echo ==============================

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

echo Checking for connected hardware...
python -c "from serial.tools import list_ports; ports = list_ports.comports(); print('Available ports:'); [print(f'- {p.device}: {p.description}') for p in ports]"
echo.

echo Running hardware tests...
echo.

REM Run only hardware tests with verbose output
python -m pytest tests/test_selve_hardware.py -v -s --tb=short

if !errorlevel! equ 0 (
    echo.
    echo ==============================
    echo Hardware tests completed!
    echo ==============================
) else (
    echo.
    echo ==============================
    echo Some hardware tests failed or were skipped!
    echo Note: Tests will be skipped if no Selve Gateway is detected.
    echo ==============================
)

echo.
echo Press any key to continue...
pause
