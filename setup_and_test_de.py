#!/usr/bin/env python3
"""
Automatisiertes Setup und Test-Runner für python-selve

Dieses Skript führt automatisch folgende Schritte aus:
1. Überprüft Python-Version Kompatibilität
2. Richtet virtuelle Umgebung ein (optional)
3. Installiert alle Abhängigkeiten
4. Erkennt Hardware automatisch
5. Führt entsprechende Test-Suites aus
6. Erstellt Berichte

Verwendung:
    python setup_and_test_de.py [Optionen]

Beispiele:
    python setup_and_test_de.py                     # Vollständige automatische Einrichtung und Tests
    python setup_and_test_de.py --no-venv           # Virtuelle Umgebung überspringen
    python setup_and_test_de.py --quick             # Schnelle Einrichtung und nur Unit-Tests
    python setup_and_test_de.py --force-hardware    # Hardware-Tests erzwingen auch ohne erkannte Hardware
    python setup_and_test_de.py --dev               # Entwicklungsmodus mit zusätzlichen Tools
"""

import argparse
import sys
import os
import subprocess
import logging
import tempfile
import shutil
import time
import platform
from pathlib import Path
from typing import Optional, List, Tuple

# Konfiguration
MIN_PYTHON_VERSION = (3, 8)
PROJECT_NAME = "python-selve"
VENV_NAME = "venv"

# Farben für Konsolen-Ausgabe
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    # Windows Kompatibilität
    @classmethod
    def init_colors(cls):
        if platform.system() == "Windows":
            try:
                import colorama
                colorama.init(autoreset=True)
            except ImportError:
                # Deaktiviere Farben auf Windows ohne colorama
                for attr in dir(cls):
                    if not attr.startswith('_') and attr != 'init_colors':
                        setattr(cls, attr, '')

# Initialisiere Farben
Colors.init_colors()

