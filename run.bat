@echo off
title GraphRAG Dashboard
cd /d "%~dp0"

echo Starting Django server...
start cmd /k "cd Django_Dashboard && python manage.py runserver"

timeout /t 4 >nul

echo Opening browser...
start "" "http://127.0.0.1:8000/"

timeout /t 2 >nul

echo Starting Uploader GUI...
start "" python uploader.py

echo Done.
exit
