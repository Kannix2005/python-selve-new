class MockErrorResponse:
    """Mock-Klasse für Gateway Fehlerantworten"""
    def __init__(self, error_type, message):
        self.error_type = error_type
        self.message = message
        self.name = "selve.GW.error"
        self.executed = False  # Für Kompatibilität mit Methoden, die executed prüfen
        self.result = False    # Für Kompatibilität mit Methoden, die result prüfen
        self.serial = None     # Für Kompatibilität mit Methoden, die nach serial fragen
        self.version = None    # Für Kompatibilität mit Methoden, die nach version fragen
