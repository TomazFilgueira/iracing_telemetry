@echo off
title iRacing Cloud Setup - Laptop

:: Ajuste o caminho abaixo se o seu Anaconda estiver em um local diferente
set CONDA_ACTIVATE_PATH=C:\Users\%USERNAME%\anaconda3\Scripts\activate.bat
set ENV_NAME=ir_telemetry

echo 🔄 Localizando ambiente Anaconda...

:: Verifica se o arquivo activate.bat existe
if not exist "%CONDA_ACTIVATE_PATH%" (
    echo ❌ Erro: O caminho do Anaconda nao foi encontrado.
    echo Verifique se o caminho em CONDA_ACTIVATE_PATH esta correto.
    pause
    exit
)

:: Inicia o Servidor FastAPI
echo 🚀 Iniciando Servidor Cloud...
start "FastAPI Server" cmd /k "call "%CONDA_ACTIVATE_PATH%" %ENV_NAME% && uvicorn server:app --host 0.0.0.0 --port 8000"

timeout /t 3

:: Inicia o Dashboard Streamlit
echo 📊 Iniciando Dashboard...
start "Strategy Dashboard" cmd /k "call "%CONDA_ACTIVATE_PATH%" %ENV_NAME% && streamlit run dashboard_cloud.py"

echo ✅ Tudo pronto! Agora abra o ngrok para gerar o link da nuvem.
pause