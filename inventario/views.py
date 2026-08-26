# DjangoCore
from django.shortcuts import render, get_object_or_404, redirect
from django.db import models, transaction
from django.db.models import Count, Q, Sum, Avg
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse, HttpResponse, Http404
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.decorators import permission_required, login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.conf import settings
from django.views.static import serve


# Autenticación
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, LoginView, PasswordChangeView
from django.contrib.admin.views.decorators import staff_member_required
from captcha.fields import CaptchaField
from django.contrib import messages

# Vistas basadas en clases
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.views.generic.edit import CreateView

# Importaciones locales
from .models import Producto, Color, Marca, Tipo, Talla, Fit, Cliente, Venta, DetalleVenta, CustomUser, Pago, MetodoPago, Devolucion, DetalleDevolucion, GastoAdministrativo, Merma
from .forms import ProductoForm, CustomUserCreationForm, CustomUserChangeForm, SimpleCaptchaLoginForm, CustomPasswordChangeForm, ClienteForm, MermaForm, GastoAdministrativoForm

import logging
import re
import json
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, time
from django.utils import timezone
import io
import os

# Función helper para calcular precio_unitario_final
def calcular_precio_unitario_final(precio_unitario, cantidad, subtotal_venta, descuento_venta):
    """
    Calcula el precio_unitario_final aplicando el descuento proporcionalmente
    
    Args:
        precio_unitario: Precio unitario original del producto
        cantidad: Cantidad del producto
        subtotal_venta: Subtotal total de la venta
        descuento_venta: Descuento total aplicado a la venta
    
    Returns:
        Decimal: Precio unitario final después del descuento proporcional
    """
    if subtotal_venta == 0:
        return precio_unitario
    
    # Calcular el subtotal de este detalle
    subtotal_detalle = precio_unitario * cantidad
    
    # Calcular el descuento proporcional para este detalle
    descuento_proporcional = (subtotal_detalle / subtotal_venta) * descuento_venta
    
    # Calcular el subtotal ajustado del detalle
    subtotal_ajustado = subtotal_detalle - descuento_proporcional
    
    # Calcular el precio unitario final
    precio_unitario_final = subtotal_ajustado / cantidad
    
    # Redondear a 2 decimales
    return precio_unitario_final.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

# MÓDULO DE REPORTES
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

User = get_user_model()

logger = logging.getLogger(__name__)

# ========================================
# FUNCIONES Y CLASES DE SEGURIDAD PARA SUSPENSIÓN DE USUARIOS
# ========================================

def is_admin(user):
    """Verificar si el usuario es administrador"""
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='Administrador').exists())

def can_suspend_user_safely(request_user, target_user):
    """
    Verificar si un usuario puede suspender a otro usuario de forma segura.
    Basado en la lógica original pero mejorada.
    
    Args:
        request_user: El usuario que intenta realizar la suspensión
        target_user: El usuario que será suspendido
        
    Returns:
        tuple: (puede_suspender, mensaje_error)
    """
    # No se puede suspender a sí mismo
    if request_user == target_user:
        return False, "No puedes suspenderte a ti mismo."
    
    # Superusuarios pueden suspender a cualquiera (excepto a sí mismos)
    if request_user.is_superuser:
        return True, None
    
    # Staff/Administradores pueden suspender a vendedores y usuarios normales
    if request_user.is_staff or request_user.groups.filter(name__iexact="Administrador").exists():
        # No pueden suspender a superusuarios
        if target_user.is_superuser:
            return False, "No tienes permiso para suspender a un superusuario."
        
        # No pueden suspender a otros staff/administradores
        if target_user.is_staff or target_user.groups.filter(name__iexact="Administrador").exists():
            return False, "No puedes suspender a otro administrador o staff."
        
        return True, None
    
    # Vendedores y usuarios normales no pueden suspender a nadie
    return False, "No tienes permisos para suspender usuarios."

class UserSuspensionSecurityMixin:
    """
    Mixin para controlar la seguridad en la suspensión de usuarios.
    Versión mejorada basada en la lógica original.
    """
    
    def can_suspend_user(self, request_user, target_user):
        """
        Verificar si un usuario puede suspender a otro usuario.
        
        Args:
            request_user: El usuario que intenta realizar la suspensión
            target_user: El usuario que será suspendido
            
        Returns:
            tuple: (puede_suspender, mensaje_error)
        """
        return can_suspend_user_safely(request_user, target_user)

def prueba(request):
    return render(request, 'inventario/prueba.html')

class InicioView(TemplateView):
    template_name = 'inventario/inicio.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')  # Redirige a la página de login si no está autenticado
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from decimal import Decimal
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Panel de Control'
        context['username'] = self.request.user.username
        
        # Obtener fechas para el período actual (último mes)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        # ========================================
        # MÉTRICAS ESPECÍFICAS DEL USUARIO
        # ========================================
        
        # Ventas del usuario en el período
        ventas_usuario = Venta.objects.filter(
            user=self.request.user,
            fecha__date__range=[start_date, end_date]
        )
        
        # Métricas principales del usuario
        context['nro_ventas_usuario'] = ventas_usuario.count()
        context['total_ingresos_usuario'] = ventas_usuario.aggregate(
            total=Sum('total_ajustado')
        )['total'] or Decimal('0')
        
        # Productos vendidos por el usuario
        productos_vendidos_usuario = DetalleVenta.objects.filter(
            venta__user=self.request.user,
            venta__fecha__date__range=[start_date, end_date]
        ).aggregate(
            total_productos=Sum('cantidad')
        )['total_productos'] or 0
        
        context['productos_vendidos_usuario'] = productos_vendidos_usuario
        
        # Comisiones por pagar (pendientes) - excluyendo ventas canceladas
        comisiones_por_pagar = ventas_usuario.filter(
            estado_comision='pendiente',
            cancelada=False
        ).aggregate(
            total=Sum('comision')
        )['total'] or Decimal('0')
        context['comisiones_por_pagar'] = comisiones_por_pagar
        
        # Comisiones pagadas
        comisiones_pagadas = ventas_usuario.filter(
            estado_comision='pagado'
        ).aggregate(
            total=Sum('comision')
        )['total'] or Decimal('0')
        context['comisiones_pagadas'] = comisiones_pagadas
        
        # Comisiones denegadas
        comisiones_denegadas = ventas_usuario.filter(
            estado_comision='denegado'
        ).aggregate(
            total=Sum('comision')
        )['total'] or Decimal('0')
        context['comisiones_denegadas'] = comisiones_denegadas
        
        # Comisiones totales calculadas (por pagar + pagadas)
        comisiones_totales = comisiones_por_pagar + comisiones_pagadas
        context['comisiones_totales'] = comisiones_totales
        
        # ========================================
        # MÉTRICAS DE DEVOLUCIONES DEL USUARIO
        # ========================================
        
        # Devoluciones del usuario en el período
        devoluciones_usuario = Devolucion.objects.filter(
            id_venta__user=self.request.user,
            fecha__range=[start_date, end_date]
        )
        
        # Número total de devoluciones
        context['nro_devoluciones_usuario'] = devoluciones_usuario.count()
        
        # Cantidad total de productos devueltos
        productos_devueltos_usuario = DetalleDevolucion.objects.filter(
            id_devolucion__id_venta__user=self.request.user,
            id_devolucion__fecha__range=[start_date, end_date]
        ).aggregate(
            total_productos=Sum('cantidad_producto')
        )['total_productos'] or 0
        
        context['productos_devueltos_usuario'] = productos_devueltos_usuario
        
        # Promedio por venta del usuario
        promedio_venta_usuario = ventas_usuario.aggregate(
            promedio=Avg('total_ajustado')
        )['promedio'] or Decimal('0')
        context['promedio_venta_usuario'] = promedio_venta_usuario
        
        # ========================================
        # MÉTRICAS GENERALES DEL SISTEMA
        # ========================================
        
        # Total de productos en el sistema
        context['productos_count'] = Producto.objects.count()
        
        # Ventas totales del sistema en el período
        ventas_totales = Venta.objects.filter(
            fecha__date__range=[start_date, end_date]
        )
        context['nro_ventas_totales'] = ventas_totales.count()
        
        # Ingresos totales del sistema
        context['ingresos_totales'] = ventas_totales.aggregate(
            total=Sum('total')
        )['total'] or Decimal('0')
        
        # ========================================
        # DATOS PARA GRÁFICOS
        # ========================================
        
        # Ventas del usuario por día (últimos 7 días)
        ventas_por_dia_usuario = []
        for i in range(7):
            fecha = end_date - timedelta(days=i)
            ventas_dia = ventas_usuario.filter(fecha__date=fecha).count()
            ventas_por_dia_usuario.append({
                'fecha': fecha.strftime('%d/%m'),
                'ventas': ventas_dia
            })
        
        context['ventas_por_dia_usuario'] = json.dumps(ventas_por_dia_usuario)
        
        # Top 5 productos más vendidos por el usuario
        top_productos_usuario = DetalleVenta.objects.filter(
            venta__user=self.request.user,
            venta__fecha__date__range=[start_date, end_date]
        ).values(
            'producto__descripcion', 'producto__marca__nombre'
        ).annotate(
            cantidad_vendida=Sum('cantidad')
        ).order_by('-cantidad_vendida')[:5]
        
        context['top_productos_usuario'] = top_productos_usuario
        
        # Ventas por marca del usuario
        ventas_por_marca_usuario = DetalleVenta.objects.filter(
            venta__user=self.request.user,
            venta__fecha__date__range=[start_date, end_date]
        ).values(
            'producto__marca__nombre'
        ).annotate(
            cantidad=Sum('cantidad')
        ).order_by('-cantidad')[:5]
        
        context['ventas_por_marca_usuario'] = json.dumps(list(ventas_por_marca_usuario))
        
        # ========================================
        # RANKING DEL USUARIO
        # ========================================
        
        # Posición del usuario en ventas totales
        ventas_por_usuario = Venta.objects.filter(
            fecha__date__range=[start_date, end_date]
        ).values('user__username').annotate(
            total_ventas=Count('id'),
            total_ingresos=Sum('total_ajustado')
        ).order_by('-total_ingresos')
        
        # Encontrar la posición del usuario actual
        posicion = 1
        for i, venta in enumerate(ventas_por_usuario):
            if venta['user__username'] == self.request.user.username:
                posicion = i + 1
                break
        
        context['posicion_usuario'] = posicion
        context['total_usuarios_activos'] = ventas_por_usuario.count()
        
        # ========================================
        # FECHAS PARA EL CONTEXTO
        # ========================================
        
        context['periodo_inicio'] = start_date.strftime('%d/%m/%Y')
        context['periodo_fin'] = end_date.strftime('%d/%m/%Y')
        
        return context
    

# vista de usuarios
class CustomUserListView(LoginRequiredMixin, ListView):
    model = CustomUser
    template_name = 'inventario/usuarios/usuario_list.html'
    context_object_name = 'usuarios'

    def get_queryset(self):
        user = self.request.user

        # Verificar si tiene permiso para ver todos los usuarios
        if user.has_perm('inventario.view_customuser') or user.is_superuser or user.is_staff:
            return CustomUser.objects.all()

        # Si no tiene permiso, solo mostrar su propio perfil
        return CustomUser.objects.filter(pk=user.pk)

    def test_func(self):
        user = self.request.user

        # Verificar si tiene permisos para ver todos los usuarios
        if user.has_perm('usuarios.view_customuser') or user.is_superuser or user.is_staff:
            return True

        # Verificar que el usuario solo pueda ver su propio perfil si no tiene el permiso
        return self.get_queryset().count() == 1 and self.get_queryset().first().pk == user.pk

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Lista de Usuarios'
        # Agregar datos para los filtros
        context['grupos'] = Group.objects.all().order_by('name')
        
        # Obtener datos únicos para filtros dinámicos
        usuarios = CustomUser.objects.all()
        context['usernames_usuarios'] = usuarios.values_list('username', flat=True).distinct().order_by('username')
        context['emails_usuarios'] = usuarios.values_list('email', flat=True).distinct().order_by('email')
        context['telefonos_usuarios'] = usuarios.values_list('telefono', flat=True).distinct().order_by('telefono')
        context['first_names_usuarios'] = usuarios.values_list('first_name', flat=True).distinct().order_by('first_name')
        context['last_names_usuarios'] = usuarios.values_list('last_name', flat=True).distinct().order_by('last_name')
        
        return context


class UsuarioAjaxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Verificar permisos
        user = request.user
        if not (user.has_perm('inventario.view_customuser') or user.is_superuser or user.is_staff):
            return JsonResponse({'error': 'No tienes permisos para ver usuarios'}, status=403)

        # Parámetros básicos de DataTables
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        order_column_index = request.GET.get('order[0][column]', 0)
        order_direction = request.GET.get('order[0][dir]', 'asc')

        # Mapeo de columnas
        columns = ['username', 'email', 'telefono', 'is_active', 'date_joined']
        if int(order_column_index) < len(columns):
            order_column = columns[int(order_column_index)]
            if order_direction == 'desc':
                order_column = '-' + order_column
        else:
            order_column = 'username'  # Ordenamiento por defecto

        # Parámetros de filtrado
        show_inactivos = request.GET.get('show_inactivos', 'false').lower() == 'true'
        show_staff = request.GET.get('show_staff', 'false').lower() == 'true'
        show_superusers = request.GET.get('show_superusers', 'false').lower() == 'true'
        grupos = request.GET.getlist('grupos[]')
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        
        # Nuevos filtros por columnas
        usernames = request.GET.getlist('usernames[]')
        first_names = request.GET.getlist('first_names[]')
        last_names = request.GET.getlist('last_names[]')
        emails = request.GET.getlist('emails[]')
        telefonos = request.GET.getlist('telefonos[]')

        # Consulta base con prefetch_related para optimización
        qs = CustomUser.objects.prefetch_related('groups')

        # Aplicar filtros de estado
        if not show_inactivos:
            qs = qs.filter(is_active=True)
        if show_staff:
            qs = qs.filter(is_staff=True)
        if show_superusers:
            qs = qs.filter(is_superuser=True)

        # Aplicar filtros por columnas
        if usernames:
            qs = qs.filter(username__in=usernames)
        if first_names:
            qs = qs.filter(first_name__in=first_names)
        if last_names:
            qs = qs.filter(last_name__in=last_names)
        if emails:
            qs = qs.filter(email__in=emails)
        if telefonos:
            qs = qs.filter(telefono__in=telefonos)
        if grupos:
            qs = qs.filter(groups__name__in=grupos)

        # Aplicar filtros de fecha
        if fecha_desde:
            qs = qs.filter(date_joined__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(date_joined__date__lte=fecha_hasta)

        # Búsqueda general
        if search_value:
            qs = qs.filter(
                Q(username__icontains=search_value) |
                Q(email__icontains=search_value) |
                Q(first_name__icontains=search_value) |
                Q(last_name__icontains=search_value) |
                Q(telefono__icontains=search_value)
            )

        # Conteo total después de filtros
        total_filtered = qs.distinct().count()

        # Paginación y ordenamiento
        usuarios = qs.distinct().order_by(order_column)[start:start + length]

        # Preparar datos para respuesta JSON
        data = []
        for usuario in usuarios:
            # Obtener grupos como string
            grupos_str = ', '.join([grupo.name for grupo in usuario.groups.all()])
            
            data.append({
                'id': usuario.id,
                'username': escape(usuario.username),
                'email': escape(usuario.email) if usuario.email else '',
                'telefono': escape(usuario.telefono) if usuario.telefono else '',
                'grupos': grupos_str,
                'is_active': usuario.is_active,
                'is_staff': usuario.is_staff,
                'is_superuser': usuario.is_superuser,
                'date_joined': usuario.date_joined.strftime('%d/%m/%Y %H:%M'),
                'imagen_url': usuario.thumbnail.url if usuario.imagen else '/static/assets/images/avatars/01.png',
            })

        return JsonResponse({
            'draw': draw,
            'recordsTotal': CustomUser.objects.count(),
            'recordsFiltered': total_filtered,
            'data': data
        })


class SupabaseDiagView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Diagnóstico de Storage Supabase cuando no hay shell disponible.
    Requiere usuario staff/superusuario y variable DIAG_ENABLE=True en entorno.
    """

    def test_func(self):
        return (self.request.user.is_staff or self.request.user.is_superuser) and (
            os.environ.get('DIAG_ENABLE', 'False').lower() == 'true'
        )

    def get(self, request, *args, **kwargs):
        result = {
            'DEBUG': settings.DEBUG,
            'DEFAULT_FILE_STORAGE': getattr(settings, 'DEFAULT_FILE_STORAGE', 'FileSystemStorage'),
            'IMAGEKIT_CACHEFILE_STORAGE': getattr(settings, 'IMAGEKIT_CACHEFILE_STORAGE', None),
            'default_storage_class': default_storage.__class__.__name__,
            'SUPABASE_URL_present': bool(os.environ.get('clave de entorno')),
            'SUPABASE_BUCKET': os.environ.get('clave de entorno'),
            'SUPABASE_PUBLIC': os.environ.get('clave de entorno'),
        }

        # Prueba usando el default_storage (debería apuntar a Supabase en producción)
        try:
            test_path = f"diag/test_{timezone.now().timestamp()}.txt"
            saved_name = default_storage.save(test_path, ContentFile(b"ok"))
            result['default_storage_saved'] = saved_name
            result['default_storage_url'] = default_storage.url(saved_name)
        except Exception as e:
            result['default_storage_error'] = str(e)

        # Prueba directa con SDK si está disponible
        try:
            from supabase import create_client
            url = os.environ.get('clave de entorno')
            key = os.environ.get('clave de entorno')
            bucket = os.environ.get('clave de entorno')
            if url and key and bucket:
                client = create_client(url, key)
                up = client.storage.from_(bucket).upload(
                    "diag/diag_sdk.txt",
                    b"sdk",
                    {
                        "content-type": "text/plain",
                        "x-upsert": "true",
                    },
                )
                data = getattr(up, 'data', up)
                result['sdk_upload'] = str(data)
                listing = client.storage.from_(bucket).list("diag")
                # Normalizar listado a tipos serializables
                try:
                    result['sdk_list_count'] = len(listing or [])
                except Exception:
                    result['sdk_list'] = str(listing)
            else:
                result['sdk_skipped'] = 'Faltan variables SUPABASE_*'
        except Exception as e:
            result['sdk_error'] = str(e)

        return JsonResponse(result)


class CustomUserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'inventario/usuarios/usuario_form.html'
    success_url = reverse_lazy('usuario_list')

    # Usamos el permiso estándar de Django para crear instancias del modelo
    permission_required = 'inventario.add_customuser'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Registrar Nuevo Usuario'
        return context

    def form_valid(self, form):
        try:
            # El formulario ya maneja la asignación de grupos en su método save()
            user = form.save()
            
            messages.success(self.request, 'Usuario creado exitosamente.')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'Error al crear el usuario: {str(e)}')
            return self.form_invalid(form)

class CustomUserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CustomUser
    form_class = CustomUserChangeForm
    template_name = 'inventario/usuarios/usuario_update.html'

    def get_object(self, queryset=None):
        return self.request.user

    def test_func(self):
        obj = self.get_object()
        return self.request.user.pk == obj.pk

    def handle_no_permission(self):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("No tienes permiso para modificar este perfil.")

    def get_success_url(self):
        return reverse('usuario_detail', kwargs={'pk': self.request.user.pk})

@csrf_exempt
@login_required
def eliminar_imagen_usuario(request, pk):
    if request.method == "POST":
        user = get_object_or_404(CustomUser, pk=pk)
        
        # Verificamos si el usuario tiene permiso para modificar esa imagen
        if request.user == user or request.user.is_superuser:
            if user.imagen:
                user.imagen.delete(save=True)
                return JsonResponse({"success": True})
            return JsonResponse({"error": "No hay imagen que eliminar"}, status=400)
        return JsonResponse({"error": "No autorizado"}, status=403)

    return JsonResponse({"error": "Método no permitido"}, status=405)
    
class UsuarioDetailView(LoginRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'inventario/usuarios/usuario_detail.html'
    context_object_name = 'usuario'

class ToggleUserActiveStatusView(LoginRequiredMixin, PermissionRequiredMixin, UserSuspensionSecurityMixin, View):
    permission_required = 'inventario.can_suspend_user'

    def post(self, request, pk, *args, **kwargs):
        # Obtener usuario sin select_for_update para evitar problemas de transacción
        user = get_object_or_404(get_user_model(), pk=pk)
        password = request.POST.get('password')

        if not password or not request.user.check_password(password):
            messages.error(request, "Contraseña incorrecta. No se realizó ningún cambio.")
            return redirect('usuario_list')

        # Verificar si el usuario puede suspender al objetivo usando el mixin
        puede_suspender, mensaje_error = self.can_suspend_user(request.user, user)
        
        if not puede_suspender:
            messages.error(request, mensaje_error)
            return redirect('usuario_list')

        # Alternar estado activo
        user.is_active = not user.is_active
        
        # Si se está activando el usuario, limpiar los intentos fallidos
        if user.is_active:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_failed_login = None
            # Forzar la actualización de todos los campos relacionados
            user.save(update_fields=['is_active', 'failed_login_attempts', 'locked_until', 'last_failed_login'])
        else:
            user.save(update_fields=['is_active'])

        estado = "activado" if user.is_active else "suspendido"
        if user.is_active:
            messages.success(request, f'El usuario "{user.username}" ha sido {estado} y sus intentos fallidos han sido reiniciados.')
        else:
            messages.success(request, f'El usuario "{user.username}" ha sido {estado}.')
        return redirect('usuario_list')
    
@require_http_methods(["POST"])
@login_required
@permission_required('inventario.can_suspend_user', raise_exception=True)
def suspender_usuario(request, user_id):
    password = request.POST.get('password')
    # Obtener usuario sin select_for_update para evitar problemas de transacción
    usuario = get_object_or_404(CustomUser, id=user_id)

    if not password or not request.user.check_password(password):
        messages.error(request, 'Contraseña incorrecta. Acción no autorizada.')
        return redirect('usuarios')

    # Crear instancia del mixin para usar su lógica
    security_mixin = UserSuspensionSecurityMixin()
    puede_suspender, mensaje_error = security_mixin.can_suspend_user(request.user, usuario)
    
    if not puede_suspender:
        messages.error(request, mensaje_error)
        return redirect('usuarios')

    usuario.is_active = not usuario.is_active
    
    # Si se está activando el usuario, limpiar los intentos fallidos
    if usuario.is_active:
        usuario.failed_login_attempts = 0
        usuario.locked_until = None
        usuario.last_failed_login = None
        # Forzar la actualización de todos los campos relacionados
        usuario.save(update_fields=['is_active', 'failed_login_attempts', 'locked_until', 'last_failed_login'])
    else:
        usuario.save(update_fields=['is_active'])
    
    estado = "activado" if usuario.is_active else "suspendido"
    if usuario.is_active:
        messages.success(request, f'El usuario "{usuario.username}" ha sido {estado} exitosamente y sus intentos fallidos han sido reiniciados.')
    else:
        messages.success(request, f'El usuario "{usuario.username}" ha sido {estado} exitosamente.')
    return redirect('usuarios')



    
@method_decorator(csrf_exempt, name='dispatch')
class CustomLoginView(LoginView):
    template_name = 'inventario/base_login.html'
    authentication_form = SimpleCaptchaLoginForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Asegurar que el formulario esté disponible
        if 'form' not in context:
            context['form'] = self.get_form()
        # Agregar la clave de reCAPTCHA v3 al contexto
        context[''] = settings.clave_de_entorno
        return context

    def get_success_url(self):
        return reverse_lazy('inicio')

    def form_valid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Limpiar intentos fallidos si inicia sesión correctamente
            username = form.cleaned_data.get('username')
            if username:
                self.request.session.pop(f'failed_attempts_{username}', None)
            login(self.request, form.get_user())
            return JsonResponse({'success': True, 'redirect_url': self.get_success_url()})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            print(f"DEBUG VIEW: Formulario inválido - Errores: {form.errors}")
            errors = {}
            if '__all__' in form.errors:
                errors['__all__'] = form.errors['__all__'][0]
            else:
                for field, error_list in form.errors.items():
                    errors[field] = error_list[0]

            # Solo manejar actualización de captcha, la lógica de bloqueo está en SimpleCaptchaLoginForm
            update_captcha = True
            if 'captcha' in form.errors:
                form.fields['captcha'].widget.recaptcha_challenge_field = None
                form.fields['captcha'].widget.recaptcha_response_field = None
                form.fields['captcha'] = CaptchaField()

            return JsonResponse({'success': False, 'errors': errors, 'update_captcha': update_captcha}, status=400)

        return self.render_to_response(self.get_context_data(form=form))

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'inventario/usuarios/cambiar_contraseña.html'
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Tu contraseña ha sido cambiada exitosamente.')
        return response
    
    def form_invalid(self, form):
        # Asegurar que los errores se muestren correctamente
        return super().form_invalid(form)


class CustomPasswordResetView(PasswordResetView):
    
    def post(self, request, *args, **kwargs):
        """
        Maneja las solicitudes POST, asegurando respuestas JSON para AJAX.
        """
        form = self.get_form()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Para AJAX, manejar directamente
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        else:
            # Para solicitudes normales, usar comportamiento estándar
            return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Verifica el correo y envía instrucciones de reseteo si es válido."""
        import logging
        logger = logging.getLogger(__name__)
        
        email = form.cleaned_data['email']
        logger.info(f"Iniciando proceso de recuperación para email: {email}")
        
        # Verificar si el correo está registrado en la base de datos
        if not User.objects.filter(email=email).exists():
            logger.warning(f"Email no encontrado en BD: {email}")
            # Determinar si es una solicitud AJAX
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'error': 'No existe una cuenta asociada a este correo.'
                }, status=400)
            else:
                # Para solicitudes normales, añadir un error al formulario
                form.add_error('email', 'No existe una cuenta asociada a este correo.')
                return self.form_invalid(form)
        
        logger.info(f"Email encontrado, iniciando envío...")
        
        # Verificar qué backend de email se está usando
        from django.core.mail import get_connection
        connection = get_connection()
        logger.info(f"Backend de email en uso: {connection.__class__.__name__}")
        
        # Si el correo existe, enviar el email usando el método estándar de Django
        try:
            logger.info("Enviando email usando método estándar de Django...")
            form.save(
                request=self.request,
                from_email=None,
                email_template_name=self.email_template_name,
                subject_template_name=self.subject_template_name
            )
            logger.info(f"Email enviado exitosamente para: {email}")
            
        except Exception as e:
            logger.error(f"Error enviando email para {email}: {str(e)}")
            
            # Si falla el envío estándar, intentar método alternativo
            try:
                logger.info("Intentando método alternativo de envío...")
                # Usar el método original de Django como fallback
                super().form_valid(form)
                logger.info(f"Email enviado exitosamente (método alternativo) para: {email}")
            except Exception as e2:
                logger.error(f"Error en método alternativo para {email}: {str(e2)}")
                
                # Determinar el tipo de error para dar un mensaje más específico
                error_message = 'Error temporal enviando el correo. Por favor intenta de nuevo.'
                if 'timeout' in str(e2).lower():
                    error_message = 'El servidor de correo tardó demasiado en responder. Por favor intenta de nuevo.'
                elif 'authentication' in str(e2).lower() or 'login' in str(e2).lower():
                    error_message = 'Error de configuración del servidor de correo. Contacta al administrador.'
                elif 'connection' in str(e2).lower():
                    error_message = 'No se pudo conectar al servidor de correo. Verifica tu conexión.'
                
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_message
                    }, status=500)
                else:
                    form.add_error('email', error_message)
                    return self.form_invalid(form)
        
        # Determinar si es una solicitud AJAX para la respuesta
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Se han enviado instrucciones a tu correo electrónico.',
                'redirect_url': self.get_success_url()
            }, status=200)
        else:
            # Para solicitudes normales, seguir el flujo estándar
            return super().form_valid(form)
    
    def form_invalid(self, form):
        """Maneja formularios inválidos."""
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = form.errors.get('email', ['Error en el formulario.'])
            return JsonResponse({
                'success': False,
                'error': errors[0]
            }, status=400)
        else:
            # Para solicitudes normales, seguir el flujo estándar
            return super().form_invalid(form)
            
    def get_success_url(self):
        """Retorna la URL de éxito."""
        if hasattr(self, 'success_url') and self.success_url:
            return self.success_url
        # De lo contrario, usa el default
        return reverse_lazy('login')


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Vista personalizada que desbloquea automáticamente usuarios bloqueados
    cuando cambian su contraseña desde el email de recuperación.
    """
    template_name = 'inventario/recuperacion/recuperar_contraseña_confirmar.html'
    
    def form_valid(self, form):
        """
        Este método se ejecuta DESPUÉS de que Django valida y cambia la contraseña.
        Agregamos lógica EXTRA para desbloquear si es necesario.
        """
        # PRIMERO: Django hace su trabajo normal (cambiar contraseña)
        response = super().form_valid(form)
        
        # DESPUÉS: Agregamos nuestra lógica personalizada
        user = form.user
        
        # Verificar si el usuario está bloqueado
        if hasattr(user, 'is_locked') and user.is_locked():
            # Usuario bloqueado → Desbloquear automáticamente
            user.unlock_user()
            
            # Mostrar mensaje de desbloqueo
            messages.success(
                self.request, 
                '✅ Tu contraseña ha sido cambiada y tu cuenta desbloqueada exitosamente.'
            )
            
            # Log de seguridad
            import logging
            security_logger = logging.getLogger('security')
            security_logger.info(
                f"Usuario {user.username} desbloqueado automáticamente "
                f"después de cambiar contraseña desde {self.request.META.get('REMOTE_ADDR')}"
            )
            
        else:
            # Usuario no bloqueado → Solo mensaje normal
            messages.success(
                self.request, 
                '✅ Tu contraseña ha sido cambiada exitosamente.'
            )
        
        return response


# Vista para listar productos
class ProductoListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = 'inventario/productos/producto_list.html' 
    context_object_name = 'productos'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # datos necesarios para los filtros
        context['tipos'] = Tipo.objects.all()
        context['marcas'] = Marca.objects.all()
        context['colores'] = Color.objects.all()
        context['tallas'] = Talla.objects.all()
        return context


class ProductoAjaxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Parámetros básicos de DataTables
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        order_column_index = request.GET.get('order[0][column]', 0)
        order_direction = request.GET.get('order[0][dir]', 'asc')

        # Mapeo de columnas
        columns = ['id', 'codigo', 'tipo__nombre', 'marca__nombre', 'color__nombre', 'talla__nombre', 'stock', 'precio_venta', 'is_active']
        order_column = columns[int(order_column_index)]
        if order_direction == 'desc':
            order_column = '-' + order_column

        # Parámetros de filtrado
        show_inactivos = request.GET.get('show_inactivos', 'false').lower() == 'true'
        show_sin_stock = request.GET.get('show_sin_stock', 'false').lower() == 'true'
        codigo_filter = request.GET.get('codigo_filter', '')
        tipos = request.GET.getlist('tipos[]')
        marcas = request.GET.getlist('marcas[]')
        colores = request.GET.getlist('colores[]')
        tallas = request.GET.getlist('tallas[]')
        stock_min = request.GET.get('stock_min')
        stock_max = request.GET.get('stock_max')
        precio_min = request.GET.get('precio_min')
        precio_max = request.GET.get('precio_max')

        # Consulta base con select_related para optimización
        qs = Producto.objects.select_related('marca', 'color', 'talla', 'tipo')

        # Aplicar filtros de estado
        if not show_inactivos:
            qs = qs.filter(is_active=True)
        if not show_sin_stock:
            qs = qs.filter(stock__gt=0)

        # Aplicar filtros por columnas
        if codigo_filter:
            qs = qs.filter(codigo__icontains=codigo_filter)
        if tipos:
            qs = qs.filter(tipo__nombre__in=tipos)
        if marcas:
            qs = qs.filter(marca__nombre__in=marcas)
        if colores:
            qs = qs.filter(color__nombre__in=colores)
        if tallas:
            qs = qs.filter(talla__nombre__in=tallas)
        if stock_min:
            qs = qs.filter(stock__gte=float(stock_min))
        if stock_max:
            qs = qs.filter(stock__lte=float(stock_max))
        if precio_min:
            qs = qs.filter(precio_venta__gte=float(precio_min))
        if precio_max:
            qs = qs.filter(precio_venta__lte=float(precio_max))

        # Búsqueda general
        if search_value:
            qs = qs.filter(
                Q(descripcion__icontains=search_value) |
                Q(codigo__icontains=search_value) |
                Q(marca__nombre__icontains=search_value) |
                Q(tipo__nombre__icontains=search_value) |
                Q(color__nombre__icontains=search_value) |
                Q(talla__nombre__icontains=search_value)
            )

        # Conteo total después de filtros
        total_filtered = qs.count()

        # Paginación y ordenamiento
        productos = qs.order_by(order_column)[start:start + length]

        # Preparar datos para respuesta JSON
        data = []
        for producto in productos:
            thumbnail_url = None
            has_image_error = False
            has_image = bool(producto.imagen)
            
            if has_image:
                try:
                    if not producto.imagen.storage.exists(producto.imagen.name):
                        raise FileNotFoundError()
                    thumbnail_url = producto.thumbnail.url
                except Exception:
                    has_image_error = True

            data.append({
                'id': producto.id,
                'descripcion': escape(producto.descripcion),
                'codigo': escape(producto.codigo),
                'precio_venta': str(producto.precio_venta),
                'stock': producto.stock,
                'marca': escape(producto.marca.nombre) if producto.marca else '',
                'color': escape(producto.color.nombre) if producto.color else '',
                'talla': escape(producto.talla.nombre) if producto.talla else '',
                'tipo': escape(producto.tipo.nombre) if producto.tipo else '',
                'is_active': producto.is_active,
                'thumbnail_url': thumbnail_url,
                'has_image': has_image,
                'has_image_error': has_image_error,
            })

        return JsonResponse({
            'draw': draw,
            'recordsTotal': Producto.objects.count(),
            'recordsFiltered': total_filtered,
            'data': data
        })


# Vista para ver detalles de un producto
class ProductoDetailView(LoginRequiredMixin, DetailView):
    model = Producto
    template_name = 'inventario/productos/producto_detail.html'
    context_object_name = 'producto'


# Vista para crear un producto
class ProductoCreateView(LoginRequiredMixin, CreateView):
    model = Producto
    template_name = 'inventario/productos/producto_create.html'
    fields = [
        'descripcion', 'codigo', 'precio_venta', 'precio_compra', 'stock',
        'imagen', 'tipo', 'marca', 'fit', 'color', 'talla'
    ]
    ordering = ['nombre']
    success_url = reverse_lazy('producto_list')

    # Para Filtrar en los select y que no aparezcan entradas no activas
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['tipo'].queryset  = Tipo.objects.filter(is_active=True).order_by('nombre')
        form.fields['marca'].queryset = Marca.objects.filter(is_active=True).order_by('nombre')
        form.fields['fit'].queryset   = Fit.objects.filter(is_active=True).order_by('nombre')
        form.fields['color'].queryset = Color.objects.filter(is_active=True).order_by('nombre')
        form.fields['talla'].queryset = Talla.objects.filter(is_active=True).order_by('nombre')
        return form

    def form_valid(self, form):
        try:
            self.object = form.save()
            messages.success(self.request, f'El producto "{self.object.codigo}" creado correctamente.')
        except Exception as e:
            logger.error(f'Error al crear producto: {str(e)}', exc_info=True)
            messages.error(self.request, 'Ocurrió un error al crear el producto. Verifique los datos e intente nuevamente.')
            return self.form_invalid(form)

        action = self.request.POST.get('action')

        if action == 'save_and_add_new':
            return redirect('producto_create')
        
        elif action == 'save_and_continue':
            return redirect('producto_update', pk=self.object.pk)

        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'El formulario contiene errores. Por favor, revise los campos resaltados.')
        return super().form_invalid(form)


# Vista para actualizar un producto
class ProductoUpdateView(LoginRequiredMixin, UpdateView):
    model = Producto
    template_name = 'inventario/productos/producto_update.html'
    fields = [
        'descripcion', 'codigo', 'precio_venta', 'precio_compra', 'stock',
        'imagen', 'tipo', 'marca', 'fit', 'color', 'talla'
    ]
    success_url = reverse_lazy('producto_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['tipo'].queryset  = Tipo.objects.filter(is_active=True).order_by('nombre')
        form.fields['marca'].queryset = Marca.objects.filter(is_active=True).order_by('nombre')
        form.fields['fit'].queryset   = Fit.objects.filter(is_active=True).order_by('nombre')
        form.fields['color'].queryset = Color.objects.filter(is_active=True).order_by('nombre')
        form.fields['talla'].queryset = Talla.objects.filter(is_active=True).order_by('nombre')
        return form

    def form_valid(self, form):
        try:
            self.object = form.save()
            messages.success(self.request, f'El producto "{self.object.codigo}" se ha actualizado correctamente.')
        except Exception as e:
            logger.error(f'Error al crear producto: {str(e)}', exc_info=True)
            messages.error(self.request, 'Ocurrió un error al crear el producto. Verifique los datos e intente nuevamente.')
            return self.form_invalid(form)

        action = self.request.POST.get('action')

        if action == 'save_and_add_new':
            return redirect('producto_create')
        
        elif action == 'save_and_continue':
            return redirect('producto_update', pk=self.object.pk)
        
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'El formulario contiene errores. Por favor, revise los campos resaltados.')
        return super().form_invalid(form)


# Vista para eliminar un producto
class ProductoDeleteView(LoginRequiredMixin, DeleteView):
    model = Producto
    template_name = 'inventario/productos/producto_confirm_delete.html'
    success_url = reverse_lazy('producto_list')


# Cambiar el estado del producto
@login_required
def producto_toggle(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    try:
        producto.is_active = not producto.is_active
        producto.save()
        estado = 'activado' if producto.is_active else 'desactivado'
        messages.success(request, f'El producto "{producto.codigo}" ha sido {estado} correctamente.')
        
    except Exception as e:
        logger.error(f'Error al cambiar el estado del producto: {str(e)}', exc_info=True)
        messages.error(request, 'Ocurrió un error al intentar cambiar el estado del producto.')

    return redirect('producto_list')


class ColorListView(LoginRequiredMixin, ListView):
    model = Color
    template_name = 'inventario/normalizacion_productos/color_list.html' 
    context_object_name = 'colores'
    ordering = ['nombre']
    
    def get_queryset(self):
        return Color.objects.annotate(
            num_productos=Count('producto')
        ).order_by('nombre')
    

class ColorCreateView(LoginRequiredMixin, CreateView):
    model = Color
    fields = ['nombre']  
    template_name = 'inventario/normalizacion_productos/color_form.html'
        
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('color_create')
        return ctx

    def form_valid(self, form):
        # Establecer is_active=True por defecto
        form.instance.is_active = True
        self.object = form.save()
        return JsonResponse({'success': True})
    
    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })
    
    def get_success_url(self):
        return reverse_lazy('color_list')


class ColorUpdateView(LoginRequiredMixin, UpdateView):
    model = Color
    fields = ['nombre']
    template_name = 'inventario/normalizacion_productos/color_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('color_update', kwargs={'pk': self.object.pk})
        return ctx
    
    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })


# Cambiar el estado del color
@login_required
def color_toggle(request, pk):
    color = get_object_or_404(Color, pk=pk)

    try:
        color.is_active = not color.is_active
        color.save()
        estado = 'activado' if color.is_active else 'desactivado'
        messages.success(request, f'El color "{color.nombre}" ha sido {estado} correctamente.')

    except Exception as e:
        logger.error(f'Error al cambiar el estado del color: {str(e)}', exc_info=True)
        messages.error(request, 'Ocurrió un error al intentar cambiar el estado del color.')

    return redirect('color_list')


class MarcaListView(LoginRequiredMixin, ListView):
    model = Marca
    template_name = 'inventario/normalizacion_productos/marca_list.html' 
    context_object_name = 'marcas'
    ordering = ['nombre']
    
    def get_queryset(self):
        return Marca.objects.annotate(
            num_productos=Count('producto')
        ).order_by('nombre')
    

class MarcaCreateView(LoginRequiredMixin, CreateView):
    model = Marca
    fields = ['nombre']  
    template_name = 'inventario/normalizacion_productos/marca_form.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('marca_create')
        return ctx

    def form_valid(self, form):
        form.instance.is_active = True
        self.object = form.save()
        return JsonResponse({'success': True})
    
    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })
    
    def get_success_url(self):
        return reverse_lazy('marca_list')


class MarcaUpdateView(LoginRequiredMixin, UpdateView):
    model = Marca
    fields = ['nombre']
    template_name = 'inventario/normalizacion_productos/marca_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('marca_update', kwargs={'pk': self.object.pk})
        return ctx
    
    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })


# Cambiar el estado del marca
@login_required
def marca_toggle(request, pk):
    marca = get_object_or_404(Marca, pk=pk)

    try:
        marca.is_active = not marca.is_active
        marca.save()
        estado = 'activado' if marca.is_active else 'desactivado'
        messages.success(request, f'El marca "{marca.nombre}" ha sido {estado} correctamente.')

    except Exception as e:
        logger.error(f'Error al cambiar el estado del marca: {str(e)}', exc_info=True)
        messages.error(request, 'Ocurrió un error al intentar cambiar el estado del marca.')

    return redirect('marca_list')


class TipoListView(LoginRequiredMixin, ListView):
    model = Tipo
    template_name = 'inventario/normalizacion_productos/tipo_list.html' 
    context_object_name = 'tipos'
    ordering = ['nombre']
    
    def get_queryset(self):
        return Tipo.objects.annotate(
            num_productos=Count('producto')
        ).order_by('categoria', 'nombre')
    
    
    
class TipoCreateView(LoginRequiredMixin, CreateView):
    model = Tipo
    fields = ['nombre','categoria']  
    template_name = 'inventario/normalizacion_productos/tipo_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('tipo_create')
        return ctx

    def form_valid(self, form):
        form.instance.is_active = True
        self.object = form.save()
        return JsonResponse({'success': True})
    
    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })
    
    def get_success_url(self):
        return reverse_lazy('tipo_list')


class TipoUpdateView(LoginRequiredMixin, UpdateView):
    model = Tipo
    fields = ['nombre', 'categoria']
    template_name = 'inventario/normalizacion_productos/tipo_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('tipo_update', kwargs={'pk': self.object.pk})
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })


# Cambiar el estado del tipo
@login_required
def tipo_toggle(request, pk):
    tipo = get_object_or_404(Tipo, pk=pk)

    try:
        tipo.is_active = not tipo.is_active
        tipo.save()
        estado = 'activado' if tipo.is_active else 'desactivado'
        messages.success(request, f'El tipo "{tipo.nombre}" ha sido {estado} correctamente.')

    except Exception as e:
        logger.error(f'Error al cambiar el estado del tipo: {str(e)}', exc_info=True)
        messages.error(request, 'Ocurrió un error al intentar cambiar el estado del tipo.')

    return redirect('tipo_list')


class TallaListView(LoginRequiredMixin, ListView):
    model = Talla
    template_name = 'inventario/normalizacion_productos/talla_list.html' 
    context_object_name = 'tallas'
    ordering = ['nombre']
    
    def get_queryset(self):
        return Talla.objects.annotate(
            num_productos=Count('producto')
        ).order_by('nombre')
    

class TallaCreateView(LoginRequiredMixin, CreateView):
    model = Talla
    fields = ['nombre']  
    template_name = 'inventario/normalizacion_productos/talla_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('talla_create')
        return ctx
    
    def form_valid(self, form):
        form.instance.is_active = True
        self.object = form.save()
        return JsonResponse({'success': True})
    
    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })
    
    def get_success_url(self):
        return reverse_lazy('talla_list')


class TallaUpdateView(LoginRequiredMixin, UpdateView):
    model = Talla
    fields = ['nombre']
    template_name = 'inventario/normalizacion_productos/talla_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('talla_update', kwargs={'pk': self.object.pk})
        return ctx
    
    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })


# Cambiar el estado del talla
@login_required
def talla_toggle(request, pk):
    talla = get_object_or_404(Talla, pk=pk)

    try:
        talla.is_active = not talla.is_active
        talla.save()
        estado = 'activado' if talla.is_active else 'desactivado'
        messages.success(request, f'El talla "{talla.nombre}" ha sido {estado} correctamente.')

    except Exception as e:
        logger.error(f'Error al cambiar el estado del talla: {str(e)}', exc_info=True)
        messages.error(request, 'Ocurrió un error al intentar cambiar el estado del talla.')

    return redirect('talla_list')


class FitListView(LoginRequiredMixin, ListView):
    model = Fit
    template_name = 'inventario/normalizacion_productos/fit_list.html' 
    context_object_name = 'fits'
    ordering = ['nombre']
    
    def get_queryset(self):
        return Fit.objects.annotate(
            num_productos=Count('producto')
        ).order_by('nombre')
    

class FitCreateView(LoginRequiredMixin, CreateView):
    model = Fit
    fields = ['nombre']  
    template_name = 'inventario/normalizacion_productos/fit_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('fit_create')
        return ctx
    
    def form_valid(self, form):
        form.instance.is_active = True
        self.object = form.save()
        return JsonResponse({'success': True})
    
    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })
    
    def get_success_url(self):
        return reverse_lazy('fit_list')


class FitUpdateView(LoginRequiredMixin, UpdateView):
    model = Fit
    fields = ['nombre']
    template_name = 'inventario/normalizacion_productos/fit_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('fit_update', kwargs={'pk': self.object.pk})
        return ctx
    
    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })


# Cambiar el estado del fit
@login_required
def fit_toggle(request, pk):
    fit = get_object_or_404(Fit, pk=pk)

    try:
        fit.is_active = not fit.is_active
        fit.save()
        estado = 'activado' if fit.is_active else 'desactivado'
        messages.success(request, f'El fit "{fit.nombre}" ha sido {estado} correctamente.')

    except Exception as e:
        logger.error(f'Error al cambiar el estado del fit: {str(e)}', exc_info=True)
        messages.error(request, 'Ocurrió un error al intentar cambiar el estado del fit.')

    return redirect('fit_list')


# ========================================
# MÓDULO DE VENTAS
# ========================================


# listas de ventas y sus acciones
class VentaListView(LoginRequiredMixin, ListView):
    model = Venta
    template_name = 'inventario/ventas/venta_list.html'
    context_object_name = 'ventas'
    ordering = ['-fecha']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Permitir ver el switch de comisiones solo a admin/staff/grupo Administrador
        user = self.request.user
        can_view = (
            user.is_superuser or user.is_staff or user.groups.filter(name='Administrador').exists()
        )
        context['can_view_comisiones'] = can_view
        return context
    
class VentaAjaxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Parámetros básicos de DataTables
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        order_column_index = request.GET.get('order[0][column]', 0)
        order_direction = request.GET.get('order[0][dir]', 'asc')

        # Mapeo de columnas (debe coincidir con las columnas del template HTML)
        # 0: id, 1: fecha, 2: cliente, 3: total, 4: descuento, 5: estado, 6: entrega, 7: acciones (no ordenable)
        columns = ['id', 'fecha', 'cliente__nombre', 'total', 'descuento', 'pagado', 'entrega']
        
        # Mapeo de índices de DataTables a índices de columnas ordenables
        # DataTables envía índices basados en todas las columnas, pero solo algunas son ordenables
        orderable_columns = {
            0: 0,   # id
            1: 1,   # fecha
            2: 2,   # cliente
            3: 3,   # total
            4: 4,   # descuento
            5: 5,   # estado (pagado)
            6: 6,   # entrega
            7: None, # acciones (no ordenable)
        }
        
        # Validar que el índice de columna esté dentro del rango válido
        order_column_index = int(order_column_index)
        if order_column_index not in orderable_columns or orderable_columns[order_column_index] is None:
            order_column_index = 1  # Por defecto ordenar por fecha
            order_direction = 'desc'
        
        # Obtener el índice real de la columna ordenable
        real_column_index = orderable_columns.get(order_column_index, 1)
        if real_column_index is None:
            real_column_index = 1  # Por defecto fecha
        order_column = columns[real_column_index]
        if order_direction == 'desc':
            order_column = '-' + order_column

        # Parámetros de filtrado
        show_solo_no_pagadas = request.GET.get('show_solo_no_pagadas', 'false').lower() == 'true'
        show_solo_no_entregadas = request.GET.get('show_solo_no_entregadas', 'false').lower() == 'true'
        
        # Filtros adicionales
        id_filter = request.GET.get('id_filter', '')
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        cliente_filter = request.GET.get('cliente_filter', '')
        total_min = request.GET.get('total_min', '')
        total_max = request.GET.get('total_max', '')
        descuento_min = request.GET.get('descuento_min', '')
        descuento_max = request.GET.get('descuento_max', '')

        # Consulta base con select_related para optimización
        qs = Venta.objects.select_related('cliente', 'user')

        # Aplicar filtros de estado (solo mostrar las que NO están pagadas/entregadas)
        if show_solo_no_pagadas:
            qs = qs.filter(pagado=False)
        if show_solo_no_entregadas:
            qs = qs.filter(entrega=False)

        # Aplicar filtros adicionales
        if id_filter:
            qs = qs.filter(id__icontains=id_filter)
        
        if fecha_desde:
            try:
                fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d')
                qs = qs.filter(fecha__date__gte=fecha_desde_obj.date())
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d')
                qs = qs.filter(fecha__date__lte=fecha_hasta_obj.date())
            except ValueError:
                pass
        
        if cliente_filter:
            qs = qs.filter(
                Q(cliente__nombre__icontains=cliente_filter) |
                Q(cliente__apellido__icontains=cliente_filter) |
                Q(cliente__identificacion__icontains=cliente_filter)
            )
        
        if total_min:
            try:
                qs = qs.filter(total__gte=float(total_min))
            except ValueError:
                pass
        
        if total_max:
            try:
                qs = qs.filter(total__lte=float(total_max))
            except ValueError:
                pass
        
        if descuento_min:
            try:
                qs = qs.filter(descuento__gte=float(descuento_min))
            except ValueError:
                pass
        
        if descuento_max:
            try:
                qs = qs.filter(descuento__lte=float(descuento_max))
            except ValueError:
                pass

        # Búsqueda general
        if search_value:
            qs = qs.filter(
                Q(id__icontains=search_value) |
                Q(cliente__nombre__icontains=search_value) |
                Q(cliente__apellido__icontains=search_value) |
                Q(cliente__identificacion__icontains=search_value) |
                Q(total__icontains=search_value) |
                Q(descuento__icontains=search_value)
            )

        # Conteo total después de filtros
        total_filtered = qs.count()

        # Paginación y ordenamiento
        ventas = qs.order_by(order_column)[start:start + length]

        # Preparar datos para respuesta JSON
        data = []
        for venta in ventas:
            # Formatear fecha
            fecha_str = venta.fecha.strftime('%d/%m/%Y (%H:%M)') if venta.fecha else ''
            
            # Formatear nombre del cliente
            cliente_nombre = ''
            if venta.cliente:
                if venta.cliente.apellido:
                    cliente_nombre = f"{venta.cliente.nombre} {venta.cliente.apellido}"
                else:
                    cliente_nombre = venta.cliente.nombre

            data.append({
                'id': venta.id,
                'fecha': fecha_str,
                'cliente': escape(cliente_nombre),
                'total': str(venta.total),
                'descuento': str(venta.descuento),
                'estado': venta.get_estado_pago(),
                'entrega': venta.entrega,
            })

        return JsonResponse({
            'draw': draw,
            'recordsTotal': Venta.objects.count(),
            'recordsFiltered': total_filtered,
            'data': data
        })

class ComisionAjaxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Parámetros básicos de DataTables
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        order_column_index = request.GET.get('order[0][column]', 0)
        order_direction = request.GET.get('order[0][dir]', 'asc')

        # Mapeo de columnas para comisiones
        columns = ['user__username', 'fecha', 'id', 'total', 'comision', 'estado_comision']
        order_column = columns[int(order_column_index)]
        if order_direction == 'desc':
            order_column = '-' + order_column

        # Filtros específicos de comisiones
        estado_comision_filter = request.GET.get('estado_comision_filter', '')
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        comision_min = request.GET.get('comision_min', '')
        comision_max = request.GET.get('comision_max', '')
        vendedor_filter = request.GET.get('vendedor_filter', '')

        # Consulta base con select_related para optimización
        qs = Venta.objects.select_related('cliente', 'user')

        # Control de permisos por rol
        is_admin = (request.user.is_superuser or 
                   request.user.is_staff or 
                   request.user.groups.filter(name='Administrador').exists())
        
        if not is_admin:
            # Vendedores solo ven sus propias comisiones
            qs = qs.filter(user=request.user)

        # Aplicar filtros específicos de comisiones
        if estado_comision_filter:
            qs = qs.filter(estado_comision=estado_comision_filter)
        
        if fecha_desde:
            try:
                fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d')
                qs = qs.filter(fecha__date__gte=fecha_desde_obj.date())
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d')
                qs = qs.filter(fecha__date__lte=fecha_hasta_obj.date())
            except ValueError:
                pass
        
        if comision_min:
            try:
                qs = qs.filter(comision__gte=float(comision_min))
            except ValueError:
                pass
        
        if comision_max:
            try:
                qs = qs.filter(comision__lte=float(comision_max))
            except ValueError:
                pass
        
        if vendedor_filter:
            qs = qs.filter(
                Q(user__username__icontains=vendedor_filter) |
                Q(user__first_name__icontains=vendedor_filter) |
                Q(user__last_name__icontains=vendedor_filter)
            )

        # Búsqueda general
        if search_value:
            qs = qs.filter(
                Q(id__icontains=search_value) |
                Q(user__username__icontains=search_value) |
                Q(user__first_name__icontains=search_value) |
                Q(user__last_name__icontains=search_value) |
                Q(total__icontains=search_value) |
                Q(comision__icontains=search_value) |
                Q(estado_comision__icontains=search_value)
            )

        # Conteo total después de filtros
        total_filtered = qs.count()

        # Paginación y ordenamiento
        ventas = qs.order_by(order_column)[start:start + length]

        # Preparar datos para respuesta JSON
        data = []
        for venta in ventas:
            # Formatear fecha
            fecha_str = venta.fecha.strftime('%d/%m/%Y (%H:%M)') if venta.fecha else ''
            
            # Formatear nombre del vendedor
            vendedor_nombre = ''
            if venta.user:
                if venta.user.first_name and venta.user.last_name:
                    vendedor_nombre = f"{venta.user.first_name} {venta.user.last_name}"
                else:
                    vendedor_nombre = venta.user.username

            # Formatear estado de comisión con badge
            estado_badge = {
                'pendiente': '<span class="badge rounded-pill bg-warning">Pendiente</span>',
                'pagado': '<span class="badge rounded-pill bg-success">Pagado</span>',
                'denegado': '<span class="badge rounded-pill bg-danger">Denegado</span>'
            }.get(venta.estado_comision, f'<span class="badge rounded-pill bg-secondary">{venta.estado_comision}</span>')

            can_edit = (request.user.is_superuser or 
                       request.user.is_staff or 
                       request.user.groups.filter(name='administrador').exists())

            # Acciones (solo admins/staff)
            acciones_html = ''
            if can_edit:
                acciones_html = (
                    f'<div class="d-flex gap-2 align-items-center">'
                    f'  <select class="form-select form-select-sm estado-comision-select" data-venta-id="{venta.id}">' 
                    f'    <option value="pendiente" {"selected" if venta.estado_comision=="pendiente" else ""}>Pendiente</option>'
                    f'    <option value="pagado" {"selected" if venta.estado_comision=="pagado" else ""}>Pagado</option>'
                    f'    <option value="denegado" {"selected" if venta.estado_comision=="denegado" else ""}>Denegado</option>'
                    f'  </select>'
                    f'  <button class="btn btn-sm btn-primary btn-guardar-estado" data-venta-id="{venta.id}">Guardar</button>'
                    f'</div>'
                )

            data.append({
                'vendedor': escape(vendedor_nombre),
                'fecha': fecha_str,
                'venta_id': venta.id,
                'total_venta': str(venta.total),
                'comision': str(venta.comision),
                'estado_comision': estado_badge,
                'estado_comision_raw': venta.estado_comision,  # Para filtros
                'acciones': acciones_html,
            })

        return JsonResponse({
            'draw': draw,
            'recordsTotal': Venta.objects.count(),
            'recordsFiltered': total_filtered,
            'data': data
        })

class ComisionEstadoUpdateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        # Solo admin, staff o grupo administrador
        is_admin = (request.user.is_superuser or 
                   request.user.is_staff or 
                   request.user.groups.filter(name='administrador').exists())
        
        if not is_admin:
            return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)

        venta_id = request.POST.get('venta_id')
        nuevo_estado = request.POST.get('estado')

        if not venta_id or not nuevo_estado:
            return JsonResponse({'success': False, 'error': 'Parámetros inválidos'}, status=400)

        # Validar estado
        estados_validos = {choice[0] for choice in Venta.COMISION_ESTADOS}
        if nuevo_estado not in estados_validos:
            return JsonResponse({'success': False, 'error': 'Estado inválido'}, status=400)

        try:
            venta = Venta.objects.get(pk=venta_id)
        except Venta.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Venta no encontrada'}, status=404)

        venta.estado_comision = nuevo_estado
        venta.save(update_fields=['estado_comision'])
        return JsonResponse({'success': True})

class ComisionMarcarPagadasPeriodoView(LoginRequiredMixin, View):
    """Marca como pagadas todas las comisiones de ventas en el período dado"""
    def post(self, request, *args, **kwargs):
        # Solo admin, staff o grupo Administrador
        is_admin = (request.user.is_superuser or 
                   request.user.is_staff or 
                   request.user.groups.filter(name='Administrador').exists())
        if not is_admin:
            return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)

        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        if not start_date or not end_date:
            return JsonResponse({'success': False, 'error': 'Fechas requeridas'}, status=400)

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Formato de fecha inválido'}, status=400)

        # Actualizar ventas en el período con estado pendiente a pagado
        updated = Venta.objects.filter(
            fecha__date__range=[start_date, end_date],
            estado_comision='pendiente'
        ).update(estado_comision='pagado')

        return JsonResponse({'success': True, 'updated': updated})

class VentaDetailView(LoginRequiredMixin, DetailView):
    model = Venta
    template_name = 'inventario/ventas/venta_detail.html'
    context_object_name = 'venta'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener los detalles de venta con información de productos
        context['detalles_venta'] = self.object.detalleventa_set.select_related('producto').all()
        # Obtener los pagos asociados a la venta
        context['pagos'] = self.object.pago_set.select_related('metodo').all()
        
        # Calcular valores sin usar custom_filters
        total_pagado = sum(pago.monto_usd for pago in context['pagos'])
        context['total_pagado'] = total_pagado
        
        # Calcular faltante, pero evitar valores negativos
        faltante = float(self.object.total_ajustado - total_pagado)
        context['faltante_por_pagar'] = max(0, faltante)
        
        # Calcular subtotales de productos
        for detalle in context['detalles_venta']:
            detalle.subtotal_producto = float(detalle.precio_unitario_final * detalle.cantidad)
        
        return context


class VentaNuevoPagoView(LoginRequiredMixin, TemplateView):
    template_name = 'inventario/ventas/pago_form.html'
    
    def get(self, request, *args, **kwargs):
        venta = get_object_or_404(Venta, pk=self.kwargs['pk'])
        
        # Validar que la venta no esté cancelada
        if venta.cancelada:
            messages.error(request, 'Esta venta está cancelada. No se pueden agregar más pagos.')
            return redirect('venta_detail', pk=venta.pk)
        
        # Validar que la venta no esté completamente pagada
        if venta.pagado:
            messages.error(request, 'Esta venta ya está completamente pagada. No se pueden agregar más pagos.')
            return redirect('venta_detail', pk=venta.pk)
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venta = get_object_or_404(Venta, pk=self.kwargs['pk'])
        
        # Información de la venta
        context['venta'] = venta
        
        # Calcular pagos existentes en USD
        pagos_existentes = venta.pago_set.all()
        total_pagado_usd = sum(pago.monto_usd for pago in pagos_existentes)
        context['total_pagado'] = total_pagado_usd
        context['faltante_por_pagar'] = float(venta.total_ajustado - total_pagado_usd)
        
        # Métodos de pago disponibles
        context['metodos_pago'] = MetodoPago.objects.all()
        
        return context
    
    def post(self, request, *args, **kwargs):
        venta = get_object_or_404(Venta, pk=self.kwargs['pk'])
        
        # Validar que la venta no esté completamente pagada
        if venta.pagado:
            messages.error(request, 'Esta venta ya está completamente pagada. No se pueden agregar más pagos.')
            return redirect('venta_detail', pk=venta.pk)
        
        try:
            # Obtener datos del formulario
            pagos_data = json.loads(request.POST.get('pagos_data', '[]'))
            
            if not pagos_data:
                messages.error(request, 'No se enviaron datos de pagos.')
                return redirect('venta_nuevo_pago', pk=venta.pk)
            
            # Validar que los pagos no excedan el faltante
            pagos_existentes = venta.pago_set.all()
            total_pagado_actual = sum(pago.monto_usd for pago in pagos_existentes)
            faltante_por_pagar = float(venta.total_ajustado - total_pagado_actual)
            
            total_nuevos_pagos_usd = 0
            
            # Validar cada pago
            for pago_data in pagos_data:
                metodo_id = pago_data.get('metodo_pago')
                monto = Decimal(str(pago_data.get('monto_pagado', 0)))
                tasa = pago_data.get('tasa_cambio')
                
                if monto <= 0:
                    messages.error(request, 'Todos los montos deben ser mayores a 0.')
                    return redirect('venta_nuevo_pago', pk=venta.pk)
                
                metodo = get_object_or_404(MetodoPago, pk=metodo_id)
                
                # Calcular monto en USD
                if metodo.requiere_tasa:
                    if not tasa or Decimal(str(tasa)) <= 0:
                        messages.error(request, f'Debe proporcionar una tasa válida para {metodo.nombre}.')
                        return redirect('venta_nuevo_pago', pk=venta.pk)
                    tasa_decimal = Decimal(str(tasa))
                    monto_usd = monto / tasa_decimal
                else:
                    monto_usd = monto
                    tasa_decimal = None
                
                total_nuevos_pagos_usd += float(monto_usd)
            
            # Validar que no se exceda el faltante
            if total_nuevos_pagos_usd > faltante_por_pagar + 0.01:  # +0.01 para tolerancia de redondeo
                messages.error(request, f'Los pagos (${":.2f".format(total_nuevos_pagos_usd)}) exceden el faltante por pagar (${":.2f".format(faltante_por_pagar)}).')
                return redirect('venta_nuevo_pago', pk=venta.pk)
            
            # Crear los pagos y manejar saldo del cliente
            with transaction.atomic():
                for pago_data in pagos_data:
                    metodo_id = pago_data.get('metodo_pago')
                    monto = Decimal(str(pago_data.get('monto_pagado', 0)))
                    tasa = pago_data.get('tasa_cambio')
                    
                    metodo = get_object_or_404(MetodoPago, pk=metodo_id)
                    
                    # Calcular monto en USD y guardar
                    if metodo.requiere_tasa:
                        tasa_decimal = Decimal(str(tasa))
                        monto_usd = monto / tasa_decimal
                        monto_moneda = monto
                    else:
                        monto_usd = monto
                        monto_moneda = None
                        tasa_decimal = None
                    
                    # Si es pago con saldo, validar y descontar del saldo del cliente
                    if metodo.nombre == 'Saldo':
                        cliente = venta.cliente
                        if cliente.saldo < monto_usd:
                            messages.error(request, f'El cliente no tiene saldo suficiente. Saldo disponible: ${cliente.saldo:.2f}')
                            return redirect('venta_nuevo_pago', pk=venta.pk)
                        
                        cliente.saldo -= monto_usd
                        cliente.save()
                    
                    Pago.objects.create(
                        venta=venta,
                        metodo=metodo,
                        monto_usd=monto_usd,
                        monto_moneda=monto_moneda,
                        tasa=tasa_decimal
                    )
                
                # Actualizar estado de pago de la venta y manejar deudas correctamente
                total_pagado_previo = total_pagado_actual  # Lo que estaba pagado antes de los nuevos pagos
                total_pagado_final = sum(pago.monto_usd for pago in venta.pago_set.all())
                
                # Validar que no haya exceso de pago contra el total ajustado
                if total_pagado_final > venta.total_ajustado:
                    exceso_real = total_pagado_final - venta.total_ajustado
                    messages.error(request, f'No se puede registrar un exceso de pago de ${exceso_real:.2f}. El pago no puede exceder el total ajustado de la venta.')
                    return redirect('venta_nuevo_pago', pk=venta.pk)

                # Actualizar estado de la venta y recalcular deuda del cliente
                venta.actualizar_estado()
                venta.save()
                if venta.cliente:
                    venta.cliente.recalcular_deuda()
            
            # Mensaje de éxito con información del ajuste de deuda si aplica
            mensaje_base = f'Se registraron {len(pagos_data)} pago(s) exitosamente.'
            if total_pagado_previo < venta.total_ajustado and total_pagado_final >= venta.total_ajustado:
                mensaje_base += ' La deuda pendiente del cliente ha sido saldada.'
            elif total_pagado_previo < venta.total_ajustado and total_pagado_final < venta.total_ajustado:
                deuda_reducida = total_nuevos_pagos_usd
                mensaje_base += f' Se redujo la deuda del cliente en ${deuda_reducida:.2f}.'
            
            messages.success(request, mensaje_base)
            return redirect('venta_detail', pk=venta.pk)
            
        except Exception as e:
            messages.error(request, f'Error al procesar los pagos: {str(e)}')
            return redirect('venta_nuevo_pago', pk=venta.pk)


@login_required
def venta_toggle_entrega(request, pk):
    venta = get_object_or_404(Venta, pk=pk)

    try:
        venta.entrega = not venta.entrega
        venta.save()
        estado = 'entregada' if venta.entrega else 'pendiente de entrega'
        messages.success(request, f'La venta #{venta.id} ha sido marcada como {estado} correctamente.')
        
    except Exception as e:
        messages.error(request, 'Ocurrió un error al intentar cambiar el estado de entrega de la venta.')
        logger.error(f'Error al cambiar el estado de entrega de la venta: {str(e)}', exc_info=True)

    return redirect('venta_list')

# ========================================

# vistas para crear ventas
# Renderiza la vista de ventas
class VentaCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'inventario/ventas/venta_create.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context

# Obtiene todos los datos necesarios para el formulario de venta
@login_required
def ajax_venta_create(request):
    try:
        # Productos disponibles
        productos = Producto.objects.filter(
            is_active=True, 
            stock__gt=0
        ).select_related('marca', 'color', 'talla', 'tipo')
        
        productos_data = []
        for producto in productos:
            productos_data.append({
                'id': producto.id,
                'codigo': producto.codigo,
                'descripcion': producto.descripcion,
                'precio_venta': str(producto.precio_venta),
                'stock': producto.stock,
                'marca': producto.marca.nombre if producto.marca else '',
                'color': producto.color.nombre if producto.color else '',
                'talla': producto.talla.nombre if producto.talla else '',
                'tipo': producto.tipo.nombre if producto.tipo else '',
                'texto_completo': f"{producto.codigo} - {producto.descripcion}"
            })
        
        # Clientes activos
        clientes = Cliente.objects.filter(status=True)
        clientes_data = []
        for cliente in clientes:
            clientes_data.append({
                'id': cliente.id,
                'nombre': cliente.nombre,
                'identificacion': cliente.identificacion,
                'saldo': str(cliente.saldo),
                'deuda': str(cliente.deuda)
            })
        
        # Vendedores (usuarios activos)
        vendedores = CustomUser.objects.filter(is_active=True)
        vendedores_data = []
        for vendedor in vendedores:
            nombre_completo = f"{vendedor.first_name} {vendedor.last_name}".strip()
            if not nombre_completo:
                nombre_completo = vendedor.username
            vendedores_data.append({
                'id': vendedor.id,
                'username': vendedor.username,
                'nombre_completo': nombre_completo
            })
        
        # Métodos de pago con información de moneda
        metodos_pago = MetodoPago.objects.all()
        metodos_data = []
        for metodo in metodos_pago:
            metodos_data.append({
                'id': metodo.id,
                'nombre': metodo.nombre,
                'moneda': metodo.moneda,
                'requiere_tasa': metodo.requiere_tasa,
            })
        
        return JsonResponse({
            'success': True,
            'productos': productos_data,
            'clientes': clientes_data,
            'vendedores': vendedores_data,
            'metodos_pago': metodos_data
        })
    
    except Exception as e:
        logger.error(f'Error al obtener datos de venta: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Error al cargar datos'}, status=500)

# Guarda la venta completa con productos y pagos
@login_required
@csrf_exempt
def create_venta(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validaciones básicas
        if not data.get('productos'):
            return JsonResponse({'success': False, 'error': 'Debe agregar al menos un producto'})
        
        if not data.get('cliente_id'):
            return JsonResponse({'success': False, 'error': 'Debe seleccionar un cliente'})
        
        # Validar stock antes de procesar
        for producto_data in data['productos']:
            try:
                producto = Producto.objects.get(id=producto_data['producto_id'])
                if producto_data['cantidad'] > producto.stock:
                    return JsonResponse({
                        'success': False, 
                        'error': f'Stock insuficiente para {producto.descripcion}. Solo hay {producto.stock} unidades.'
                    })
            except Producto.DoesNotExist:
                return JsonResponse({'success': False, 'error': f'Producto con ID {producto_data["producto_id"]} no encontrado'})
        
        # Cálculos
        subtotal = sum(
            Decimal(str(p['precio_unitario'])) * int(p['cantidad']) 
            for p in data['productos']
        )
        
        descuento = Decimal(str(data.get('descuento', 0)))
        
        # Validar que el descuento no sea mayor al subtotal
        if descuento > subtotal:
            return JsonResponse({
                'success': False, 
                'error': f'El descuento (${":.2f".format(descuento)}) no puede ser mayor al subtotal (${":.2f".format(subtotal)}).'
            })
        
        total = subtotal - descuento
        
        comision_porcentaje = Decimal(str(data.get('comision_porcentaje', 10)))
        comision_monto = (total * comision_porcentaje) / 100
        
        # Calcular total pagado
        total_pagado = Decimal('0')
        if data.get('pagos'):
            for pago_data in data['pagos']:
                monto = Decimal(str(pago_data['monto_pagado']))
                tasa = Decimal(str(pago_data.get('tasa', 1))) if pago_data.get('tasa') else None
                
                # Obtener el método de pago para saber la moneda
                metodo = MetodoPago.objects.get(id=pago_data['metodo_id'])
                if metodo.moneda != 'USD' and tasa:
                    monto = monto / tasa
                total_pagado += monto
        
        pagado = total_pagado >= total
        
        # Calcular faltante por pagar (para nuevas ventas, total_ajustado = total)
        faltante_por_pagar = total - total_pagado if total_pagado < total else Decimal('0')
        
        # Convertir fecha a aware datetime
        import datetime
        fecha_str = data['fecha']
        if 'T' in fecha_str:
            fecha_dt = datetime.datetime.strptime(fecha_str, '%Y-%m-%dT%H:%M')
        else:
            fecha_dt = datetime.datetime.fromisoformat(fecha_str)
        fecha_aware = timezone.make_aware(fecha_dt)
        
        # Guardar en base de datos con transacción
        with transaction.atomic():
            venta = Venta.objects.create(
                cliente_id=data['cliente_id'],
                user_id=data.get('vendedor_id', request.user.id),
                fecha=fecha_aware,
                subtotal=subtotal,
                descuento=descuento,
                comision=comision_monto,
                total=total,
                total_ajustado=total,  # Para nuevas ventas, total_ajustado = total
                entrega=data.get('entrega', False),
                pagado=pagado
            )
            
            # Crear detalles de venta y actualizar stock
            for producto_data in data['productos']:
                producto = Producto.objects.get(id=producto_data['producto_id'])
                precio_unitario = Decimal(str(producto_data['precio_unitario']))
                cantidad = int(producto_data['cantidad'])
                
                # Calcular precio_unitario_final aplicando descuento proporcional
                precio_unitario_final = calcular_precio_unitario_final(
                    precio_unitario=precio_unitario,
                    cantidad=cantidad,
                    subtotal_venta=subtotal,
                    descuento_venta=descuento
                )
                
                detalle = DetalleVenta.objects.create(
                    venta=venta,
                    producto_id=producto_data['producto_id'],
                    precio_unitario=precio_unitario,
                    precio_unitario_final=precio_unitario_final,
                    cantidad=cantidad,
                    precio_compra=producto.precio_compra
                )
                
                # Actualizar stock
                producto.stock -= cantidad
                producto.save()
            
            # Crear pagos si existen (con conversión a USD) y manejar saldo del cliente
            cliente = Cliente.objects.get(id=data['cliente_id'])
            total_pago_con_saldo = Decimal('0')
            
            if data.get('pagos'):
                for pago_data in data['pagos']:
                    monto = Decimal(str(pago_data['monto_pagado']))
                    tasa = Decimal(str(pago_data.get('tasa', 1))) if pago_data.get('tasa') else None
                    
                    # Obtener el método de pago
                    metodo = MetodoPago.objects.get(id=pago_data['metodo_id'])
                    
                    # Calcular monto en USD y monto en moneda local
                    if metodo.requiere_tasa and tasa:
                        monto_usd = monto / tasa
                        monto_moneda = monto
                    else:
                        monto_usd = monto
                        monto_moneda = None
                        tasa = None
                    
                    # Si es pago con saldo, descontar del saldo del cliente
                    if metodo.nombre == 'Saldo':
                        # Validar que el cliente tenga saldo suficiente
                        if cliente.saldo < monto_usd:
                            return JsonResponse({
                                'success': False, 
                                'error': f'El cliente no tiene saldo suficiente. Saldo disponible: ${cliente.saldo:.2f}'
                            })
                        
                        cliente.saldo -= monto_usd
                        cliente.save()  # Guardar el saldo modificado
                        total_pago_con_saldo += monto_usd
                    
                    Pago.objects.create(
                        venta=venta,
                        monto_usd=monto_usd,
                        monto_moneda=monto_moneda,
                        tasa=tasa,
                        metodo=metodo
                    )
            
            # Calcular total realmente pagado (recalcular después de crear todos los pagos)
            total_pagado_final = sum(pago.monto_usd for pago in venta.pago_set.all())
            
            # Validar que no haya exceso de pago (usando total_ajustado)
            if total_pagado_final > venta.total_ajustado:
                exceso = total_pagado_final - venta.total_ajustado
                return JsonResponse({
                    'success': False, 
                    'error': f'No se puede registrar un exceso de pago de ${exceso:.2f}. El pago no puede exceder el total ajustado de la venta.'
                })
            
            # Actualizar estado de la venta y recalcular deuda del cliente
            venta.actualizar_estado()
            venta.save()
            if cliente:
                cliente.recalcular_deuda()
        
        # Preparar mensaje de respuesta
        mensaje_base = 'Venta registrada exitosamente'
        
        return JsonResponse({
            'success': True,
            'venta_id': venta.id,
            'message': mensaje_base
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f'Error al guardar venta: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Error al guardar la venta'}, status=500)

# Valida stock para múltiples productos de una vez
@login_required
def validar_stock_batch(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        productos_validacion = data.get('productos', [])
        
        resultados = []
        for item in productos_validacion:
            producto_id = item['producto_id']
            cantidad = int(item['cantidad'])
            
            try:
                producto = Producto.objects.get(id=producto_id, is_active=True)
                stock_suficiente = cantidad <= producto.stock
                
                resultados.append({
                    'producto_id': producto_id,
                    'stock_disponible': producto.stock,
                    'cantidad_solicitada': cantidad,
                    'stock_suficiente': stock_suficiente,
                    'mensaje': f'Stock disponible: {producto.stock}' if stock_suficiente else f'Stock insuficiente. Solo hay {producto.stock} unidades.'
                })
            except Producto.DoesNotExist:
                resultados.append({
                    'producto_id': producto_id,
                    'error': 'Producto no encontrado'
                })
        
        return JsonResponse({'success': True, 'resultados': resultados})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f'Error al validar stock: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Error al validar stock'}, status=500)


# ========================================
# MÓDULO DE DEVOLUCIONES
# ========================================


class DevolucionListView(LoginRequiredMixin, ListView):
    model = Devolucion
    template_name = 'inventario/devoluciones/devolucion_list.html'
    context_object_name = 'devoluciones'
    ordering = ['-fecha']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Lista de Devoluciones'
        return context


class DevolucionCreateView(LoginRequiredMixin, View):
    template_name = 'inventario/devoluciones/devolucion_form.html'
    

    def get(self, request, venta_id):
        venta = get_object_or_404(Venta, id=venta_id)
        detalles_venta = venta.detalleventa_set.select_related('producto').all()
        
        # Calcular cantidad ya devuelta por producto
        for detalle in detalles_venta:
            cantidad_devuelta = DetalleDevolucion.objects.filter(
                id_detalle_venta=detalle
            ).aggregate(total=Sum('cantidad_producto'))['total'] or 0
            detalle.cantidad_disponible = detalle.cantidad - cantidad_devuelta
        
        context = {
            'venta': venta,
            'detalles_venta': detalles_venta,
            'cliente': venta.cliente,
            'total_venta': venta.total,
            'total_pagado': venta.get_total_pagado(),
            'title': f'Crear Devolución - Venta #{venta.id}'
        }
        return render(request, self.template_name, context)

    def post(self, request, venta_id):
        venta = get_object_or_404(Venta, id=venta_id)
        
        try:
            with transaction.atomic():
                # Validar reembolso antes de crear la devolución
                reembolsado = request.POST.get('reembolsado', '').strip()
                if reembolsado:
                    try:
                        reembolsado = Decimal(reembolsado)
                        total_pagado = venta.get_total_pagado()
                        if reembolsado > total_pagado:
                            messages.error(request, f'El monto reembolsado no puede ser mayor al total pagado de la venta (${total_pagado})')
                            return redirect('devolucion_create', venta_id=venta_id)
                    except (ValueError, TypeError):
                        messages.error(request, 'El monto reembolsado debe ser un número válido')
                        return redirect('devolucion_create', venta_id=venta_id)
                else:
                    reembolsado = None
                
                # Crear la devolución primero (sin total, se calculará después)
                devolucion = Devolucion(
                    id_venta=venta,
                    motivo=request.POST.get('motivo', '').strip() or None,
                    reembolsado=reembolsado,
                    total=Decimal('0')  # Se calculará después
                )
                # Guardar sin ejecutar el método save() completo para evitar el error
                devolucion.save_simple()  # Esto le asigna el ID sin ejecutar lógica adicional
                
                # Procesar detalles de devolución
                detalles_creados = False
                for detalle_venta in venta.detalleventa_set.all():
                    cantidad_devuelta = request.POST.get(f'cantidad_devuelta_{detalle_venta.id}', '0')
                    cantidad_danada = request.POST.get(f'cantidad_danada_{detalle_venta.id}', '0')
                    
                    cantidad_devuelta = int(cantidad_devuelta) if cantidad_devuelta else 0
                    cantidad_danada = int(cantidad_danada) if cantidad_danada else 0
                    
                    # Validar que no se devuelva más de lo disponible
                    cantidad_ya_devuelta = DetalleDevolucion.objects.filter(
                        id_detalle_venta=detalle_venta
                    ).aggregate(total=Sum('cantidad_producto'))['total'] or 0
                    
                    cantidad_disponible = detalle_venta.cantidad - cantidad_ya_devuelta
                    
                    if cantidad_devuelta + cantidad_danada > cantidad_disponible:
                        messages.error(request, f'No se puede devolver más de {cantidad_disponible} unidades del producto {detalle_venta.producto.codigo}')
                        return redirect('devolucion_create', venta_id=venta_id)
                    
                    # Crear detalle para productos devueltos en buen estado
                    if cantidad_devuelta > 0:
                        DetalleDevolucion.objects.create(
                            id_devolucion=devolucion,
                            id_detalle_venta=detalle_venta,
                            cantidad_producto=cantidad_devuelta,
                            precio_compra=detalle_venta.precio_compra,
                            danado=False
                        )
                        detalles_creados = True
                    
                    # Crear detalle para productos devueltos dañados
                    if cantidad_danada > 0:
                        DetalleDevolucion.objects.create(
                            id_devolucion=devolucion,
                            id_detalle_venta=detalle_venta,
                            cantidad_producto=cantidad_danada,
                            precio_compra=detalle_venta.precio_compra,
                            danado=True
                        )
                        detalles_creados = True
                
                if not detalles_creados:
                    devolucion.delete()
                    messages.error(request, 'Debe seleccionar al menos un producto para devolver')
                    return redirect('devolucion_create', venta_id=venta_id)
                
                # Recalcular el total de la devolución
                devolucion.total = devolucion.calcular_total()
                # Validar que el reembolso no sea mayor al total calculado
                if reembolsado and reembolsado > devolucion.total:
                    devolucion.delete()
                    messages.error(request, f'El monto reembolsado (${reembolsado}) no puede ser mayor al total de la devolución (${devolucion.total})')
                    return redirect('devolucion_create', venta_id=venta_id)
                devolucion.save_simple()  # Guardar solo el total sin ejecutar lógica adicional
                
                # Recalcular total_ajustado de la venta manualmente
                venta.recalcular_total_ajustado()
                # Como usamos save_simple() y no se ejecuta el hook del modelo Devolucion,
                # recalculamos explícitamente la deuda del cliente
                if venta.cliente:
                    venta.cliente.recalcular_deuda()
                
                messages.success(request, f'Devolución #{devolucion.id} creada exitosamente')
                return redirect('devolucion_detail', pk=devolucion.id)
                
        except ValidationError as e:
            if hasattr(e, 'message_dict'):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f'Error en {field}: {error}')
            else:
                messages.error(request, f'Error de validación: {str(e)}')
            return redirect('devolucion_create', venta_id=venta_id)
        except Exception as e:
            messages.error(request, f'Error al crear la devolución: {str(e)}')
            return redirect('devolucion_create', venta_id=venta_id)


class DevolucionAjaxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            # Parámetros básicos de DataTables
            draw = int(request.GET.get('draw', 1))
            start = int(request.GET.get('start', 0))
            length = int(request.GET.get('length', 10))
            search_value = request.GET.get('search[value]', '')
            order_column_index = request.GET.get('order[0][column]', 0)
            order_direction = request.GET.get('order[0][dir]', 'asc')

            # Mapeo de columnas según los nuevos requerimientos
            columns = ['id', 'fecha', 'id_venta__id', 'total', 'id_venta__cliente__nombre', 'total_productos']
            if int(order_column_index) < len(columns):
                order_column = columns[int(order_column_index)]
                if order_direction == 'desc':
                    order_column = '-' + order_column
            else:
                order_column = '-fecha'  # Ordenamiento por defecto

            # Parámetros de filtrado
            id_filter = request.GET.get('id_filter', '')
            fecha_desde = request.GET.get('fecha_desde', '')
            fecha_hasta = request.GET.get('fecha_hasta', '')
            cliente_filter = request.GET.get('cliente_filter', '')
            venta_filter = request.GET.get('venta_filter', '')
            monto_min = request.GET.get('monto_min', '')
            monto_max = request.GET.get('monto_max', '')

            # Consulta base con select_related para optimización
            qs = Devolucion.objects.select_related('id_venta__cliente').prefetch_related('detalles')

            # Aplicar filtros por columnas
            if id_filter:
                try:
                    # Convertir a entero para búsqueda exacta
                    id_exacto = int(id_filter)
                    qs = qs.filter(id=id_exacto)
                except (ValueError, TypeError):
                    # Si no es un número válido, no aplicar filtro
                    pass
            if fecha_desde:
                qs = qs.filter(fecha__gte=fecha_desde)
            if fecha_hasta:
                qs = qs.filter(fecha__lte=fecha_hasta)
            if cliente_filter:
                qs = qs.filter(id_venta__cliente__nombre__icontains=cliente_filter)
            if venta_filter:
                try:
                    # Convertir a entero para búsqueda exacta
                    venta_exacta = int(venta_filter)
                    qs = qs.filter(id_venta__id=venta_exacta)
                except (ValueError, TypeError):
                    # Si no es un número válido, no aplicar filtro
                    pass
            if monto_min:
                try:
                    qs = qs.filter(total__gte=float(monto_min))
                except (ValueError, TypeError):
                    pass
            if monto_max:
                try:
                    qs = qs.filter(total__lte=float(monto_max))
                except (ValueError, TypeError):
                    pass

            # Búsqueda general
            if search_value:
                qs = qs.filter(
                    Q(id__icontains=search_value) |
                    Q(id_venta__cliente__nombre__icontains=search_value) |
                    Q(id_venta__id__icontains=search_value) |
                    Q(motivo__icontains=search_value)
                )

            # Contar total de registros antes de paginación
            total_records = qs.count()

            # Aplicar ordenamiento
            qs = qs.order_by(order_column)

            # Aplicar paginación
            qs = qs[start:start + length]

            # Preparar datos para DataTables
            data = []
            for devolucion in qs:
                # Calcular total de productos devueltos
                total_productos = sum(detalle.cantidad_producto for detalle in devolucion.detalles.all())
                
                data.append({
                    'id': devolucion.id,
                    'fecha': devolucion.fecha.strftime('%d/%m/%Y'),
                    'venta_id': devolucion.id_venta.id,
                    'total': float(devolucion.total),
                    'cliente': f"{devolucion.id_venta.cliente.nombre} {devolucion.id_venta.cliente.apellido or ''}".strip() if devolucion.id_venta.cliente else 'N/A',
                    'total_productos': total_productos
                })

            return JsonResponse({
                'draw': draw,
                'recordsTotal': total_records,
                'recordsFiltered': total_records,
                'data': data
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en DevolucionAjaxView: {str(e)}")
            return JsonResponse({
                'draw': 1,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': [],
                'error': str(e)
            }, status=500)


class DevolucionDetailView(LoginRequiredMixin, DetailView):
    model = Devolucion
    template_name = 'inventario/devoluciones/devolucion_detail.html'
    context_object_name = 'devolucion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        devolucion = self.get_object()
        
        # Agregar información adicional al contexto
        context['venta'] = devolucion.id_venta
        detalles = devolucion.detalles.select_related('id_detalle_venta__producto').all()
        
        # Calcular subtotal para cada detalle y total de productos
        total_productos = 0
        for detalle in detalles:
            detalle.subtotal = detalle.id_detalle_venta.precio_unitario_final * detalle.cantidad_producto
            total_productos += detalle.cantidad_producto
        
        context['detalles'] = detalles
        context['cliente'] = devolucion.id_venta.cliente
        context['total_pagado'] = devolucion.id_venta.get_total_pagado()
        context['total_productos'] = total_productos
        
        # Calcular saldo pendiente
        saldo_pendiente = devolucion.id_venta.total_ajustado - devolucion.id_venta.get_total_pagado()
        context['saldo_pendiente'] = max(Decimal('0'), saldo_pendiente)
        
        return context


# ========================================
# MÓDULO DE CLIENTES
# ========================================


class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = 'inventario/clientes/cliente_list.html'
    context_object_name = 'clientes'
    ordering = ['nombre']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(nombre__icontains=search_query) |
                Q(apellido__icontains=search_query) |
                Q(identificacion__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(telefono__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Lista de Clientes'
        # Agregar datos para los filtros
        context['tallas'] = Talla.objects.filter(is_active=True).order_by('nombre')
        
        # Obtener datos únicos para filtros dinámicos
        clientes = Cliente.objects.all()
        context['nombres_clientes'] = clientes.values_list('nombre', flat=True).distinct().order_by('nombre')
        context['apellidos_clientes'] = clientes.values_list('apellido', flat=True).distinct().order_by('apellido')
        context['identificaciones_clientes'] = clientes.values_list('identificacion', flat=True).distinct().order_by('identificacion')
        context['emails_clientes'] = clientes.values_list('email', flat=True).distinct().order_by('email')
        context['telefonos_clientes'] = clientes.values_list('telefono', flat=True).distinct().order_by('telefono')
        
        return context


class ClienteAjaxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Parámetros básicos de DataTables
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        order_column_index = request.GET.get('order[0][column]', 0)
        order_direction = request.GET.get('order[0][dir]', 'asc')

        # Mapeo de columnas
        columns = ['nombre', 'identificacion', 'email', 'telefono', 'saldo', 'status']
        if int(order_column_index) < len(columns):
            order_column = columns[int(order_column_index)]
            if order_direction == 'desc':
                order_column = '-' + order_column
        else:
            order_column = 'nombre'  # Ordenamiento por defecto

        # Parámetros de filtrado
        show_inactivos = request.GET.get('show_inactivos', 'false').lower() == 'true'
        show_con_saldo = request.GET.get('show_con_saldo', 'false').lower() == 'true'
        tallas = request.GET.getlist('tallas[]')
        saldo_min = request.GET.get('saldo_min')
        saldo_max = request.GET.get('saldo_max')
        
        # Nuevos filtros por columnas
        nombres = request.GET.getlist('nombres[]')
        apellidos = request.GET.getlist('apellidos[]')
        identificaciones = request.GET.getlist('identificaciones[]')
        emails = request.GET.getlist('emails[]')
        telefonos = request.GET.getlist('telefonos[]')

        # Consulta base con select_related para optimización
        qs = Cliente.objects.prefetch_related('tallas')

        # Aplicar filtros de estado
        if not show_inactivos:
            qs = qs.filter(status=True)
        if show_con_saldo:
            qs = qs.filter(saldo__gt=0)

        # Aplicar filtros por columnas
        if nombres:
            qs = qs.filter(nombre__in=nombres)
        if apellidos:
            qs = qs.filter(apellido__in=apellidos)
        if identificaciones:
            qs = qs.filter(identificacion__in=identificaciones)
        if emails:
            qs = qs.filter(email__in=emails)
        if telefonos:
            qs = qs.filter(telefono__in=telefonos)
        if tallas:
            qs = qs.filter(tallas__nombre__in=tallas)
        if saldo_min:
            qs = qs.filter(saldo__gte=float(saldo_min))
        if saldo_max:
            qs = qs.filter(saldo__lte=float(saldo_max))

        # Búsqueda general
        if search_value:
            qs = qs.filter(
                Q(nombre__icontains=search_value) |
                Q(apellido__icontains=search_value) |
                Q(identificacion__icontains=search_value) |
                Q(email__icontains=search_value) |
                Q(telefono__icontains=search_value)
            )

        # Conteo total después de filtros
        total_filtered = qs.distinct().count()

        # Paginación y ordenamiento
        clientes = qs.distinct().order_by(order_column)[start:start + length]

        # Preparar datos para respuesta JSON
        data = []
        for cliente in clientes:
            # Obtener tallas como string
            tallas_str = ', '.join([talla.nombre for talla in cliente.tallas.all()])
            
            data.append({
                'id': cliente.id,
                'nombre': escape(f"{cliente.nombre}{' ' + cliente.apellido if cliente.apellido else ''}"),
                'identificacion': cliente.identificacion,
                'email': escape(cliente.email) if cliente.email else '',
                'telefono': escape(cliente.telefono) if cliente.telefono else '',
                'saldo': str(cliente.saldo),
                'deuda': str(cliente.deuda),
                'status': cliente.status,
                'tallas': tallas_str,
            })

        return JsonResponse({
            'draw': draw,
            'recordsTotal': Cliente.objects.count(),
            'recordsFiltered': total_filtered,
            'data': data
        })


class ClienteDetailView(LoginRequiredMixin, DetailView):
    model = Cliente
    template_name = 'inventario/clientes/cliente_detail.html'
    context_object_name = 'cliente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Detalle del Cliente: {self.object.nombre}'
        return context


class ClienteVentasAjaxView(LoginRequiredMixin, View):
    def get(self, request, cliente_id, *args, **kwargs):
        # Verificar que el cliente existe
        try:
            cliente = Cliente.objects.get(pk=cliente_id)
        except Cliente.DoesNotExist:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

        # Parámetros básicos de DataTables
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        order_column_index = request.GET.get('order[0][column]', 0)
        order_direction = request.GET.get('order[0][dir]', 'asc')

        # Mapeo de columnas
        columns = ['fecha', 'subtotal', 'descuento', 'total', 'pagado', 'entrega']
        order_column = columns[int(order_column_index)]
        if order_direction == 'desc':
            order_column = '-' + order_column

        # Parámetros de filtrado
        show_pendientes = request.GET.get('show_pendientes', 'false').lower() == 'true'
        show_entregadas = request.GET.get('show_entregadas', 'false').lower() == 'true'
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        monto_min = request.GET.get('monto_min')
        monto_max = request.GET.get('monto_max')

        # Consulta base
        qs = Venta.objects.filter(cliente=cliente)

        # Aplicar filtros de estado
        if show_pendientes:
            qs = qs.filter(pagado=False)
        if show_entregadas:
            qs = qs.filter(entrega=True)

        # Aplicar filtros de fecha
        if fecha_desde:
            qs = qs.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__date__lte=fecha_hasta)

        # Aplicar filtros de monto
        if monto_min:
            qs = qs.filter(total__gte=float(monto_min))
        if monto_max:
            qs = qs.filter(total__lte=float(monto_max))

        # Búsqueda general
        if search_value:
            qs = qs.filter(
                Q(id__icontains=search_value) |
                Q(fecha__icontains=search_value) |
                Q(subtotal__icontains=search_value) |
                Q(descuento__icontains=search_value) |
                Q(total__icontains=search_value)
            )

        # Conteo total después de filtros
        total_filtered = qs.count()

        # Paginación y ordenamiento
        ventas = qs.order_by(order_column)[start:start + length]

        # Preparar datos para respuesta JSON
        data = []
        for venta in ventas:
            data.append({
                'id': venta.id,
                'fecha': venta.fecha.strftime('%d/%m/%Y %H:%M'),
                'fecha_iso': venta.fecha.isoformat(),
                'subtotal': str(venta.subtotal),
                'descuento': str(venta.descuento),
                'total': str(venta.total),
                'pagado': venta.get_estado_pago(),
                'entrega': venta.entrega,
            })

        return JsonResponse({
            'draw': draw,
            'recordsTotal': Venta.objects.filter(cliente=cliente).count(),
            'recordsFiltered': total_filtered,
            'data': data
        })


class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    template_name = 'inventario/clientes/cliente_form.html'
    form_class = ClienteForm
    success_url = reverse_lazy('cliente_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Registrar Nuevo Cliente'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Personalizar widgets si es necesario
        return form

    def form_valid(self, form):
        try:
            # Guardar el cliente con commit=False para manejar relaciones many-to-many
            cliente = form.save(commit=False)
            cliente.save()  # Guardar el cliente primero
            
            # Marcar que el siguiente save() es para relaciones many-to-many
            cliente._skip_edit_signal = True
            
            # Guardar las relaciones many-to-many
            form.save_m2m()
            
            messages.success(self.request, 'Cliente creado exitosamente.')
            
            # Manejar diferentes acciones
            action = self.request.POST.get('action', 'save')
            if action == 'save_and_add_new':
                return redirect('cliente_create')
            elif action == 'save_and_continue':
                return redirect('cliente_update', pk=cliente.pk)
            else:
                return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'Error al crear el cliente: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrija los errores en el formulario.')
        return super().form_invalid(form)


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Cliente
    template_name = 'inventario/clientes/cliente_form.html'
    form_class = ClienteForm
    success_url = reverse_lazy('cliente_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Cliente'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Personalizar widgets si es necesario
        return form

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, 'Cliente actualizado exitosamente.')
            
            # Manejar diferentes acciones
            action = self.request.POST.get('action', 'save')
            if action == 'save_and_add_new':
                return redirect('cliente_create')
            elif action == 'save_and_continue':
                return redirect('cliente_update', pk=self.object.pk)
            else:
                return response
        except Exception as e:
            messages.error(self.request, f'Error al actualizar el cliente: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrija los errores en el formulario.')
        return super().form_invalid(form)


class ClienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Cliente
    template_name = 'inventario/clientes/cliente_confirm_delete.html'
    success_url = reverse_lazy('cliente_list')

    def delete(self, request, *args, **kwargs):
        try:
            messages.success(request, 'Cliente eliminado exitosamente.')
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'Error al eliminar el cliente: {str(e)}')
            return redirect('cliente_list')


class ToggleClienteStatusView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventario.change_cliente'

    def post(self, request, pk, *args, **kwargs):
        cliente = get_object_or_404(Cliente, pk=pk)
        password = request.POST.get('password')

        if not password or not request.user.check_password(password):
            messages.error(request, "Contraseña incorrecta. No se realizó ningún cambio.")
            return redirect('cliente_list')

        try:
            nuevo_status = not cliente.status
            # Usar update() para evitar signals de edición
            Cliente.objects.filter(id=cliente.id).update(status=nuevo_status)
            
            status_text = "activado" if nuevo_status else "desactivado"
            messages.success(request, f'Cliente {status_text} exitosamente.')
            
        except Exception as e:
            messages.error(request, f'Error al cambiar el estado del cliente: {str(e)}')
        
        return redirect('cliente_list')


@require_http_methods(["POST"])
@login_required
def cliente_toggle(request, pk):
    try:
        cliente = Cliente.objects.get(pk=pk)
        nuevo_status = not cliente.status
        # Usar update() para evitar signals de edición
        Cliente.objects.filter(id=cliente.id).update(status=nuevo_status)
        
        status_text = "activado" if nuevo_status else "desactivado"
        messages.success(request, f'Cliente {status_text} exitosamente.')
        
        return JsonResponse({
            'success': True,
            'message': f'Cliente {status_text} exitosamente',
            'status': cliente.status
        })
    except Cliente.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cliente no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al cambiar el estado: {str(e)}'
        }, status=500)

class ReporteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista principal para reportes"""
    template_name = 'inventario/reportes/reporte.html'
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get_context_data(self, **kwargs):
        from decimal import Decimal
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reportes'
        
        # Obtener fechas por defecto (último mes)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Obtener parámetros de la URL si existen
        start_date_param = self.request.GET.get('start_date')
        end_date_param = self.request.GET.get('end_date')
        
        if start_date_param and end_date_param:
            try:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
            except ValueError:
                pass  # Usar fechas por defecto si hay error
        
        context['start_date'] = start_date
        context['end_date'] = end_date
        
        # Calcular métricas directamente en la vista
        ventas_periodo = Venta.objects.filter(fecha__date__range=[start_date, end_date])
        
        # Métricas principales
        nro_ventas_totales = ventas_periodo.count()
        gasto_total_clientes = ventas_periodo.aggregate(total=Sum('total'))['total'] or 0
        gasto_medio_clientes = ventas_periodo.aggregate(promedio=Avg('total'))['promedio'] or 0
        
        # ========================================
        # CÁLCULO DE BENEFICIOS MEJORADO
        # ========================================
        
        # 1. INGRESOS: Sumar pagos que NO son con método "Saldo"
        ingresos = Pago.objects.filter(
            venta__in=ventas_periodo
        ).exclude(
            metodo__nombre='Saldo'
        ).aggregate(
            total_ingresos=Sum('monto_usd')
        )['total_ingresos'] or Decimal('0')
        
        # 2. GASTOS: Calcular todos los componentes
        from decimal import Decimal, ROUND_HALF_UP
        from datetime import time
        start_datetime = datetime.combine(start_date, time.min)
        end_datetime = datetime.combine(end_date, time.max)
        
        # 2.1 Coste_productos: sum(detalleventa.precio_compra x cantidad) - sum(detalledevolucion.precio_coste x cantidad where danada=False)
        coste_productos = Decimal('0')
        for venta in ventas_periodo:
            # Sumar costos de productos vendidos
            for detalle in venta.detalleventa_set.all():
                coste_productos += detalle.precio_compra * detalle.cantidad
            
            # Restar costos de productos devueltos NO dañados
            for devolucion in venta.devoluciones.all():
                for detalle_dev in devolucion.detalles.filter(danado=False):
                    coste_productos -= detalle_dev.precio_compra * detalle_dev.cantidad_producto
        
        # 2.2 Comisiones: sum(venta.comision where estado_comision == 'pagado')
        ventas_comisiones_pagadas = Venta.objects.filter(
            fecha__gte=start_datetime,
            fecha__lte=end_datetime,
            estado_comision='pagado'
        )
        
        comisiones = Decimal('0')
        for venta in ventas_comisiones_pagadas:
            if venta.comision > 0:
                comisiones += venta.comision
            else:
                # Si la comisión no está calculada, calcularla al vuelo
                comision_calculada = (venta.total * Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                comisiones += comision_calculada
                # Actualizar la comisión en la base de datos
                venta.comision = comision_calculada
                venta.save(update_fields=['comision'])
        
        # 2.3 Gastos_Generales: sum(gastos_administrativos.monto)
        gastos_administrativos = GastoAdministrativo.objects.filter(
            fecha__range=[start_date, end_date],
            activo=True
        ).aggregate(
            total_gastos=Sum('monto')
        )['total_gastos'] or Decimal('0')
        
        # 2.4 Devoluciones: sum(devolucion.reembolsado)
        devoluciones_reembolsadas = Devolucion.objects.filter(
            id_venta__in=ventas_periodo,
            reembolsado__isnull=False
        ).aggregate(
            total_reembolsos=Sum('reembolsado')
        )['total_reembolsos'] or Decimal('0')
        
        # 2.5 Mermas: sum(merma.precio_compra x cantidad where origen == 'tienda')
        mermas = Decimal('0')
        for merma in Merma.objects.filter(
            fecha__range=[start_date, end_date],
            origen='tienda'
        ):
            mermas += merma.total_costo
        
        # Calcular gastos totales
        gastos_totales = coste_productos + comisiones + gastos_administrativos + devoluciones_reembolsadas + mermas
        
        # Beneficios = Ingresos - Gastos
        beneficios_netos = ingresos - gastos_totales
        
        # Calcular sumatoria de deudas de clientes
        total_deudas_clientes = Cliente.objects.aggregate(
            total_deudas=Sum('deuda')
        )['total_deudas'] or Decimal('0')
        
        # Calcular cantidad total de productos vendidos
        total_productos_vendidos = 0
        for venta in ventas_periodo:
            for detalle in venta.detalleventa_set.all():
                total_productos_vendidos += detalle.cantidad
        
        # Calcular total de productos en stock
        total_productos_stock = Producto.objects.aggregate(
            total_stock=Sum('stock')
        )['total_stock'] or 0
        
        # Calcular cantidad de productos devueltos
        cantidad_productos_devueltos = 0
        devoluciones_periodo = Devolucion.objects.filter(
            fecha__range=[start_date, end_date]
        )
        for devolucion in devoluciones_periodo:
            for detalle in devolucion.detalles.all():
                cantidad_productos_devueltos += detalle.cantidad_producto
        
        # Calcular valor promedio de productos (precio de venta)
        valor_promedio_productos = Producto.objects.aggregate(
            promedio_precio=Avg('precio_venta')
        )['promedio_precio'] or Decimal('0')
        
        # Calcular promedio de precio de compra de productos
        promedio_precio_compra = Producto.objects.aggregate(
            promedio_compra=Avg('precio_compra')
        )['promedio_compra'] or Decimal('0')
        
        # Calcular gasto promedio por cliente
        gasto_promedio_cliente = gasto_total_clientes / nro_ventas_totales if nro_ventas_totales > 0 else Decimal('0')
        
        # Calcular total de productos en merma
        total_productos_merma = Merma.objects.filter(
            fecha__range=[start_date, end_date]
        ).aggregate(
            total_cantidad=Sum('cantidad')
        )['total_cantidad'] or 0
        
        # Datos para gráficos - Ventas por usuario con métricas detalladas
        ventas_por_usuario = []
        usuarios_con_ventas = ventas_periodo.values('user__username').distinct()
        
        for usuario_data in usuarios_con_ventas:
            username = usuario_data['user__username']
            
            # Obtener ventas del usuario en el período
            ventas_usuario = ventas_periodo.filter(user__username=username)
            
            # Calcular métricas básicas
            total_ventas = ventas_usuario.count()
            total_venta_bruto = ventas_usuario.aggregate(
                total=Sum('total')
            )['total'] or Decimal('0')
            
            # Calcular ingresos reales (excluyendo pagos con método "Saldo")
            ingresos_reales_usuario = Decimal('0')
            for venta in ventas_usuario:
                pagos_reales = Pago.objects.filter(
                    venta=venta
                ).exclude(
                    metodo__nombre='Saldo'
                )
                for pago in pagos_reales:
                    ingresos_reales_usuario += pago.monto_usd
            
            # Calcular productos vendidos por el usuario
            productos_vendidos_usuario = 0
            for venta in ventas_usuario:
                for detalle in venta.detalleventa_set.all():
                    productos_vendidos_usuario += detalle.cantidad
            
            # Calcular comisiones pagadas del usuario
            comisiones_pagadas_usuario = ventas_usuario.filter(
                estado_comision='pagado'
            ).aggregate(
                total_comisiones=Sum('comision')
            )['total_comisiones'] or Decimal('0')
            
            # Calcular promedio por venta
            promedio_por_venta = ingresos_reales_usuario / total_ventas if total_ventas > 0 else Decimal('0')
            
            ventas_por_usuario.append({
                'user__username': username,
                'total_ventas': total_ventas,
                'ingreso_total': total_venta_bruto,
                'ingresos_reales': ingresos_reales_usuario,
                'productos_vendidos': productos_vendidos_usuario,
                'comisiones_pagadas': comisiones_pagadas_usuario,
                'promedio_por_venta': promedio_por_venta
            })
        
        # Ordenar por total de ventas descendente y limitar a 10
        ventas_por_usuario.sort(key=lambda x: x['total_ventas'], reverse=True)
        ventas_por_usuario = ventas_por_usuario[:10]
        
        # Compras por cliente con métricas detalladas
        compras_por_cliente = []
        clientes_con_compras = ventas_periodo.values('cliente__nombre', 'cliente__apellido').distinct()
        
        for cliente_data in clientes_con_compras:
            nombre = cliente_data['cliente__nombre']
            apellido = cliente_data['cliente__apellido']
            
            # Obtener ventas del cliente en el período
            ventas_cliente = ventas_periodo.filter(
                cliente__nombre=nombre,
                cliente__apellido=apellido
            )
            
            # Calcular métricas básicas
            total_compras = ventas_cliente.count()
            
            # Calcular gasto total del cliente
            gasto_total_cliente = ventas_cliente.aggregate(
                total=Sum('total')
            )['total'] or Decimal('0')
            
            # Calcular productos comprados por el cliente
            productos_comprados_cliente = 0
            tallas_compradas = set()
            for venta in ventas_cliente:
                for detalle in venta.detalleventa_set.all():
                    productos_comprados_cliente += detalle.cantidad
                    if detalle.producto.talla:
                        tallas_compradas.add(detalle.producto.talla.nombre)
            
            # Calcular gasto promedio por compra
            gasto_promedio_cliente = gasto_total_cliente / total_compras if total_compras > 0 else Decimal('0')
            
            compras_por_cliente.append({
                'cliente__nombre': nombre,
                'cliente__apellido': apellido,
                'total_compras': total_compras,
                'productos_comprados': productos_comprados_cliente,
                'gasto_total': gasto_total_cliente,
                'gasto_promedio': gasto_promedio_cliente,
                'tallas_compradas': ', '.join(sorted(tallas_compradas)) if tallas_compradas else 'N/A'
            })
        
        # Ordenar por total de compras descendente y limitar a 10
        compras_por_cliente.sort(key=lambda x: x['total_compras'], reverse=True)
        compras_por_cliente = compras_por_cliente[:10]
        
        # Tallas más vendidas
        tallas_vendidas = []
        for venta in ventas_periodo:
            for item in venta.detalleventa_set.all():
                if item.producto.talla:
                    tallas_vendidas.append(item.producto.talla.nombre)
        
        from collections import Counter
        tallas_counter = Counter(tallas_vendidas)
        total_tallas_vendidas = sum(tallas_counter.values())
        
        tallas_mas_vendidas = []
        for talla, cantidad in tallas_counter.most_common(10):
            porcentaje = (cantidad / total_tallas_vendidas * 100) if total_tallas_vendidas > 0 else 0
            tallas_mas_vendidas.append({
                'talla': talla, 
                'cantidad': cantidad,
                'porcentaje': porcentaje
            })
        
        # Marcas más vendidas
        marcas_vendidas = []
        for venta in ventas_periodo:
            for item in venta.detalleventa_set.all():
                if item.producto.marca:
                    marcas_vendidas.append(item.producto.marca.nombre)
        
        marcas_counter = Counter(marcas_vendidas)
        total_marcas_vendidas = sum(marcas_counter.values())
        
        marcas_mas_vendidas = []
        for marca, cantidad in marcas_counter.most_common(10):
            porcentaje = (cantidad / total_marcas_vendidas * 100) if total_marcas_vendidas > 0 else 0
            marcas_mas_vendidas.append({
                'marca': marca, 
                'cantidad': cantidad,
                'porcentaje': porcentaje
            })
        
        # Tipos más vendidos
        tipos_vendidos = []
        for venta in ventas_periodo:
            for item in venta.detalleventa_set.all():
                if item.producto.tipo:
                    tipos_vendidos.append(item.producto.tipo.nombre)
        
        tipos_counter = Counter(tipos_vendidos)
        total_tipos_vendidos = sum(tipos_counter.values())
        
        tipos_mas_vendidos = []
        for tipo, cantidad in tipos_counter.most_common(10):
            porcentaje = (cantidad / total_tipos_vendidos * 100) if total_tipos_vendidos > 0 else 0
            tipos_mas_vendidos.append({
                'tipo': tipo, 
                'cantidad': cantidad,
                'porcentaje': porcentaje
            })
        
        # Ventas por día para gráfico
        ventas_por_dia = ventas_periodo.annotate(
            fecha_dia=TruncDate('fecha')
        ).values('fecha_dia').annotate(
            total_ventas=Count('id'),
            total_ingresos=Sum('total')
        ).order_by('fecha_dia')
        
        context.update({
            'nro_ventas_totales': nro_ventas_totales,
            'gasto_total_clientes': gasto_total_clientes,
            'gasto_medio_clientes': gasto_medio_clientes,
            'gasto_promedio_cliente': gasto_promedio_cliente,
            'ingresos_reales': ingresos,
            'total_productos_vendidos': total_productos_vendidos,
            'total_productos_stock': total_productos_stock,
            'cantidad_productos_devueltos': cantidad_productos_devueltos,
            'valor_promedio_productos': valor_promedio_productos,
            'promedio_precio_compra': promedio_precio_compra,
            'total_productos_merma': total_productos_merma,
            'beneficios_netos': beneficios_netos,
            'costos_ventas': coste_productos,
            'comisiones': comisiones,
            'devoluciones': devoluciones_reembolsadas,
            'gastos_administrativos': gastos_administrativos,
            'mermas': mermas,
            'gastos_totales': gastos_totales,
            'total_deudas_clientes': total_deudas_clientes,
            'ventas_por_usuario': list(ventas_por_usuario),
            'compras_por_cliente': list(compras_por_cliente),
            'tallas_mas_vendidas': tallas_mas_vendidas,
            'marcas_mas_vendidas': marcas_mas_vendidas,
            'tipos_mas_vendidos': tipos_mas_vendidos,
            'ventas_por_dia': list(ventas_por_dia),
            'periodo_inicio': start_date.strftime('%d/%m/%Y'),
            'periodo_fin': end_date.strftime('%d/%m/%Y'),
        })
        
        return context

class ReporteAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista AJAX para obtener datos de reportes"""
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get(self, request, *args, **kwargs):
        # Obtener parámetros de fecha
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not start_date or not end_date:
            return JsonResponse({'error': 'Fechas requeridas'}, status=400)
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
        
        # Filtrar ventas por período
        ventas_periodo = Venta.objects.filter(
            fecha__date__range=[start_date, end_date]
        )
        
        # Calcular métricas
        metricas = self.calcular_metricas(ventas_periodo, start_date, end_date)
        
        return JsonResponse(metricas)
    
    def calcular_metricas(self, ventas_periodo, start_date, end_date):
        """Calcular todas las métricas del reporte"""
        
        # 1. Número de Ventas Totales
        nro_ventas_totales = ventas_periodo.count()
        
        # 2. Número de Ventas por Usuario
        ventas_por_usuario = ventas_periodo.values('user__username').annotate(
            total_ventas=Count('id')
        ).order_by('-total_ventas')
        
        # 3. Número de Compras por Cliente
        compras_por_cliente = ventas_periodo.values('cliente__nombre', 'cliente__apellido').annotate(
            total_compras=Count('id')
        ).order_by('-total_compras')
        
        # 4. Tallas más vendidas
        tallas_vendidas = []
        for venta in ventas_periodo:
            for item in venta.detalleventa_set.all():
                if item.producto.talla:
                    tallas_vendidas.append(item.producto.talla.nombre)
        
        from collections import Counter
        tallas_counter = Counter(tallas_vendidas)
        tallas_mas_vendidas = [{'talla': talla, 'cantidad': cantidad} 
                              for talla, cantidad in tallas_counter.most_common(10)]
        
        # 5. Gasto total de clientes
        gasto_total_clientes = ventas_periodo.aggregate(
            total=Sum('total')
        )['total'] or 0
        
        # 6. Gasto medio de clientes
        gasto_medio_clientes = ventas_periodo.aggregate(
            promedio=Avg('total')
        )['promedio'] or 0
        
        # 7. Ingreso total por usuario
        ingresos_por_usuario = ventas_periodo.values('user__username').annotate(
            ingreso_total=Sum('total')
        ).order_by('-ingreso_total')
        
        # 8. Ingreso medio por usuario
        ingreso_medio_usuario = ventas_periodo.values('user__username').annotate(
            ingreso_promedio=Avg('total')
        ).order_by('-ingreso_promedio')
        
        # 9. Beneficios netos - CÁLCULO MEJORADO
        # 1. INGRESOS: Sumar pagos que NO son con método "Saldo"
        ingresos = Pago.objects.filter(
            venta__in=ventas_periodo
        ).exclude(
            metodo__nombre='Saldo'
        ).aggregate(
            total_ingresos=Sum('monto_usd')
        )['total_ingresos'] or Decimal('0')
        
        # 2. GASTOS: Calcular todos los componentes
        # 2.1 Coste_productos: sum(detalleventa.precio_compra x cantidad) - sum(detalledevolucion.precio_coste x cantidad where danada=False)
        coste_productos = Decimal('0')
        for venta in ventas_periodo:
            # Sumar costos de productos vendidos
            for detalle in venta.detalleventa_set.all():
                coste_productos += detalle.precio_compra * detalle.cantidad
            
            # Restar costos de productos devueltos NO dañados
            for devolucion in venta.devoluciones.all():
                for detalle_dev in devolucion.detalles.filter(danado=False):
                    coste_productos -= detalle_dev.precio_compra * detalle_dev.cantidad_producto
        
        # 2.2 Comisiones: sum(venta.comision where estado_comision == 'pagado')
        start_datetime = datetime.combine(start_date, time.min)
        end_datetime = datetime.combine(end_date, time.max)
        
        ventas_comisiones_pagadas = Venta.objects.filter(
            fecha__gte=start_datetime,
            fecha__lte=end_datetime,
            estado_comision='pagado'
        )
        
        comisiones = Decimal('0')
        for venta in ventas_comisiones_pagadas:
            if venta.comision > 0:
                comisiones += venta.comision
            else:
                # Si la comisión no está calculada, calcularla al vuelo
                comision_calculada = (venta.total * Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                comisiones += comision_calculada
                # Actualizar la comisión en la base de datos
                venta.comision = comision_calculada
                venta.save(update_fields=['comision'])
        
        # 2.3 Gastos_Generales: sum(gastos_administrativos.monto)
        gastos_administrativos = GastoAdministrativo.objects.filter(
            fecha__range=[start_date, end_date],
            activo=True
        ).aggregate(
            total_gastos=Sum('monto')
        )['total_gastos'] or Decimal('0')
        
        # 2.4 Devoluciones: sum(devolucion.reembolsado)
        devoluciones_reembolsadas = Devolucion.objects.filter(
            id_venta__in=ventas_periodo,
            reembolsado__isnull=False
        ).aggregate(
            total_reembolsos=Sum('reembolsado')
        )['total_reembolsos'] or Decimal('0')
        
        # 2.5 Mermas: sum(merma.precio_compra x cantidad where origen == 'tienda')
        mermas = Decimal('0')
        for merma in Merma.objects.filter(
            fecha__range=[start_date, end_date],
            origen='tienda'
        ):
            mermas += merma.total_costo
        
        # Calcular gastos totales
        gastos_totales = coste_productos + comisiones + gastos_administrativos + devoluciones_reembolsadas + mermas
        
        # Beneficios = Ingresos - Gastos
        beneficios_netos = ingresos - gastos_totales
        
        # Datos adicionales para gráficos
        ventas_por_dia = ventas_periodo.annotate(
            fecha_dia=TruncDate('fecha')
        ).values('fecha_dia').annotate(
            total_ventas=Count('id'),
            total_ingresos=Sum('total')
        ).order_by('fecha_dia')
        
        return {
            'periodo': {
                'inicio': start_date.strftime('%d/%m/%Y'),
                'fin': end_date.strftime('%d/%m/%Y')
            },
            'metricas_principales': {
                'nro_ventas_totales': nro_ventas_totales,
                'gasto_total_clientes': float(gasto_total_clientes),
                'gasto_medio_clientes': float(gasto_medio_clientes),
                'beneficios_netos': float(beneficios_netos),
                'costos_ventas': float(coste_productos),
                'comisiones': float(comisiones),
                'devoluciones': float(devoluciones_reembolsadas),
                'gastos_administrativos': float(gastos_administrativos)
            },
            'ventas_por_usuario': list(ventas_por_usuario),
            'compras_por_cliente': list(compras_por_cliente),
            'tallas_mas_vendidas': tallas_mas_vendidas,
            'ingresos_por_usuario': list(ingresos_por_usuario),
            'ingreso_medio_usuario': list(ingreso_medio_usuario),
            'ventas_por_dia': list(ventas_por_dia)
        }

class ReportePDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para generar y descargar reportes en PDF"""
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get(self, request, *args, **kwargs):
        # Obtener parámetros
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not start_date or not end_date:
            return HttpResponse('Fechas requeridas', status=400)
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return HttpResponse('Formato de fecha inválido', status=400)
        
        # Generar PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_ventas_{start_date}_{end_date}.pdf"'
        
        # Crear el documento PDF
        doc = SimpleDocTemplate(response, pagesize=A4)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.black
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.black
        )

        # Estilo de tablas unificado (sobrio)
        header_bg = colors.HexColor('#2f3542')  # gris oscuro
        header_fg = colors.whitesmoke
        body_bg = colors.white
        grid_color = colors.HexColor('#dfe4ea')  # gris claro
        body_text = colors.HexColor('#2f3542')

        def apply_table_style(table: Table, header_rows: int = 1):
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, header_rows - 1), header_bg),
                ('TEXTCOLOR', (0, 0), (-1, header_rows - 1), header_fg),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, header_rows - 1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, header_rows - 1), 9),  # Reducido de 11 a 9
                ('BOTTOMPADDING', (0, 0), (-1, header_rows - 1), 8),  # Reducido de 10 a 8
                ('BACKGROUND', (0, header_rows), (-1, -1), body_bg),
                ('TEXTCOLOR', (0, header_rows), (-1, -1), body_text),
                ('FONTNAME', (0, header_rows), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, header_rows), (-1, -1), 8),  # Reducido de 9 a 8
                ('GRID', (0, 0), (-1, -1), 0.5, grid_color),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
        
        # Título del reporte
        title = Paragraph(f'<b>REPORTE DE VENTAS</b><br/>Período: {start_date.strftime("%d/%m/%Y")} - {end_date.strftime("%d/%m/%Y")}', title_style)
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Obtener datos
        ventas_periodo = Venta.objects.filter(fecha__date__range=[start_date, end_date])
        
        # Calcular métricas principales
        nro_ventas = ventas_periodo.count()
        total_ventas = ventas_periodo.aggregate(total=Sum('total'))['total'] or 0
        gasto_medio = total_ventas / nro_ventas if nro_ventas > 0 else 0
        
        # ========================================
        # CÁLCULO DE BENEFICIOS MEJORADO (PDF)
        # ========================================
        
        # 1. INGRESOS: Sumar pagos que NO son con método "Saldo"
        ingresos = Pago.objects.filter(
            venta__in=ventas_periodo
        ).exclude(
            metodo__nombre='Saldo'
        ).aggregate(
            total_ingresos=Sum('monto_usd')
        )['total_ingresos'] or Decimal('0')
        
        # 2. GASTOS: Calcular todos los componentes
        start_datetime = datetime.combine(start_date, time.min)
        end_datetime = datetime.combine(end_date, time.max)
        
        # 2.1 Coste_productos: sum(detalleventa.precio_compra x cantidad) - sum(detalledevolucion.precio_coste x cantidad where danada=False)
        coste_productos = Decimal('0')
        for venta in ventas_periodo:
            # Sumar costos de productos vendidos
            for detalle in venta.detalleventa_set.all():
                coste_productos += detalle.precio_compra * detalle.cantidad
            
            # Restar costos de productos devueltos NO dañados
            for devolucion in venta.devoluciones.all():
                for detalle_dev in devolucion.detalles.filter(danado=False):
                    coste_productos -= detalle_dev.precio_compra * detalle_dev.cantidad_producto
        
        # 2.2 Comisiones: sum(venta.comision where estado_comision == 'pagado')
        ventas_comisiones_pagadas = Venta.objects.filter(
            fecha__gte=start_datetime,
            fecha__lte=end_datetime,
            estado_comision='pagado'
        )
        
        comisiones = Decimal('0')
        for venta in ventas_comisiones_pagadas:
            if venta.comision > 0:
                comisiones += venta.comision
            else:
                # Si la comisión no está calculada, calcularla al vuelo
                comision_calculada = (venta.total * Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                comisiones += comision_calculada
                # Actualizar la comisión en la base de datos
                venta.comision = comision_calculada
                venta.save(update_fields=['comision'])
        
        # 2.3 Gastos_Generales: sum(gastos_administrativos.monto)
        gastos_administrativos = GastoAdministrativo.objects.filter(
            fecha__range=[start_date, end_date],
            activo=True
        ).aggregate(
            total_gastos=Sum('monto')
        )['total_gastos'] or Decimal('0')
        
        # 2.4 Devoluciones: sum(devolucion.reembolsado)
        devoluciones_reembolsadas = Devolucion.objects.filter(
            id_venta__in=ventas_periodo,
            reembolsado__isnull=False
        ).aggregate(
            total_reembolsos=Sum('reembolsado')
        )['total_reembolsos'] or Decimal('0')
        
        # 2.5 Mermas: sum(merma.precio_compra x cantidad where origen == 'tienda')
        mermas = Decimal('0')
        for merma in Merma.objects.filter(
            fecha__range=[start_date, end_date],
            origen='tienda'
        ):
            mermas += merma.total_costo
        
        # Calcular gastos totales
        gastos_totales = coste_productos + comisiones + gastos_administrativos + devoluciones_reembolsadas + mermas
        
        # Beneficios = Ingresos - Gastos
        beneficios_netos = ingresos - gastos_totales
        
        # Calcular métricas adicionales
        # Total de productos vendidos
        total_productos_vendidos = 0
        for venta in ventas_periodo:
            for detalle in venta.detalleventa_set.all():
                total_productos_vendidos += detalle.cantidad
        
        # Total de productos en stock
        total_productos_stock = Producto.objects.aggregate(
            total_stock=Sum('stock')
        )['total_stock'] or 0
        
        # Cantidad de productos devueltos
        cantidad_productos_devueltos = 0
        devoluciones_periodo = Devolucion.objects.filter(
            fecha__range=[start_date, end_date]
        )
        for devolucion in devoluciones_periodo:
            for detalle in devolucion.detalles.all():
                cantidad_productos_devueltos += detalle.cantidad_producto
        
        # Valor promedio de productos (precio de venta)
        valor_promedio_productos = Producto.objects.aggregate(
            promedio_precio=Avg('precio_venta')
        )['promedio_precio'] or Decimal('0')
        
        # Promedio de precio de compra de productos
        promedio_precio_compra = Producto.objects.aggregate(
            promedio_compra=Avg('precio_compra')
        )['promedio_compra'] or Decimal('0')
        
        # Gasto promedio por cliente
        gasto_promedio_cliente = total_ventas / nro_ventas if nro_ventas > 0 else Decimal('0')
        
        # Total de productos en merma
        total_productos_merma = Merma.objects.filter(
            fecha__range=[start_date, end_date]
        ).aggregate(
            total_cantidad=Sum('cantidad')
        )['total_cantidad'] or 0
        
        # Sumatoria de deudas de clientes
        total_deudas_clientes = Cliente.objects.aggregate(
            total_deudas=Sum('deuda')
        )['total_deudas'] or Decimal('0')

        # Tabla de métricas principales
        metricas_data = [
            ['MÉTRICA', 'VALOR'],
            ['Número de Ventas Totales', str(nro_ventas)],
            ['Total de Productos Vendidos', str(total_productos_vendidos)],
            ['Total de Productos en Stock (registro no historico)', str(total_productos_stock)],
            ['Cantidad de Productos Devueltos', str(cantidad_productos_devueltos)],
            ['Gasto Total de Clientes', f'${total_ventas:,.2f}'],
            ['Gasto Promedio por Cliente', f'${gasto_promedio_cliente:,.2f}'],
            ['Valor Promedio de Productos', f'${valor_promedio_productos:,.2f}'],
            ['Promedio Precio de Compra', f'${promedio_precio_compra:,.2f}'],
            ['Total de Productos en Merma', str(total_productos_merma)],
            ['Total de Deudas de Clientes', f'${total_deudas_clientes:,.2f}'],
            ['Beneficios Netos', f'${beneficios_netos:,.2f}'],
        ]
        
        metricas_table = Table(metricas_data, colWidths=[280, 180])
        apply_table_style(metricas_table)

        elements.append(Paragraph('Métricas Generales', subtitle_style))
        elements.append(metricas_table)
        elements.append(Spacer(1, 20))

        # Tabla de desglose financiero
        desglose_data = [
            ['CONCEPTO', 'MONTO'],
            ['INGRESOS', ''],
            ['Ingresos (sin saldo)', f'${ingresos:,.2f}'],
            ['', ''],
            ['GASTOS', ''],
            ['Costos de Productos', f'${coste_productos:,.2f}'],
            ['Comisiones Pagadas', f'${comisiones:,.2f}'],
            ['Gastos Administrativos', f'${gastos_administrativos:,.2f}'],
            ['Devoluciones Reembolsadas', f'${devoluciones_reembolsadas:,.2f}'],
            ['Mermas (Tienda)', f'${mermas:,.2f}'],
            ['', ''],
            ['TOTAL GASTOS', f'${gastos_totales:,.2f}'],
            ['', ''],
            ['BENEFICIOS NETOS', f'${beneficios_netos:,.2f}'],
        ]

        desglose_table = Table(desglose_data, colWidths=[280, 180])
        apply_table_style(desglose_table)

        elements.append(Paragraph('Análisis Financiero Detallado', subtitle_style))
        elements.append(desglose_table)
        elements.append(Spacer(1, 20))

        # Ventas por usuario con métricas detalladas
        ventas_usuario_data = [['USUARIO', 'VENTAS', 'PRODUCTOS', 'INGRESOS', 'PAGO COMISION', 'PROM/VENTA']]
        usuarios_con_ventas = ventas_periodo.values('user__username').distinct()
        
        for usuario_data in usuarios_con_ventas:
            username = usuario_data['user__username']
            
            # Obtener ventas del usuario en el período
            ventas_usuario = ventas_periodo.filter(user__username=username)
            
            # Calcular métricas básicas
            total_ventas = ventas_usuario.count()
            
            # Calcular ingresos reales (excluyendo pagos con método "Saldo")
            ingresos_reales_usuario = Decimal('0')
            for venta in ventas_usuario:
                pagos_reales = Pago.objects.filter(
                    venta=venta
                ).exclude(
                    metodo__nombre='Saldo'
                )
                for pago in pagos_reales:
                    ingresos_reales_usuario += pago.monto_usd
            
            # Calcular productos vendidos por el usuario
            productos_vendidos_usuario = 0
            for venta in ventas_usuario:
                for detalle in venta.detalleventa_set.all():
                    productos_vendidos_usuario += detalle.cantidad
            
            # Calcular comisiones pagadas del usuario
            comisiones_pagadas_usuario = ventas_usuario.filter(
                estado_comision='pagado'
            ).aggregate(
                total_comisiones=Sum('comision')
            )['total_comisiones'] or Decimal('0')
            
            # Calcular promedio por venta
            promedio_por_venta = ingresos_reales_usuario / total_ventas if total_ventas > 0 else Decimal('0')
            
            ventas_usuario_data.append([
                username,
                str(total_ventas),
                str(productos_vendidos_usuario),
                f"${ingresos_reales_usuario:,.2f}",
                f"${comisiones_pagadas_usuario:,.2f}",
                f"${promedio_por_venta:,.2f}"
            ])
        
        # Ordenar por total de ventas descendente y limitar a 10
        ventas_usuario_data[1:] = sorted(ventas_usuario_data[1:], key=lambda x: int(x[1]), reverse=True)[:10]

        if len(ventas_usuario_data) > 1:
            ventas_usuario_table = Table(ventas_usuario_data, colWidths=[120, 80, 80, 100, 100, 100])
            apply_table_style(ventas_usuario_table)

            elements.append(Paragraph('Rendimiento de Vendedores', subtitle_style))
            elements.append(ventas_usuario_table)
            elements.append(Spacer(1, 20))

        # Compras por cliente con métricas detalladas
        compras_cliente_data = [['CLIENTE', 'NRO. VENTAS', 'NRO. PRODUCTOS', 'GASTO TOTAL', 'GASTO PROMEDIO']]
        clientes_con_compras = ventas_periodo.values('cliente__nombre', 'cliente__apellido').distinct()
        
        for cliente_data in clientes_con_compras:
            nombre = cliente_data['cliente__nombre']
            apellido = cliente_data['cliente__apellido']
            
            # Obtener ventas del cliente en el período
            ventas_cliente = ventas_periodo.filter(
                cliente__nombre=nombre,
                cliente__apellido=apellido
            )
            
            # Calcular métricas básicas
            total_compras = ventas_cliente.count()
            
            # Calcular gasto total del cliente
            gasto_total_cliente = ventas_cliente.aggregate(
                total=Sum('total')
            )['total'] or Decimal('0')
            
            # Calcular productos comprados por el cliente
            productos_comprados_cliente = 0
            for venta in ventas_cliente:
                for detalle in venta.detalleventa_set.all():
                    productos_comprados_cliente += detalle.cantidad
            
            # Calcular gasto promedio por compra
            gasto_promedio_cliente = gasto_total_cliente / total_compras if total_compras > 0 else Decimal('0')
            
            nombre_completo = f"{nombre} {apellido}".strip()
            compras_cliente_data.append([
                nombre_completo,
                str(total_compras),
                str(productos_comprados_cliente),
                f"${gasto_total_cliente:,.2f}",
                f"${gasto_promedio_cliente:,.2f}"
            ])
        
        # Ordenar por total de compras descendente y limitar a 10
        compras_cliente_data[1:] = sorted(compras_cliente_data[1:], key=lambda x: int(x[1]), reverse=True)[:10]

        if len(compras_cliente_data) > 1:
            compras_cliente_table = Table(compras_cliente_data, colWidths=[150, 80, 80, 100, 100])
            apply_table_style(compras_cliente_table)

            elements.append(Paragraph('Análisis de Comportamiento de Clientes', subtitle_style))
            elements.append(compras_cliente_table)
            elements.append(Spacer(1, 20))

        # Tallas más vendidas con porcentajes
        tallas_vendidas = []
        for venta in ventas_periodo:
            for item in venta.detalleventa_set.all():
                if item.producto.talla:
                    tallas_vendidas.append(item.producto.talla.nombre)

        from collections import Counter
        tallas_counter = Counter(tallas_vendidas)
        total_tallas_vendidas = sum(tallas_counter.values())
        tallas_mas_vendidas = tallas_counter.most_common(10)

        if tallas_mas_vendidas:
            tallas_data = [['TALLA', 'CANTIDAD VENDIDA', 'PORCENTAJE']]
            for talla, cantidad in tallas_mas_vendidas:
                porcentaje = (cantidad / total_tallas_vendidas * 100) if total_tallas_vendidas > 0 else 0
                tallas_data.append([talla, str(cantidad), f"{porcentaje:.1f}%"])

            tallas_table = Table(tallas_data, colWidths=[180, 120, 100])
            apply_table_style(tallas_table)

            elements.append(Paragraph('Ranking de Tallas por Demanda', subtitle_style))
            elements.append(tallas_table)
            elements.append(Spacer(1, 20))

        # Marcas más vendidas con porcentajes
        marcas_vendidas = []
        for venta in ventas_periodo:
            for item in venta.detalleventa_set.all():
                if item.producto.marca:
                    marcas_vendidas.append(item.producto.marca.nombre)

        marcas_counter = Counter(marcas_vendidas)
        total_marcas_vendidas = sum(marcas_counter.values())
        marcas_mas_vendidas = marcas_counter.most_common(10)

        if marcas_mas_vendidas:
            marcas_data = [['MARCA', 'CANTIDAD VENDIDA', 'PORCENTAJE']]
            for marca, cantidad in marcas_mas_vendidas:
                porcentaje = (cantidad / total_marcas_vendidas * 100) if total_marcas_vendidas > 0 else 0
                marcas_data.append([marca, str(cantidad), f"{porcentaje:.1f}%"])

            marcas_table = Table(marcas_data, colWidths=[180, 120, 100])
            apply_table_style(marcas_table)

            elements.append(Paragraph('Ranking de Marcas por Popularidad', subtitle_style))
            elements.append(marcas_table)
            elements.append(Spacer(1, 20))

        # Tipos más vendidos con porcentajes
        tipos_vendidos = []
        for venta in ventas_periodo:
            for item in venta.detalleventa_set.all():
                if item.producto.tipo:
                    tipos_vendidos.append(item.producto.tipo.nombre)

        tipos_counter = Counter(tipos_vendidos)
        total_tipos_vendidos = sum(tipos_counter.values())
        tipos_mas_vendidos = tipos_counter.most_common(10)

        if tipos_mas_vendidos:
            tipos_data = [['TIPO', 'CANTIDAD VENDIDA', 'PORCENTAJE']]
            for tipo, cantidad in tipos_mas_vendidos:
                porcentaje = (cantidad / total_tipos_vendidos * 100) if total_tipos_vendidos > 0 else 0
                tipos_data.append([tipo, str(cantidad), f"{porcentaje:.1f}%"])

            tipos_table = Table(tipos_data, colWidths=[180, 120, 100])
            apply_table_style(tipos_table)

            elements.append(Paragraph('Ranking de Tipos de Productos', subtitle_style))
            elements.append(tipos_table)
            elements.append(Spacer(1, 20))

        # Pie de página
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey
        )

        footer = Paragraph(f'Reporte generado el {datetime.now().strftime("%d/%m/%Y %H:%M")} | Sistema de Inventario', footer_style)
        elements.append(footer)

        # Construir PDF
        doc.build(elements)

        return response


