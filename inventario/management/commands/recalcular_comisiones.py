from django.core.management.base import BaseCommand
from inventario.models import Venta
from decimal import Decimal, ROUND_HALF_UP

class Command(BaseCommand):
    help = 'Recalcula las comisiones de todas las ventas existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula los cambios sin guardarlos en la base de datos.',
        )

    def handle(self, *args, **options):
        self.stdout.write('Recalculando comisiones...')
        dry_run = options['dry_run']
        
        ventas = Venta.objects.all()
        total_ventas = ventas.count()
        updated_count = 0
        
        self.stdout.write(f'Procesando {total_ventas} ventas...')
        
        for venta in ventas:
            old_comision = venta.comision
            
            # Recalcular comisión
            if venta.total is not None:
                nueva_comision = (venta.total * Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                venta.comision = nueva_comision
                
                if not dry_run:
                    venta.save(update_fields=['comision'])
                
                if venta.comision != old_comision:
                    updated_count += 1
                    self.stdout.write(f'  Venta {venta.id}: comision de {old_comision} a {venta.comision}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Modo Dry-run: Los cambios no se guardaron.'))
        else:
            self.stdout.write(self.style.SUCCESS('Comisiones recalculadas exitosamente.'))
        
        self.stdout.write(f'{updated_count} ventas actualizadas.')

