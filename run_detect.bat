@echo off
call .\venv\Scripts\activate.bat
python pipeline.py --detect-all
pause
