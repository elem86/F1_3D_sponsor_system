@echo off
rem Build the F1 3D Sponsor System as a Windows onedir executable using
rem PyInstaller and the versioned F1SponsorSystem.spec file.
rem
rem Usage:
rem   build_exe.bat            (normal windowed release build)
rem   build_exe.bat debug      (console-enabled debug build, same .exe name)
rem
rem Run this from an activated virtualenv that has requirements-build.txt
rem installed (pip install -r requirements-build.txt).

cd /d "%~dp0"

set F1SPONSOR_DEBUG_CONSOLE=0
if /i "%~1"=="debug" set F1SPONSOR_DEBUG_CONSOLE=1

if "%F1SPONSOR_DEBUG_CONSOLE%"=="1" echo Building DEBUG variant with console enabled...
if "%F1SPONSOR_DEBUG_CONSOLE%"=="0" echo Building release variant windowed no console...

where pyinstaller >nul 2>nul
if errorlevel 1 goto :no_pyinstaller

echo Cleaning previous build output...
if exist "build" rmdir /s /q "build"
if exist "dist\F1SponsorSystem" rmdir /s /q "dist\F1SponsorSystem"

echo Running PyInstaller...
pyinstaller F1SponsorSystem.spec --noconfirm
if errorlevel 1 goto :build_failed

if not exist "dist\F1SponsorSystem\F1SponsorSystem.exe" goto :exe_missing

echo.
echo Build succeeded.
echo Executable: %cd%\dist\F1SponsorSystem\F1SponsorSystem.exe
echo.
exit /b 0

:no_pyinstaller
echo [ERROR] pyinstaller was not found on PATH.
echo Install build dependencies first: pip install -r requirements-build.txt
exit /b 1

:build_failed
echo [ERROR] PyInstaller build failed. See output above.
exit /b 1

:exe_missing
echo [ERROR] Expected output executable was not created:
echo     dist\F1SponsorSystem\F1SponsorSystem.exe
exit /b 1
