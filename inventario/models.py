from django.db import models
from django.db.models import Sum
from django.db.models.functions import Lower
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator, FileExtensionValidator, ValidationError
from django.utils import timezone
from imagekit.models import ProcessedImageField, ImageSpecField
from django.conf import settings
from imagekit.processors import ResizeToFit, Transpose

import bleach
from django.utils.html import escape

# Configuración global de bleach
BLEACH_CONFIG = {
    'tags': [],  # No permitir ninguna etiqueta HTML
    'attributes': {},  # No permitir ningún atributo
    'strip': True,  # Eliminar etiquetas no permitidas
    'strip_comments': True  # Eliminar comentarios HTML
}

def sanitize_text_smart(text, allow_special_chars=False):
    """
    Args:
        text: Texto a sanitizar
        allow_special_chars: Si es True, permite caracteres especiales como ', &, /
    """
    if text is None:
        return None
    
    text = str(text)
    
    # Lista de patrones peligrosos que siempre se bloquean
    dangerous_patterns = [
        '<script', '</script>', 'javascript:', 'vbscript:', 'data:', 'onload=',
        'onerror=', 'onclick=', 'onmouseover=', 'eval(', 'alert(', 'confirm(',
        'prompt(', 'document.cookie', 'window.location', 'innerHTML',
        'outerHTML', 'insertAdjacentHTML', 'document.write'
    ]
    
    # Eliminar patrones peligrosos
    cleaned = text
    for pattern in dangerous_patterns:
        cleaned = cleaned.replace(pattern, '')
        cleaned = cleaned.replace(pattern.upper(), '')
        cleaned = cleaned.replace(pattern.title(), '')
    
    # Si no se permiten caracteres especiales, aplicar bleach
    if not allow_special_chars:
        cleaned = bleach.clean(
            cleaned,
            tags=[],  # No permitir ninguna etiqueta
            attributes={},  # No permitir ningún atributo
            strip=True,  # Eliminar etiquetas no permitidas
            strip_comments=True  # Eliminar comentarios HTML
        )
        # Escapar caracteres HTML
        cleaned = escape(cleaned)
    
    return cleaned

# Función centralizada para sanitización de texto (mantiene compatibilidad)
def sanitize_text(text):

    return sanitize_text_smart(text, allow_special_chars=False)
# Helpers para rutas de subida según entorno
def user_upload_to(instance, filename):
    """En dev mantiene la ruta actual, en prod usa carpeta 'usuarios/'"""
    if getattr(settings, 'DEBUG', True):
        return f'images/pefil/{filename}'
    user_id = getattr(instance, 'pk', None) or 'tmp'
    return f'usuarios/{user_id}/{filename}'


def product_upload_to(instance, filename):
    """En dev mantiene la ruta actual, en prod usa carpeta 'productos/'"""
    if getattr(settings, 'DEBUG', True):
        return f'images/productos/{filename}'
    code_or_id = getattr(instance, 'codigo', None) or getattr(instance, 'pk', None) or 'tmp'
    return f'productos/{code_or_id}/{filename}'


# validador de tamaño de imagenes
def validate_image_size(image):
    max_bytes = 12 * 1024 * 1024   # 12 MB, basta con cambiar el primero 
    if image.size > max_bytes:
        raise ValidationError(
            f"Tamaño máximo permitido: 12 MB. El archivo tiene {image.size / (1024*1024):.2f} MB."
        )

# verificar que sirva
def validate_image_content(image):
    try:
        from PIL import Image
        img = Image.open(image)
        img.verify()  # Verifica que sea una imagen válida
    except Exception as e:
        raise ValidationError("El archivo no es una imagen válida o está corrupto.") 

# Validador actualizado que permite caracteres especiales legítimos
name_validator = RegexValidator(
    regex=r'^[\w\sáéíóúÁÉÍÓÚñÑ\-.,;:¡!¿?()\'&/]+$',
    message="Solo se permiten letras, números, signos de puntuación básicos y caracteres especiales como ', &, /."
)

# Validador actualizado que permite caracteres especiales legítimos
name_validator = RegexValidator(
    regex=r'^[\w\sáéíóúÁÉÍÓÚñÑ\-.,;:¡!¿?()\'&/]+$',
    message="Solo se permiten letras, números, signos de puntuación básicos y caracteres especiales como ', &, /."
)