# ===================== VISTAS GASTOS ADMINISTRATIVOS =====================

class GastoAdministrativoListView(LoginRequiredMixin, ListView):
    model = GastoAdministrativo
    template_name = 'inventario/gastos_administrativos/gasto_administrativo_list.html' 
    context_object_name = 'gastos_administrativos'
    ordering = ['-fecha', 'nombre']
    

class GastoAdministrativoCreateView(LoginRequiredMixin, CreateView):
    model = GastoAdministrativo
    form_class = GastoAdministrativoForm
    template_name = 'inventario/gastos_administrativos/gasto_administrativo_form.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('gasto_administrativo_create')
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})
    
    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })
    
    def get_success_url(self):
        return reverse_lazy('gasto_administrativo_list')


class GastoAdministrativoUpdateView(LoginRequiredMixin, UpdateView):
    model = GastoAdministrativo
    form_class = GastoAdministrativoForm
    template_name = 'inventario/gastos_administrativos/gasto_administrativo_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_url'] = reverse_lazy('gasto_administrativo_update', kwargs={'pk': self.object.pk})
        return ctx
    
    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
            'html': self.render_to_response(self.get_context_data(form=form)).rendered_content
        })


# Cambiar el estado del gasto administrativo
@login_required
def gasto_administrativo_toggle(request, pk):
    gasto = get_object_or_404(GastoAdministrativo, pk=pk)

    try:
        gasto.activo = not gasto.activo
        gasto.save()
        estado = 'activado' if gasto.activo else 'desactivado'
        messages.success(request, f'El gasto administrativo "{gasto.nombre}" ha sido {estado} correctamente.')
        
    except Exception as e:
        messages.error(request, f'Error al cambiar el estado del gasto administrativo: {str(e)}')
        logger.error(f'Error al cambiar el estado del gasto administrativo: {str(e)}', exc_info=True)

    return redirect('gasto_administrativo_list')

