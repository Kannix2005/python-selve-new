@echo off
echo ========================================
echo Einzelne Hardware-Tests - Sequenziell
echo ========================================

if not exist venv (
    echo Virtuelle Umgebung nicht gefunden. Führe setup.bat aus...
    call setup.bat
)

call venv\Scripts\activate.bat

echo.
echo Führe Hardware-Tests einzeln aus (um Port-Konflikte zu vermeiden)...
echo.

echo Test 1: Hardware Connection...
python -m pytest tests/test_selve_hardware.py::TestSelveHardwareIntegration::test_hardware_connection -v -s --tb=short

echo.
echo Test 2: Gateway Version...
python -m pytest tests/test_selve_hardware.py::TestSelveHardwareIntegration::test_gateway_version -v -s --tb=short

echo.
echo Test 3: Gateway State...
python -m pytest tests/test_selve_hardware.py::TestSelveHardwareIntegration::test_gateway_state -v -s --tb=short

echo.
echo ========================================
echo Hardware-Tests abgeschlossen
echo ========================================
pause
