#!/usr/bin/env python3
"""
Script para verificar la configuración de la base de datos en Render
"""

import os
import sys

def check_database_config():
    """Verificar la configuración de la base de datos"""
    print("🔍 Verificando configuración de base de datos...")
    
    # Verificar variables de entorno
    debug = os.environ.get('DEBUG', 'False') == 'True'
    database_url = os.environ.get('DATABASE_URL')
    
    print(f"DEBUG: {debug}")
    print(f"DATABASE_URL: {'Configurada' if database_url else 'No configurada'}")
    
    if database_url:
        print(f"URL de base de datos: {database_url[:50]}...")
    
    # Verificar si estamos en producción
    if not debug:
        print("🌐 Modo: PRODUCCIÓN")
        if not database_url:
            print("❌ ERROR: DATABASE_URL no está configurada en producción")
            print("💡 Solución: Configura la variable DATABASE_URL en Render")
            return False
        else:
            print("✅ DATABASE_URL configurada correctamente")
            return True
    else:
        print("💻 Modo: DESARROLLO")
        print("✅ Usando SQLite para desarrollo")
        return True

def check_dependencies():
    """Verificar dependencias necesarias"""
    print("\n📦 Verificando dependencias...")
    
    try:
        import django
        print(f"✅ Django {django.get_version()}")
    except ImportError:
        print("❌ Django no está instalado")
        return False
    
    try:
        import dj_database_url
        print("✅ dj-database-url instalado")
    except ImportError:
        print("❌ dj-database-url no está instalado")
        return False
    
    try:
        import psycopg2
        print("✅ psycopg2 instalado")
    except ImportError:
        print("❌ psycopg2 no está instalado")
        return False
    
    return True

def main():
    """Función principal"""
    print("🚀 Verificación de Configuración para Render")
    print("=" * 50)
    
    # Verificar dependencias
    deps_ok = check_dependencies()
    
    # Verificar configuración de base de datos
    db_ok = check_database_config()
    
    print("\n" + "=" * 50)
    if deps_ok and db_ok:
        print("✅ Configuración correcta")
        print("🎉 Tu aplicación está lista para desplegarse")
    else:
        print("❌ Hay problemas en la configuración")
        print("🔧 Revisa los errores anteriores")
        sys.exit(1)

if __name__ == "__main__":
    main() 