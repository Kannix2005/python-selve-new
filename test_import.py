#!/usr/bin/env python3

import sys
sys.path.append('.')

try:
    from selve import Selve
    print('✓ Selve Import erfolgreich')
    
    # Basic instantiation test
    selve = Selve()
    print('✓ Selve Instanziierung erfolgreich')
    
    print('Alle grundlegenden Checks bestanden!')
except Exception as e:
    print(f'✗ Fehler: {e}')
    import traceback
    traceback.print_exc()
