@echo off
title iRacing Telemetry - Modo Solo
color 0A
chcp 65001 >nul

set CONDA_ACTIVATE_PATH=C:\Users\%USERNAME%\anaconda3\Scripts\activate.bat
set ENV_NAME=ir_telemetry

echo.
echo  =====================================================
echo   🏎️  iRacing Telemetry — MODO SOLO
echo  =====================================================
echo.

if not exist "%CONDA_ACTIVATE_PATH%" (
    echo  ❌ Anaconda nao encontrado. Verifique o caminho em CONDA_ACTIVATE_PATH. Ou instale o pacote.
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
