@echo off
title iRacing Client - Telemetry

:: Ajuste o caminho abaixo se o seu Anaconda estiver em um local diferente
set CONDA_ACTIVATE_PATH=C:\Users\%USERNAME%\anaconda3\Scripts\activate.bat
set ENV_NAME=ir_telemetry

echo 🏎️ Ativando ambiente e conectando ao iRacing...

:: Executa o coletor
cmd /k "%CONDA_ACTIVATE_PATH% %ENV_NAME% && python read_iracing_cloud.py"

pause