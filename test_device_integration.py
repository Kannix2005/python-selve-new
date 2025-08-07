import subprocess
import sys
import os

os.chdir(r'c:\Users\Stefan\Documents\Projekte\python-selve-new')

result = subprocess.run([
    'venv\\Scripts\\python.exe', '-m', 'pytest', 
    'tests/test_selve_integration.py::TestSelveCommandsIntegration::test_device_commands_integration',
    '-v', '--tb=long'
], capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")
