# fix_files.py
files = [
    'src/backend/init_db.py',
    'src/backend/main.py',
    'src/backend/auth/shift_management.py'
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove all trailing whitespace/newlines, then add exactly one newline
    content = content.rstrip() + '\n'
    
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    
    print(f"Fixed {filepath}")

print("\ All files fixed!")