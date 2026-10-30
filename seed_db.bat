@echo off
setlocal EnableDelayedExpansion
title CalibTrack - Reset and Seed Database
cd /d "%~dp0"

echo ====================================================================
echo        CalibTrack - Reset dan Seed Database Laboratorium
echo ====================================================================
echo.

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
    echo [ERROR] Python tidak ditemukan.
    pause
    exit /b 1
)

echo [PERINGATAN] Proses ini akan mereset tabel database calibration.db
echo dan mengisinya kembali dengan data standar kalibrasi, order, dan customer.
echo.
set /p CONFIRM="Lanjutkan reset database? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Dibatalkan oleh pengguna.
    pause
    exit /b 0
)

echo.
echo Menjalankan seed.py ...
"%PYTHON_CMD%" seed.py

if !errorlevel! equ 0 (
    echo.
    echo [SUKSES] Database berhasil di-seed ulang dengan data baru.
) else (
    echo.
    echo [ERROR] Terjadi kegagalan saat menjalankan seed.py.
)

echo.
pause
