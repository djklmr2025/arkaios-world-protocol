@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Sigue primero la preparacion en README.md.
  exit /b 2
)
if "%~1"=="" (
  ".venv\Scripts\python.exe" network.py --state .local-state
) else (
  ".venv\Scripts\python.exe" network.py --state .local-state --artifact "%~1"
)
exit /b %errorlevel%
