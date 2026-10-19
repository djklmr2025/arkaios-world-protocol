@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Uso: run_pilot.cmd "C:\ARKAIOS\music-circuit-source"
  exit /b 2
)
if not exist ".venv-pilot\Scripts\python.exe" (
  py -3.11 -m venv .venv-pilot
  if errorlevel 1 exit /b 1
)
".venv-pilot\Scripts\python.exe" -m pip install -r simulator\agent_economy\requirements-circuit.txt
if errorlevel 1 exit /b 1
".venv-pilot\Scripts\python.exe" run_pilot.py --music-root "%~1"
exit /b %errorlevel%
