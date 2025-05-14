#!/usr/bin/env python
# Fix Batch_configuration_of_addresses.py indentation

# Read the file
with open('modules/Batch_configuration_of_addresses/Batch_configuration_of_addresses.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Manual fix for lines around line 141
# The specific problem is that we have an indentation issue with the else: statement
# We're only going to fix the specific section around line 141
for i in range(len(lines)):
    # Find and fix the problematic indentation in the else statement
    if i >= 137 and i <= 145:
        # Check if we found the incorrectly indented 'else:'
        if 'else:' in lines[i] and (lines[i].startswith('    else:') or lines[i].startswith('            else:')):
            # Ensure the line has the correct indentation
            lines[i] = '                    else:\n'
            print(f"Fixed line {i+1}: {lines[i].strip()}")

# Write back the fixed file
with open('modules/Batch_configuration_of_addresses/Batch_configuration_of_addresses.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('File fixed successfully') 