def print_header(text: str):
    """Druckt eine formatierte Überschrift."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"{text.center(60)}")
    print(f"{'='*60}{Colors.END}\n")

def print_success(text: str):
    """Druckt eine Erfolgsmeldung."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    """Druckt eine Fehlermeldung."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text: str):
    """Druckt eine Warnmeldung."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text: str):
    """Druckt eine Informationsmeldung."""
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")

def print_step(step: int, total: int, text: str):
    """Druckt einen Schritt-Indikator."""
    print(f"{Colors.BOLD}[{step}/{total}] {Colors.CYAN}{text}{Colors.END}")

class SetupManager:
    """Verwaltet den Setup-Prozess für das python-selve Projekt."""
    
    def __init__(self, args):
        self.args = args
        self.project_root = Path(__file__).parent.absolute()
        self.venv_path = self.project_root / VENV_NAME
        self.python_exe = self._get_python_executable()
        self.setup_logging()
        
    def setup_logging(self):
        """Richtet Logging ein."""
        log_level = logging.DEBUG if self.args.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.project_root / 'setup.log'),
                logging.StreamHandler() if self.args.verbose else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _get_python_executable(self) -> str:
        """Ermittelt den Python-Interpreter."""
        if self.args.no_venv or not self.venv_path.exists():
            return sys.executable
        
        if platform.system() == "Windows":
            return str(self.venv_path / "Scripts" / "python.exe")
        else:
            return str(self.venv_path / "bin" / "python")

    def check_python_version(self) -> bool:
        """Überprüft die Python-Version."""
        print_step(1, 8, "Überprüfe Python-Version...")
        
        current_version = sys.version_info[:2]
        if current_version < MIN_PYTHON_VERSION:
            print_error(f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ wird benötigt, aber {current_version[0]}.{current_version[1]} ist installiert")
            return False
        
        print_success(f"Python {current_version[0]}.{current_version[1]} ist kompatibel")
        return True

    def setup_virtual_environment(self) -> bool:
        """Richtet virtuelle Umgebung ein."""
        if self.args.no_venv:
            print_info("Virtuelle Umgebung wird übersprungen")
            return True
            
        print_step(2, 8, "Richte virtuelle Umgebung ein...")
        
        try:
            if not self.venv_path.exists():
                print_info("Erstelle neue virtuelle Umgebung...")
                subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)], 
                             check=True, capture_output=True)
                print_success("Virtuelle Umgebung erstellt")
            else:
                print_info("Virtuelle Umgebung bereits vorhanden")
            
            # Aktualisiere Python-Pfad
            self.python_exe = self._get_python_executable()
            
            # Aktualisiere pip
            print_info("Aktualisiere pip...")
            subprocess.run([self.python_exe, "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print_error(f"Fehler beim Einrichten der virtuellen Umgebung: {e}")
            return False

    def install_dependencies(self) -> bool:
        """Installiert alle Abhängigkeiten."""
        print_step(3, 8, "Installiere Abhängigkeiten...")
        
        dependencies = [
            # Basis-Abhängigkeiten
            ("pyserial", "Serielle Kommunikation"),
            ("asyncio-mqtt", "MQTT-Unterstützung"),
            
            # Test-Abhängigkeiten
            ("pytest", "Test-Framework"),
            ("pytest-cov", "Code-Coverage"),
            ("pytest-asyncio", "Async-Test-Unterstützung"),
            ("pytest-mock", "Mock-Unterstützung"),
            ("pytest-xdist", "Parallele Tests"),
            ("pytest-html", "HTML-Berichte"),
            
            # Entwicklungs-Tools
            ("black", "Code-Formatierung"),
            ("flake8", "Code-Linting"),
            ("mypy", "Type-Checking"),
            ("colorama", "Farbige Ausgabe (Windows)"),
        ]
        
        if self.args.dev:
            dependencies.extend([
                ("sphinx", "Dokumentation"),
                ("sphinx-rtd-theme", "Dokumentations-Theme"),
                ("pre-commit", "Git-Hooks"),
                ("bandit", "Sicherheits-Scanner"),
            ])
        
        for package, description in dependencies:
            try:
                print_info(f"Installiere {package} ({description})...")
                subprocess.run([self.python_exe, "-m", "pip", "install", package], 
                             check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                print_warning(f"Konnte {package} nicht installieren: {e}")
        
        # Installiere das Projekt selbst im Entwicklungsmodus
        try:
            print_info("Installiere Projekt im Entwicklungsmodus...")
            subprocess.run([self.python_exe, "-m", "pip", "install", "-e", "."], 
                         check=True, capture_output=True, cwd=self.project_root)
            print_success("Alle Abhängigkeiten installiert")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Fehler bei der Installation: {e}")
            return False

    def detect_hardware(self) -> Tuple[bool, List[str]]:
        """Erkennt verfügbare Hardware."""
        print_step(4, 8, "Erkenne Hardware...")
        
        try:
            # Versuche seriellen Import
            result = subprocess.run([
                self.python_exe, "-c", 
                "import serial.tools.list_ports; "
                "ports = [p.device for p in serial.tools.list_ports.comports() "
                "if 'USB' in p.description or 'COM' in p.device or 'ttyUSB' in p.device]; "
                "print(','.join(ports))"
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                ports = [p.strip() for p in result.stdout.strip().split(',') if p.strip()]
                if ports:
                    print_success(f"Hardware erkannt: {', '.join(ports)}")
                    return True, ports
            
            print_warning("Keine kompatible Hardware erkannt")
            return False, []
            
        except Exception as e:
            print_warning(f"Hardware-Erkennung fehlgeschlagen: {e}")
            return False, []

    def run_tests(self, has_hardware: bool, hardware_ports: List[str]) -> bool:
        """Führt die Tests aus."""
        print_step(5, 8, "Führe Tests aus...")
        
        test_commands = []
        
        if self.args.quick:
            # Nur Unit-Tests
            test_commands.append(("Unit-Tests", [
                self.python_exe, "-m", "pytest", "tests/test_selve_unit.py", 
                "-v", "--tb=short"
            ]))
        else:
            # Vollständige Test-Suite
            test_commands.extend([
                ("Unit-Tests", [
                    self.python_exe, "-m", "pytest", "tests/test_selve_unit.py", 
                    "-v", "--cov=selve", "--cov-report=html"
                ]),
                ("Struktur-Tests", [
                    self.python_exe, "-m", "pytest", "tests/test_selve_structure.py", 
                    "-v"
                ]),
                ("Integrations-Tests", [
                    self.python_exe, "-m", "pytest", "tests/test_selve_integration.py", 
                    "-v"
                ])
            ])
            
            # Hardware-Tests wenn verfügbar oder erzwungen
            if has_hardware or self.args.force_hardware:
                if hardware_ports:
                    # Setze Umgebungsvariable für Hardware-Tests
                    os.environ['SELVE_TEST_PORT'] = hardware_ports[0]
                
                test_commands.append(("Hardware-Tests", [
                    self.python_exe, "-m", "pytest", "tests/test_selve_hardware.py", 
                    "-v", "--tb=short"
                ]))
            
            # Performance-Tests (optional)
            if not self.args.no_performance:
                test_commands.append(("Performance-Tests", [
                    self.python_exe, "-m", "pytest", "tests/test_selve_advanced.py", 
                    "-v", "--tb=short"
                ]))
        
        all_passed = True
        
        for test_name, command in test_commands:
            print_info(f"Führe {test_name} aus...")
            try:
                result = subprocess.run(command, cwd=self.project_root, 
                                     capture_output=not self.args.verbose)
                if result.returncode == 0:
                    print_success(f"{test_name} erfolgreich")
                else:
                    print_error(f"{test_name} fehlgeschlagen")
                    all_passed = False
            except Exception as e:
                print_error(f"Fehler bei {test_name}: {e}")
                all_passed = False
        
        return all_passed

    def generate_report(self, test_success: bool, has_hardware: bool):
        """Erstellt einen Bericht."""
        print_step(6, 8, "Erstelle Bericht...")
        
        report_path = self.project_root / "test_report.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"Python-Selve Test-Bericht\n")
            f.write(f"=" * 40 + "\n\n")
            f.write(f"Datum: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Python-Version: {sys.version}\n")
            f.write(f"Plattform: {platform.platform()}\n")
            f.write(f"Projekt-Pfad: {self.project_root}\n\n")
            
            f.write(f"Setup-Konfiguration:\n")
            f.write(f"  - Virtuelle Umgebung: {'Nein' if self.args.no_venv else 'Ja'}\n")
            f.write(f"  - Schneller Modus: {'Ja' if self.args.quick else 'Nein'}\n")
            f.write(f"  - Hardware erkannt: {'Ja' if has_hardware else 'Nein'}\n")
            f.write(f"  - Hardware erzwungen: {'Ja' if self.args.force_hardware else 'Nein'}\n\n")
            
            f.write(f"Test-Ergebnisse:\n")
            f.write(f"  - Gesamt-Status: {'✓ ERFOLGREICH' if test_success else '✗ FEHLGESCHLAGEN'}\n")
            
            # Coverage-Bericht hinzufügen falls vorhanden
            coverage_path = self.project_root / "htmlcov" / "index.html"
            if coverage_path.exists():
                f.write(f"  - Coverage-Bericht: {coverage_path}\n")
        
        print_success(f"Bericht erstellt: {report_path}")

    def cleanup(self):
        """Aufräumen nach Tests."""
        print_step(7, 8, "Räume auf...")
        
        # Temporäre Dateien entfernen
        temp_patterns = ["*.pyc", "__pycache__", ".pytest_cache"]
        for pattern in temp_patterns:
            for path in self.project_root.rglob(pattern):
                try:
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        shutil.rmtree(path)
                except Exception:
                    pass
        
        print_success("Aufräumen abgeschlossen")

    def show_next_steps(self, test_success: bool, has_hardware: bool):
        """Zeigt nächste Schritte an."""
        print_step(8, 8, "Nächste Schritte")
        
        print(f"\n{Colors.BOLD}Zusammenfassung:{Colors.END}")
        if test_success:
            print_success("Setup und Tests erfolgreich abgeschlossen!")
        else:
            print_error("Einige Tests sind fehlgeschlagen. Siehe Logs für Details.")
        
        print(f"\n{Colors.BOLD}Nächste Schritte:{Colors.END}")
        
        if not self.args.no_venv and self.venv_path.exists():
            if platform.system() == "Windows":
                activate_cmd = f"{self.venv_path}\\Scripts\\activate"
            else:
                activate_cmd = f"source {self.venv_path}/bin/activate"
            print_info(f"Virtuelle Umgebung aktivieren: {activate_cmd}")
        
        print_info("Tests erneut ausführen: python run_tests.py")
        print_info("Entwicklung starten: Siehe README.md für Details")
        
        if not has_hardware and not self.args.force_hardware:
            print_warning("Hardware-Tests wurden übersprungen. Verbinde ein Selve Gateway für vollständige Tests.")
        
        # Coverage-Bericht anzeigen
        coverage_path = self.project_root / "htmlcov" / "index.html"
        if coverage_path.exists():
            print_info(f"Coverage-Bericht öffnen: {coverage_path}")

    def run(self) -> bool:
        """Führt den kompletten Setup-Prozess aus."""
        print_header(f"Python-Selve Setup & Test Runner")
        print_info(f"Projekt-Pfad: {self.project_root}")
        
        try:
            # Schritt 1: Python-Version prüfen
            if not self.check_python_version():
                return False
            
            # Schritt 2: Virtuelle Umgebung
            if not self.setup_virtual_environment():
                return False
            
            # Schritt 3: Abhängigkeiten installieren
            if not self.install_dependencies():
                return False
            
            # Schritt 4: Hardware erkennen
            has_hardware, hardware_ports = self.detect_hardware()
            
            # Schritt 5: Tests ausführen
            test_success = self.run_tests(has_hardware, hardware_ports)
            
            # Schritt 6: Bericht erstellen
            self.generate_report(test_success, has_hardware)
            
            # Schritt 7: Aufräumen
            self.cleanup()
            
            # Schritt 8: Nächste Schritte
            self.show_next_steps(test_success, has_hardware)
            
            return test_success
            
        except KeyboardInterrupt:
            print_error("\nSetup wurde vom Benutzer abgebrochen")
            return False
        except Exception as e:
            print_error(f"Unerwarteter Fehler: {e}")
            self.logger.exception("Setup failed with unexpected error")
            return False

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(
        description="Automatisiertes Setup und Test-Runner für python-selve",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  %(prog)s                     # Vollständige automatische Einrichtung
  %(prog)s --quick             # Schnelle Einrichtung, nur Unit-Tests
  %(prog)s --no-venv           # Keine virtuelle Umgebung verwenden
  %(prog)s --force-hardware    # Hardware-Tests erzwingen
  %(prog)s --dev               # Entwicklungsmodus mit zusätzlichen Tools
        """
    )
    
    parser.add_argument(
        "--no-venv", 
        action="store_true",
        help="Keine virtuelle Umgebung erstellen/verwenden"
    )
    
    parser.add_argument(
        "--quick", 
        action="store_true",
        help="Schneller Modus: nur Unit-Tests ausführen"
    )
    
    parser.add_argument(
        "--force-hardware", 
        action="store_true",
        help="Hardware-Tests erzwingen, auch wenn keine Hardware erkannt wird"
    )
    
    parser.add_argument(
        "--no-performance", 
        action="store_true",
        help="Performance-Tests überspringen"
    )
    
    parser.add_argument(
        "--dev", 
        action="store_true",
        help="Entwicklungsmodus: zusätzliche Entwicklungstools installieren"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Ausführliche Ausgabe aktivieren"
    )
    
    args = parser.parse_args()
    
    # Setup-Manager erstellen und ausführen
    setup_manager = SetupManager(args)
    success = setup_manager.run()
    
    # Exit-Code setzen
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
