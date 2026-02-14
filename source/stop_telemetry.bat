@echo off
title Encerrando e Arquivando - Racing4all
echo Finalizando processos de telemetria...

:: 1. Mata os processos do Python e Streamlit
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM streamlit.exe /T >nul 2>&1

echo OK -  Processos encerrados.

:: 2. Configura os caminhos (Mesma lógica do seu config.py)
set SOURCE_DIR=Data_Logs
set DEST_DIR=concluded_sessions

:: 3. Cria a pasta de destino se ela não existir
if not exist "%DEST_DIR%" (
    echo Criando pasta de sessões concluídas...
    mkdir "%DEST_DIR%"
)

:: 4. Move os arquivos CSV da sessão atual para o arquivo histórico
echo  Arquivando telemetria...
move "%SOURCE_DIR%\stint_*.csv" "%DEST_DIR%\" >nul 2>&1

if %errorlevel% equ 0 (
    echo Sessao arquivada com sucesso em /%DEST_DIR%
) else (
    echo  Nenhum arquivo novo encontrado para mover.
)

echo.
echo [Tudo pronto para a proxima corrida!]
pause