"""
Comando Django para configurar permisos del sistema
Funciona con PostgreSQL/Supabase en producción
Ejecutar con: python manage.py configurar_permisos
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection


class Command(BaseCommand):
    help = 'Configura permisos para Administrador y Vendedor en producción'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Resetear permisos antes de configurar'
        )
        parser.add_argument(
            '--grupo',
            type=str,
            choices=['administrador', 'vendedor', 'todos'],
            default='todos',
            help='Grupo específico a configurar'
        )

    def handle(self, *args, **options):
        reset = options['reset']
        grupo = options['grupo']
        
        self.stdout.write('🔧 Configurando permisos del sistema...')
        
        try:
            if reset:
                self.reset_permisos()
            
            if grupo in ['administrador', 'todos']:
                self.configurar_administrador()
                
            if grupo in ['vendedor', 'todos']:
                self.configurar_vendedor()
                
            self.stdout.write(
                self.style.SUCCESS('🎉 ¡Permisos configurados exitosamente!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {e}')
            )
            raise

    def reset_permisos(self):
        """Resetea todos los permisos de los grupos"""
        self.stdout.write('🧹 Reseteando permisos...')
        
        grupos = ['Administrador', 'Vendedor']
        for nombre_grupo in grupos:
            try:
                grupo = Group.objects.get(name=nombre_grupo)
                grupo.permissions.clear()
                self.stdout.write(f'✅ Permisos de {nombre_grupo} reseteados')
            except Group.DoesNotExist:
                self.stdout.write(f'⚠️ Grupo {nombre_grupo} no existe')

    def configurar_administrador(self):
        """Configura permisos para Administrador - TODOS los permisos"""
        self.stdout.write('\n👑 Configurando Administrador...')
        
        grupo_admin, created = Group.objects.get_or_create(name='Administrador')
        if created:
            self.stdout.write('✅ Grupo Administrador creado')
        else:
            self.stdout.write('✅ Grupo Administrador ya existe')
        
        # Obtener todos los permisos de inventario
        content_types = ContentType.objects.filter(app_label='inventario')
        todos_permisos = Permission.objects.filter(content_type__in=content_types)
        
        grupo_admin.permissions.set(todos_permisos)
        self.stdout.write(f'✅ {len(todos_permisos)} permisos asignados a Administrador')

    def configurar_vendedor(self):
        """Configura permisos para Vendedor - Solo ver y añadir"""
        self.stdout.write('\n👤 Configurando Vendedor...')
        
        grupo_vendedor, created = Group.objects.get_or_create(name='Vendedor')
        if created:
            self.stdout.write('✅ Grupo Vendedor creado')
        else:
            self.stdout.write('✅ Grupo Vendedor ya existe')
        
        # Modelos que el vendedor puede manejar
        modelos_vendedor = [
            'producto', 'cliente', 'venta', 'detalleventa', 
            'pago', 'devolucion', 'detalledevolucion', 'metodopago'
        ]
        
        # Tipos de permisos: solo view y add
        tipos_permisos = ['view', 'add']
        
        permisos_vendedor = []
        
        for modelo in modelos_vendedor:
            try:
                content_type = ContentType.objects.get(
                    app_label='inventario',
                    model=modelo
                )
                
                permisos_modelo = []
                for tipo_permiso in tipos_permisos:
                    codename = f'{tipo_permiso}_{modelo}'
                    try:
                        permiso = Permission.objects.get(
                            content_type=content_type,
                            codename=codename
                        )
                        permisos_modelo.append(permiso)
                    except Permission.DoesNotExist:
                        self.stdout.write(f'⚠️ Permiso {codename} no encontrado')
                
                permisos_vendedor.extend(permisos_modelo)
                permisos_str = ', '.join(tipos_permisos)
                self.stdout.write(f'   ✅ {modelo}: {permisos_str}')
                
            except ContentType.DoesNotExist:
                self.stdout.write(f'   ❌ {modelo}: no encontrado')
        
        grupo_vendedor.permissions.set(permisos_vendedor)
        self.stdout.write(f'✅ {len(permisos_vendedor)} permisos asignados a Vendedor')

    def mostrar_resumen(self):
        """Muestra un resumen de los permisos configurados"""
        self.stdout.write('\n📊 Resumen de permisos:')
        
        grupos = Group.objects.all()
        for grupo in grupos:
            self.stdout.write(f'\n👥 {grupo.name}:')
            permisos = grupo.permissions.all()
            if permisos:
                self.stdout.write(f'   Total: {len(permisos)} permisos')
                # Mostrar algunos ejemplos
                for permiso in permisos[:5]:
                    self.stdout.write(f'   - {permiso.content_type.model}: {permiso.codename}')
                if len(permisos) > 5:
                    self.stdout.write(f'   ... y {len(permisos) - 5} más')
            else:
                self.stdout.write('   Sin permisos asignados')