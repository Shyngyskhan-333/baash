@echo off
REM Автоматический запуск индексации внутри правильного окружения
call .\venv\Scripts\activate.bat
python pipeline.py --build-index %*
pause
