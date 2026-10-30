@echo off
setlocal
title CalibTrack - Calibration Lab Operational and Tracking System
cd /d "%~dp0"

echo ====================================================================
echo        CalibTrack - Calibration Lab Operational System
echo ====================================================================
echo.

:: 1. Detect Working Python Binary
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
    echo [ERROR] Python tidak ditemukan pada sistem.
    echo Pastikan Python 3.11+ telah terinstal.
    echo.
    pause
    exit /b 1
)

echo [OK] Menggunakan Python: "%PYTHON_CMD%"
"%PYTHON_CMD%" --version
echo.

:: 2. Check Database and Auto-Seed if Missing
if not exist "calibration.db" goto :init_db
goto :run_app

:init_db
echo [INFO] Database calibration.db belum ditemukan.
echo Menjalankan inisialisasi awal database laboratorium seed.py ...
"%PYTHON_CMD%" seed.py
if errorlevel 1 (
    echo [ERROR] Gagal melakukan inisialisasi database.
    pause
    exit /b 1
)
echo [OK] Database berhasil dibuat dan diisi data awal.
echo.

:run_app
:: 3. Launch Default Browser after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"

:: 4. Start Uvicorn Server
echo ====================================================================
echo   Server berjalan di: http://127.0.0.1:8000
echo   Dokumentasi API di: http://127.0.0.1:8000/docs
echo.
echo   Tekan Ctrl+C untuk menghentikan server.
echo ====================================================================
echo.

"%PYTHON_CMD%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

echo.
pause
