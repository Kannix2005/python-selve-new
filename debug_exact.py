original_malformed = '<?xml version="1.0"? encoding="UTF-8"?>'
expected_pattern = '<?xml version="1.0"? encoding="UTF-8"?>'

print("Original malformed:")
for i, char in enumerate(original_malformed):
    print(f"  {i:2}: {repr(char)} ({ord(char)})")

print("\nExpected pattern:")
for i, char in enumerate(expected_pattern):
    print(f"  {i:2}: {repr(char)} ({ord(char)})")

print("\nAre they equal?", original_malformed == expected_pattern)

# Let me also check what's actually in the source code
with open('selve/__init__.py', 'r') as f:
    content = f.read()
    
import re
match = re.search(r'xmlstr\.replace\([^)]+\)', content)
if match:
    print("\nFound in source code:")
    print(match.group())

# Try to find the exact strings
malformed_pattern = re.search(r"'([^']*\?[^']*)'", content[content.find('xmlstr.replace'):content.find('xmlstr.replace')+200])
if malformed_pattern:
    print("\nMalformed pattern from source:", repr(malformed_pattern.group(1)))
