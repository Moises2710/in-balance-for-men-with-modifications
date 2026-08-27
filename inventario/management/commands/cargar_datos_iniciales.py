from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from inventario.models import Categoria, Tipo, Color, Talla, Marca, Fit, MetodoPago

User = get_user_model()

class Command(BaseCommand):
    help = 'Carga datos iniciales del sistema'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando carga de datos iniciales...')
        
        # Crear grupos
        self.crear_grupos()
        
        # Crear superusuario
        self.crear_superusuario()
        
        # Crear datos de normalización
        self.crear_datos_normalizacion()
        
        # Crear métodos de pago
        self.crear_metodos_pago()
        
        self.stdout.write(
            self.style.SUCCESS('Datos iniciales cargados exitosamente!')
        )

    def crear_grupos(self):
        self.stdout.write('Creando grupos...')
        
        # Grupo Administrador
        admin_group, created = Group.objects.get_or_create(name='Administrador')
        if created:
            self.stdout.write('  - Grupo Administrador creado')
        
        # Grupo Vendedor
        vendedor_group, created = Group.objects.get_or_create(name='Vendedor')
        if created:
            self.stdout.write('  - Grupo Vendedor creado')

    def crear_superusuario(self):
        self.stdout.write('Creando superusuario...')
        
        # Verificar si ya existe el superusuario
        if User.objects.filter(username='admin').exists():
            self.stdout.write('El superusuario ya existe. No se creará uno nuevo.')
            return
        
        # Crear superusuario
        try:
            superuser = User.objects.create_superuser(
                username='admin',
                email='mscoronado630@example.com',
                password='+Password20022710'
            )
            
            # Asignar al grupo Administrador
            admin_group = Group.objects.get(name='Administrador')
            superuser.groups.add(admin_group)
            
            self.stdout.write(
                self.style.SUCCESS('  - Superusuario creado exitosamente')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  - Error creando superusuario: {e}')
            )

    def crear_datos_normalizacion(self):
        self.stdout.write('Creando datos de normalización...')
        
        # Crear categorías
        categorias_data = [
            {'nombre': 'Ropa'},
            {'nombre': 'Calzado'},
            {'nombre': 'Accesorios'},
        ]
        
        for cat_data in categorias_data:
            categoria, created = Categoria.objects.get_or_create(
                nombre=cat_data['nombre']
            )
            if created:
                self.stdout.write(f'  - Categoría {categoria.nombre} creada')
        
        # Crear tipos (necesitamos las categorías primero)
        tipos_data = [
            {'nombre': 'Camisetas', 'categoria': 'Ropa'},
            {'nombre': 'Pantalones', 'categoria': 'Ropa'},
            {'nombre': 'Sudaderas', 'categoria': 'Ropa'},
            {'nombre': 'Zapatillas', 'categoria': 'Calzado'},
            {'nombre': 'Botas', 'categoria': 'Calzado'},
            {'nombre': 'Gorras', 'categoria': 'Accesorios'},
            {'nombre': 'Mochilas', 'categoria': 'Accesorios'},
        ]
        
        for tipo_data in tipos_data:
            categoria = Categoria.objects.get(nombre=tipo_data['categoria'])
            tipo, created = Tipo.objects.get_or_create(
                nombre=tipo_data['nombre'],
                categoria=categoria
            )
            if created:
                self.stdout.write(f'  - Tipo {tipo.nombre} creado')
        
        # Crear colores
        colores_data = [
            {'nombre': 'Negro'},
            {'nombre': 'Blanco'},
            {'nombre': 'Azul'},
            {'nombre': 'Rojo'},
            {'nombre': 'Verde'},
            {'nombre': 'Amarillo'},
            {'nombre': 'Gris'},
            {'nombre': 'Marrón'},
        ]
        
        for color_data in colores_data:
            color, created = Color.objects.get_or_create(
                nombre=color_data['nombre']
            )
            if created:
                self.stdout.write(f'  - Color {color.nombre} creado')
        
        # Crear tallas
        tallas_data = [
            {'nombre': 'XS'},
            {'nombre': 'S'},
            {'nombre': 'M'},
            {'nombre': 'L'},
            {'nombre': 'XL'},
            {'nombre': 'XXL'},
            {'nombre': '36'},
            {'nombre': '37'},
            {'nombre': '38'},
            {'nombre': '39'},
            {'nombre': '40'},
            {'nombre': '41'},
            {'nombre': '42'},
            {'nombre': '43'},
            {'nombre': '44'},
        ]
        
        for talla_data in tallas_data:
            talla, created = Talla.objects.get_or_create(
                nombre=talla_data['nombre']
            )
            if created:
                self.stdout.write(f'  - Talla {talla.nombre} creada')
        
        # Crear marcas
        marcas_data = [
            {'nombre': 'Nike'},
            {'nombre': 'Adidas'},
            {'nombre': 'Puma'},
            {'nombre': 'Under Armour'},
            {'nombre': 'Reebok'},
            {'nombre': 'New Balance'},
            {'nombre': 'Converse'},
            {'nombre': 'Vans'},
        ]
        
        for marca_data in marcas_data:
            marca, created = Marca.objects.get_or_create(
                nombre=marca_data['nombre']
            )
            if created:
                self.stdout.write(f'  - Marca {marca.nombre} creada')
        
        # Crear fits
        fits_data = [
            {'nombre': 'Regular'},
            {'nombre': 'Slim'},
            {'nombre': 'Oversized'},
            {'nombre': 'Relaxed'},
            {'nombre': 'Tapered'},
        ]
        
        for fit_data in fits_data:
            fit, created = Fit.objects.get_or_create(
                nombre=fit_data['nombre']
            )
            if created:
                self.stdout.write(f'  - Fit {fit.nombre} creado')
        
        self.stdout.write(
            self.style.SUCCESS('Datos de normalización creados exitosamente!')
        )

    def crear_metodos_pago(self):
        self.stdout.write('Creando métodos de pago...')
        
        # Crear métodos de pago
        metodos_pago_data = [
            {'nombre': 'Efectivo dolares', 'moneda': 'USD', 'requiere_tasa': False},
            {'nombre': 'Efectivo bolívares', 'moneda': 'VES', 'requiere_tasa': True},
            {'nombre': 'Transferencia', 'moneda': 'USD', 'requiere_tasa': False},
            {'nombre': 'Pago movil', 'moneda': 'VES', 'requiere_tasa': True},
            {'nombre': 'Zelle', 'moneda': 'USD', 'requiere_tasa': False},
            {'nombre': 'Binance', 'moneda': 'USD', 'requiere_tasa': False},
            {'nombre': 'Saldo', 'moneda': 'USD', 'requiere_tasa': False},
        ]
        
        for metodo_data in metodos_pago_data:
            metodo, created = MetodoPago.objects.get_or_create(
                nombre=metodo_data['nombre'],
                defaults={
                    'moneda': metodo_data['moneda'],
                    'requiere_tasa': metodo_data['requiere_tasa']
                }
            )
            if created:
                self.stdout.write(f'  - Método de pago {metodo.nombre} creado')
        
        self.stdout.write(
            self.style.SUCCESS('Métodos de pago creados exitosamente!')
        )