class CustomUser(AbstractUser):
    id = models.BigAutoField(primary_key=True)
    telefono = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r'^\+?\d{7,17}$', message="Ingrese un número de teléfono válido.")]
    )
    imagen = ProcessedImageField(
        upload_to=user_upload_to,
        processors=[
            Transpose(),
            #ResizeToFit(800, 800) # opcional: ajustar tamaño máximo
            ],
        format='WEBP', # convertir a WebP, para que cargar todo mas efecientemente
        options={'quality':  100}, # calidad de compresión
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png','heic', 'webp']), validate_image_size]  # sólo estas extensiones :contentReference[oaicite:1]{index=1}
    )
    # thumbnail (miniaturas) automático para las tables
    thumbnail = ImageSpecField(
        source='imagen',
        processors=[ResizeToFit(100, 100)], # tamaño thumbnail
        format='WEBP',
        options={'quality': 80}
    )
    USERNAME_FIELD = 'username'
    
    # Campos para sistema de suspensión progresiva
    failed_login_attempts = models.PositiveIntegerField(default=0, help_text="Número de intentos fallidos de login")
    locked_until = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora hasta cuando el usuario está bloqueado")
    last_failed_login = models.DateTimeField(null=True, blank=True, help_text="Último intento fallido de login")

    class Meta:
        permissions = [
            ("can_suspend_user", "Puede suspender usuarios"),
        ]

    def save(self, *args, **kwargs):
        if self.telefono:
            self.telefono = sanitize_text(self.telefono)
        super().save(*args, **kwargs)
        # Regenerar miniatura cuando exista imagen
        try:
            if self.imagen:
                # eliminar caché previo para evitar apuntar a /media/CACHE
                try:
                    if hasattr(self.thumbnail, 'delete'):
                        self.thumbnail.delete()
                except Exception:
                    pass
                # forzar generación de cache (ImageKit)
                _ = self.thumbnail.generate()
        except Exception:
            pass

    def __str__(self):
        return self.username
    
    def is_locked(self):
        """Verifica si el usuario está bloqueado por intentos fallidos"""
        if not self.locked_until:
            return False
        
        # Si el bloqueo ya expiró, limpiarlo automáticamente
        if timezone.now() >= self.locked_until:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.last_failed_login = None
            self.save(update_fields=['failed_login_attempts', 'locked_until', 'last_failed_login'])
            return False
        
        return True
    
    def get_lockout_duration(self):
        """Calcula la duración del bloqueo basado en el número de intentos fallidos"""
        durations = [
            5,      # 5 minutos para el primer bloqueo
            15,     # 15 minutos para el segundo
            30,     # 30 minutos para el tercero
            60,     # 1 hora para el cuarto
            120,    # 2 horas para el quinto
            240,    # 4 horas para el sexto
            480,    # 8 horas para el séptimo
            1440,   # 24 horas para el octavo y siguientes
        ]
        
        attempt_index = min(self.failed_login_attempts - 1, len(durations) - 1)
        return durations[attempt_index]
    
    def record_failed_login(self):
        """Registra un intento fallido de login y aplica bloqueo si es necesario"""
        from datetime import timedelta
        
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        
        # Si alcanza 3 o más intentos fallidos, aplicar bloqueo
        if self.failed_login_attempts >= 3:
            duration_minutes = self.get_lockout_duration()
            self.locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'locked_until'])
    
    def record_successful_login(self):
        """Registra un login exitoso y resetea los contadores"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_failed_login = None
        self.save(update_fields=['failed_login_attempts', 'locked_until', 'last_failed_login'])
    
    def unlock_user(self):
        """Desbloquea al usuario (usado por administradores)"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_failed_login = None
        self.save(update_fields=['failed_login_attempts', 'locked_until', 'last_failed_login'])
    
    def get_remaining_lockout_time(self):
        """Retorna el tiempo restante de bloqueo en minutos"""
        if not self.is_locked():
            return 0
        
        remaining = self.locked_until - timezone.now()
        return max(0, int(remaining.total_seconds() / 60))

    def get_image_url(self):
        """
        Obtiene la URL de la imagen con fallback a una imagen por defecto
        """
        if self.imagen and hasattr(self.imagen, 'url'):
            return self.imagen.url
        else:
            # Retornar URL de imagen por defecto
            return '/static/images/avatars/01.png'


