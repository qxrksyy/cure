@echo off
echo Starting Hybrid Discord Bot Setup...
echo.

:: Lavalink runs on Raspberry Pi, not locally
echo Lavalink server is running on Raspberry Pi at 10.0.0.75:2333
echo Skipping local Lavalink startup...
echo.

:: Start the JavaScript bot in a new window
echo Starting JavaScript bot...
start "JavaScript Bot" cmd /k "npm start"

:: Wait a moment for the JavaScript bot to initialize
timeout /t 5 /nobreak

:: Start the Python bot in the current window
echo Starting Python bot...
python bot.py

:: If the Python bot exits, keep the window open
pause 