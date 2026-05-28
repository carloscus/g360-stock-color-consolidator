@echo off
:: ============================================
:: G360 Stock Color Consolidator - Portable Launcher
:: Ejecuta la aplicacion en cualquier PC Windows sin Python preinstalado
:: ============================================
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

:: ============================================
:: Funcion: Mostrar mensaje con timestamp
:: ============================================
goto :main

:LogMsg
    echo [%DATE% %TIME%] [%~1] %~2
    echo [%DATE% %TIME%] [%~1] %~2 >> %LOG_FILE%
    goto :eof

:main
set LOG_FILE=run_log.txt
echo [%DATE% %TIME%] Inicio launcher > %LOG_FILE%

:: ============================================
:: Funcion: Auto-minimizar consola
:: ============================================
if not "%1"=="-" (
    start /min cmd /c "%~dpnx0 -"
    exit /b 0
)

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
:: Funcion: Verificar conectividad a internet
:: ============================================
call :LogMsg "STEP" "Verificando conectividad..."
ping -n 1 -w 2000 github.com >nul 2>&1
if errorlevel 1 (
    call :LogMsg "ERROR" "Sin internet - ejecute con conexion o copie uv.exe desde otra PC"
    timeout /t 5 /nobreak >nul
    exit /b 1
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
call :InstallDependencies
call :InstallChromium
call :VerifyImports
call :LogMsg "OK" "Iniciando aplicacion..."

set "FLET_BIN=%~dp0.venv\Lib\site-packages\flet\bin"
if exist "%FLET_BIN%" set "PATH=%FLET_BIN%;%PATH%"

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
call :LogMsg "INFO" "uv.exe detectado, instalando Python..."
uv python install 3.10 2>> %LOG_FILE%
if errorlevel 1 (
    call :LogMsg "WARN" "Fallback a Python 3.11..."
    uv venv .venv --python 3.11 --seed >> %LOG_FILE% 2>&1
)
goto :eof

:SetupVenv
if exist ".venv\Scripts\python.exe" goto :eof
call :LogMsg "STEP" "Creando entorno virtual..."
uv venv .venv --python 3.10 --seed >> %LOG_FILE% 2>&1
if errorlevel 1 (
    call :LogMsg "WARN" "Fallback a Python 3.11/3.12..."
    uv venv .venv --python 3.11 --seed >> %LOG_FILE% 2>&1
    if errorlevel 1 uv venv .venv --python 3.12 --seed >> %LOG_FILE% 2>&1
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