# Vista para servir archivos media en producción

def serve_media_file(request, path):
    """
    Vista personalizada para servir archivos media en producción
    """
    if settings.DEBUG:
        # En desarrollo, usar la vista estándar de Django
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    else:
        # En producción, verificar si el archivo existe
        file_path = os.path.join(settings.MEDIA_ROOT, path)
        if os.path.exists(file_path):
            return serve(request, path, document_root=settings.MEDIA_ROOT)
        else:
            # Si el archivo no existe, devolver una imagen por defecto
            default_image_path = os.path.join(settings.STATIC_ROOT, 'images', 'no-image-available-icon-vector.jpg')
            if os.path.exists(default_image_path):
                with open(default_image_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='image/jpeg')
                    return response
            else:
                raise Http404("Archivo no encontrado")


@login_required
@require_http_methods(["POST"])
def gestionar_saldo_cliente(request, pk):
    """
    Vista para gestionar el saldo de un cliente (sumar o restar)
    """
    try:
        cliente = get_object_or_404(Cliente, pk=pk)
        
        # Obtener datos del JSON
        data = json.loads(request.body)
        operacion = data.get('operacion')
        cantidad = Decimal(str(data.get('cantidad', 0)))
        
        # Validaciones
        if operacion not in ['sumar', 'restar']:
            return JsonResponse({
                'success': False,
                'error': 'Operación no válida'
            })
        
        if cantidad <= 0:
            return JsonResponse({
                'success': False,
                'error': 'La cantidad debe ser mayor a 0'
            })
        
        # Realizar la operación
        with transaction.atomic():
            if operacion == 'sumar':
                cliente.saldo += cantidad
                mensaje = f'Se agregó ${cantidad:.2f} al saldo del cliente. Nuevo saldo: ${cliente.saldo:.2f}'
            else:  # restar
                nuevo_saldo = cliente.saldo - cantidad
                if nuevo_saldo < 0:
                    return JsonResponse({
                        'success': False,
                        'error': f'No se puede restar ${cantidad:.2f}. El saldo quedaría en ${nuevo_saldo:.2f} (negativo)'
                    })
                cliente.saldo = nuevo_saldo
                mensaje = f'Se restó ${cantidad:.2f} del saldo del cliente. Nuevo saldo: ${cliente.saldo:.2f}'
                
            cliente.save()
        
        return JsonResponse({
            'success': True,
            'message': mensaje,
            'nuevo_saldo': str(cliente.saldo)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos JSON inválidos'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar la operación: {str(e)}'
        })


