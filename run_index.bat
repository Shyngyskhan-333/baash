@echo off
call .\venv\Scripts\activate.bat
python pipeline.py --build-index %*
pause
