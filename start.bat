@echo off
title AI Chatbot Launcher

echo [1/3] Starting backend (FastAPI, http://localhost:8000)
start "Chatbot Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn main:app --reload"

echo [2/3] Starting frontend (Vite, http://localhost:5173)
echo       If port 5173 is already used by another app, this step will fail - close that app first.
start "Chatbot Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --port 5173 --strictPort"

echo [3/3] Waiting for servers to start...
ping -n 6 127.0.0.1 >nul

start chrome http://localhost:5173

echo Done. Check Chrome for the chatbot.
echo To stop the servers, close the two new console windows (Backend / Frontend).
