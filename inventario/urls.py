from django.urls import path, reverse_lazy, include
from django.contrib.auth import views as auth_views

from inventario import views
from .bitacora_views import BitacoraView, BitacoraAjaxView
from .views import (
    # Vistas de autenticación/personalizadas
    CustomPasswordResetView,
    InicioView,
    CustomLoginView,
    CustomPasswordResetConfirmView,
    
    # Vistas de productos
    ProductoListView,
    ProductoAjaxView,
    ProductoDetailView,
    ProductoCreateView,
    ProductoUpdateView,
    ProductoDeleteView,
    producto_toggle,
    
    # Vistas de colores
    ColorListView,
    ColorCreateView,
    ColorUpdateView,
    color_toggle,

    # Vistas de marcas
    MarcaListView,
    MarcaCreateView,
    MarcaUpdateView,
    marca_toggle,

    # Vistas de tipos de prendas
    TipoListView,
    TipoCreateView,
    TipoUpdateView,
    tipo_toggle,

    # Vistas de tallas
    TallaListView,
    TallaCreateView,
    TallaUpdateView,
    talla_toggle,

    # Vistas de fits
    FitListView,
    FitCreateView,
    FitUpdateView,
    fit_toggle,

    # Vistas de ventas
    VentaListView,
    VentaAjaxView,
    ComisionAjaxView,
    VentaCreateView,
    ajax_venta_create,
    create_venta,
    validar_stock_batch,
    venta_toggle_entrega,
    VentaDetailView,
    ComisionEstadoUpdateView,
    ComisionMarcarPagadasPeriodoView,


    # Vistas de ventas
    DevolucionListView,
    DevolucionAjaxView,
    DevolucionDetailView,
    DevolucionCreateView,

    # Vistas de usuarios
    CustomUserListView,
    UsuarioAjaxView,
    SupabaseDiagView,
    CustomUserCreateView,
    ToggleUserActiveStatusView,
    UsuarioDetailView,
    CustomUserUpdateView,
    CustomPasswordChangeView,

    # Vistas de clientes
    ClienteListView,
    ClienteAjaxView,
    ClienteDetailView,
    ClienteVentasAjaxView,
    ClienteCreateView,
    ClienteUpdateView,
    ClienteDeleteView,
    ToggleClienteStatusView,
    cliente_toggle,

    # Vistas de gastos administrativos
    GastoAdministrativoListView,
    GastoAdministrativoCreateView,
    GastoAdministrativoUpdateView,
    gasto_administrativo_toggle,

    # Vistas de mermas
    MermaListView,
    MermaAjaxView,
    MermaDetailView,
    MermaCreateFromProductView,
)

