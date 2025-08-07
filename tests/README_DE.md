# Python-Selve Test-Suite

Eine umfassende Test-Suite für das python-selve Projekt mit automatischer Hardware-Erkennung und verschiedenen Test-Ebenen.

## Schnellstart

### Automatisierte Einrichtung und Tests

Das einfachste Verfahren ist die Verwendung des automatisierten Setup-Skripts:

```bash
# Vollständige Einrichtung mit allen Tests
python setup_and_test_de.py

# Schnelle Einrichtung nur mit Unit-Tests
python setup_and_test_de.py --quick

# Ohne virtuelle Umgebung
python setup_and_test_de.py --no-venv

# Hardware-Tests erzwingen (auch ohne erkannte Hardware)
python setup_and_test_de.py --force-hardware

# Entwicklungsmodus mit zusätzlichen Tools
python setup_and_test_de.py --dev
```

### Manuelle Test-Ausführung

Falls Sie die Tests manuell ausführen möchten:

```bash
# Abhängigkeiten installieren
pip install -r tests/requirements.txt

# Verschiedene Test-Typen ausführen
python run_tests.py --unit          # Nur Unit-Tests
python run_tests.py --integration   # Integrations-Tests
python run_tests.py --hardware      # Hardware-Tests (benötigt USB-Stick)
python run_tests.py --all          # Alle Tests
```

## Test-Struktur

### Test-Kategorien

1. **Unit-Tests** (`test_selve_unit.py`)
   - Testen einzelne Komponenten isoliert
   - Verwenden Mocks für externe Abhängigkeiten
   - Schnell ausführbar, keine Hardware erforderlich

2. **Integrations-Tests** (`test_selve_integration.py`)
   - Testen das Zusammenspiel zwischen Komponenten
   - Simulieren reale Verwendungsszenarien
   - Keine echte Hardware erforderlich

3. **Hardware-Tests** (`test_selve_hardware.py`)
   - Testen mit echter Selve Gateway Hardware
   - Automatische Erkennung von USB-Geräten
   - Werden übersprungen wenn keine Hardware erkannt wird

4. **Performance-Tests** (`test_selve_advanced.py`)
   - Testen Speicherverbrauch und Leistung
   - Stress-Tests für robuste Implementierung
   - Timeout- und Fehlerbehandlungs-Tests

5. **Struktur-Tests** (`test_selve_structure.py`)
   - Validieren API-Konsistenz
   - Prüfen Klassen-Hierarchien
   - Sicherstellen der Datenstruktur-Integrität

### Hardware-Erkennung

Die Test-Suite erkennt automatisch kompatible Hardware:

- **Windows**: COM-Ports mit USB-Beschreibung
- **Linux**: /dev/ttyUSB* Geräte
- **macOS**: /dev/cu.* Geräte

Erkannte Geräte werden automatisch für Hardware-Tests verwendet.

## Test-Konfiguration

### Umgebungsvariablen

```bash
# Spezifischen Port für Tests festlegen
export SELVE_TEST_PORT=COM3  # Windows
export SELVE_TEST_PORT=/dev/ttyUSB0  # Linux

# Debug-Modus aktivieren
export SELVE_DEBUG=1

# Test-Timeout anpassen
export SELVE_TEST_TIMEOUT=30
```

### Pytest-Konfiguration

Die Konfiguration befindet sich in `pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    unit: Unit tests
    integration: Integration tests
    hardware: Hardware tests (requires device)
    slow: Slow running tests
```

## Test-Ausführung

### Basis-Befehle

```bash
# Alle Tests ausführen
pytest

# Nur bestimmte Kategorien
pytest -m unit
pytest -m integration
pytest -m hardware

# Mit Coverage-Bericht
pytest --cov=selve --cov-report=html

# Parallele Ausführung
pytest -n auto

# Ausführliche Ausgabe
pytest -v -s
```

### Hardware-Tests

Hardware-Tests werden automatisch übersprungen wenn keine kompatible Hardware erkannt wird:

```bash
# Hardware-Tests nur ausführen wenn Gerät verfügbar
pytest -m hardware

# Hardware-Tests erzwingen (kann fehlschlagen)
pytest -m hardware --force-hardware
```

### Performance-Tests

```bash
# Performance-Tests ausführen
pytest tests/test_selve_advanced.py

# Mit Memory-Profiling
pytest tests/test_selve_advanced.py --profile
```

## Coverage-Berichte

Nach Test-Ausführung mit Coverage:

```bash
# HTML-Bericht generieren
pytest --cov=selve --cov-report=html

# Terminal-Bericht
pytest --cov=selve --cov-report=term

# XML-Bericht für CI/CD
pytest --cov=selve --cov-report=xml
```

Die HTML-Berichte finden Sie in `htmlcov/index.html`.

## Problembehebung

### Häufige Probleme

1. **Keine Hardware erkannt**
   ```bash
   # Verfügbare Ports manuell auflisten
   python -c "import serial.tools.list_ports; [print(p) for p in serial.tools.list_ports.comports()]"
   ```

2. **Berechtigungsfehler (Linux)**
   ```bash
   # Benutzer zur dialout-Gruppe hinzufügen
   sudo usermod -a -G dialout $USER
   # Neuanmeldung erforderlich
   ```

3. **Import-Fehler**
   ```bash
   # Projekt im Entwicklungsmodus installieren
   pip install -e .
   ```

4. **Pytest nicht gefunden**
   ```bash
   # Test-Abhängigkeiten installieren
   pip install -r tests/requirements.txt
   ```

### Debug-Modus

Für detaillierte Debug-Ausgaben:

```bash
# Debug-Logging aktivieren
export SELVE_DEBUG=1
pytest -v -s

# Oder direkt mit Python
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Ihr Test-Code hier
"
```

## CI/CD Integration

### GitHub Actions Beispiel

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r tests/requirements.txt
    
    - name: Run unit tests
      run: pytest -m unit --cov=selve --cov-report=xml
    
    - name: Run integration tests
      run: pytest -m integration
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Entwicklung

### Neue Tests hinzufügen

1. **Unit-Test hinzufügen:**
   ```python
   # In test_selve_unit.py
   def test_neue_funktion():
       # Test-Code hier
       pass
   ```

2. **Hardware-Test hinzufügen:**
   ```python
   # In test_selve_hardware.py
   @pytest.mark.hardware
   def test_hardware_funktion(hardware_gateway):
       # Test mit echter Hardware
       pass
   ```

3. **Fixtures erweitern:**
   ```python
   # In conftest.py
   @pytest.fixture
   def neue_fixture():
       # Setup-Code
       yield test_objekt
       # Cleanup-Code
   ```

### Test-Richtlinien

- **Isoliert**: Jeder Test sollte unabhängig ausführbar sein
- **Wiederholbar**: Tests sollten bei mehrfacher Ausführung gleiche Ergebnisse liefern
- **Schnell**: Unit-Tests sollten schnell ausführbar sein
- **Aussagekräftig**: Test-Namen sollten das getestete Verhalten beschreiben
- **Dokumentiert**: Komplexe Test-Szenarien sollten kommentiert werden

## Lizenz

Diese Test-Suite steht unter der gleichen Lizenz wie das Hauptprojekt.
