@echo off
echo Iniciando repositorio y preparando archivos...

:: Inicializa git en la carpeta
git init

:: Agrega TODOS los archivos descargados al bloque de confirmación
git add .

:: Crea el primer commit (confirmación) con todos los archivos
git commit -m "Initial commit - Nel Audio Capture"

:: Renombra la rama principal a 'main'
git branch -M main

:: Vincula tu carpeta local con el repositorio remoto de GitHub
git remote add origin https://github.com/dedalo-integraciones/nel.audio.capture.git

:: Sube los archivos a GitHub (forzando la subida para evitar conflictos iniciales)
echo.
echo Subiendo archivos a GitHub...
git push -u origin main --force

echo.
echo Proceso terminado. Revisa tu repositorio en GitHub.
pause