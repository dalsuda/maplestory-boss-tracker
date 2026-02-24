@echo off
REM ============================================================
REM BossTracker 실행용 BAT 파일 (PyQt5 GUI, 가상환경 자동 활성화)
REM ============================================================

REM --- 1. BAT 파일이 있는 폴더로 이동 ---
cd /d "%~dp0"

REM --- 2. 가상환경 활성화 ---
call venv\Scripts\activate.bat

REM --- 3. pythonw.exe로 GUI 실행 (콘솔 없이) ---
"%VIRTUAL_ENV%\Scripts\python.exe" main.py

REM --- 4. 종료 ---
pause
exit
