@echo off
setlocal

call .venv\scripts\activate
python fetch.py %*