class Categoria(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=30, unique=True, validators=[name_validator])
    
    def save(self, *args, **kwargs):
        self.nombre = sanitize_text(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Tipo(models.Model):
    id = models.BigAutoField(primary_key=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=30, unique=True, validators=[name_validator])
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.nombre = sanitize_text(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Marca(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True, validators=[name_validator])
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = sanitize_text_smart(self.nombre, allow_special_chars=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Fit(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=40, unique=True, validators=[name_validator])
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = sanitize_text_smart(self.nombre, allow_special_chars=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Color(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True, validators=[name_validator])
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.nombre = sanitize_text(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Talla(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=12, unique=True, validators=[name_validator])
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.nombre = sanitize_text(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    id = models.BigAutoField(primary_key=True)
    descripcion = models.CharField(max_length=30, null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(validators=[MaxValueValidator(10000)])
    is_active = models.BooleanField(default=True)

    codigo = models.CharField(
        max_length=20,
        unique=True, 
        # db_index=True            
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9\-_]+$',
                message="El código solo puede contener letras, números, guiones y guiones bajos."
            )
        ]
    )

    # Validación para que el código sea interpretado por la db como único sin importar mayúsculas/minúsculas
    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('codigo'),
                name='codigo_lower_unique',
            ),
        ]
    
    imagen = ProcessedImageField(
        upload_to=product_upload_to,
        processors=[
            Transpose(),
            #ResizeToFit(800, 800) # opcional: ajustar tamaño máximo
            ],
        format='JPEG', # convertir a WebP, para que cargar todo mas efecientemente
        options={'quality':  100}, # calidad de compresión
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png','heic', 'avif', 'webp']), validate_image_size]  # sólo estas extensiones :contentReference[oaicite:1]{index=1}
  # sólo estas extensiones :contentReference[oaicite:1]{index=1}
    )
    # thumbnail (miniaturas) automático para las tables
    thumbnail = ImageSpecField(
        source='imagen',
        processors=[ResizeToFit(100, 100)], # tamaño thumbnail
        format='WEBP',
        options={'quality': 80}
    )

    tipo = models.ForeignKey(Tipo, on_delete=models.SET_NULL, null=True, blank=True)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True)
    fit = models.ForeignKey(Fit, on_delete=models.SET_NULL, null=True, blank=True)
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    talla = models.ForeignKey(Talla, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Primero convertir a mayúsculas
        if self.codigo:
            self.codigo = self.codigo.upper()
        
        # Luego sanitizar (si es necesario)
        self.descripcion = sanitize_text(self.descripcion) if self.descripcion else None
        self.codigo = sanitize_text(self.codigo) if self.codigo else None
        
        super().save(*args, **kwargs)
        
        # Regenerar miniatura cuando exista imagen
        try:
            if self.imagen:
                # Marcar para evitar signal de edición durante regeneración de miniatura
                self._skip_edit_signal = True
                try:
                    if hasattr(self.thumbnail, 'delete'):
                        self.thumbnail.delete()
                except Exception:
                    pass
                _ = self.thumbnail.generate()
        except Exception:
            pass

    def __str__(self):
        return f"{self.codigo} {self.descripcion} - {self.tipo} - {self.marca} - {self.color}"

    def get_image_url(self):
        """
        Obtiene la URL de la imagen con fallback a una imagen por defecto
        """
        if self.imagen and hasattr(self.imagen, 'url'):
            return self.imagen.url
        else:
            # Retornar URL de imagen por defecto
            return '/static/images/no-image-available-icon-vector.jpg'


class Etiqueta(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=40, unique=True, validators=[name_validator])
    
    def save(self, *args, **kwargs):
        self.nombre = sanitize_text(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre
    
    
class Cliente(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100, validators=[name_validator])
    apellido = models.CharField(max_length=100, validators=[name_validator], blank=True, null=True)
    identificacion = models.IntegerField(unique=True)
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])  # Solo valores positivos para crédito
    deuda = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])  # Solo valores positivos para deuda
    status = models.BooleanField(default=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    
    telefono = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r'^\+?\d{7,17}$', message="Ingrese un número de teléfono válido.")]
    )
    

    
    tallas = models.ManyToManyField(Talla, through='TallaCliente', related_name='clientes')
    etiqueta = models.ManyToManyField(Etiqueta, related_name='etiquetas', blank=True)

    def save(self, *args, **kwargs):
        self.nombre = sanitize_text(self.nombre)
        if self.apellido:
            self.apellido = sanitize_text(self.apellido)
        if self.telefono:
            self.telefono = sanitize_text(self.telefono)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.apellido:
            return f"{self.nombre} {self.apellido}"
        return self.nombre

    def recalcular_deuda(self):
        """Recalcula la deuda a partir de todas las ventas activas (no canceladas) del cliente.
        Deuda = sumatorio por venta de max(0, total_ajustado - total_pagado).
        """
        from decimal import Decimal
        total_deuda = Decimal('0')
        # Obtener ventas del cliente que no están canceladas
        ventas_cliente = self.venta_set.filter(cancelada=False)
        for venta in ventas_cliente:
            total_pagado = venta.get_total_pagado()
            faltante = venta.total_ajustado - total_pagado
            if faltante > 0:
                total_deuda += faltante
        # Asegurar no negativo y con dos decimales según campo
        if total_deuda < 0:
            total_deuda = Decimal('0')
        self.deuda = total_deuda
        # Usar update() para evitar signals de edición
        Cliente.objects.filter(id=self.id).update(deuda=total_deuda)


