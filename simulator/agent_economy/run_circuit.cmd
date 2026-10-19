@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Uso: run_circuit.cmd "C:\ARKAIOS\music-circuit-source"
  echo Preparacion y dependencias: ver CIRCUIT.md
  exit /b 2
)
if not exist ".venv-circuit\Scripts\python.exe" (
  echo Falta el entorno Python. Sigue la preparacion en CIRCUIT.md.
  exit /b 2
)
".venv-circuit\Scripts\python.exe" circuit.py --state ".local-state" --music-root "%~1"
exit /b %errorlevel%
