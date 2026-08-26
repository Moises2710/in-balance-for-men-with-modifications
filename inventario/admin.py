from django.contrib import admin

from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

# Importación de modelos relacionados con productos y categorías
from .models import Categoria, Tipo, Marca, Fit, Color, Talla, Etiqueta, TallaCliente
# Importación de modelos relacionados con ventas y devoluciones
from .models import Cliente, Producto, Venta, DetalleVenta, Devolucion, DetalleDevolucion
# Importación de modelos relacionados con pagos y gastos
from .models import MetodoPago, Pago, GastoAdministrativo, Merma

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    fieldsets = UserAdmin.fieldsets + (
        ('Campos adicionales', {
            'fields': ('telefono', 'imagen',),
        }),
    )
    list_display = ['username', 'email', 'telefono', 'is_staff']

admin.site.register(CustomUser)
admin.site.register(Categoria)
admin.site.register(Tipo)
admin.site.register(Marca)
admin.site.register(Fit)
admin.site.register(Color)
admin.site.register(Talla)
admin.site.register(Etiqueta)
admin.site.register(Cliente)
admin.site.register(TallaCliente)
admin.site.register(Producto)
admin.site.register(Venta)
admin.site.register(DetalleVenta)
admin.site.register(Devolucion)
admin.site.register(DetalleDevolucion)
admin.site.register(Merma)
admin.site.register(MetodoPago)
admin.site.register(Pago)
admin.site.register(GastoAdministrativo)
