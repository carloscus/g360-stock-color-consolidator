@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo === G360 Stock Consolidator - Build Portable ===
echo.

REM Verificar uv
where uv >nul 2>&1
if errorlevel 1 (
    echo Instalando uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
)

REM Build standalone con PyInstaller
echo [BUILD] Generando ejecutable standalone...
uv run pyinstaller ^
    --onefile ^
    --windowed ^
    --name "StockConsolidator-CIPSA" ^
    --icon assets\images\favicon.ico ^
    --add-data "assets;assets" ^
    --add-data "src;src" ^
    --add-data "g360_flet;g360_flet" ^
    --collect-all flet ^
    run.py

if errorlevel 1 (
    echo.
    echo ERROR: Fallo el build.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   BUILD EXITOSO
echo   Ejecutable en: dist\StockConsolidator-CIPSA.exe
echo ========================================
echo.
pause
