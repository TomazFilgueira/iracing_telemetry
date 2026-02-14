@echo off
title Sistema de Telemetria - Finalizar e Arquivar
echo 🏁 Finalizando ecossistema de telemetria...

:: 1. Fecha as janelas específicas pelo título (evita fechar outros Pythons)
:: O filtro /FI busca o nome exato que demos no comando 'start'
taskkill /F /FI "WINDOWTITLE eq Captura iRacing*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Interface Dashboard*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Acesso Remoto*" /T >nul 2>&1

echo ✅ Terminais de telemetria encerrados.

:: 2. Configura os caminhos (Lendo as pastas que definimos no config.py)
set SOURCE_DIR=Data_Logs
set DEST_DIR=concluded_sessions

:: 3. Cria a pasta de destino se ela não existir
if not exist "%DEST_DIR%" (
    echo 📂 Criando pasta de sessoes concluidas...
    mkdir "%DEST_DIR%"
)

:: 4. Move os arquivos CSV para o arquivo histórico
echo 📦 Arquivando telemetria da sessao...
move "%SOURCE_DIR%\stint_*.csv" "%DEST_DIR%\" >nul 2>&1

if %errorlevel% equ 0 (
    echo ✨ Sucesso: Dados movidos para /%DEST_DIR%
) else (
    echo ℹ️ Nenhum arquivo novo para arquivar.
)

echo.
echo [Pronto para a proxima corrida, Tomaz!]
timeout /t 5
exit