@echo off
echo ========================================================
echo   Iniciando Mar-ia (Microservicio IA para SICGOV)
echo ========================================================
echo.
echo Buscando ejecutable de uvicorn en entornos virtuales...

set UVICORN_PATH=
if exist "venv312\Scripts\uvicorn.exe" (
    echo [+] Entorno venv312 encontrado.
    set UVICORN_PATH=venv312\Scripts\uvicorn.exe
) else if exist "venv\Scripts\uvicorn.exe" (
    echo [+] Entorno venv encontrado.
    set UVICORN_PATH=venv\Scripts\uvicorn.exe
) else (
    echo [ERROR] No se encontro uvicorn en los entornos virtuales. 
    echo Por favor instala las dependencias: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo [+] Iniciando el servidor FastAPI en el puerto 8090...
echo.
"%UVICORN_PATH%" main:app --host 0.0.0.0 --port 8090 --reload
pause
