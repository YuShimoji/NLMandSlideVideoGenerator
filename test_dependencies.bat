@echo off
REM Test dependencies in virtual environment
echo ========================================
echo Testing Dependencies in Virtual Environment
echo ========================================

cd /d "%~dp0"

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Testing individual modules...
python -c "import requests; print('requests: OK')"
python -c "import moviepy; print('moviepy: OK')"
python -c "from PIL import Image; print('PIL: OK')"
python -c "import pysrt; print('pysrt: OK')"
python -c "from dotenv import load_dotenv; print('python-dotenv: OK')"
python -c "import loguru; print('loguru: OK')"
python -c "import google.generativeai as genai; print('google-generativeai: OK')"

echo.
echo ========================================
echo If all modules show 'OK', dependencies are working
echo ========================================
echo.
pause
