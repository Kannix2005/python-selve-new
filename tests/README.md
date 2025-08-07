# Python Selve - Test Suite

Dieses Verzeichnis enthält umfassende Tests für die python-selve Bibliothek.

## Test-Kategorien

### 1. Unit Tests (`test_selve_unit.py`)
- **Zweck**: Schnelle Tests mit Mocks für isolierte Funktionalität
- **Laufzeit**: < 30 Sekunden
- **Hardware**: Nicht erforderlich
- **Abdeckung**: Grundlegende Funktionalität, Initialisierung, Worker-Management

```bash
# Unit Tests ausführen
python run_tests.py --type unit
```

### 2. Hardware Integration Tests (`test_selve_hardware.py`)
- **Zweck**: Tests mit echter Selve Gateway Hardware
- **Laufzeit**: 2-5 Minuten
- **Hardware**: Selve Gateway USB-Stick erforderlich
- **Abdeckung**: Echte Kommunikation, Verbindungsaufbau, Geräte-Discovery

```bash
# Hardware Tests ausführen (automatische Hardware-Erkennung)
python run_tests.py --type hardware

# Hardware Tests mit spezifischem Port
python run_tests.py --type hardware --hardware-port COM3
```

### 3. Integration Tests (`test_selve_integration.py`)
- **Zweck**: Tests für Komponenten-Interaktionen mit Mocks
- **Laufzeit**: 1-2 Minuten
- **Hardware**: Nicht erforderlich
- **Abdeckung**: Command-System, Event-Processing, Discovery-Workflow

```bash
# Integration Tests ausführen
python run_tests.py --type integration
```

### 4. Performance Tests (`test_selve_advanced.py`)
- **Zweck**: Performance- und Speicher-Tests
- **Laufzeit**: 2-3 Minuten
- **Hardware**: Nicht erforderlich
- **Abdeckung**: Geschwindigkeit, Speicherverbrauch, Robustheit

```bash
# Performance Tests ausführen
python run_tests.py --type performance
```

### 5. Stress Tests (`test_selve_hardware.py` mit `stress` Markierung)
- **Zweck**: Belastungstests mit echter Hardware
- **Laufzeit**: 5-10 Minuten
- **Hardware**: Selve Gateway erforderlich
- **Abdeckung**: Stabilität unter Last, Dauerbetrieb

```bash
# Stress Tests ausführen
python run_tests.py --type stress
```

### 6. Struktur Tests (`test_selve_structure.py`)
- **Zweck**: Tests für Code-Struktur und API-Konsistenz
- **Laufzeit**: < 30 Sekunden
- **Hardware**: Nicht erforderlich
- **Abdeckung**: Klassen-Definitionen, Konstanten, Datenstrukturen

## Test-Setup

### Abhängigkeiten installieren
```bash
pip install -r tests/requirements.txt
```

### Hardware-Erkennung
Die Tests erkennen automatisch verfügbare Hardware:
```bash
# Verfügbare Hardware anzeigen
python run_tests.py --list-hardware
```

### Alle Tests ausführen
```bash
# Alle Tests (außer Hardware-Tests wenn keine Hardware verfügbar)
python run_tests.py --type all

# Alle Tests mit Coverage-Report
python run_tests.py --type all --coverage
```

## Test-Ausführung

### Schneller Entwicklungs-Zyklus
```bash
# Nur Unit Tests (schnell)
python run_tests.py

# Mit Verbose-Output
python run_tests.py --verbose
```

### Vollständige Validierung
```bash
# Alle Tests mit Coverage
python run_tests.py --type all --coverage --verbose
```

### Hardware-Tests
```bash
# Hardware automatisch erkennen
python run_tests.py --type hardware

# Spezifischen Port verwenden
python run_tests.py --type hardware --hardware-port COM3

# Nur Stress-Tests
python run_tests.py --type stress
```

## Test-Konfiguration

### pytest.ini
- Marker-Definitionen
- Asyncio-Konfiguration
- Coverage-Einstellungen

### Test-Marker
- `hardware`: Benötigt echte Hardware
- `stress`: Belastungstest (langsam)
- `slow`: Langsame Tests
- `unit`: Unit Tests
- `integration`: Integration Tests

### Spezifische Tests ausschließen
```bash
# Keine Hardware-Tests
pytest -m "not hardware"

# Keine langsamen Tests
pytest -m "not slow and not stress"

# Nur Unit Tests
pytest -m "unit"
```

## Coverage Reports

### HTML-Report generieren
```bash
python run_tests.py --coverage
# Report verfügbar in: htmlcov/index.html
```

### Terminal-Report
```bash
pytest --cov=selve --cov-report=term-missing
```

## Hardware-Anforderungen

### Unterstützte Hardware
- Selve Gateway USB-Stick
- USB-Serial Adapter mit Gateway
- Kompatible COM-Ports

### Hardware-Erkennung
Die Tests suchen nach USB-Serial Adaptern mit folgenden Kennungen:
- `usb`, `serial`, `cp210`, `ftdi`, `ch340`

### Manual Hardware-Setup
```python
# In Tests Hardware-Port setzen
os.environ['SELVE_TEST_PORT'] = 'COM3'
```

## Troubleshooting

### Häufige Probleme

1. **Keine Hardware erkannt**
   ```bash
   python run_tests.py --list-hardware
   python run_tests.py --hardware-port COM3
   ```

2. **Import-Fehler**
   ```bash
   pip install -r tests/requirements.txt
   ```

3. **Timeout-Probleme**
   - Hardware-Verbindung prüfen
   - Gateway-Status überprüfen
   - Port-Berechtigung prüfen

4. **Test-Abhängigkeiten**
   ```bash
   pip install pytest pytest-asyncio pytest-mock pytest-cov
   ```

### Debug-Modus
```bash
# Maximaler Debug-Output
python run_tests.py --type hardware --verbose
```

### Einzelne Tests ausführen
```bash
# Spezifische Test-Datei
pytest tests/test_selve_unit.py -v

# Spezifische Test-Klasse
pytest tests/test_selve_unit.py::TestSelveInitialization -v

# Spezifischer Test
pytest tests/test_selve_unit.py::TestSelveInitialization::test_init_default_parameters -v
```

## Test-Entwicklung

### Neue Tests hinzufügen
1. Passende Test-Datei wählen
2. Test-Klasse erstellen
3. Fixtures verwenden
4. Marker setzen (`@pytest.mark.hardware` etc.)

### Mock-Patterns
```python
# Async Mock
@pytest.fixture
def mock_selve():
    with patch('selve.Selve') as mock:
        yield mock

# Hardware Mock
@pytest.fixture
def mock_serial():
    with patch('selve.serial.Serial') as mock:
        yield mock
```

### Hardware-Test Patterns
```python
@pytest.mark.hardware
@pytest.mark.asyncio
async def test_hardware_feature():
    port = detect_selve_hardware()
    if not port:
        pytest.skip("No hardware available")
    # Test implementation
```

## Kontinuierliche Integration

### Pre-Commit Tests
```bash
# Schnelle Tests vor Commit
python run_tests.py --type unit
```

### CI/CD Pipeline
```bash
# Vollständige Test-Suite
python run_tests.py --type all --coverage
```

### Automatisierte Hardware-Tests
Hardware-Tests können in CI/CD mit Hardware-Simulatoren oder echten Test-Geräten ausgeführt werden.
