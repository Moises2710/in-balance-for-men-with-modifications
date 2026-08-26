from django.core.management.base import BaseCommand
from inventario.models import Venta
from decimal import Decimal
from django.db.models import Sum

class Command(BaseCommand):
    help = 'Debug comisiones para verificar cálculo'

    def handle(self, *args, **options):
        self.stdout.write('=== DEBUG COMISIONES ===')
        
        # Mostrar todas las ventas con sus comisiones
        ventas = Venta.objects.all().order_by('-fecha')[:10]
        
        self.stdout.write(f'Total ventas: {Venta.objects.count()}')
        self.stdout.write(f'Ventas con comision > 0: {Venta.objects.filter(comision__gt=0).count()}')
        self.stdout.write(f'Ventas con estado_comision="pagado": {Venta.objects.filter(estado_comision="pagado").count()}')
        
        self.stdout.write('\n--- Últimas 10 ventas ---')
        for venta in ventas:
            self.stdout.write(f'Venta {venta.id}: total=${venta.total}, comision=${venta.comision}, estado={venta.estado_comision}, fecha={venta.fecha}')
        
        # Verificar cálculo manual
        self.stdout.write('\n--- Verificación cálculo ---')
        for venta in ventas[:3]:
            calculo_manual = venta.total * Decimal('0.10')
            self.stdout.write(f'Venta {venta.id}: ${venta.total} * 0.10 = ${calculo_manual} (guardado: ${venta.comision})')
        
        # Sumar comisiones pagadas
        comisiones_pagadas = Venta.objects.filter(estado_comision='pagado').aggregate(
            total=Sum('comision')
        )['total'] or Decimal('0')
        
        self.stdout.write(f'\nTotal comisiones pagadas: ${comisiones_pagadas}')
