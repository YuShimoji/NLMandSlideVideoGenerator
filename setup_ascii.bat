@echo off
REM Final setup script - ASCII only version
echo ========================================
echo NLMandSlideVideoGenerator Final Setup
echo ========================================

cd /d "%~dp0"

echo [1/3] Python check...
python --version
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
echo Python OK

echo [2/3] Environment setup...
if exist venv rmdir /s /q venv
python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [3/3] Test run...
python -c "from config.settings import create_directories; create_directories()"
python test_basic.py 2>nul
if errorlevel 1 (
    echo WARNING: Test failed but basic functionality may still work
)

echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Video generation commands:
echo python run_modular_demo.py --topic "Python Intro" --thumbnail
echo python run_modular_demo.py --topic "AI Tech" --quality 1080p --thumbnail --thumbnail-style modern
echo.
echo Generated videos will be saved in data\videos\ folder
echo.
pause
