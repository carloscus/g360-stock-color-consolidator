@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

set LOG_FILE=run_log.txt
echo [%DATE% %TIME%] Inicio launcher > %LOG_FILE%

goto :main

:LogMsg
    echo [%DATE% %TIME%] [%~1] %~2
    echo [%DATE% %TIME%] [%~1] %~2 >> %LOG_FILE%
    goto :eof

:main
:: ============================================
:: Funcion: Verificar privilegios de admin
:: Uso: solo informa, no requiere elevacion
:: ============================================
net session >nul 2>&1
if errorlevel 1 (
    call :LogMsg "INFO" "Sin privilegios de admin - usando modo portable (sin instalar Python sistema)"
    set "NEED_ADMIN=0"
) else (
    set "NEED_ADMIN=1"
)

:: ============================================
:: Funcion: Verificar DLLs de Visual C++ runtime
:: ============================================
call :CheckVCRuntime

:: ============================================
:: PASO 0: Verificar conectividad
:: ============================================
call :LogMsg "STEP" "Verificando conectividad..."
ping -n 1 -w 2000 github.com >nul 2>&1
if errorlevel 1 (
    call :LogMsg "WARN" "Sin internet - conexión opcional si ya existe uv.exe"
) else (
    call :LogMsg "OK" "Conexion a internet OK"
)

:: ============================================
:: Funcion: Detectar o instalar Python
:: ============================================
call :LogMsg "STEP" "Verificando Python..."
where python >nul 2>&1
if not errorlevel 1 goto :RunApp

:: ============================================
:: Funcion: Usar uv.exe existente o descargar
:: ============================================
call :SetupPythonWithUV

:: ============================================
:: Funcion: Iniciar aplicacion
:: ============================================
:RunApp
call :SetupVenv
if errorlevel 1 exit /b 1
call :InstallDependencies
if errorlevel 1 exit /b 1
call :InstallChromium
call :VerifyImports
if errorlevel 1 exit /b 1
call :LogMsg "OK" "Iniciando aplicacion..."

set "FLET_BIN=%~dp0.venv\Lib\site-packages\flet\bin"
if exist "%FLET_BIN%" set "PATH=%FLET_BIN%;%PATH%"

if not exist ".venv\Scripts\python.exe" (
    call :LogMsg "ERROR" "Python no disponible en .venv\Scripts"
    type %LOG_FILE%
    pause
    exit /b 1
)

call :LogMsg "OK" "Ejecutando aplicacion..."
.venv\Scripts\python.exe run.py
if errorlevel 1 (
    call :LogMsg "ERROR" "La aplicacion fallo - ver run_log.txt"
    type %LOG_FILE%
    pause
)
exit /b 0

:: ============================================
:: Funciones auxiliares
:: ============================================

:CheckVCRuntime
set "MISSING_DLL=0"
for %%d in (vcruntime140.dll msvcp140.dll) do (
    where %%d >nul 2>&1
    if errorlevel 1 set "MISSING_DLL=1"
)
if "%MISSING_DLL%"=="1" if "%NEED_ADMIN%"=="1" (
    call :LogMsg "WARNING" "Faltan DLLs de Visual C++ - instale: https://aka.ms/vs/17/release/vc_redist_x64.exe"
)
goto :eof

:SetupPythonWithUV
if not exist "uv.exe" (
    call :LogMsg "ERROR" "Sin Python e internet - copie uv.exe desde otra PC o conectese"
    timeout /t 10 /nobreak >nul
    exit /b 1
)
set "PATH=%~dp0;%PATH%"
call :LogMsg "INFO" "uv.exe detectado, listo para crear entorno virtual"
goto :eof

:SetupVenv
call :LogMsg "STEP" "Preparando entorno virtual (.venv)..."
if exist ".venv\Scripts\python.exe" (
    call :LogMsg "INFO" "Verificando .venv existente..."
    .venv\Scripts\python.exe -c "import sys" 2>> %LOG_FILE%
    if errorlevel 1 (
        call :LogMsg "WARN" ".venv corrupto, recreando..."
        rd /s /q ".venv" >> %LOG_FILE% 2>&1
    ) else (
        call :LogMsg "OK" ".venv existe y funciona"
        goto :eof
    )
)
call :LogMsg "INFO" "Creando nuevo entorno virtual..."
uv venv .venv --python 3.10 --seed >> %LOG_FILE% 2>&1
if errorlevel 1 (
    call :LogMsg "WARN" "Fallback a Python 3.11/3.12..."
    uv venv .venv --python 3.11 --seed >> %LOG_FILE% 2>&1
    if errorlevel 1 uv venv .venv --python 3.12 --seed >> %LOG_FILE% 2>&1
)
if exist ".venv\Scripts\python.exe" (
    call :LogMsg "OK" "Entorno virtual listo"
) else (
    call :LogMsg "ERROR" "No se pudo crear el entorno virtual"
    exit /b 1
)
goto :eof

:InstallDependencies
call :LogMsg "STEP" "Instalando dependencias..."
uv pip install -r requirements.txt >> %LOG_FILE% 2>&1
if errorlevel 1 (
    call :LogMsg "ERROR" "Error al instalar dependencias"
    type %LOG_FILE%
    pause
    exit /b 1
)
goto :eof

:InstallChromium
call :LogMsg "STEP" "Instalando Chromium (para descarga S2)..."
set "CHROMIUM_OK=0"
for /l %%i in (1,1,3) do (
    .venv\Scripts\python.exe -m playwright install chromium >> %LOG_FILE% 2>&1
    if not errorlevel 1 (
        set "CHROMIUM_OK=1"
        call :LogMsg "OK" "Chromium instalado"
        goto :eof
    )
    timeout /t 2 /nobreak >nul
)
call :LogMsg "WARN" "Chromium fallo - puede cargar S2 manualmente"
goto :eof

:VerifyImports
call :LogMsg "STEP" "Verificando modulos..."
.venv\Scripts\python.exe -c "import flet, pandas, openpyxl, bs4, lxml" 2>> %LOG_FILE%
if errorlevel 1 (
    call :LogMsg "ERROR" "Verificacion fallida - ver run_log.txt"
    type %LOG_FILE%
    pause
    exit /b 1
)
call :LogMsg "OK" "Todos los modulos disponibles"
goto :eof