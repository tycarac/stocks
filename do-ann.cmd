@echo off
setlocal

call .venv\scripts\activate
python getann.py %*
