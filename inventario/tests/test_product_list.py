import time
from django.test import TestCase
from django.urls import reverse

from inventario.models import Producto, Tipo, Marca, Fit, Color, Talla, Categoria
from inventario.models import CustomUser
class DataTablePerformanceTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Crear usuario para autenticación
        cls.user = CustomUser.objects.create_user(username='testuser', password='testpass')

        cls.categoria = Categoria.objects.create(nombre='Ropa') 
        cls.tipo = Tipo.objects.create(nombre='Camiseta', categoria=cls.categoria)  
        cls.marca = Marca.objects.create(nombre='Nike')
        cls.fit = Fit.objects.create(nombre='Regular')
        cls.color = Color.objects.create(nombre='Rojo')
        cls.talla = Talla.objects.create(nombre='M')

        productos = []
        for i in range(1000):
            productos.append(Producto(
                descripcion=f"Producto de prueba {i}",
                codigo=f"PROD{i:04d}",
                precio_venta=round((i * 1.5) % 300 + 10, 2),
                precio_compra=round((i * 1.2) % 200 + 5, 2),
                stock=i % 25,
                is_active=(i % 3 != 0),
                imagen=None,  # Sin imagen
                tipo=cls.tipo,
                marca=cls.marca,
                fit=cls.fit,
                color=cls.color,
                talla=cls.talla
            ))
        Producto.objects.bulk_create(productos)

    def setUp(self):
        # Login antes de cada test
        self.client.login(username='testuser', password='testpass')

    def test_datatable_serverside_response_time(self):
        url = reverse("producto_ajax")  
        start_time = time.perf_counter()
        response = self.client.get(url, {
            'draw': 1,
            'start': 0,
            'length': 10,
            'search[value]': '',
            'order[0][column]': 0,
            'order[0][dir]': 'asc'
        })
        end_time = time.perf_counter()
        elapsed = end_time - start_time

        print(f"Server-side response time: {elapsed:.4f} seconds")
        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 1.0, "Respuesta demasiado lenta")