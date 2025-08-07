@echo off
setlocal enabledelayedexpansion

echo Python Selve - Software Tests Only
echo ====================================

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment and run software tests only
call venv\Scripts\activate.bat

echo Running software tests (excluding hardware tests)...
echo.

REM Run tests excluding hardware tests
python -m pytest tests/ --ignore=tests/test_selve_hardware.py -v --tb=short

if !errorlevel! equ 0 (
    echo.
    echo ====================================
    echo All software tests passed successfully!
    echo ====================================
) else (
    echo.
    echo ====================================
    echo Some software tests failed!
    echo ====================================
    exit /b 1
)

pause
