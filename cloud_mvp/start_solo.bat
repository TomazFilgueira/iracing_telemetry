@echo off
title iRacing Telemetry - Modo Solo
color 0A

set CONDA_ACTIVATE_PATH=C:\Users\%USERNAME%\anaconda3\Scripts\activate.bat
set ENV_NAME=ir_telemetry

echo.
echo  =====================================================
echo   🏎️  iRacing Telemetry — MODO SOLO
echo  =====================================================
echo.

if not exist "%CONDA_ACTIVATE_PATH%" (
    echo  ❌ Anaconda nao encontrado. Chame o Tomaz.
    pause
    exit
)

start "iRacing Coletor" cmd /k "call "%CONDA_ACTIVATE_PATH%" %ENV_NAME% && python read_iracing_cloud.py"
timeout /t 3 /nobreak >nul
start "Dashboard" cmd /k "call "%CONDA_ACTIVATE_PATH%" %ENV_NAME% && streamlit run dashboard_cloud.py"
timeout /t 4 /nobreak >nul
start http://localhost:8501

echo  ✅ Pronto! O dashboard abrira no navegador.
echo.
pause
