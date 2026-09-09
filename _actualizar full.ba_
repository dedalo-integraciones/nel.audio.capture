@echo off
echo =======================================================
echo Iniciando proceso de actualizacion en GitHub (Limpieza total)...
echo =======================================================

echo.
echo 1. Preparando la nueva base sin historial...
:: Crea una rama huérfana (sin historial anterior)
git checkout --orphan temp_branch

echo.
echo 2. Añadiendo tus archivos modificados localmente...
:: Agrega el estado actual de los archivos
git add -A

echo.
echo 3. Guardando los cambios (Commit)...
:: Limpiamos la variable por si el sistema recordaba un valor anterior
set "mensaje="
set /p mensaje="Escribe de que se trata este cambio (o presiona Enter para usar texto por defecto): "

:: Si no se escribió nada, asignamos el mensaje por defecto de forma segura
if not defined mensaje set "mensaje=Reinicio de repositorio con el nuevo proyecto completo"

:: Ahora lo enviamos usando comillas solo aquí
git commit -m "%mensaje%"

echo.
echo 4. Reemplazando la rama principal...
:: Borramos la antigua rama main local
git branch -D main
:: Renombramos la rama temporal a main
git branch -m main

echo.
echo 5. Subiendo los archivos a GitHub de forma forzada...
:: El flag --force / -f hace que los cambios locales sobrescriban GitHub por completo
git push -f origin main

echo.
echo =======================================================
echo Proceso terminado. Revisa tu repositorio en GitHub.
echo =======================================================
pause