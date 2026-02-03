@echo off
chcp 65001 > NUL
setlocal enabledelayedexpansion

echo ====================================
echo YMM4 Plugin Build Setup
echo ====================================
echo.

if exist "Directory.Build.props" (
    echo [INFO] Directory.Build.props already exists.
    echo.
    type Directory.Build.props
    echo.
    choice /C YN /M "Overwrite existing file?"
    if errorlevel 2 goto :END
)

echo.
echo Please enter your YMM4 installation directory.
echo Example: C:\Users\YourName\AppData\Local\YukkuriMovieMaker4\
echo Note: Path must end with backslash (\)
echo.
set /p YMM4_PATH="YMM4 Directory Path: "

if not defined YMM4_PATH (
    echo [ERROR] Path is empty. Aborted.
    goto :END
)

if not exist "%YMM4_PATH%YukkuriMovieMaker.Plugin.dll" (
    echo [WARNING] YukkuriMovieMaker.Plugin.dll not found in specified directory.
    echo [WARNING] Build may fail if YMM4 is not installed at this path.
    echo.
    choice /C YN /M "Continue anyway?"
    if errorlevel 2 goto :END
)

echo ^<Project^> > Directory.Build.props
echo   ^<PropertyGroup^> >> Directory.Build.props
echo     ^<YMM4DirPath^>%YMM4_PATH%^</YMM4DirPath^> >> Directory.Build.props
echo   ^</PropertyGroup^> >> Directory.Build.props
echo ^</Project^> >> Directory.Build.props

echo.
echo [SUCCESS] Directory.Build.props created successfully!
echo.
type Directory.Build.props
echo.

:END
echo.
pause
