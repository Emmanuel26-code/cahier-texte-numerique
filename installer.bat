@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Installation du projet Cahier de texte numerique ===
where py >nul 2>nul && (py setup.py) || (python setup.py)
echo.
pause
