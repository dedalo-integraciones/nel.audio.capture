@echo off
echo =======================================================
echo Iniciando proceso de actualizacion en GitHub...
echo =======================================================

echo.
echo 1. Preparando tus archivos modificados localmente...
git add .

echo.
echo 2. Guardando los cambios (Commit)...
:: Limpiamos la variable por si el sistema recordaba un valor anterior
set "mensaje="
set /p mensaje="Escribe de que se trata este cambio (o presiona Enter para usar texto por defecto): "

:: Si no se escribió nada, asignamos el mensaje por defecto de forma segura
if not defined mensaje set "mensaje=Actualizador Universal"

:: Ahora lo enviamos usando comillas solo aquí
git commit -m "%mensaje%"

echo.
echo 3. Subiendo los archivos a GitHub de forma forzada...
:: El flag --force hace que los cambios locales sobrescriban GitHub
:: sin preguntar ni generar conflictos en la consola.
git push origin main --force

echo.
echo =======================================================
echo Proceso terminado. Revisa tu repositorio en GitHub.
echo =======================================================
pause