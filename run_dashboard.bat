@echo off
REM Запуск визуального дашборда UI
call .\venv\Scripts\activate.bat
streamlit run app/dashboard.py
pause
