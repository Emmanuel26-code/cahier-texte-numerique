@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Rappel : MySQL doit etre demarre dans XAMPP.
start "" http://127.0.0.1:8000/admin/
.venv\Scripts\python.exe manage.py runserver
pause
