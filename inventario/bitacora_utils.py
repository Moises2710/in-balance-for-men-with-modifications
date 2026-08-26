"""
Utilidades para el registro de acciones en la bitácora del sistema
"""
import logging
from datetime import datetime
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger('bitacora')

def registrar_accion(usuario, tipo_accion, entidad, entidad_id=None, descripcion=""):
    """
    Registra una acción en la bitácora del sistema
    
    Args:
        usuario: Usuario que realizó la acción (User instance o username string)
        tipo_accion: Tipo de acción (crear, editar, eliminar, activar, etc.)
        entidad: Entidad afectada (usuario, cliente, producto, venta, etc.)
        entidad_id: ID de la entidad afectada (opcional)
        descripcion: Descripción detallada de la acción
    """
    try:
        # Normalizar usuario
        if isinstance(usuario, str):
            usuario_nombre = usuario
        elif hasattr(usuario, 'username'):
            usuario_nombre = usuario.username
        else:
            usuario_nombre = 'Sistema'
        
        # Normalizar entidad_id
        if entidad_id is None:
            entidad_id_str = 'N/A'
        else:
            entidad_id_str = str(entidad_id)
        
        # Crear mensaje estructurado
        extra_data = {
            'usuario': usuario_nombre,
            'tipo_accion': tipo_accion,
            'entidad': entidad,
            'entidad_id': entidad_id_str,
            'descripcion': descripcion
        }
        
        logger.info(f"Acción registrada", extra=extra_data)
        
    except Exception as e:
        # Fallback logging si hay error
        logger.error(f"Error al registrar acción: {str(e)}")

def registrar_creacion(usuario, entidad, entidad_id, descripcion=""):
    """Helper para registrar creación de entidades"""
    registrar_accion(usuario, 'crear', entidad, entidad_id, descripcion)

def registrar_edicion(usuario, entidad, entidad_id, descripcion=""):
    """Helper para registrar edición de entidades"""
    registrar_accion(usuario, 'editar', entidad, entidad_id, descripcion)

def registrar_eliminacion(usuario, entidad, entidad_id, descripcion=""):
    """Helper para registrar eliminación de entidades"""
    registrar_accion(usuario, 'eliminar', entidad, entidad_id, descripcion)

def registrar_cambio_estado(usuario, entidad, entidad_id, nuevo_estado, descripcion=""):
    """Helper para registrar cambios de estado"""
    desc = f"{descripcion} - Nuevo estado: {nuevo_estado}" if descripcion else f"Estado cambiado a: {nuevo_estado}"
    registrar_accion(usuario, 'editar', entidad, entidad_id, desc)

def registrar_acceso(usuario, tipo_acceso, descripcion=""):
    """Helper para registrar accesos (login/logout)"""
    registrar_accion(usuario, tipo_acceso, 'sistema', None, descripcion)

def registrar_cambio_password(usuario, descripcion=""):
    """Helper para registrar cambios de contraseña"""
    registrar_accion(usuario, 'cambiar_password', 'usuario', usuario.id if hasattr(usuario, 'id') else None, descripcion)

