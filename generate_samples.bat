@echo off
REM Generate sample videos with virtual environment
echo ========================================
echo Sample Video Generation with Virtual Env
echo ========================================

cd /d "%~dp0"

echo [1/1] Activating virtual environment and generating videos...
call venv\Scripts\activate.bat

echo.
echo ========================================
echo Generating Sample 1: Python Programming
echo ========================================
python run_modular_demo.py --topic "Python Programming" --thumbnail
if errorlevel 1 (
    echo ERROR: Failed to generate Sample 1
    pause
    exit /b 1
)

echo.
echo ========================================
echo Generating Sample 2: Machine Learning
echo ========================================
python run_modular_demo.py --topic "Machine Learning" --quality 1080p --thumbnail --thumbnail-style modern
if errorlevel 1 (
    echo ERROR: Failed to generate Sample 2
    pause
    exit /b 1
)

echo.
echo ========================================
echo Generating Sample 3: Data Science
echo ========================================
python run_modular_demo.py --topic "Data Science" --quality 1080p --thumbnail --thumbnail-style educational
if errorlevel 1 (
    echo ERROR: Failed to generate Sample 3
    pause
    exit /b 1
)

echo.
echo ========================================
echo All sample videos generated successfully!
echo ========================================
echo.
echo Check the following directories for generated files:
echo data\videos\     - Video files (.mp4)
echo data\thumbnails\ - Thumbnail images (.png)
echo data\audio\      - Audio files (.mp3)
echo data\transcripts\ - Transcript files (.json)
echo.
pause
