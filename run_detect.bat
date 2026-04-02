@echo off
REM Запуск детектора (Аудит всей базы)
call .\venv\Scripts\activate.bat
python pipeline.py --detect-all
pause
