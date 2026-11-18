@echo off
rem ============================================================================
rem  QGIS MCP - Instalador ETL: arranque SIN Python y SIN el .exe
rem
rem  Doble clic en este archivo (o ejecutalo desde una consola con los mismos
rem  argumentos que etl_installer.py). Hace tres cosas, todas a la vista:
rem
rem    1. Descarga `uv` (version y SHA-256 fijados, los mismos de manifest.py)
rem       con curl.exe, comprueba el hash con certutil.exe y lo extrae con
rem       tar.exe. Las tres herramientas vienen con Windows 10/11.
rem    2. Con `uv` instala un CPython 3.12 propio en %USERPROFILE%\qgis-mcp.
rem    3. Ejecuta etl_installer.py (el codigo de este mismo repositorio).
rem
rem  Sirve para equipos donde Windows (SmartScreen, antivirus, Smart App
rem  Control) no deja abrir el .exe sin firma, y no requiere administrador.
rem ============================================================================
setlocal EnableExtensions
set "UV_VERSION=0.13.7"
set "UV_SHA256=0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021"
set "UV_URL=https://github.com/astral-sh/uv/releases/download/%UV_VERSION%/uv-x86_64-pc-windows-msvc.zip"
set "PY_VERSION=3.12"

set "HERE=%~dp0"
set "BASE=%USERPROFILE%\qgis-mcp"
set "UVDIR=%BASE%\tools\uv"
set "UV=%UVDIR%\uv.exe"
set "UVZIP=%BASE%\downloads\uv-%UV_VERSION%-x86_64-pc-windows-msvc.zip"
set "SYS=%SystemRoot%\System32"

if not exist "%HERE%etl_installer.py" (
  echo [ERROR] No encuentro etl_installer.py junto a este archivo.
  echo         Extrae el ZIP completo antes de ejecutar instalar.cmd.
  goto :fail
)

if exist "%UV%" (
  "%UV%" --version 2>nul | "%SYS%\findstr.exe" /c:"%UV_VERSION%" >nul && goto :python
)

echo [1/3] Descargando uv %UV_VERSION% ...
if not exist "%UVDIR%" mkdir "%UVDIR%"
if not exist "%BASE%\downloads" mkdir "%BASE%\downloads"
"%SYS%\curl.exe" -fL --retry 3 --retry-delay 3 -o "%UVZIP%" "%UV_URL%"
if errorlevel 1 (
  echo [ERROR] No se pudo descargar uv. Revisa tu conexion a internet o el proxy.
  goto :fail
)
"%SYS%\certutil.exe" -hashfile "%UVZIP%" SHA256 | "%SYS%\findstr.exe" /i /x "%UV_SHA256%" >nul
if errorlevel 1 (
  echo [ERROR] El SHA-256 de uv NO coincide con el esperado. Descarga descartada.
  del "%UVZIP%" >nul 2>&1
  goto :fail
)
echo       SHA-256 verificado.
"%SYS%\tar.exe" -xf "%UVZIP%" -C "%UVDIR%"
if errorlevel 1 (
  echo [ERROR] No se pudo extraer uv.
  goto :fail
)

:python
set "UV_PYTHON_INSTALL_DIR=%BASE%\python"
set "UV_CACHE_DIR=%BASE%\cache\uv"
set "UV_MANAGED_PYTHON=1"
set "UV_NO_CONFIG=1"
set "UV_NO_PROJECT=1"
set "UV_NO_PROGRESS=1"
set "UV_SYSTEM_CERTS=1"
set "PY="
call :findpy
if not defined PY (
  echo [2/3] Instalando un CPython %PY_VERSION% propio en %BASE%\python ...
  "%UV%" python install --no-bin --no-registry %PY_VERSION%
  call :findpy
)
if not defined PY (
  echo [ERROR] No se pudo preparar Python %PY_VERSION%.
  goto :fail
)

echo [3/3] Iniciando el instalador ...
"%PY%" -E -s "%HERE%etl_installer.py" %*
set "RC=%ERRORLEVEL%"
goto :end

:findpy
rem Busca el python.exe que uv dejo en %BASE%\python (sin leer su salida, para
rem no depender de la pagina de codigos si la ruta tiene tildes).
for /d %%D in ("%BASE%\python\cpython-%PY_VERSION%*") do (
  if exist "%%D\python.exe" set "PY=%%D\python.exe"
)
exit /b 0

:fail
set "RC=1"

:end
echo %* | "%SYS%\findstr.exe" /c:"--non-interactive" >nul
if errorlevel 1 (
  echo.
  pause
)
exit /b %RC%
