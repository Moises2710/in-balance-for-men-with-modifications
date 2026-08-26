#!/usr/bin/env python
"""
Script independiente para configurar permisos en PostgreSQL/Supabase
Funciona sin Django - solo con conexión directa a PostgreSQL
Ejecutar con: python configurar_permisos_postgresql.py
"""
import psycopg2
import os
from urllib.parse import urlparse


def configurar_permisos_postgresql():
    print("🔧 Configurando permisos del sistema en PostgreSQL/Supabase...")
    
    # Obtener URL de la base de datos desde variables de entorno
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ No se encontró DATABASE_URL en las variables de entorno")
        print("💡 Asegúrate de tener configurada la variable DATABASE_URL")
        return
    
    try:
        # Conectar a PostgreSQL
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("✅ Conectado a la base de datos PostgreSQL")
        
        # Crear grupos si no existen
        admin_group_id = crear_o_obtener_grupo(cursor, 'Administrador')
        vendedor_group_id = crear_o_obtener_grupo(cursor, 'Vendedor')
        
        # Limpiar permisos existentes
        limpiar_permisos(cursor, admin_group_id, vendedor_group_id)
        
        # Obtener todos los permisos de inventario
        permisos_inventario = obtener_permisos_inventario(cursor)
        
        # Configurar Administrador - TODOS los permisos
        configurar_administrador(cursor, admin_group_id, permisos_inventario)
        
        # Configurar Vendedor - Solo view y add
        configurar_vendedor(cursor, vendedor_group_id)
        
        # Confirmar cambios
        conn.commit()
        print("\n🎉 ¡Permisos configurados exitosamente!")
        
        # Mostrar resumen
        mostrar_resumen(cursor, admin_group_id, vendedor_group_id)
        
    except psycopg2.Error as e:
        print(f"❌ Error de base de datos: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def crear_o_obtener_grupo(cursor, nombre_grupo):
    """Crea un grupo si no existe o lo obtiene si ya existe"""
    cursor.execute("SELECT id FROM auth_group WHERE name = %s", (nombre_grupo,))
    grupo = cursor.fetchone()
    
    if not grupo:
        cursor.execute("INSERT INTO auth_group (name) VALUES (%s) RETURNING id", (nombre_grupo,))
        grupo_id = cursor.fetchone()[0]
        print(f"✅ Grupo {nombre_grupo} creado")
    else:
        grupo_id = grupo[0]
        print(f"✅ Grupo {nombre_grupo} ya existe")
    
    return grupo_id


def limpiar_permisos(cursor, admin_group_id, vendedor_group_id):
    """Limpia los permisos existentes de los grupos"""
    print("\n🧹 Limpiando permisos existentes...")
    cursor.execute("DELETE FROM auth_group_permissions WHERE group_id IN (%s, %s)", 
                  (admin_group_id, vendedor_group_id))


def obtener_permisos_inventario(cursor):
    """Obtiene todos los permisos de la app inventario"""
    print("\n📋 Obteniendo permisos de inventario...")
    cursor.execute("""
        SELECT p.id, p.codename, ct.model 
        FROM auth_permission p
        JOIN django_content_type ct ON p.content_type_id = ct.id
        WHERE ct.app_label = 'inventario'
    """)
    permisos = cursor.fetchall()
    print(f"✅ Encontrados {len(permisos)} permisos de inventario")
    return permisos


def configurar_administrador(cursor, admin_group_id, permisos_inventario):
    """Configura permisos para Administrador - TODOS los permisos"""
    print("\n👑 Configurando Administrador...")
    
    for permiso_id, codename, model in permisos_inventario:
        cursor.execute("""
            INSERT INTO auth_group_permissions (group_id, permission_id)
            VALUES (%s, %s)
            ON CONFLICT (group_id, permission_id) DO NOTHING
        """, (admin_group_id, permiso_id))
    
    print(f"✅ {len(permisos_inventario)} permisos asignados a Administrador")


def configurar_vendedor(cursor, vendedor_group_id):
    """Configura permisos para Vendedor - Solo view y add"""
    print("\n👤 Configurando Vendedor...")
    
    # Modelos que el vendedor puede manejar
    modelos_vendedor = [
        'producto', 'cliente', 'venta', 'detalleventa', 
        'pago', 'devolucion', 'detalledevolucion', 'metodopago'
    ]
    
    # Tipos de permisos: solo view y add
    tipos_permisos = ['view', 'add']
    
    permisos_vendedor = 0
    
    for modelo in modelos_vendedor:
        permisos_modelo = []
        
        for tipo_permiso in tipos_permisos:
            codename = f'{tipo_permiso}_{modelo}'
            
            # Buscar el permiso
            cursor.execute("""
                SELECT p.id
                FROM auth_permission p
                JOIN django_content_type ct ON p.content_type_id = ct.id
                WHERE ct.app_label = 'inventario' 
                AND ct.model = %s
                AND p.codename = %s
            """, (modelo, codename))
            
            permiso = cursor.fetchone()
            if permiso:
                permisos_modelo.append(permiso[0])
        
        # Asignar permisos encontrados
        if permisos_modelo:
            for permiso_id in permisos_modelo:
                cursor.execute("""
                    INSERT INTO auth_group_permissions (group_id, permission_id)
                    VALUES (%s, %s)
                    ON CONFLICT (group_id, permission_id) DO NOTHING
                """, (vendedor_group_id, permiso_id))
                permisos_vendedor += 1
            
            permisos_str = ', '.join(tipos_permisos)
            print(f"   ✅ {modelo}: {permisos_str}")
        else:
            print(f"   ❌ {modelo}: no encontrado")
    
    print(f"✅ {permisos_vendedor} permisos asignados a Vendedor")


def mostrar_resumen(cursor, admin_group_id, vendedor_group_id):
    """Muestra un resumen de los permisos configurados"""
    print("\n📊 Resumen de permisos:")
    
    # Permisos del Administrador
    cursor.execute("SELECT COUNT(*) FROM auth_group_permissions WHERE group_id = %s", (admin_group_id,))
    admin_count = cursor.fetchone()[0]
    print(f"👑 Administrador: {admin_count} permisos")
    
    # Permisos del Vendedor
    cursor.execute("SELECT COUNT(*) FROM auth_group_permissions WHERE group_id = %s", (vendedor_group_id,))
    vendedor_count = cursor.fetchone()[0]
    print(f"👤 Vendedor: {vendedor_count} permisos")
    
    # Mostrar algunos permisos del vendedor como ejemplo
    print("\n📋 Ejemplo de permisos del Vendedor:")
    cursor.execute("""
        SELECT p.codename, ct.model
        FROM auth_group_permissions gp
        JOIN auth_permission p ON gp.permission_id = p.id
        JOIN django_content_type ct ON p.content_type_id = ct.id
        WHERE gp.group_id = %s
        ORDER BY ct.model, p.codename
        LIMIT 10
    """, (vendedor_group_id,))
    
    permisos_ejemplo = cursor.fetchall()
    for codename, model in permisos_ejemplo:
        print(f"   - {model}: {codename}")


if __name__ == '__main__':
    configurar_permisos_postgresql()
