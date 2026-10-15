@echo off
title AI Chatbot Launcher
cd /d "%~dp0"
node launch.mjs
if errorlevel 1 pause
