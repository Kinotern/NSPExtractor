@echo off
setlocal
cd /d "%~dp0"

if not exist "tools\hactool.exe" (
    echo [SETUP] Tools not found. Running setup...
    python "%~dp0setup.py"
    if errorlevel 1 (
        echo.
        echo Setup failed. Please check the error messages above.
        pause
        exit /b 1
    )
    echo.
)

if "%~1"=="" (
    python "%~dp0nsp_toolkit.py" --gui
) else (
    python "%~dp0nsp_toolkit.py" %*
)

set EXIT_CODE=%ERRORLEVEL%
if not "%EXIT_CODE%"=="0" (
    echo.
    echo Extraction finished with errors. Check the logs folder for details.
)
endlocal & exit /b %EXIT_CODE%
