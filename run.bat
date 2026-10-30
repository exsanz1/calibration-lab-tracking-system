@echo off
setlocal EnableDelayedExpansion
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
) else if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
) else (
    where py >nul 2>nul
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=py"
    ) else (
        where python >nul 2>nul
        if !errorlevel! equ 0 (
            set "PYTHON_CMD=python"
        )
    )
)

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

:: 2. Check Database & Auto-Seed if Missing
if not exist "calibration.db" (
    echo [INFO] Database calibration.db belum ditemukan.
    echo Menjalankan inisialisasi awal database laboratorium (seed.py)...
    "%PYTHON_CMD%" seed.py
    if !errorlevel! neq 0 (
        echo [ERROR] Gagal melakukan inisialisasi database.
        pause
        exit /b 1
    )
    echo [OK] Database berhasil dibuat dan diisi data awal.
    echo.
)

:: 3. Launch Default Browser after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

:: 4. Start Uvicorn Server
echo ====================================================================
echo   Server berjalan di: http://localhost:8000
echo   Dokumentasi API di: http://localhost:8000/docs
echo.
echo   Tekan [Ctrl + C] untuk menghentikan server.
echo ====================================================================
echo.

"%PYTHON_CMD%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

echo.
pause
