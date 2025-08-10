#!/usr/bin/env python3
"""
Release script for python-selve-new

This script helps create new releases with automatic version bumping.
Usage:
    python release.py patch   # 2.3.4 -> 2.3.5
    python release.py minor   # 2.3.4 -> 2.4.0
    python release.py major   # 2.3.4 -> 3.0.0
"""

import subprocess
import sys
import re
from typing import Tuple


def get_current_version() -> str:
    """Get current version from git tags."""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # No tags found, start with v0.0.0
        return "v0.0.0"


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse version string into tuple."""
    # Remove 'v' prefix if present
    version = version.lstrip('v')
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(version: str, bump_type: str) -> str:
    """Bump version according to type."""
    major, minor, patch = parse_version(version)
    
    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")
    
    return f"v{major}.{minor}.{patch}"


def create_release(new_version: str):
    """Create a new git tag and push it."""
    print(f"Creating release {new_version}")
    
    # Create tag
    subprocess.run(['git', 'tag', '-a', new_version, '-m', f'Release {new_version}'], check=True)
    
    # Push tag
    subprocess.run(['git', 'push', 'origin', new_version], check=True)
    
    print(f"✅ Release {new_version} created and pushed!")
    print("GitHub Actions will now automatically:")
    print("  1. Run tests")
    print("  2. Build the package")
    print("  3. Publish to PyPI")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ['major', 'minor', 'patch']:
        print(__doc__)
        sys.exit(1)
    
    bump_type = sys.argv[1]
    
    # Check if working directory is clean
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.stdout.strip():
        print("❌ Working directory is not clean. Please commit your changes first.")
        sys.exit(1)
    
    current_version = get_current_version()
    new_version = bump_version(current_version, bump_type)
    
    print(f"Current version: {current_version}")
    print(f"New version: {new_version}")
    
    confirm = input("Create this release? (y/N): ")
    if confirm.lower() != 'y':
        print("Release cancelled.")
        sys.exit(0)
    
    create_release(new_version)


if __name__ == '__main__':
    main()
