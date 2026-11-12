@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>nul || (echo Docker CLI not found.& exit /b 1)
docker compose down
exit /b %ERRORLEVEL%