# ========================================
# MÓDULO DE MERMAS
# ========================================

class MermaListView(LoginRequiredMixin, ListView):
    """Vista para listar mermas con filtros avanzados"""
    model = Merma
    template_name = 'inventario/mermas/merma_list.html'
    context_object_name = 'mermas'
    ordering = ['-fecha']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener opciones para los filtros
        context['origenes'] = Merma.objects.values_list('origen', flat=True).distinct()
        context['tipos'] = Tipo.objects.all()
        context['marcas'] = Marca.objects.all()
        context['colores'] = Color.objects.all()
        context['tallas'] = Talla.objects.all()
        return context


class MermaAjaxView(LoginRequiredMixin, View):
    """Vista AJAX para DataTables de mermas"""
    def get(self, request, *args, **kwargs):
        # Parámetros básicos de DataTables
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        order_column_index = request.GET.get('order[0][column]', 0)
        order_direction = request.GET.get('order[0][dir]', 'desc')
        
        # Mapeo de columnas (debe coincidir con las columnas del template HTML)
        # 0: imagen (no ordenable), 1: id, 2: fecha, 3: codigo, 4: tipo, 5: marca, 
        # 6: talla, 7: cantidad, 8: precio_compra, 9: total_costo (calculado), 10: origen, 11: acciones (no ordenable)
        # Nota: total_costo es una propiedad calculada, no se puede ordenar directamente
        columns = ['id', 'fecha', 'id_producto__codigo', 'id_producto__tipo__nombre', 
                  'id_producto__marca__nombre', 'id_producto__talla__nombre', 
                  'cantidad', 'precio_compra', 'origen']
        
        # Mapeo de índices de DataTables a índices de columnas ordenables
        # DataTables envía índices basados en todas las columnas, pero solo algunas son ordenables
        orderable_columns = {
            1: 0,   # id
            2: 1,   # fecha
            3: 2,   # codigo  
            4: 3,   # tipo
            5: 4,   # marca
            6: 5,   # talla
            7: 6,   # cantidad
            8: 7,   # precio_compra
            9: None, # total_costo (no ordenable - es una propiedad calculada)
            10: 8,  # origen
        }
        
        # Validar que el índice de columna esté dentro del rango válido
        order_column_index = int(order_column_index)
        if order_column_index not in orderable_columns or orderable_columns[order_column_index] is None:
            order_column_index = 1  # Por defecto ordenar por ID
            order_direction = 'desc'
        
        # Obtener el índice real de la columna ordenable
        real_column_index = orderable_columns.get(order_column_index, 0)
        if real_column_index is None:
            real_column_index = 0  # Por defecto ID
        order_column = columns[real_column_index]
        if order_direction == 'desc':
            order_column = '-' + order_column
        
        # Parámetros de filtrado
        id_filter = request.GET.get('id_filter', '')
        codigo_filter = request.GET.get('codigo_filter', '')
        origen_filter = request.GET.get('origen_filter', '')
        tipo_filter = request.GET.get('tipo_filter', '')
        marca_filter = request.GET.get('marca_filter', '')
        talla_filter = request.GET.get('talla_filter', '')
        cantidad_min = request.GET.get('cantidad_min')
        cantidad_max = request.GET.get('cantidad_max')
        precio_min = request.GET.get('precio_min')
        precio_max = request.GET.get('precio_max')
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        
        # Consulta base con select_related para optimizar
        qs = Merma.objects.select_related(
            'id_producto__tipo',
            'id_producto__marca', 
            'id_producto__talla'
        ).all()
        
        # Aplicar filtros
        if search_value:
            qs = qs.filter(
                Q(id_producto__codigo__icontains=search_value) |
                Q(id_producto__tipo__nombre__icontains=search_value) |
                Q(id_producto__marca__nombre__icontains=search_value) |
                Q(id_producto__talla__nombre__icontains=search_value) |
                Q(origen__icontains=search_value) |
                Q(motivo__icontains=search_value)
            )
        
        if id_filter:
            qs = qs.filter(id=id_filter)
        
        if codigo_filter:
            qs = qs.filter(id_producto__codigo__icontains=codigo_filter)
        
        if origen_filter:
            qs = qs.filter(origen=origen_filter)
        
        if tipo_filter:
            qs = qs.filter(id_producto__tipo__nombre__in=tipo_filter.split(','))
        
        if marca_filter:
            qs = qs.filter(id_producto__marca__nombre__in=marca_filter.split(','))
        
        if talla_filter:
            qs = qs.filter(id_producto__talla__nombre__in=talla_filter.split(','))
        
        if cantidad_min:
            qs = qs.filter(cantidad__gte=int(cantidad_min))
        
        if cantidad_max:
            qs = qs.filter(cantidad__lte=int(cantidad_max))
        
        if precio_min:
            qs = qs.filter(precio_compra__gte=float(precio_min))
        
        if precio_max:
            qs = qs.filter(precio_compra__lte=float(precio_max))
        
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        
        if fecha_hasta:
            qs = qs.filter(fecha__lte=fecha_hasta)
        
        # Contar total de registros
        total_records = qs.count()
        
        # Aplicar ordenamiento
        qs = qs.order_by(order_column)
        
        # Aplicar paginación
        qs = qs[start:start + length]
        
        # Preparar datos para DataTables
        data = []
        for merma in qs:
            producto = merma.id_producto
            data.append({
                'id': merma.id,
                'fecha': merma.fecha.strftime('%d/%m/%Y'),
                'codigo': producto.codigo,
                'tipo': producto.tipo.nombre if producto.tipo else '-',
                'marca': producto.marca.nombre if producto.marca else '-',
                'talla': producto.talla.nombre if producto.talla else '-',
                'cantidad': merma.cantidad,
                'precio_compra': float(merma.precio_compra),
                'total_costo': float(merma.cantidad * merma.precio_compra),
                'origen': merma.get_origen_display(),
                'thumbnail_url': producto.thumbnail.url if producto.thumbnail else None,
                'has_image': bool(producto.imagen)
            })
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': total_records,
            'data': data
        })


