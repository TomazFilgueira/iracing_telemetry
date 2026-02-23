@echo off
title Encerrar iRacing Telemetry
color 0C

echo.
echo  =====================================================
echo   🛑  Encerrando iRacing Telemetry
echo  =====================================================
echo.

:: Mata o coletor Python (read_iracing_cloud.py)
taskkill /f /im python.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo  ✅ Coletor iRacing encerrado.
) else (
    echo  ℹ️  Coletor nao estava rodando.
)

:: Mata o Streamlit (apenas se estiver rodando local - modo solo)
taskkill /f /im streamlit.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo  ✅ Dashboard local Streamlit encerrado.
) else (
    echo  ℹ️  Dashboard local nao estava rodando.
)

echo.
echo  ✨ Tudo encerrado!
echo  ℹ️  O servidor e dashboard no Render continuam
echo     rodando normalmente na nuvem.
echo.
pause