urlpatterns = [
    path('', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('inicio/', InicioView.as_view(), name='inicio'),

    # Productos rutas
    path('inventario/productos/', ProductoListView.as_view(), name='producto_list'),
    path('inventario/productos/ajax', ProductoAjaxView.as_view(), name='producto_ajax'),
    path('inventario/productos/<int:pk>/', ProductoDetailView.as_view(), name='producto_detail'),
    path('inventario/productos/crear/', ProductoCreateView.as_view(), name='producto_create'),
    path('inventario/productos/editar/<int:pk>/', ProductoUpdateView.as_view(), name='producto_update'),
    path('inventario/productos/eliminar/<int:pk>/', ProductoDeleteView.as_view(), name='producto_delete'),
    path('inventario/productos/toggle/<int:pk>/', producto_toggle, name='producto_toggle'),

    # Productos_normalizacion rutas
    path('inventario/colores/', ColorListView.as_view(), name='color_list'),
    path('inventario/colores/crear/', ColorCreateView.as_view(), name='color_create'),
    path('inventario/colores/editar/<int:pk>/', ColorUpdateView.as_view(), name='color_update'),
    path('inventario/colores/toggle/<int:pk>/', color_toggle, name='color_toggle'),

    path('inventario/marcas/', MarcaListView.as_view(), name='marca_list'),
    path('inventario/marcas/crear/', MarcaCreateView.as_view(), name='marca_create'),
    path('inventario/marcas/editar/<int:pk>/', MarcaUpdateView.as_view(), name='marca_update'),
    path('inventario/marcas/toggle/<int:pk>/', marca_toggle, name='marca_toggle'),

    path('inventario/tipos/', TipoListView.as_view(), name='tipo_list'),
    path('inventario/tipos/crear/', TipoCreateView.as_view(), name='tipo_create'),
    path('inventario/tipos/editar/<int:pk>/', TipoUpdateView.as_view(), name='tipo_update'),
    path('inventario/tipos/toggle/<int:pk>/', tipo_toggle, name='tipo_toggle'),

    path('inventario/tallas/', TallaListView.as_view(), name='talla_list'),
    path('inventario/tallas/crear/', TallaCreateView.as_view(), name='talla_create'),
    path('inventario/tallas/editar/<int:pk>/', TallaUpdateView.as_view(), name='talla_update'),
    path('inventario/tallas/toggle/<int:pk>/', talla_toggle, name='talla_toggle'),    

    path('inventario/fits/', FitListView.as_view(), name='fit_list'),
    path('inventario/fits/crear/', FitCreateView.as_view(), name='fit_create'),
    path('inventario/fits/editar/<int:pk>/', FitUpdateView.as_view(), name='fit_update'),
    path('inventario/fits/toggle/<int:pk>/', fit_toggle, name='fit_toggle'),  

    # Ventas rutas
    path('venta/listado', VentaListView.as_view(), name='venta_list'),
    path('venta/ajax', VentaAjaxView.as_view(), name='venta_ajax'),
    path('venta/comisiones/ajax', ComisionAjaxView.as_view(), name='comision_ajax'),
    path('venta/crear/', VentaCreateView.as_view(), name='venta_create'),
    path('venta/detalle/<int:pk>/', VentaDetailView.as_view(), name='venta_detail'),
    path('venta/ajax/datos-venta/', ajax_venta_create, name='ajax_datos_venta'),
    path('venta/ajax/guardar-venta/', create_venta, name='ajax_guardar_venta'),
    path('venta/ajax/validar-stock/', validar_stock_batch, name='ajax_validar_stock'),
    path('venta/toggle-entrega/<int:pk>/', venta_toggle_entrega, name='venta_toggle_entrega'),
    path('venta/comisiones/estado/', ComisionEstadoUpdateView.as_view(), name='comision_estado_update'),
    path('venta/comisiones/marcar-pagadas/', ComisionMarcarPagadasPeriodoView.as_view(), name='comision_marcar_pagadas_periodo'),
    path('venta/nuevo-pago/<int:pk>/', views.VentaNuevoPagoView.as_view(), name='venta_nuevo_pago'),


    # devoluciones rutas
    path('devolucion/listado', DevolucionListView.as_view(), name='devolucion_list'),
    path('devolucion/ajax', DevolucionAjaxView.as_view(), name='devolucion_ajax'),
    path('devolucion/detalle/<int:pk>/', DevolucionDetailView.as_view(), name='devolucion_detail'),
    path('devolucion/crear/<int:venta_id>/', DevolucionCreateView.as_view(), name='devolucion_create'),

    # Usuarios rutas
    path('usuarios/', CustomUserListView.as_view(), name='usuario_list'),
    path('usuarios/ajax/', UsuarioAjaxView.as_view(), name='usuario_ajax'),
    path('usuarios/crear/', CustomUserCreateView.as_view(), name='usuario_create'),
    path('usuarios/editar/<int:pk>/', CustomUserUpdateView.as_view(), name='usuario_update'),
    path('perfil/editar/', CustomUserUpdateView.as_view(), name='perfil_editar'),
    path('usuarios/toggle-activo/<int:pk>/', ToggleUserActiveStatusView.as_view(), name='usuario_toggle_activo'),
    path('usuarios/toggle/<int:pk>/', ToggleUserActiveStatusView.as_view(), name='toggle_user_active_status'),
    path('usuarios/suspender/<int:user_id>/', views.suspender_usuario, name='suspender_usuario'),
    path('usuarios/detalle/<int:pk>/', UsuarioDetailView.as_view(), name='usuario_detail'),
    path('diag/supabase/', SupabaseDiagView.as_view(), name='supabase_diag'),
    path('usuarios/<int:pk>/eliminar-imagen/', views.eliminar_imagen_usuario, name='eliminar_imagen_usuario'),

    # Clientes rutas
    path('clientes/', ClienteListView.as_view(), name='cliente_list'),
    path('clientes/ajax/', ClienteAjaxView.as_view(), name='cliente_ajax'),
    path('clientes/<int:cliente_id>/ventas/ajax/', ClienteVentasAjaxView.as_view(), name='cliente_ventas_ajax'),
    path('clientes/crear/', ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<int:pk>/', ClienteDetailView.as_view(), name='cliente_detail'),
    path('clientes/editar/<int:pk>/', ClienteUpdateView.as_view(), name='cliente_update'),
    path('clientes/eliminar/<int:pk>/', ClienteDeleteView.as_view(), name='cliente_delete'),
    path('clientes/toggle-status/<int:pk>/', ToggleClienteStatusView.as_view(), name='cliente_toggle_status'),
    path('clientes/toggle/<int:pk>/', cliente_toggle, name='cliente_toggle'),
    path('clientes/gestionar-saldo/<int:pk>/', views.gestionar_saldo_cliente, name='gestionar_saldo_cliente'),

    # Vista para solicitar la recuperación de contraseña
    path('recuperar_contraseña/', CustomPasswordResetView.as_view(
        template_name='inventario/recuperacion/recuperar_contraseña.html',
        email_template_name='inventario/recuperacion/recuperar_contraseña_email.html',
        subject_template_name='inventario/recuperacion/recuperar_contraseña_subject.txt',
        success_url=reverse_lazy('login')
    ), name='recuperar_contraseña'),

    # Vista para que el usuario ingrese su nueva contraseña desde el enlace enviado por correo
    path('recuperar-contraseña_confirmar/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(
        template_name='inventario/recuperacion/recuperar_contraseña_confirmar.html',
        success_url='/recuperar-contraseña_completo/'
    ), name='recuperar_contraseña_confirmar'),

    # Vista que confirma que la contraseña fue cambiada exitosamente
    path('recuperar-contraseña_completo/', auth_views.PasswordResetCompleteView.as_view(
        template_name='inventario/recuperacion/recuperar_contraseña_completo.html'
    ), name='recuperar_contraseña_completo'),
    
    path('cambiar-contraseña/', auth_views.PasswordChangeView.as_view(
        template_name='inventario/usuarios/cambiar_contraseña.html',
        success_url='/cambiar_contraseña_completo/'
    ), name='password_change'),

    path('cambiar_contraseña/', CustomPasswordChangeView.as_view(), name='password_change'),
    
    path('captcha/', include('captcha.urls')),
    
    path('prueba/', views.prueba, name='prueba'),

    # Reportes
    path('reportes/', views.ReporteView.as_view(), name='reporte'),
    path('reportes/ajax/', views.ReporteAjaxView.as_view(), name='reporte_ajax'),
    path('reportes/pdf/', views.ReportePDFView.as_view(), name='reporte_pdf'),

    # Gastos Administrativos
    path('gastos-administrativos/', GastoAdministrativoListView.as_view(), name='gasto_administrativo_list'),
    path('gastos-administrativos/crear/', GastoAdministrativoCreateView.as_view(), name='gasto_administrativo_create'),
    path('gastos-administrativos/editar/<int:pk>/', GastoAdministrativoUpdateView.as_view(), name='gasto_administrativo_update'),
    path('gastos-administrativos/toggle/<int:pk>/', gasto_administrativo_toggle, name='gasto_administrativo_toggle'),

    # Mermas
    path('inventario/mermas/', MermaListView.as_view(), name='merma_list'),
    path('inventario/mermas/ajax/', MermaAjaxView.as_view(), name='merma_ajax'),
    path('inventario/mermas/<int:pk>/', MermaDetailView.as_view(), name='merma_detail'),
    path('inventario/mermas/crear/<int:producto_id>/', MermaCreateFromProductView.as_view(), name='merma_create_from_product'),
    
    #Bitácora de acciones
    path('bitacora/', BitacoraView.as_view(), name='bitacora_list'),
    path('bitacora/ajax/', BitacoraAjaxView.as_view(), name='bitacora_ajax'),
] 

"""
    path('dashboard/', views.dashboard, name='dashboard'),     
    # Productos
    path('productos/', views.listar_productos, name='listar_productos'),
    path('productos/crear/', views.crear_producto, name='crear_producto'),
    path('productos/editar/<int:id>/', views.editar_producto, name='editar_producto'),
    path('productos/eliminar/<int:id>/', views.eliminar_producto, name='eliminar_producto'),

    # Empleados
    path('empleados/', views.listar_empleados, name='listar_empleados'),
    path('empleados/crear/', views.crear_empleado, name='crear_empleado'),
    path('empleados/editar/<int:id>/', views.editar_empleado, name='editar_empleado'),
    path('empleados/eliminar/<int:id>/', views.eliminar_empleado, name='eliminar_empleado'),

    # Movimientos (solo para admin)
    path('movimientos/', views.listar_movimientos, name='listar_movimientos'), 
    
    # Bitácora de acciones
    path('bitacora/', BitacoraView.as_view(), name='bitacora_list'),
    path('bitacora/ajax/', BitacoraAjaxView.as_view(), name='bitacora_ajax'),
    
"""