class TallaCliente(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    talla = models.ForeignKey(Talla, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        if self.categoria:
            return f"{self.cliente} - {self.talla} ({self.categoria})"
        return f"{self.cliente} - {self.talla}"


class Venta(models.Model):
    id = models.BigAutoField(primary_key=True)
    fecha = models.DateTimeField(default=timezone.now)
    total = models.DecimalField(max_digits=12, decimal_places=6, validators=[MinValueValidator(0)])
    subtotal = models.DecimalField(max_digits=12, decimal_places=6, validators=[MinValueValidator(0)])
    total_ajustado = models.DecimalField(max_digits=12, decimal_places=6, validators=[MinValueValidator(0)])
    descuento = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    COMISION_ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('denegado', 'Denegado'),
    ]

    comision = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    estado_comision = models.CharField(max_length=10, choices=COMISION_ESTADOS, default='pendiente')
    entrega = models.BooleanField(default=False)
    pagado = models.BooleanField(default=False)
    cancelada = models.BooleanField(default=False, help_text="Indica si la venta fue devuelta en su totalidad")
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    productos = models.ManyToManyField(Producto, through='DetalleVenta', related_name='ventas')

    def clean(self):
        """Validaciones personalizadas para el modelo Venta"""
        super().clean()
        from decimal import Decimal
        
        # Validar que el descuento no sea mayor al subtotal
        if self.descuento and self.subtotal:
            if self.descuento > self.subtotal:
                raise ValidationError({
                    'descuento': 'El descuento no puede ser mayor al subtotal de la venta.'
                })
    
    def save(self, *args, **kwargs):
        # Calcular comisión fija del 10% del total
        from decimal import Decimal, ROUND_HALF_UP
        if self.total is not None:
            self.comision = (self.total * Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Si es una nueva venta (sin ID), establecer total_ajustado = total
        if not self.pk and self.total_ajustado is None:
            self.total_ajustado = self.total
        
        # Ejecutar validaciones antes de guardar
        self.full_clean()
        super().save(*args, **kwargs)

    def recalcular_total_ajustado(self):
        """Recalcula el total_ajustado basado en las devoluciones existentes"""
        from decimal import Decimal
        total_devoluciones = sum(
            devolucion.total for devolucion in self.devoluciones.all()
        )
        self.total_ajustado = self.total - total_devoluciones
        self.actualizar_estado()
        self.save(update_fields=['total_ajustado', 'pagado', 'cancelada'])

    def get_total_pagado(self):
        """Obtiene el total pagado de la venta"""
        return sum(pago.monto_usd for pago in self.pago_set.all())
    
    def get_total_devoluciones(self):
        """Obtiene el total de devoluciones de la venta"""
        return sum(devolucion.total for devolucion in self.devoluciones.all())
    
    def get_total_reembolsado(self):
        """Obtiene el total reembolsado de la venta"""
        return sum(devolucion.reembolsado for devolucion in self.devoluciones.all() if devolucion.reembolsado)

    def get_estado_pago(self):
        """
        Determina el estado de pago de la venta basado en total_ajustado
        Retorna: 'pagada', 'no_pagada', 'cancelada'
        """
        from decimal import Decimal
        total_pagado = self.get_total_pagado()
        total_devoluciones = sum(
            devolucion.total for devolucion in self.devoluciones.all()
        )
        
        # Si el total es igual a la suma de devoluciones, la venta está cancelada
        if self.total == total_devoluciones:
            return 'cancelada'
        
        # Si total_ajustado <= pagos, la venta está pagada
        if self.total_ajustado <= total_pagado:
            return 'pagada'
        
        # Si total_ajustado > pagos, la venta no está pagada
        return 'no_pagada'
    
    def actualizar_estado(self):
        """Actualiza los campos pagado y cancelada basado en la lógica de estado"""
        estado = self.get_estado_pago()
        
        if estado == 'cancelada':
            self.cancelada = True
            self.pagado = False
        elif estado == 'pagada':
            self.cancelada = False
            self.pagado = True
        else:  # no_pagada
            self.cancelada = False
            self.pagado = False

    def get_faltante_por_pagar(self):
        """Calcula el faltante por pagar basado en total_ajustado"""
        from decimal import Decimal
        total_pagado = self.get_total_pagado()
        return max(Decimal('0'), self.total_ajustado - total_pagado)

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha}"


class DetalleVenta(models.Model):
    id = models.BigAutoField(primary_key=True)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    precio_unitario_final = models.DecimalField(max_digits=12, decimal_places=6, validators=[MinValueValidator(0)], help_text="Precio unitario ajustado proporcionalmente después del descuento")
    cantidad = models.PositiveIntegerField()
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)

    def get_subtotal_original(self):
        """Calcula el subtotal original (precio_unitario * cantidad)"""
        return self.precio_unitario * self.cantidad

    def get_subtotal_final(self):
        """Calcula el subtotal final (precio_unitario_final * cantidad)"""
        return self.precio_unitario_final * self.cantidad

    def get_descuento_proporcional(self):
        """Calcula el descuento proporcional aplicado a este detalle"""
        return self.get_subtotal_original() - self.get_subtotal_final()

    def __str__(self):
        return f'venta #{self.venta.id} - producto #{self.producto.codigo} x {self.cantidad}'


