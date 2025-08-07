@echo off
REM Automatisiertes Setup und Test-Runner für python-selve
REM Deutsche Version für Windows

echo ========================================
echo Python-Selve Setup und Test-Runner
echo ========================================
echo.

REM Prüfe und aktiviere virtuelle Umgebung falls vorhanden
set PYTHON_CMD=python
if exist "venv\Scripts\activate.bat" (
    echo Aktiviere virtuelle Umgebung...
    call venv\Scripts\activate.bat
    set PYTHON_CMD=venv\Scripts\python.exe
    echo Virtuelle Umgebung aktiviert.
    echo.
) else (
    echo Keine virtuelle Umgebung gefunden. Verwende System-Python.
    echo.
)

REM Prüfe ob Python verfügbar ist
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python ist nicht installiert oder nicht im PATH verfügbar.
    echo Bitte installieren Sie Python 3.8+ von https://python.org
    pause
    exit /b 1
)

echo Python ist verfügbar:
%PYTHON_CMD% --version
if defined VIRTUAL_ENV (
    echo Verwendet virtuelle Umgebung: %VIRTUAL_ENV%
) else (
    echo Verwendet System-Python
)
echo.

REM Zeige Optionen an
echo Wählen Sie eine Option:
echo.
echo 1. Vollständige Einrichtung mit allen Tests
echo 2. Schnelle Einrichtung (nur Unit-Tests)
echo 3. Einrichtung ohne virtuelle Umgebung
echo 4. Hardware-Tests erzwingen
echo 5. Entwicklungsmodus
echo 6. Nur Tests ausführen (bereits eingerichtet)
echo 7. Nur Abhängigkeiten installieren
echo.
set /p choice="Ihre Wahl (1-7): "

if "%choice%"=="1" goto full_setup
if "%choice%"=="2" goto quick_setup
if "%choice%"=="3" goto no_venv_setup
if "%choice%"=="4" goto force_hardware
if "%choice%"=="5" goto dev_setup
if "%choice%"=="6" goto run_tests_only
if "%choice%"=="7" goto install_deps_only

echo Ungültige Auswahl. Verwende Vollständige Einrichtung.
goto full_setup

:full_setup
echo.
echo Starte vollständige Einrichtung...
%PYTHON_CMD% setup_and_test_de.py
goto end

:quick_setup
echo.
echo Starte schnelle Einrichtung...
%PYTHON_CMD% setup_and_test_de.py --quick
goto end

:no_venv_setup
echo.
echo Starte Einrichtung ohne virtuelle Umgebung...
%PYTHON_CMD% setup_and_test_de.py --no-venv
goto end

:force_hardware
echo.
echo Starte Einrichtung mit erzwungenen Hardware-Tests...
%PYTHON_CMD% setup_and_test_de.py --force-hardware
goto end

:dev_setup
echo.
echo Starte Entwicklungsmodus...
%PYTHON_CMD% setup_and_test_de.py --dev
goto end

:run_tests_only
echo.
echo Prüfe Test-Abhängigkeiten...

REM Prüfe ob pytest installiert ist
%PYTHON_CMD% -c "import pytest" >nul 2>&1
if errorlevel 1 (
    echo WARNUNG: pytest ist nicht installiert.
    echo Installiere Test-Abhängigkeiten...
    
    REM Versuche requirements.txt zu installieren
    if exist "tests\requirements.txt" (
        echo Installiere aus tests\requirements.txt...
        %PYTHON_CMD% -m pip install -r tests\requirements.txt
        if errorlevel 1 (
            echo FEHLER: Konnte Test-Abhängigkeiten nicht installieren.
            echo Führe stattdessen vollständige Einrichtung aus...
            %PYTHON_CMD% setup_and_test_de.py --quick
            goto end
        )
    ) else (
        echo Installiere pytest direkt...
        %PYTHON_CMD% -m pip install pytest pytest-cov pytest-asyncio
        if errorlevel 1 (
            echo FEHLER: Konnte pytest nicht installieren.
            echo Führe stattdessen vollständige Einrichtung aus...
            %PYTHON_CMD% setup_and_test_de.py --quick
            goto end
        )
    )
    echo Test-Abhängigkeiten erfolgreich installiert.
    echo.
)

echo Führe Tests aus...
if exist "run_tests.py" (
    %PYTHON_CMD% run_tests.py --all
    if errorlevel 1 (
        echo.
        echo WARNUNG: Einige Tests sind fehlgeschlagen!
        echo Mögliche Lösungen:
        echo - Führe Option 7 aus um Abhängigkeiten zu installieren
        echo - Führe Option 1 oder 2 für vollständige Einrichtung aus
        echo - Prüfe ob alle erforderlichen Module installiert sind
        echo.
    )
) else (
    echo run_tests.py nicht gefunden. Führe pytest direkt aus...
    %PYTHON_CMD% -m pytest tests/ -v
    if errorlevel 1 (
        echo.
        echo WARNUNG: Tests sind fehlgeschlagen!
        echo Führe Option 1 oder 7 für vollständige Einrichtung aus.
        echo.
    )
)
goto end

:install_deps_only
echo.
echo Installiere nur Test-Abhängigkeiten...

REM Aktualisiere pip
echo Aktualisiere pip...
%PYTHON_CMD% -m pip install --upgrade pip

REM Installiere Basis-Abhängigkeiten
echo Installiere Basis-Abhängigkeiten...
%PYTHON_CMD% -m pip install pyserial pyserial-asyncio untangle

REM Installiere Test-Abhängigkeiten
if exist "tests\requirements.txt" (
    echo Installiere aus tests\requirements.txt...
    %PYTHON_CMD% -m pip install -r tests\requirements.txt
) else (
    echo Installiere pytest und Zusatzmodule...
    %PYTHON_CMD% -m pip install pytest pytest-cov pytest-asyncio pytest-mock
)

REM Installiere Projekt im Entwicklungsmodus
echo Installiere Projekt im Entwicklungsmodus...
%PYTHON_CMD% -m pip install -e .

echo Abhängigkeiten erfolgreich installiert!
goto end

:end
echo.
echo ========================================
echo Setup abgeschlossen.
echo.
echo Nächste Schritte:
echo - Siehe test_report.txt für Details
if exist "venv\Scripts\activate.bat" (
    if defined VIRTUAL_ENV (
        echo - Virtuelle Umgebung ist bereits aktiv
    ) else (
        echo - Aktiviere virtuelle Umgebung mit: venv\Scripts\activate
    )
) else (
    echo - Erstelle virtuelle Umgebung mit: python -m venv venv
)
echo - Führe Tests erneut aus mit: python run_tests.py
echo.
pause
