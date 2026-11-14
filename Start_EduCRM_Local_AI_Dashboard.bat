@echo off
setlocal
cd /d "%~dp0"
python ollama_summary_server.py
endlocal
