import os
import re

def clean_project():
    # 1. Clear .env file to protect API keys when sharing
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Keep keys but empty values
        cleaned_env = re.sub(r'(=).*', r'=YOUR_KEY_HERE', content)
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_env)
        print("Scrubbed API keys from .env")

    # 2. Delete whole-line comments starting with # from .py files
    py_files = []
    for root, _, files in os.walk('.'):
        if 'venv' in root or '.venv' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py') and file != 'cleanup_script.py':
                py_files.append(os.path.join(root, file))

    removed_lines = 0
    for file in py_files:
        with open(file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Keep lines that do NOT match 'optional whitespace then #'
        new_lines = [line for line in lines if not re.match(r'^\s*#', line)]
        
        if len(lines) != len(new_lines):
            with open(file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            removed_lines += (len(lines) - len(new_lines))
            print(f"Cleaned {file}")
            
    print(f"Removed {removed_lines} comment lines in total.")

if __name__ == '__main__':
    clean_project()
    # Self-destruct old script if exists
    if os.path.exists('remove_comments.py'):
        os.remove('remove_comments.py')
