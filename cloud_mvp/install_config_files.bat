@echo off
title iRacing Telemetry - Setup Equipe
echo 🛠️ Verificando e instalando dependencias do requirements.txt...

:: Verifica se o Python está no PATH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Erro: Python nao encontrado! Instale em python.org e marque "Add to PATH".
    pause
    exit
)

:: Instala as dependências exatas
python -m pip install -r requirements.txt --quiet

if %errorlevel% neq 0 (
    echo ❌ Falha ao instalar dependencias. Verifique sua conexao ou o arquivo requirements.txt.
    pause
    exit
)

echo ✅ Ambiente sincronizado! Iniciando envio para a nuvem...
python read_iracing.py

pause