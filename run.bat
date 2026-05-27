@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title G360 App
cd /d "%~dp0"

REM Si no se pasa "visible", relanzar minimizado
if not "%1"=="visible" (
    start /min cmd /c "%~dpnx0 visible"
    exit /b 0
)

set LOG_FILE=run_log.txt
echo [%DATE% %TIME%] > %LOG_FILE%

echo.
echo ==============================================
echo   G360 - Running Application
echo ==============================================
echo.

REM --------------------------
REM VERIFICAR PYTHON (usando UV)
REM --------------------------
echo [1/5] Verificando entorno...
echo [1/5] python >> %LOG_FILE%

where python >nul 2>&1
if not errorlevel 1 (
    echo   Python encontrado, usando instalacion del sistema
    echo [1/5] python sistema >> %LOG_FILE%
    goto :run_app
)

if not exist "uv.exe" (
    where uv >nul 2>&1
    if not errorlevel 1 (
        echo   UV encontrado en el sistema.
    ) else (
        echo   Descargando uv portable...
        echo [1/5] descargando uv >> %LOG_FILE%
        powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip -OutFile uv.zip"
        tar -xf uv.zip >nul 2>&1
        del uv.zip >nul 2>&1
        if not exist "uv.exe" (
            echo   ERROR: No se pudo descargar uv
            echo [1/5] ERROR uv >> %LOG_FILE%
            pause & exit /b
        )
        echo   uv descargado en la carpeta del proyecto.
    )
) else (
    echo   Usando uv local.
)
set "PATH=%~dp0;%PATH%"
uv python install 3.10

:run_app
REM --------------------------
REM CREAR ENTORNO VIRTUAL
REM --------------------------
echo [2/5] Preparando entorno virtual...
echo [2/5] venv >> %LOG_FILE%

if not exist ".venv\Scripts\python.exe" (
    uv venv .venv --python 3.10 --seed >> %LOG_FILE% 2>&1
    if not exist ".venv\Scripts\python.exe" (
        echo ERROR: No se pudo crear el entorno virtual
        echo [2/5] ERROR venv >> %LOG_FILE%
        pause
        exit /b
    )
)

REM --------------------------
REM INSTALAR DEPENDENCIAS
REM --------------------------
echo [3/5] Instalando dependencias...
echo [3/5] pip install >> %LOG_FILE%

uv pip install -r requirements.txt >> %LOG_FILE% 2>&1
if errorlevel 1 (
    type %LOG_FILE%
    echo ERROR: No se pudieron instalar las dependencias
    echo [3/5] ERROR deps >> %LOG_FILE%
    pause
    exit /b
)

REM --------------------------
REM INSTALAR CHROMIUM
REM --------------------------
echo [4/5] Instalando Chromium...
set CHROMIUM_OK=0
for /l %%i in (1,1,3) do (
    echo [4/5] playwright ^(intento %%i de 3^) >> %LOG_FILE%
    if %%i==1 echo.
    echo    [%%i/3] Instalando Chromium...
    .venv\Scripts\python.exe -m playwright install chromium >> %LOG_FILE% 2>&1
    if !errorlevel! equ 0 (
        set CHROMIUM_OK=1
        echo    [%%i/3] Chromium instalado correctamente.
        echo [4/5] playwright OK ^(intento %%i^) >> %LOG_FILE%
        goto :chromium_ok
    )
    echo    [%%i/3] Chromium: ERROR - revise run_log.txt
    echo [4/5] playwright ERROR ^(intento %%i^) >> %LOG_FILE%
    if %%i lss 3 (
        echo    Reintentando en 5 segundos...
        timeout /t 5 /nobreak >nul
    )
)
:chromium_ok
if not "%CHROMIUM_OK%"=="1" (
    echo.
    echo =============================================
    echo   ERROR: No se pudo instalar Chromium
    echo   Revise run_log.txt para detalles
    echo =============================================
    echo.
    echo    Para instalar manualmente:
    echo    .venv\Scripts\python.exe -m playwright install chromium
    echo.
    pause
)

REM --------------------------
REM VERIFICAR INSTALACION
REM --------------------------
echo.
echo [5/5] Verificando instalacion...
echo [5/5] verificacion >> %LOG_FILE%
.venv\Scripts\python.exe -c "import flet, pandas, openpyxl, playwright, bs4, lxml" >> %LOG_FILE% 2>&1
if errorlevel 1 (
    echo.
    echo ==============================================
    echo   ERROR: Instalacion incompleta
    echo   Revise el archivo run_log.txt para detalles
    echo ==============================================
    echo [5/5] ERROR verificacion >> %LOG_FILE%
    type %LOG_FILE%
    pause
    exit /b
)
echo    Instalacion verificada correctamente.
echo [5/5] verificacion OK >> %LOG_FILE%

REM --------------------------
REM CREAR ACCESO DIRECTO
REM --------------------------
echo.
echo Verificando acceso directo...

if exist "%~dp0create_shortcut.vbs" (
    cscript //nologo "%~dp0create_shortcut.vbs" >nul 2>&1
)

REM --------------------------
REM AGREGAR DLLS NATIVAS DE FLET AL PATH
REM (evita error 'DLL load failed' si falta VC++ Redistributable)
REM --------------------------
set "FLET_BIN=%~dp0.venv\Lib\site-packages\flet\bin\flet"
if exist "%FLET_BIN%\vcruntime140.dll" (
    set "PATH=%FLET_BIN%;%PATH%"
)

REM --------------------------
REM INICIAR APLICACION
REM --------------------------
echo.
echo ==============================================
echo   Aplicacion iniciada correctamente
echo   Esta ventana se cerrara en 5 segundos...
echo ==============================================
echo.

start "" /min .venv\Scripts\python.exe src\main.py >> %LOG_FILE% 2>&1
timeout /t 3 /nobreak >nul
exit