class Devolucion(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='devoluciones')
    total = models.DecimalField(max_digits=12, decimal_places=6, validators=[MinValueValidator(0)], help_text="Total calculado automáticamente")
    reembolsado = models.DecimalField(max_digits=12, decimal_places=6, blank=True, null=True, help_text="Monto reembolsado al cliente")
    fecha = models.DateField(default=timezone.now)
    motivo = models.TextField(blank=True, null=True,validators=[
        RegexValidator(
            regex=r'^[\w\sáéíóúÁÉÍÓÚñÑ\-.,;:¡!¿?()\n]+$',
            message="El motivo contiene caracteres no permitidos."
        )])

    def clean(self):
        """Validaciones personalizadas para el modelo Devolucion"""
        super().clean()
        
        # Validar que el reembolso sea un valor positivo si se proporciona
        if self.reembolsado is not None and self.reembolsado < 0:
            raise ValidationError({
                'reembolsado': 'El monto reembolsado no puede ser negativo'
            })
        
        # Validar que el reembolso no sea mayor al total de la devolución
        # Solo validar si el total ya está calculado (no es 0)
        if self.reembolsado and self.total and self.total > 0:
            if self.reembolsado > self.total:
                raise ValidationError({
                    'reembolsado': f'El monto reembolsado (${self.reembolsado}) no puede ser mayor al total de la devolución (${self.total})'
                })
        
        # Validar que el reembolso no sea mayor a los pagos de la venta
        # Solo validar si hay pagos registrados en la venta
        if self.reembolsado and self.id_venta:
            total_pagado = self.id_venta.get_total_pagado()
            if total_pagado > 0 and self.reembolsado > total_pagado:
                raise ValidationError({
                    'reembolsado': f'El monto reembolsado (${self.reembolsado}) no puede ser mayor al total pagado de la venta (${total_pagado})'
                })

    def calcular_total(self):
        """Calcula el total de la devolución basado en los detalles"""
        from decimal import Decimal
        total = Decimal('0')
        for detalle in self.detalles.all():
            # Usar el precio_unitario_final del detalle de venta
            subtotal = detalle.id_detalle_venta.precio_unitario_final * detalle.cantidad_producto
            total += subtotal
        return total

    def save(self, *args, **kwargs):
        # Sanitizar motivo
        if self.motivo:
            self.motivo = sanitize_text(self.motivo)
        
        # Ejecutar validaciones antes de guardar
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Recalcular total_ajustado de la venta después de guardar la devolución
        self.id_venta.recalcular_total_ajustado()
        # Recalcular deuda del cliente después de afectar la venta
        if self.id_venta and self.id_venta.cliente:
            self.id_venta.cliente.recalcular_deuda()
    
    def save_simple(self, *args, **kwargs):
        """Método save simplificado que no ejecuta lógica adicional"""
        # Sanitizar motivo
        if self.motivo:
            self.motivo = sanitize_text(self.motivo)
        
        # Ejecutar validaciones antes de guardar
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        venta = self.id_venta
        super().delete(*args, **kwargs)
        # Recalcular total_ajustado de la venta después de eliminar la devolución
        venta.recalcular_total_ajustado()
        # Recalcular deuda del cliente después de revertir la devolución
        if venta and venta.cliente:
            venta.cliente.recalcular_deuda()

    def __str__(self):
        return f"Devolución #{self.id} - Venta #{self.id_venta.id} - {self.fecha}"


