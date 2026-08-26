"""
Signals para capturar automáticamente las acciones de usuarios en el sistema
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.auth import get_user_model
from .models import Cliente, Producto, Venta, DetalleVenta, Pago, Devolucion, GastoAdministrativo
from .bitacora_utils import (
    registrar_creacion, registrar_edicion, registrar_eliminacion,
    registrar_cambio_estado, registrar_acceso, registrar_cambio_password
)
from .middleware import get_current_user

User = get_user_model()

# ==================== USUARIOS ====================
@receiver(post_save, sender=User)
def usuario_creado_editado(sender, instance, created, **kwargs):
    """Registra creación o edición de usuarios"""
    # Obtener el usuario actual desde el middleware
    current_user = get_current_user()
    usuario_nombre = current_user.username if current_user and current_user.is_authenticated else 'Sistema'
    
    if created:
        registrar_creacion(
            usuario=usuario_nombre,
            entidad='usuario',
            entidad_id=instance.id,
            descripcion=f"Usuario creado: {instance.username} - {instance.email}"
        )
    else:
        registrar_edicion(
            usuario=usuario_nombre,
            entidad='usuario',
            entidad_id=instance.id,
            descripcion=f"Usuario editado: {instance.username}"
        )

@receiver(user_logged_in)
def usuario_login(sender, request, user, **kwargs):
    """Registra inicio de sesión"""
    registrar_acceso(
        usuario=user,
        tipo_acceso='login',
        descripcion=f"Usuario {user.username} inició sesión"
    )

@receiver(user_logged_out)
def usuario_logout(sender, request, user, **kwargs):
    """Registra cierre de sesión"""
    registrar_acceso(
        usuario=user,
        tipo_acceso='logout',
        descripcion=f"Usuario {user.username} cerró sesión"
    )

# ==================== CLIENTES ====================
@receiver(post_save, sender=Cliente)
def cliente_creado_editado(sender, instance, created, **kwargs):
    """Registra creación o edición de clientes"""
    # Obtener el usuario actual desde el middleware
    current_user = get_current_user()
    usuario_nombre = current_user.username if current_user and current_user.is_authenticated else 'Sistema'
    
    if created:
        registrar_creacion(
            usuario=usuario_nombre,
            entidad='cliente',
            entidad_id=instance.id,
            descripcion=f"Cliente creado: {instance.nombre} {instance.apellido}"
        )
    else:
        # Ignorar si está marcado para saltar el signal de edición
        if hasattr(instance, '_skip_edit_signal') and instance._skip_edit_signal:
            return
            
        registrar_edicion(
            usuario=usuario_nombre,
            entidad='cliente',
            entidad_id=instance.id,
            descripcion=f"Cliente editado: {instance.nombre} {instance.apellido}"
        )

@receiver(post_delete, sender=Cliente)
def cliente_eliminado(sender, instance, **kwargs):
    """Registra eliminación de clientes"""
    # Obtener el usuario actual desde el middleware
    current_user = get_current_user()
    usuario_nombre = current_user.username if current_user and current_user.is_authenticated else 'Sistema'
    
    registrar_eliminacion(
        usuario=usuario_nombre,
        entidad='cliente',
        entidad_id=instance.id,
        descripcion=f"Cliente eliminado: {instance.nombre} {instance.apellido}"
    )

# ==================== PRODUCTOS ====================
@receiver(post_save, sender=Producto)
def producto_creado_editado(sender, instance, created, **kwargs):
    """Registra creación o edición de productos"""
    # Obtener el usuario actual desde el middleware
    current_user = get_current_user()
    usuario_nombre = current_user.username if current_user and current_user.is_authenticated else 'Sistema'
    
    if created:
        registrar_creacion(
            usuario=usuario_nombre,
            entidad='producto',
            entidad_id=instance.id,
            descripcion=f"Producto creado: {instance.codigo}"
        )
    else:
        # Ignorar si está marcado para saltar el signal de edición
        if hasattr(instance, '_skip_edit_signal') and instance._skip_edit_signal:
            return
        
        # Ignorar si no hay usuario actual (puede ser regeneración automática de miniatura)
        if not current_user or not current_user.is_authenticated:
            return
        
        # Verificar si ya se registró esta edición en la misma transacción
        if hasattr(instance, '_edit_registered') and instance._edit_registered:
            return
            
        # Marcar como registrado para evitar duplicados
        instance._edit_registered = True
            
        registrar_edicion(
            usuario=usuario_nombre,
            entidad='producto',
            entidad_id=instance.id,
            descripcion=f"Producto editado: {instance.codigo}"
        )

@receiver(post_delete, sender=Producto)
def producto_eliminado(sender, instance, **kwargs):
    """Registra eliminación de productos"""
    # Obtener el usuario actual desde el middleware
    current_user = get_current_user()
    usuario_nombre = current_user.username if current_user and current_user.is_authenticated else 'Sistema'
    
    registrar_eliminacion(
        usuario=usuario_nombre,
        entidad='producto',
        entidad_id=instance.id,
        descripcion=f"Producto eliminado: {instance.codigo}"
    )

# ==================== VENTAS ====================
@receiver(post_save, sender=Venta)
def venta_creada_editada(sender, instance, created, **kwargs):
    """Registra creación o edición de ventas"""
    if created:
        registrar_creacion(
            usuario=instance.user,
            entidad='venta',
            entidad_id=instance.id,
            descripcion=f"Venta creada - Cliente: {instance.cliente.nombre} {instance.cliente.apellido} - Total: ${instance.total}"
        )
    else:
        registrar_edicion(
            usuario=instance.user,
            entidad='venta',
            entidad_id=instance.id,
            descripcion=f"Venta editada - ID: {instance.id}"
        )

@receiver(post_delete, sender=Venta)
def venta_eliminada(sender, instance, **kwargs):
    """Registra eliminación de ventas"""
    registrar_eliminacion(
        usuario=instance.user,
        entidad='venta',
        entidad_id=instance.id,
        descripcion=f"Venta eliminada - Cliente: {instance.cliente.nombre} {instance.cliente.apellido}"
    )

# ==================== PAGOS ====================
@receiver(post_save, sender=Pago)
def pago_creado_editado(sender, instance, created, **kwargs):
    """Registra creación o edición de pagos"""
    # Obtener el usuario actual desde el middleware
    current_user = get_current_user()
    usuario_nombre = current_user.username if current_user and current_user.is_authenticated else 'Sistema'
    if created:
        registrar_creacion(
            usuario=usuario_nombre,
            entidad='pago',
            entidad_id=instance.id,
            descripcion=f"Pago creado - Venta: {instance.venta.id} - Monto: ${instance.monto_usd}"
        )
    else:
        registrar_edicion(
            usuario=usuario_nombre,
            entidad='pago',
            entidad_id=instance.id,
            descripcion=f"Pago editado - ID: {instance.id}"
        )

@receiver(post_delete, sender=Pago)
def pago_eliminado(sender, instance, **kwargs):
    """Registra eliminación de pagos"""
    # Obtener el usuario actual desde el middleware
    current_user = get_current_user()
    usuario_nombre = current_user.username if current_user and current_user.is_authenticated else 'Sistema'
    registrar_eliminacion(
        usuario=usuario_nombre,
        entidad='pago',
        entidad_id=instance.id,
        descripcion=f"Pago eliminado - Venta: {instance.venta.id}"
    )

# ==================== DEVOLUCIONES ====================
@receiver(post_save, sender=Devolucion)
def devolucion_creada_editada(sender, instance, created, **kwargs):
    """Registra creación o edición de devoluciones"""
    # Obtener el usuario actual desde el middleware
    current_user = get_current_user()
    usuario_nombre = current_user.username if current_user and current_user.is_authenticated else 'Sistema'
    if created:
        registrar_creacion(
            usuario=usuario_nombre,
            entidad='devolucion',
            entidad_id=instance.id,
            descripcion=f"Devolución creada - ID: {instance.id}"
        )
    else:
        registrar_edicion(
            usuario=usuario_nombre,
            entidad='devolucion',
            entidad_id=instance.id,
            descripcion=f"Devolución editada - ID: {instance.id}"
        )

# ==================== GASTOS ADMINISTRATIVOS ====================
@receiver(post_save, sender=GastoAdministrativo)
def gasto_creado_editado(sender, instance, created, **kwargs):
    """Registra creación o edición de gastos administrativos"""
    # Obtener el usuario actual desde el middleware
    current_user = get_current_user()
    usuario_nombre = current_user.username if current_user and current_user.is_authenticated else 'Sistema'
    if created:
        registrar_creacion(
            usuario=usuario_nombre,
            entidad='gasto_administrativo',
            entidad_id=instance.id,
            descripcion=f"Gasto administrativo creado: {instance.nombre} - Monto: ${instance.monto}"
        )
    else:
        registrar_edicion(
            usuario=usuario_nombre,
            entidad='gasto_administrativo',
            entidad_id=instance.id,
            descripcion=f"Gasto administrativo editado: {instance.nombre}"
        )

@receiver(post_delete, sender=GastoAdministrativo)
def gasto_eliminado(sender, instance, **kwargs):
    """Registra eliminación de gastos administrativos"""
    # Obtener el usuario actual desde el middleware
    current_user = get_current_user()
    usuario_nombre = current_user.username if current_user and current_user.is_authenticated else 'Sistema'
    registrar_eliminacion(
        usuario=usuario_nombre,
        entidad='gasto_administrativo',
        entidad_id=instance.id,
        descripcion=f"Gasto administrativo eliminado: {instance.nombre}"
    )

