@echo off
title Sistema de Telemetria - Finalizar e Arquivar
echo 🏁 Encerrando processos de telemetria...

:: 1. Mata os processos específicos filtrando pelo nome do arquivo
:: Isso garante que apenas o SEU coletor e o SEU dashboard sejam fechados.
wmic process where "CommandLine like '%%read_iracing.py%%'" call terminate >nul 2>&1
wmic process where "CommandLine like '%%streamlit%%'" call terminate >nul 2>&1
wmic process where "CommandLine like '%%ngrok%%'" call terminate >nul 2>&1

echo ✅ Scripts de captura e dashboard encerrados.

:: 2. Configura os caminhos (Mesma lógica do seu config.py)
set SOURCE_DIR=Data_Logs
set DEST_DIR=concluded_sessions

:: 3. Cria a pasta de destino se ela não existir
if not exist "%DEST_DIR%" (
    echo 📂 Criando pasta de sessoes concluidas...
    mkdir "%DEST_DIR%"
)

:: 4. Move os arquivos CSV da sessão atual para o histórico
echo 📦 Arquivando telemetria...
move "%SOURCE_DIR%\stint_*.csv" "%DEST_DIR%\" >nul 2>&1

if %errorlevel% equ 0 (
    echo ✨ Sucesso: Dados movidos para /%DEST_DIR%
) else (
    echo ℹ️ Nenhum arquivo novo encontrado para mover.
)

echo.
echo [Tudo pronto para a proxima corrida, Tomaz!]
timeout /t 5
exit