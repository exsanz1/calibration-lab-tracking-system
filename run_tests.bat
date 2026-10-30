@echo off
setlocal
title CalibTrack - Run Tests and Mypy Check
cd /d "%~dp0"

echo ====================================================================
echo        CalibTrack - Automated Unit Tests and Type Check
echo ====================================================================
echo.

set "PYTHON_CMD="

if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
    goto :python_found
)

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    goto :python_found
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=py"
    goto :python_found
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python"
    goto :python_found
)

:python_found
if not defined PYTHON_CMD (
    echo [ERROR] Python tidak ditemukan.
    pause
    exit /b 1
)

echo [1/2] Menjalankan Pytest ...
echo --------------------------------------------------------------------
"%PYTHON_CMD%" -m pytest tests/ -v
if errorlevel 1 (
    echo.
    echo [FAIL] Pengujian pytest mengalami kegagalan!
    pause
    exit /b 1
)

echo.
echo [2/2] Menjalankan Mypy Strict Type Check ...
echo --------------------------------------------------------------------
"%PYTHON_CMD%" -m mypy app tests
if errorlevel 1 (
    echo.
    echo [FAIL] Mypy mendeteksi error pengetikan tipe!
    pause
    exit /b 1
)

echo.
echo ====================================================================
echo   [SUKSES] Seluruh pengujian dan pemeriksaan tipe lolos 100%%!
echo ====================================================================
echo.
pause
