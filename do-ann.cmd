@echo off
setlocal

call .venv\scripts\activate
python.exe announcements %*
