#!/usr/bin/env python3
"""
Script to update hardware test fixtures
"""
import re

# Read the file
with open('tests/test_selve_hardware.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace selve_hardware parameter with setup_selve
content = re.sub(r'async def test_([^(]+)\(self, selve_hardware\)', r'async def test_\1(self, setup_selve)', content)

# Replace await selve_hardware.setup calls (they're not needed anymore)
content = re.sub(r'await selve_hardware\.setup\([^)]+\)\s*\n', '', content)

# Replace selve_hardware references with setup_selve
content = re.sub(r'selve_hardware', 'setup_selve', content)

# Write the file back
with open('tests/test_selve_hardware.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Hardware tests updated successfully')
