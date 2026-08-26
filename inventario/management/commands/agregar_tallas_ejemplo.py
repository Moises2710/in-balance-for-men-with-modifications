from django.core.management.base import BaseCommand
from inventario.models import Talla, Categoria

class Command(BaseCommand):
    help = 'Agrega tallas de ejemplo para demostrar la diferencia entre tren superior e inferior'

    def handle(self, *args, **options):
        # Crear categorías si no existen
        tren_superior, created = Categoria.objects.get_or_create(
            nombre='Tren Superior',
            defaults={'nombre': 'Tren Superior'}
        )
        
        tren_inferior, created = Categoria.objects.get_or_create(
            nombre='Tren Inferior',
            defaults={'nombre': 'Tren Inferior'}
        )

        # Tallas de tren superior (letras)
        tallas_superior = [
            'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL'
        ]

        # Tallas de tren inferior (números)
        tallas_inferior = [
            '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42', '43', '44'
        ]

        # Crear tallas de tren superior
        for talla_nombre in tallas_superior:
            talla, created = Talla.objects.get_or_create(
                nombre=talla_nombre,
                defaults={'nombre': talla_nombre}
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Talla de tren superior creada: {talla_nombre}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Talla de tren superior ya existe: {talla_nombre}')
                )

        # Crear tallas de tren inferior
        for talla_nombre in tallas_inferior:
            talla, created = Talla.objects.get_or_create(
                nombre=talla_nombre,
                defaults={'nombre': talla_nombre}
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Talla de tren inferior creada: {talla_nombre}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Talla de tren inferior ya existe: {talla_nombre}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Proceso completado!\n'
                f'📊 Resumen:\n'
                f'   • Tallas de tren superior: {len(tallas_superior)} (XS, S, M, L, XL, XXL, XXXL)\n'
                f'   • Tallas de tren inferior: {len(tallas_inferior)} (26, 28, 30, 32, 34, 36, 38, 40, 42, 44)\n'
                f'   • Total de tallas: {Talla.objects.count()}\n\n'
                f'🎯 Ahora puedes probar el formulario de añadir cliente para ver la leyenda en acción!'
            )
        ) 