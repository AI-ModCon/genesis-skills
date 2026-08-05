#!/usr/bin/env python3
"""
JSON Validator - Simple utility to validate JSON files

Usage:
    python load_json_test.py <json_file>

Returns:
    VALID - if the JSON file loads successfully
    INVALID - if the JSON file fails to load
"""

import json
import sys


def validate_json(filepath):
    """
    Validate a JSON file by attempting to load it.
    
    Args:
        filepath: Path to the JSON file to validate
        
    Returns:
        "VALID" if successful, "INVALID" otherwise
    """
    try:
        with open(filepath, 'r') as f:
            json.load(f)
        return "VALID"
    except (FileNotFoundError, json.JSONDecodeError, PermissionError, OSError):
        return "INVALID"


def main():
    if len(sys.argv) != 2:
        print("INVALID")
        sys.exit(1)
    
    filepath = sys.argv[1]
    result = validate_json(filepath)
    print(result)
    
    # Exit with appropriate status code
    sys.exit(0 if result == "VALID" else 1)


if __name__ == "__main__":
    main()
