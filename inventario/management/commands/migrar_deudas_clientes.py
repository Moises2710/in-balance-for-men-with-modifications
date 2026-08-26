from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import Cliente, Venta, Pago
from decimal import Decimal

class Command(BaseCommand):
    help = 'Migra las deudas de los clientes del campo saldo negativo al campo deuda'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar en modo de prueba sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DE PRUEBA - No se realizarán cambios reales')
            )
        
        with transaction.atomic():
            # Obtener todos los clientes con saldo negativo
            clientes_con_deuda = Cliente.objects.filter(saldo__lt=0)
            
            total_clientes = clientes_con_deuda.count()
            self.stdout.write(f'Encontrados {total_clientes} clientes con saldo negativo')
            
            for cliente in clientes_con_deuda:
                deuda_actual = abs(cliente.saldo)  # Convertir saldo negativo a deuda positiva
                
                self.stdout.write(
                    f'Cliente: {cliente.nombre} - Saldo actual: ${cliente.saldo} - Deuda a migrar: ${deuda_actual}'
                )
                
                if not dry_run:
                    # Migrar la deuda
                    cliente.deuda = deuda_actual
                    cliente.saldo = Decimal('0')  # Resetear saldo a 0
                    cliente.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Migrado: {cliente.nombre} - Nueva deuda: ${cliente.deuda}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'[DRY RUN] Se migraría: {cliente.nombre} - Deuda: ${deuda_actual}')
                    )
            
            # Verificar ventas no pagadas y actualizar deudas
            ventas_no_pagadas = Venta.objects.filter(pagado=False)
            self.stdout.write(f'\nVerificando {ventas_no_pagadas.count()} ventas no pagadas...')
            
            for venta in ventas_no_pagadas:
                total_pagado = sum(pago.monto_usd for pago in venta.pago_set.all())
                faltante = venta.total - total_pagado
                
                if faltante > 0:
                    self.stdout.write(
                        f'Venta #{venta.id} - Cliente: {venta.cliente.nombre} - Faltante: ${faltante}'
                    )
                    
                    if not dry_run:
                        # Agregar faltante a la deuda del cliente
                        venta.cliente.deuda += faltante
                        venta.cliente.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Actualizada deuda: {venta.cliente.nombre} - Nueva deuda: ${venta.cliente.deuda}')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'[DRY RUN] Se agregaría ${faltante} a la deuda de {venta.cliente.nombre}')
                        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nMIGRACIÓN COMPLETADA EN MODO DE PRUEBA')
            )
            self.stdout.write(
                'Para ejecutar la migración real, ejecute el comando sin --dry-run'
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\nMIGRACIÓN COMPLETADA EXITOSAMENTE')
            )

