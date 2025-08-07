# Python-Selve - Automatisierte Einrichtung und Tests

Dieses Projekt stellt eine umfassende Test-Suite und automatisierte Einrichtung für das python-selve Gateway zur Verfügung.

## 🚀 Schnellstart

### Windows (Empfohlen)
Doppelklicken Sie auf `setup.bat` oder führen Sie in der Eingabeaufforderung aus:
```cmd
setup.bat
```

### Alle Betriebssysteme
```bash
python setup_and_test_de.py
```

Das war's! Das Skript führt automatisch folgende Schritte aus:
1. ✅ Prüft Python-Version (3.8+ erforderlich)
2. ✅ Erstellt virtuelle Umgebung
3. ✅ Installiert alle Abhängigkeiten
4. ✅ Erkennt automatisch Hardware (Selve Gateway USB-Stick)
5. ✅ Führt entsprechende Tests aus
6. ✅ Erstellt Berichte und Coverage-Statistiken

## 📋 Verfügbare Optionen

### Automatisiertes Setup
```bash
# Vollständige Einrichtung (empfohlen)
python setup_and_test_de.py

# Schnell-Modus (nur Unit-Tests)
python setup_and_test_de.py --quick

# Ohne virtuelle Umgebung
python setup_and_test_de.py --no-venv

# Hardware-Tests erzwingen
python setup_and_test_de.py --force-hardware

# Entwicklungsmodus (mit zusätzlichen Tools)
python setup_and_test_de.py --dev
```

### Manuelle Test-Ausführung
```bash
# Einzelne Test-Kategorien
python run_tests.py --unit          # Unit-Tests
python run_tests.py --integration   # Integrations-Tests  
python run_tests.py --hardware      # Hardware-Tests
python run_tests.py --all          # Alle Tests
```

## 🔌 Hardware-Unterstützung

Das System erkennt automatisch:
- **Windows**: COM-Ports (COM1, COM2, ...)
- **Linux**: USB-Serial Geräte (/dev/ttyUSB*)
- **macOS**: Serial-Geräte (/dev/cu.*)

### Hardware-Tests
- Werden **automatisch übersprungen** wenn keine Hardware erkannt wird
- Können mit `--force-hardware` erzwungen werden
- Testen echte Kommunikation mit Selve Gateway

## 📊 Test-Kategorien

| Test-Typ | Beschreibung | Hardware erforderlich |
|----------|--------------|----------------------|
| **Unit** | Einzelne Komponenten, mit Mocks | ❌ Nein |
| **Integration** | Zusammenspiel der Komponenten | ❌ Nein |
| **Hardware** | Echte Geräte-Kommunikation | ✅ Ja |
| **Performance** | Speicher und Geschwindigkeit | ❌ Nein |
| **Struktur** | API und Datenvalidierung | ❌ Nein |

## 📈 Coverage-Berichte

Nach dem Test-Lauf finden Sie:
- **HTML-Bericht**: `htmlcov/index.html`
- **Text-Bericht**: In der Konsole
- **Gesamt-Bericht**: `test_report.txt`

## 🛠 Anforderungen

- **Python**: Version 3.8 oder höher
- **Betriebssystem**: Windows, Linux, macOS
- **Hardware**: Selve Gateway USB-Stick (optional, für Hardware-Tests)

## 📝 Nächste Schritte nach Setup

1. **Virtuelle Umgebung aktivieren**:
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS  
   source venv/bin/activate
   ```

2. **Entwicklung starten**:
   ```bash
   # Code editieren in selve/ Verzeichnis
   # Tests ausführen mit:
   python run_tests.py
   ```

3. **Neue Tests hinzufügen**:
   - Unit-Tests: `tests/test_selve_unit.py`
   - Hardware-Tests: `tests/test_selve_hardware.py`
   - Integration: `tests/test_selve_integration.py`

## 🔧 Problemlösung

### "Python nicht gefunden"
- Installieren Sie Python 3.8+ von [python.org](https://python.org)
- Stellen Sie sicher, dass Python im PATH ist

### "Keine Hardware erkannt"
- Verbinden Sie das Selve Gateway USB-Stick
- Prüfen Sie verfügbare Ports:
  ```bash
  python -c "import serial.tools.list_ports; [print(p) for p in serial.tools.list_ports.comports()]"
  ```

### Berechtigungsfehler (Linux)
```bash
sudo usermod -a -G dialout $USER
# Neuanmeldung erforderlich
```

### Import-Fehler
```bash
pip install -e .  # Projekt im Entwicklungsmodus installieren
```

## 📚 Dokumentation

- **Vollständige Test-Dokumentation**: `tests/README_DE.md`
- **API-Dokumentation**: Siehe Docstrings in den Python-Dateien
- **Beispiele**: `test.py` für Verwendungsbeispiele

## 🎯 Projekt-Struktur

```
python-selve-new/
├── setup_and_test_de.py    # Automatisiertes Setup (Deutsch)
├── setup.bat               # Windows Batch-Datei
├── run_tests.py           # Manueller Test-Runner
├── selve/                 # Haupt-Bibliothek
├── tests/                 # Test-Suite
│   ├── test_selve_unit.py      # Unit-Tests
│   ├── test_selve_hardware.py  # Hardware-Tests
│   ├── test_selve_integration.py # Integration-Tests
│   ├── test_selve_advanced.py    # Performance-Tests
│   └── conftest.py             # Test-Konfiguration
└── htmlcov/              # Coverage-Berichte (nach Tests)
```

---

**Viel Erfolg bei der Entwicklung! 🎉**

Bei Fragen oder Problemen, siehe die Logs in `setup.log` oder die Test-Berichte in `test_report.txt`.
