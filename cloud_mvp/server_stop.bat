@echo off
title Encerrar Telemetria iRacing
echo 🛑 Encerrando processos do Servidor e Dashboard...

:: Mata o processo do Uvicorn (FastAPI)
taskkill /f /im uvicorn.exe >nul 2>&1
if %errorlevel% equ 0 (echo ✅ Servidor FastAPI encerrado.) else (echo ℹ️ Servidor nao estava rodando.)

:: Mata o processo do Streamlit (Dashboard)
taskkill /f /im streamlit.exe >nul 2>&1
if %errorlevel% equ 0 (echo ✅ Dashboard Streamlit encerrado.) else (echo ℹ️ Dashboard nao estava rodando.)

:: Opcional: Mata processos Python genéricos que sobraram do coletor
:: taskkill /f /im python.exe >nul 2>&1

echo.
echo ✨ Tudo limpo! As portas 8000 e 8501 estao livres.
pause