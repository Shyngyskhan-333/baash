import os
import zipfile
import re

def create_clean_zip():
    source_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(os.path.dirname(source_dir), 'baash_ready.zip')
    
    exclude_dirs = {'.git', 'venv', '.venv', 'env', '__pycache__', '.idea', '.vscode', '.streamlit'}
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            rel_root = os.path.relpath(root, source_dir)
            
            # Исключаем тяжелые папки с векторами
            if any(rel_root.replace('\\', '/').startswith(ep) for ep in ['data/cache', 'data/faiss', 'data/embeddings', 'data/raw']):
                continue
                
            for file in files:
                # Пропускаем временные скрипты
                if file in ['remove_comments.py', 'cleanup_script.py', 'zip_clean_repo.py', 'baash_ready.zip']:
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                
                # Маскируем .env
                if file == '.env':
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    cleaned_env = re.sub(r'(=).*', r'=', content)
                    zipf.writestr(arcname, cleaned_env)
                    
                # Убираем комментарии из .py файлов по пути
                elif file.endswith('.py'):
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    new_lines = [line for line in lines if not re.match(r'^\s*#', line)]
                    zipf.writestr(arcname, ''.join(new_lines))
                
                else:
                    zipf.write(file_path, arcname)
    
    print(f"✅ Готово! Легковесный архив сохранен на рабочем столе: {zip_path}")
    print("В нем удалены все тяжелые веса моделей, виртуальное окружение и ключи API.")

if __name__ == '__main__':
    create_clean_zip()