class DetalleDevolucion(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_detalle_venta = models.ForeignKey(DetalleVenta, on_delete=models.CASCADE, related_name='detalles_devolucion')
    id_devolucion = models.ForeignKey(Devolucion, on_delete=models.CASCADE, related_name='detalles')
    cantidad_producto = models.PositiveIntegerField()
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    danado = models.BooleanField(default=False, help_text="Indica si el producto va a merma")

    def clean(self):
        """Validaciones personalizadas para el modelo DetalleDevolucion"""
        super().clean()
        
        # Validar que no se devuelva más cantidad de la que se vendió
        if self.id_detalle_venta and self.cantidad_producto:
            cantidad_vendida = self.id_detalle_venta.cantidad
            
            # Calcular cantidad ya devuelta de este detalle de venta
            cantidad_ya_devuelta = DetalleDevolucion.objects.filter(
                id_detalle_venta=self.id_detalle_venta
            ).exclude(id=self.id).aggregate(
                total=Sum('cantidad_producto')
            )['total'] or 0
            
            cantidad_disponible = cantidad_vendida - cantidad_ya_devuelta
            
            if self.cantidad_producto > cantidad_disponible:
                raise ValidationError({
                    'cantidad_producto': f'No se puede devolver más de {cantidad_disponible} unidades. Cantidad vendida: {cantidad_vendida}, ya devuelta: {cantidad_ya_devuelta}'
                })

    def save(self, *args, **kwargs):
        # Ejecutar validaciones antes de guardar
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Actualizar stock o crear merma según el estado del producto
        if self.danado:
            # Crear merma para productos dañados
            Merma.objects.create(
                id_producto=self.id_detalle_venta.producto,
                cantidad=self.cantidad_producto,
                precio_compra=self.precio_compra,
                origen='devolucion',
                motivo=f'Producto devuelto dañado - Devolución #{self.id_devolucion.id}'
            )
        else:
            # Reponer stock
            producto = self.id_detalle_venta.producto
            producto.stock += self.cantidad_producto
            producto.save()

    def delete(self, *args, **kwargs):
        # Antes de eliminar, revertir los cambios en stock/merma
        if self.danado:
            # Eliminar merma correspondiente (se crea una merma por cada detalle)
            Merma.objects.filter(
                id_producto=self.id_detalle_venta.producto,
                origen='devolucion',
                cantidad=self.cantidad_producto,
                precio_compra=self.precio_compra
            ).delete()
        else:
            # Reducir stock
            producto = self.id_detalle_venta.producto
            producto.stock = max(0, producto.stock - self.cantidad_producto)
            producto.save()
        
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Detalle Devolución #{self.id} - {self.cantidad_producto} unidades"


class Merma(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='mermas')
    cantidad = models.PositiveIntegerField()
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    fecha = models.DateField(default=timezone.now)
    origen = models.CharField(max_length=100, default='tienda', choices=[
        ('tienda', 'tienda'),
        ('devolucion', 'Devolución'),
    ]) 
    motivo = models.TextField(blank=True, null=True, validators=[
        RegexValidator(
            regex=r'^[\w\sáéíóúÁÉÍÓÚñÑ\-.,;:¡!¿?()\n]*$',
            message="El motivo contiene caracteres no permitidos."
        )])

    def save(self, *args, **kwargs):
        if self.motivo:
            self.motivo = sanitize_text(self.motivo)
        super().save(*args, **kwargs)

    @property
    def total_costo(self):
        """Calcula el costo total de la merma"""
        return self.cantidad * self.precio_compra

    @property
    def margen_ganancia(self):
        """Calcula el margen de ganancia perdido por la merma"""
        return self.cantidad * (self.id_producto.precio_venta - self.id_producto.precio_compra)

    def __str__(self):
        return f"Merma #{self.id} - {self.id_producto.codigo} - {self.cantidad} unidades"


class MetodoPago(models.Model):
    MONEDAS = [
        ('USD', 'Dólar'),
        ('VES', 'Bolívar'),
        ('EUR', 'Euro'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=30, unique=True, choices=[
        ('Efectivo dolares', 'Efectivo dolares'),
        ('Efectivo bolívares', 'Efectivo bolívares'),
        ('Transferencia', 'Transferencia Bancaria'),
        ('Pago movil', 'Pago movil'),
        ('Zelle', 'Zelle'),
        ('Binance', 'Binance'),
        ('Saldo', 'Saldo Cliente'),
    ])
    moneda = models.CharField(max_length=3, choices=MONEDAS, default='USD')
    requiere_tasa = models.BooleanField(default=False, help_text="Indica si este método requiere tasa de cambio")

    def save(self, *args, **kwargs):
        # Determinar automáticamente si requiere tasa basado en la moneda
        self.requiere_tasa = self.moneda != 'USD'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.moneda})"


