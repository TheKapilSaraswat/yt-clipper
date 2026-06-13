@echo off
cd /d "%~dp0"
C:\Windows\py.exe daily_pipeline.py >> pipeline_log.txt 2>&1
