@echo off
title Racing4all - Sistema de Telemetria
echo 🏁 Iniciando o ecossistema Racing4all...

:: Garante que o terminal entenda onde o projeto está localizado
cd /d "%~dp0"

:: 1. Inicia o coletor de dados em uma janela separada (background)
echo 🏎️ Iniciando captura de dados (read_iracing.py)...
start "Captura iRacing" cmd /k python read_iracing.py

:: 2. Inicia o Dashboard do Streamlit na janela atual
echo 📊 Abrindo interface do Streamlit...
streamlit run dashboard.py

:: Caso o Streamlit seja fechado, o pause impede que a janela suma imediatamente
pause