@echo off
title iRacing Telemetry - Modo Equipe
color 0E
chcp 65001 >nul

set CONDA_ACTIVATE_PATH=C:\Users\%USERNAME%\anaconda3\Scripts\activate.bat
set ENV_NAME=ir_telemetry
set DASHBOARD_URL=https://dashboard-dmvw.onrender.com

echo.
echo  =====================================================
echo   🏎️  iRacing Telemetry — MODO EQUIPE
echo  =====================================================
echo.
echo  Dashboard da equipe:
echo  %DASHBOARD_URL%
echo.

if not exist "%CONDA_ACTIVATE_PATH%" (
    echo  ❌ Anaconda nao encontrado. Verifique o caminho em CONDA_ACTIVATE_PATH. Ou instale o pacote.
    exit
)

start %DASHBOARD_URL%
timeout /t 2 /nobreak >nul
start "iRacing Coletor" cmd /k "call "%CONDA_ACTIVATE_PATH%" %ENV_NAME% && python read_iracing_cloud.py"

echo  ✅ Pronto! Enviando telemetria para a equipe.
echo.
pause
