"""Fix Unicode encoding issues in scripts for Windows compatibility."""

import os
import re

def fix_unicode_in_file(filepath):
    """Replace Unicode characters with ASCII equivalents."""
    
    # Unicode to ASCII mapping
    unicode_map = {
        '\u2713': '[OK]',      # ✓
        '\u2705': '[OK]',      # ✅
        '\u274c': '[ERROR]',   # ❌
        '\u26a0': '[WARNING]', # ⚠️
        '\u1f389': '[SUCCESS]', # 🎉
        '\u1f4dd': '[NOTE]',   # 📝
        '\u1f517': '[LINK]',   # 🔗
        '\u1f4c1': '[FOLDER]', # 📁
        '\u1f504': '[LOADING]', # 🔄
        '\u1f6aa': '[SHOP]',   # 🏪
        '\u1f4cb': '[CLIPBOARD]', # 📋
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace Unicode characters
        for unicode_char, ascii_replacement in unicode_map.items():
            content = content.replace(unicode_char, ascii_replacement)
        
        # Write back with UTF-8 encoding
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fixed Unicode in: {filepath}")
        return True
        
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False

def main():
    """Fix Unicode issues in all Python scripts."""
    print("Fixing Unicode encoding issues for Windows compatibility...")
    
    # Files to fix
    files_to_fix = [
        'install.py',
        'test_mcp_simple.py',
        'troubleshoot.py',
        'prepare_repo.py'
    ]
    
    fixed_count = 0
    
    for filename in files_to_fix:
        if os.path.exists(filename):
            if fix_unicode_in_file(filename):
                fixed_count += 1
        else:
            print(f"File not found: {filename}")
    
    print(f"\nFixed {fixed_count} files")
    print("Unicode characters have been replaced with ASCII equivalents")
    print("Scripts should now work properly on Windows console")

if __name__ == "__main__":
    main()