class Pago(models.Model):
    id = models.BigAutoField(primary_key=True)
    monto_usd = models.DecimalField(max_digits=12, decimal_places=6, validators=[MinValueValidator(0)], help_text="Monto en dólares (USD)")
    monto_moneda = models.DecimalField(max_digits=12, decimal_places=6, validators=[MinValueValidator(0)], null=True, blank=True, help_text="Monto en moneda local si aplica")
    tasa = models.DecimalField(max_digits=12, decimal_places=6, validators=[MinValueValidator(0)], null=True, blank=True, help_text="Tasa de cambio al momento del pago (solo para monedas diferentes a USD)")
    fecha = models.DateTimeField(default=timezone.now)

    metodo = models.ForeignKey(MetodoPago, on_delete=models.SET_NULL, null=True)
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)

    def __str__(self):
        if self.metodo and self.metodo.moneda != 'USD':
            return f"Pago {self.id} - {self.monto_moneda} {self.metodo.moneda} (USD: {self.monto_usd})"
        return f"Pago {self.id} - {self.monto_usd} USD"



class GastoAdministrativo(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.TextField(max_length=1000, validators=[name_validator])
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    fecha = models.DateField(default=timezone.now)
    activo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.nombre = sanitize_text(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} - {self.monto} ({self.fecha})"
    

""" # verificar que sirva
def validate_image_content(image):
    Validación adicional del contenido de la imagen
    try:
        from PIL import Image
        img = Image.open(image)
        img.verify()  # Verifica que sea una imagen válida
    except Exception as e:
        raise ValidationError("El archivo no es una imagen válida o está corrupto.") 
        """

# ========================================
# MODELO PARA REPORTES
# ========================================

class ReporteConfiguracion(models.Model):
    """Configuración para reportes del sistema"""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Configuración de Reporte'
        verbose_name_plural = 'Configuraciones de Reportes'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return self.nombre