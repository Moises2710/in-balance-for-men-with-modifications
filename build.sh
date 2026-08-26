#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Instalando dependencias..."
pip install -r requirements.txt

echo "Creando directorios necesarios..."
mkdir -p media
mkdir -p staticfiles
mkdir -p logs

echo "Limpiando cache de miniaturas antiguas..."
rm -rf media/CACHE || true

echo "Recopilando archivos estáticos..."
python manage.py collectstatic --no-input --verbosity=2

echo "Verificando archivos estáticos..."
ls -la staticfiles/

echo "Ejecutando migraciones restantes..."
python manage.py makemigrations
python manage.py migrate

echo "Cargando datos iniciales..."
python manage.py cargar_datos_iniciales

echo "Configurando permisos del sistema..."
python manage.py configurar_permisos

echo "Build completado exitosamente!" 