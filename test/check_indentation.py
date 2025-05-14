#!/usr/bin/env python
# Check for indentation issues in Batch_configuration_of_addresses.py

# This script will check for any indentation issues in the Python file

import sys
import tokenize
import io

filename = 'modules/Batch_configuration_of_addresses/Batch_configuration_of_addresses.py'

try:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Try to compile the code to check for syntax errors
    compile(content, filename, 'exec')
    print(f"✅ No syntax errors found in {filename}")
    
except SyntaxError as e:
    line_no = e.lineno
    msg = e.msg
    print(f"❌ Syntax error in {filename} at line {line_no}: {msg}")
    
    # Print the problematic lines for context
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Print a few lines before and after the error for context
    context = 3
    start = max(0, line_no - context - 1)
    end = min(len(lines), line_no + context)
    
    print("\nContext:")
    for i in range(start, end):
        prefix = ">>>" if i == line_no - 1 else "   "
        print(f"{prefix} Line {i+1}: {lines[i].rstrip()}")
        
except Exception as e:
    print(f"Error checking file: {str(e)}") 