class MermaDetailView(LoginRequiredMixin, DetailView):
    """Vista para mostrar detalles de una merma"""
    model = Merma
    template_name = 'inventario/mermas/merma_detail.html'
    context_object_name = 'merma'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Detalle de Merma #{self.object.id}'
        return context


class MermaCreateFromProductView(LoginRequiredMixin, View):
    """Vista para crear merma desde un producto específico"""
    
    def get(self, request, producto_id):
        try:
            producto = Producto.objects.get(id=producto_id)
        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)
        
        form = MermaForm(producto=producto)
        context = {
            'form': form,
            'producto': producto,
            'action_url': request.path
        }
        
        html = render_to_string('inventario/mermas/merma_form.html', context, request=request)
        return JsonResponse({'html': html})
    
    def post(self, request, producto_id):
        try:
            producto = Producto.objects.get(id=producto_id)
        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)
        
        form = MermaForm(request.POST, producto=producto)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Crear la merma
                    merma = Merma.objects.create(
                        id_producto=producto,
                        cantidad=form.cleaned_data['cantidad'],
                        precio_compra=producto.precio_compra,
                        origen='tienda',
                        motivo=form.cleaned_data.get('motivo', '')
                    )
                    
                    # Reducir el stock del producto
                    producto.stock -= form.cleaned_data['cantidad']
                    producto.save()
                    
                return JsonResponse({
                    'success': True,
                    'message': f'Merma creada exitosamente. Stock actualizado: {producto.stock} unidades'
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Error al crear la merma: {str(e)}'
                })
        else:
            # Mostrar errores del formulario
            context = {
                'form': form,
                'producto': producto,
                'action_url': request.path
            }
            html = render_to_string('inventario/mermas/merma_form.html', context, request=request)
            return JsonResponse({'html': html})
