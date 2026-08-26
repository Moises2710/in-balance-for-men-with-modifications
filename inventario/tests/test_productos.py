import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.utils.crypto import get_random_string
from django.test import TestCase, override_settings
from PIL import Image
from io import BytesIO
import tempfile
import os
import decimal
import shutil
from django.db import connection

from inventario.models import Producto, Tipo, Marca, Fit, Color, Talla, Categoria, Etiqueta, Cliente, Devolucion, GastoAdministrativo, Venta, DetalleVenta

# Configuración para usar un directorio temporal para MEDIA_ROOT durante las pruebas
TEST_MEDIA_ROOT = tempfile.mkdtemp()

# --------------------------
# Funciones de utilidad para tests
# --------------------------

def create_test_image():
    """Crea una imagen de prueba en memoria"""
    image = Image.new('RGB', (100, 100), color='red')
    image_file = BytesIO()
    image.save(image_file, 'JPEG')
    image_file.seek(0)
    return SimpleUploadedFile('test.jpg', image_file.getvalue(), content_type='image/jpeg')

def get_sql_queries():
    """Obtiene las consultas SQL ejecutadas (para pruebas de inyección)"""
    return [q['sql'] for q in connection.queries]

# --------------------------
# Clases de Test
# --------------------------

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ProductoBaseTestCase(TestCase):
    """Clase base con configuración común para todos los tests de Producto"""
    
    @classmethod
    def setUpTestData(cls):
        # Configuración inicial para todos los tests
        cls.categoria = Categoria.objects.create(nombre='Ropa') 
        cls.tipo = Tipo.objects.create(nombre='Camiseta', categoria=cls.categoria)  
        cls.marca = Marca.objects.create(nombre='Nike')
        cls.fit = Fit.objects.create(nombre='Regular')
        cls.color = Color.objects.create(nombre='Rojo')
        cls.talla = Talla.objects.create(nombre='M')
        
        cls.producto = Producto.objects.create(
            descripcion='Camiseta deportiva',
            codigo='NIK001',
            precio_venta=29.99,
            precio_compra=15.00,
            stock=50,
            tipo=cls.tipo,
            marca=cls.marca,
            fit=cls.fit,
            color=cls.color,
            talla=cls.talla
        )

    @classmethod
    def tearDownClass(cls):
        # Eliminar el directorio temporal después de todas las pruebas
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()


class ProductoModelTests(ProductoBaseTestCase):
    """Tests para funcionalidad básica del modelo Producto"""
    
    def test_creacion_basica(self):
        """Test que verifica la creación básica de un producto"""
        self.assertEqual(self.producto.descripcion, 'Camiseta deportiva')
        self.assertEqual(self.producto.codigo, 'NIK001')
        self.assertEqual(float(self.producto.precio_venta), 29.99)
        self.assertEqual(float(self.producto.precio_compra), 15.00)
        self.assertEqual(self.producto.stock, 50)
        self.assertTrue(self.producto.is_active)

    def test_relaciones_clave_foranea(self):
        """Test que verifica las relaciones con otros modelos"""
        self.assertEqual(self.producto.tipo, self.tipo)
        self.assertEqual(self.producto.marca, self.marca)
        self.assertEqual(self.producto.fit, self.fit)
        self.assertEqual(self.producto.color, self.color)
        self.assertEqual(self.producto.talla, self.talla)

    def test_foreign_key_null(self):
        """Test que verifica que las claves foráneas pueden ser nulas"""
        producto = Producto.objects.create(
            descripcion='Producto sin relaciones',
            codigo='NRL001',
            precio_venta=10.00,
            precio_compra=5.00,
            stock=20
        )
        
        self.assertIsNone(producto.tipo)
        self.assertIsNone(producto.marca)
        self.assertIsNone(producto.fit)
        self.assertIsNone(producto.color)
        self.assertIsNone(producto.talla)


class ProductoValidationTests(ProductoBaseTestCase):
    """Tests para validación de datos del modelo Producto"""
    
    def test_codigo_unique_constraint(self):
        """Test que verifica que el código debe ser único"""
        with self.assertRaises(Exception):
            Producto.objects.create(
                descripcion='Otra camiseta',
                codigo='NIK001',  # Mismo código que el producto existente
                precio_venta=25.00,
                precio_compra=12.00,
                stock=30
            )

    def test_precio_venta_min_value(self):
        """Test que verifica que el precio de venta no puede ser negativo"""
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Producto inválido',
                codigo='INV001',
                precio_venta=-10.00,
                precio_compra=5.00,
                stock=10
            )
            producto.full_clean()

    def test_precio_compra_min_value(self):
        """Test que verifica que el precio de compra no puede ser negativo"""
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Producto inválido',
                codigo='INV002',
                precio_venta=15.00,
                precio_compra=-5.00,
                stock=10
            )
            producto.full_clean()

    def test_stock_positive(self):
        """Test que verifica que el stock no puede ser negativo"""
        # Intentar crear con stock negativo debería fallar
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Producto inválido',
                codigo='INV003',
                precio_venta=15.00,
                precio_compra=10.00,
                stock=-5
            )
            producto.full_clean()

    def test_is_active_default(self):
        """Test que verifica que is_active tiene el valor por defecto correcto"""
        producto = Producto.objects.create(
            descripcion='Producto activo',
            codigo='ACT001',
            precio_venta=10.00,
            precio_compra=5.00,
            stock=20
        )
        
        self.assertTrue(producto.is_active)

    def test_descripcion_optional(self):
        """Test que verifica que la descripción puede ser nula"""
        producto = Producto.objects.create(
            descripcion=None,
            codigo='OPT001',
            precio_venta=10.00,
            precio_compra=5.00,
            stock=20
        )
        
        self.assertIsNone(producto.descripcion)


class ProductoEdgeCasesTests(ProductoBaseTestCase):
    """Tests para casos límite del modelo Producto"""
    
    def test_precio_compra_max_digits(self):
        """Test que verifica los límites máximos de los campos"""
        # Precio con 10 dígitos (máximo permitido) - 99999999.99
        max_price = decimal.Decimal('99999999.99')
        producto = Producto.objects.create(
            descripcion='Producto carísimo',
            codigo='EXP001',
            precio_venta=100.00,
            precio_compra=max_price,
            stock=1
        )
        self.assertEqual(producto.precio_compra, max_price)
        
        # Intentar exceder el límite de dígitos (11 dígitos - 100000000.00)
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Producto inválido',
                codigo='INV005',
                precio_venta=100.00,
                precio_compra=100000000.00,
                stock=1
            )
            producto.full_clean()

    def test_precio_venta_max_digits(self):
        """Test que verifica el límite máximo de dígitos para precio_venta"""
        # Precio con 10 dígitos (máximo permitido) - 99999999.99
        max_price = decimal.Decimal('99999999.99')
        producto = Producto.objects.create(
            descripcion='Producto carísimo',
            codigo='EXP001',
            precio_venta=max_price,
            precio_compra=100.00,
            stock=1
        )
        self.assertEqual(producto.precio_venta, max_price)
        
        # Intentar exceder el límite de dígitos (11 dígitos - 100000000.00)
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Producto inválido',
                codigo='INV005',
                precio_venta=100000000.00,
                precio_compra=100.00,
                stock=1
            )
            producto.full_clean()

    def test_stock_max_value(self):
        """Test que verifica el valor máximo para stock"""
        # Máximo valor para PositiveIntegerField (2147483647)
        max_stock = 1000 #Máximo valor para stock
        producto = Producto.objects.create(
            descripcion='Producto en grandes cantidades',
            codigo='BULK001',
            precio_venta=1.00,
            precio_compra=0.50,
            stock=max_stock
        )
        self.assertEqual(producto.stock, max_stock)
        
        # Intentar exceder el límite
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Producto inválido',
                codigo='INV006',
                precio_venta=1.00,
                precio_compra=0.50,
                stock=10001  # Excede el límite
            )
            producto.full_clean()

    def test_codigo_max_length(self):
        """Test que verifica el límite máximo de caracteres para código"""
        # Código con exactamente 20 caracteres (máximo permitido)
        max_code = 'A' * 20
        producto = Producto.objects.create(
            descripcion='Código largo',
            codigo=max_code,
            precio_venta=10.00,
            precio_compra=5.00,
            stock=10
        )
        self.assertEqual(len(producto.codigo), 20)
        
        # Intentar exceder el límite
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Código demasiado largo',
                codigo='B' * 21,  # 21 caracteres
                precio_venta=10.00,
                precio_compra=5.00,
                stock=10
            )
            producto.full_clean()

    def test_descripcion_max_length(self):
        """Test que verifica el límite máximo de caracteres para descripción"""
        # Descripción con exactamente 30 caracteres (máximo permitido)
        max_desc = 'C' * 30
        producto = Producto.objects.create(
            descripcion=max_desc,
            codigo='LONGDESC',
            precio_venta=10.00,
            precio_compra=5.00,
            stock=10
        )
        self.assertEqual(len(producto.descripcion), 30)
        
        # Intentar exceder el límite
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='D' * 31,  # 31 caracteres
                codigo='INV007',
                precio_venta=10.00,
                precio_compra=5.00,
                stock=10
            )
            producto.full_clean()

    def test_duplicate_codigo_case_insensitive(self):
        """Test que verifica que el código es único insensible a mayúsculas/minúsculas"""
        Producto.objects.create(
            descripcion='Producto original',
            codigo='abc123',
            precio_venta=10.00,
            precio_compra=5.00,
            stock=10
        )
        
        # Intentar crear con mismo código en mayúsculas
        with self.assertRaises(IntegrityError):
            Producto.objects.create(
                descripcion='Producto duplicado',
                codigo='ABC123',  # Mismo código en mayúsculas
                precio_venta=15.00,
                precio_compra=7.00,
                stock=5
            )

    def test_zero_values(self):
        """Test que verifica valores cero en campos numéricos"""
        # Precio venta/compra cero permitido
        producto = Producto.objects.create(
            descripcion='Producto gratis',
            codigo='FREE001',
            precio_venta=0,
            precio_compra=0,
            stock=0
        )
        self.assertEqual(float(producto.precio_venta), 0.0)
        self.assertEqual(float(producto.precio_compra), 0.0)
        self.assertEqual(producto.stock, 0)

    def test_foreign_key_cascade_behavior(self):
        """Test que verifica el comportamiento cuando se elimina una relación"""
        # Crear producto con relaciones
        producto = Producto.objects.create(
            descripcion='Producto con relaciones',
            codigo='REL001',
            precio_venta=20.00,
            precio_compra=10.00,
            stock=15,
            tipo=self.tipo,
            marca=self.marca
        )
        
        # Eliminar el tipo
        self.tipo.delete()
        producto.refresh_from_db()
        
        # Verificar que el campo tipo es nulo (on_delete=models.SET_NULL)
        self.assertIsNone(producto.tipo)
        
        # La marca debería seguir existiendo
        self.assertIsNotNone(producto.marca)

    def test_codigo_rechaza_caracteres_invalidos(self):
        """Test que verifica que el campo código rechace caracteres especiales, emojis, tildes, ñ, etc."""
        invalid_codes = [
            '!@#$%^&*()_+',
            'código-con-ñ',
            'espacio código',
            '空间代码',       # Caracteres chinos
            '😊👍🌟',        # Emojis
            'abc.def',      # Punto
            'abc/def',      # Slash
            'áéíóúñÑ',      # Tildes y ñ
        ]
        
        for code in invalid_codes:
            with self.subTest(code=code):
                producto = Producto(
                    descripcion=f'Producto inválido: {code}',
                    codigo=code,
                    precio_venta=10.00,
                    precio_compra=5.00,
                    stock=10
                )
                with self.assertRaises(ValidationError):
                    producto.full_clean()  # Lanza ValidationError si el código no pasa la validación


class ProductoImageTests(ProductoBaseTestCase):
    """Tests específicos para manejo de imágenes en Producto"""
    
    def test_imagen_upload(self):
        """Test que verifica la subida de imágenes"""
        test_image = create_test_image()
        
        producto = Producto.objects.create(
            descripcion='Producto con imagen',
            codigo='IMG001',
            precio_venta=20.00,
            precio_compra=10.00,
            stock=15,
            imagen=test_image
        )
        
        self.assertTrue(producto.imagen)
        self.assertTrue(producto.thumbnail)
        self.assertIn('images/productos/', producto.imagen.name)

    def test_imagen_validation(self):
        """Test que verifica la validación de formatos de imagen"""
        invalid_file = SimpleUploadedFile('test.txt', b'file_content', content_type='text/plain')
        
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Producto inválido',
                codigo='INV004',
                precio_venta=15.00,
                precio_compra=10.00,
                stock=5,
                imagen=invalid_file
            )
            producto.full_clean()

    def test_imagen_extremely_large(self):
        """Test que verifica una imagen extremadamente grande (más de 10MB)"""
        # Crear una imagen grande (12MB+)
        large_image = SimpleUploadedFile(
            'huge_image.jpg',
            b'\0' * 14 * 1024 * 1024,  # 14MB de datos nulos
            content_type='image/jpeg'
        )
        
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Imagen enorme',
                codigo='BIGIMG',
                precio_venta=10.00,
                precio_compra=5.00,
                stock=10,
                imagen=large_image
            )
            producto.full_clean()

    def test_imagen_with_invalid_extension_but_valid_content(self):
        """Test que verifica una imagen con extensión incorrecta pero contenido válido"""
        # Crear una imagen JPEG real pero con extensión .txt
        image = Image.new('RGB', (100, 100), color='blue')
        image_file = BytesIO()
        image.save(image_file, 'JPEG')
        image_file.seek(0)
        
        invalid_extension_file = SimpleUploadedFile(
            'valid_image.txt',  # Extensión incorrecta
            image_file.getvalue(),
            content_type='image/jpeg'  # Pero tipo MIME correcto
        )
        
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Imagen extensión inválida',
                codigo='EXTINV',
                precio_venta=10.00,
                precio_compra=5.00,
                stock=10,
                imagen=invalid_extension_file
            )
            producto.full_clean()

    def test_validacion_formato_imagen(self):
        """Test que verifica la validación de formatos de imagen"""
        invalid_file = SimpleUploadedFile('test.txt', b'file_content', content_type='text/plain')
        
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Producto inválido',
                codigo='INV004',
                precio_venta=15.00,
                precio_compra=10.00,
                stock=5,
                imagen=invalid_file
            )
            producto.full_clean()


class SecurityTests(TestCase):
    """Tests específicos de seguridad (XSS, SQLi, etc.)"""
    
    @classmethod
    def setUpTestData(cls):
        # Configuración común para tests de seguridad
        cls.categoria = Categoria.objects.create(nombre='Ropa')
        cls.tipo = Tipo.objects.create(nombre='Camiseta', categoria=cls.categoria)
        cls.marca = Marca.objects.create(nombre='Nike')
        cls.fit = Fit.objects.create(nombre='Regular')
        cls.color = Color.objects.create(nombre='Rojo')
        cls.talla = Talla.objects.create(nombre='M')
    
    def get_unique_code(self):
        """Genera un código único para pruebas"""
        return f"TEST_{get_random_string(5)}"
    
    def test_proteccion_xss(self):
        """Test que verifica la protección contra XSS"""
        xss_attacks = [
            '<script>alert("XSS")</script>',
            '<img src="x" onerror="alert(1)">',
            '<a href="javascript:alert(1)">click</a>',
            '"><script>alert(1)</script>',
            '\'><script>alert(1)</script>',
            'javascript:alert(1)',
            'onload=alert(1)',
            'eval(String.fromCharCode(97,108,101,114,116,40,49,41))'
        ]
        
        for attack in xss_attacks:
            with self.subTest(attack=attack):
                # Crear producto con input malicioso
                producto = Producto.objects.create(
                    descripcion=attack,
                    codigo=self.get_unique_code(),
                    precio_venta=10.00,
                    precio_compra=5.00,
                    stock=10
                )
                
                # Verificar que el contenido peligroso fue neutralizado
                self.assertNotIn('<script>', producto.descripcion)
                self.assertNotIn('javascript:', producto.descripcion)
                self.assertNotIn('onerror', producto.descripcion)
                self.assertNotIn('eval(', producto.descripcion)
                

class ComprehensiveSecurityTests(TestCase):
    """Pruebas exhaustivas de seguridad para todos los campos de texto en los modelos"""
    
    @classmethod
    def setUpTestData(cls):
        # Configuración común para todas las pruebas
        cls.categoria = Categoria.objects.create(nombre='Ropa')
        cls.tipo = Tipo.objects.create(nombre='Camiseta', categoria=cls.categoria)
        cls.marca = Marca.objects.create(nombre='MarcaPrueba')
        cls.fit = Fit.objects.create(nombre='FitPrueba')
        cls.color = Color.objects.create(nombre='ColorPrueba')
        cls.talla = Talla.objects.create(nombre='TallaPrueba')
        cls.etiqueta = Etiqueta.objects.create(nombre='EtiquetaPrueba')
        
        # Crear un producto base para relaciones
        cls.producto = Producto.objects.create(
            descripcion='Producto prueba',
            codigo='TEST001',
            precio_venta=10.00,
            precio_compra=5.00,
            stock=10,
            tipo=cls.tipo,
            marca=cls.marca,
            fit=cls.fit,
            color=cls.color,
            talla=cls.talla
        )
        
        # Crear un cliente base
        cls.cliente = Cliente.objects.create(
            nombre='Cliente prueba',
            identificacion=12345678,
            telefono='+1234567890'
        )
        
        # Crear una venta base
        cls.venta = Venta.objects.create(
            subtotal=100.00,
            descuento=0.00,
            comision=0.00,
            cliente=cls.cliente,
            user=None
        )
        
        # Crear un detalle de venta
        cls.detalle_venta = DetalleVenta.objects.create(
            venta=cls.venta,
            producto=cls.producto,
            precio_unitario=10.00,
            cantidad=1
        )

    def get_unique_identificacion(self):
        """Genera un número de identificación único para pruebas"""
        return random.randint(10000000, 99999999)
    
    def test_xss_protection_in_all_models(self):
        """Verifica protección XSS en todos los campos de texto relevantes"""
        xss_attacks = [
            '<script>alert("XSS")</script>',
            '<img src="x" onerror="alert(1)">',
            '<a href="javascript:alert(1)">click</a>',
            '"><script>alert(1)</script>',
            '\'><script>alert(1)</script>',
            'javascript:alert(1)',
            'onload=alert(1)',
            'eval(String.fromCharCode(97,108,101,114,116,40,49,41))'
        ]
        
        for i, attack in enumerate(xss_attacks):
            with self.subTest(attack=attack):
                # Categoria
                cat = Categoria.objects.create(nombre=f"Cat{i} {attack[:20]}")
                self.assert_protected(cat.nombre)
                
                # Tipo
                tipo = Tipo.objects.create(nombre=f"Tipo{i} {attack[:20]}", categoria=self.categoria)
                self.assert_protected(tipo.nombre)
                
                # Marca
                marca = Marca.objects.create(nombre=f"Marca{i} {attack[:20]}")
                self.assert_protected(marca.nombre)
                
                # Fit
                fit = Fit.objects.create(nombre=f"Fit{i} {attack[:20]}")
                self.assert_protected(fit.nombre)
                
                # Color
                color = Color.objects.create(nombre=f"Color{i} {attack[:20]}")
                self.assert_protected(color.nombre)
                
                # Talla (limitado por max_length)
                talla_nombre = f"T{i} {attack[:7]}"  # Ajuste para max_length=12
                talla = Talla.objects.create(nombre=talla_nombre)
                self.assert_protected(talla.nombre)
                
                # Etiqueta
                etiqueta_nombre = f"ETQ{i} {attack[:35]}"  # Ajuste para max_length=40
                etiqueta = Etiqueta.objects.create(nombre=etiqueta_nombre)
                self.assert_protected(etiqueta.nombre)
                
                # Producto
                producto = Producto.objects.create(
                    descripcion=attack[:30],  # Ajuste para max_length=30
                    codigo=f"XSS{i:03d}",
                    precio_venta=10.00,
                    precio_compra=5.00,
                    stock=10
                )
                if producto.descripcion:
                    self.assert_protected(producto.descripcion)
                
                # Devolución
                devolucion = Devolucion.objects.create(
                    motivo=attack[:300],  # Ajuste para max_length=300
                    cantidad_producto=1,
                    monto=10.00,
                    detalle_venta=self.detalle_venta
                )
                self.assert_protected(devolucion.motivo)
                
                # Gasto Administrativo
                gasto = GastoAdministrativo.objects.create(
                    nombre=attack[:1000],  # Ajuste para max_length=1000
                    monto=10.00
                )
                self.assert_protected(gasto.nombre)
    
    def assert_protected(self, field_value):
        """Método auxiliar para verificar que un campo está protegido contra XSS"""
        if field_value is None:
            return
            
        self.assertNotIn('<script>', field_value)
        self.assertNotIn('javascript:', field_value)
        self.assertNotIn('onerror', field_value)
        self.assertNotIn('onload', field_value)
        self.assertNotIn('eval(', field_value)
        self.assertNotIn('alert(', field_value)
        
        # Verificar que el contenido HTML peligroso fue escapado o eliminado
        self.assertTrue(
            not any(tag in field_value for tag in ['<', '>', '"', "'"]),
            f"Se encontraron caracteres peligrosos en el campo: {field_value}"
        )


class SQLSecurityTests(TestCase):

    def test_proteccion_sql_injection(self):
            """Test que verifica la protección contra inyección SQL"""
            # Ejemplo de payloads SQLi comunes
            sql_injection_attempts = [
                "' OR '1'='1",
                "' OR 1=1 --",
                "'; DROP TABLE inventario_producto; --",
                "' UNION SELECT username, password FROM auth_user --",
                "' OR EXISTS(SELECT * FROM information_schema.tables) --"
            ]
            
            for attempt in sql_injection_attempts:
                with self.subTest(attempt=attempt):
                    # Resetear las queries registradas
                    connection.queries = []
                    
                    # Intentar buscar con inyección SQL
                    with self.assertRaises(Producto.DoesNotExist):
                        Producto.objects.get(codigo=attempt)
                    
                    # Verificar que no se ejecutó SQL peligroso
                    queries = get_sql_queries()
                    for query in queries:
                        self.assertNotIn('DROP', query)
                        self.assertNotIn('UNION', query)
                        self.assertNotIn('information_schema', query)
                    
                    # Verificar que la consulta fue parametrizada
                    if queries:
                        self.assertIn('%s', queries[0])  # Django usa parámetros

    def test_proteccion_sql_injection_through_relations(self):
        """Test que verifica SQLi a través de relaciones"""
        malicious_input = "1' OR '1'='1"
        
        # Intentar explotar a través de relaciones
        with self.assertRaises(Tipo.DoesNotExist):
            tipo = Tipo.objects.get(id=malicious_input)
        
        # Verificar que no se ejecutó SQL peligroso
        queries = get_sql_queries()
        for query in queries:
            self.assertNotIn('1=1', query)

    def test_proteccion_contra_orm_injection(self):
        """Test que verifica intentos de inyección a través del ORM"""
        from django.db.models import Q
        
        # Intentar crear un objeto con campos maliciosos
        with self.assertRaises(ValidationError):
            Producto.objects.create(
                descripcion="Valid description",
                codigo="NORMAL123",
                precio_venta="10.00",
                precio_compra="5.00",
                stock="10",
                tipo_id="1' OR '1'='1"  # Intento de inyección
            )
        
        # Intentar usar Q objects con input malicioso
        try:
            Producto.objects.filter(Q(codigo__contains="' OR '1'='1"))
        except Exception as e:
            self.fail(f"El ORM no debería permitir inyección SQL: {e}")

    def test_proteccion_codigo_malicioso(self):
        """Test que verifica que el campo código rechace caracteres peligrosos"""
        codigos_maliciosos = [
            "'; DROP TABLE inventario_producto; --",
            "' OR 1=1 --",
            "<script>alert(1)</script>",
            "1' UNION SELECT username, password FROM auth_user --"
        ]
        
        for codigo in codigos_maliciosos:
            with self.subTest(codigo=codigo):
                with self.assertRaises(ValidationError):
                    producto = Producto(
                        descripcion="Producto de prueba",
                        codigo=codigo,
                        precio_venta=10.00,
                        precio_compra=5.00,
                        stock=10
                    )
                    producto.full_clean()

    def test_unicode_attack_protection(self):
        """Test que verifica protección contra ataques con Unicode especial"""
        unicode_attacks = [
            "𝗨𝗻𝗶𝗰𝗼𝗱𝗲 𝗧𝗿𝗶𝗰𝗸𝘀",  # Unicode bold
            "ℹ ™ №",           # Caracteres especiales
            "𝒮𝒸𝓇𝒾𝓅𝓉",         # Unicode script
            "𝕏𝕊𝕊",             # Unicode double-struck
            "Ｕｎｉｃｏｄｅ"     # Unicode fullwidth
        ]
        
        for attack in unicode_attacks:
            with self.subTest(attack=attack):
                # Crear producto con input Unicode
                producto = Producto.objects.create(
                    descripcion=attack,
                    codigo=self.get_unique_code(),
                    precio_venta=10.00,
                    precio_compra=5.00,
                    stock=10
                )
                
                # Verificar que el contenido fue sanitizado
                self.assertNotEqual(producto.descripcion, attack)
                self.assertNotIn('<', producto.descripcion)
                self.assertNotIn('>', producto.descripcion)

    def test_imagen_svg_xss_protection(self):
        """Test que verifica protección contra XSS en SVG"""
        malicious_svg = """<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>"""
        
        svg_file = SimpleUploadedFile(
            'test.svg',
            malicious_svg.encode(),
            content_type='image/svg+xml'
        )
        
        with self.assertRaises(ValidationError):
            producto = Producto(
                descripcion='Imagen SVG peligrosa',
                codigo='SVGXSS',
                precio_venta=10.00,
                precio_compra=5.00,
                stock=10,
                imagen=svg_file
            )
            producto.full_clean()


class SpecialCharactersTestCase(TestCase):
    """Tests para verificar que caracteres especiales legítimos se mantienen"""
    
    @classmethod
    def setUpTestData(cls):
        # Configuración común para tests de caracteres especiales
        cls.categoria = Categoria.objects.create(nombre='Ropa')
        cls.tipo = Tipo.objects.create(nombre='Camiseta', categoria=cls.categoria)
        cls.color = Color.objects.create(nombre='Rojo')
        cls.talla = Talla.objects.create(nombre='M')
    
    def test_marca_special_characters(self):
        """Test que verifica que las marcas mantengan caracteres especiales"""
        special_marcas = [
            "Levi's",
            "Abercrombie & Fitch", 
            "H&M",
            "Tommy Hilfiger",
            "Calvin Klein"
        ]
        
        for marca_nombre in special_marcas:
            with self.subTest(marca=marca_nombre):
                marca = Marca.objects.create(nombre=marca_nombre)
                # Verificar que el nombre se mantiene intacto
                self.assertEqual(marca.nombre, marca_nombre)
                
                # Verificar que los caracteres especiales están presentes
                if "'" in marca_nombre:
                    self.assertIn("'", marca.nombre)
                if "&" in marca_nombre:
                    self.assertIn("&", marca.nombre)
    
    def test_fit_special_characters(self):
        """Test que verifica que los fits mantengan caracteres especiales"""
        special_fits = [
            "Athletic Fit / Muscle Fit",
            "Regular Fit / Classic Fit",
            "Loose Fit / Baggy Fit",
            "Slim Straight Fit",
            "Drop Shoulder Fit"
        ]
        
        for fit_nombre in special_fits:
            with self.subTest(fit=fit_nombre):
                fit = Fit.objects.create(nombre=fit_nombre)
                # Verificar que el nombre se mantiene intacto
                self.assertEqual(fit.nombre, fit_nombre)
                
                # Verificar que los caracteres especiales están presentes
                if "/" in fit_nombre:
                    self.assertIn("/", fit.nombre)
                if "&" in fit_nombre:
                    self.assertIn("&", fit.nombre)
    
    def test_xss_protection_with_special_chars(self):
        """Test que verifica protección XSS mientras mantiene caracteres especiales"""
        # Casos que combinan caracteres especiales legítimos con ataques XSS
        test_cases = [
            ("Levi's<script>alert('xss')</script>", "Levi's"),
            ("Abercrombie & Fitch<script>alert('xss')</script>", "Abercrombie & Fitch"),
            ("Athletic Fit / Muscle Fit<script>alert('xss')</script>", "Athletic Fit / Muscle Fit"),
        ]
        
        for input_text, expected_output in test_cases:
            with self.subTest(input=input_text):
                # Crear marca con texto que combina caracteres especiales y XSS
                marca = Marca.objects.create(nombre=input_text)
                
                # Verificar que los caracteres especiales se mantienen
                if "'" in expected_output:
                    self.assertIn("'", marca.nombre)
                if "&" in expected_output:
                    self.assertIn("&", marca.nombre)
                if "/" in expected_output:
                    self.assertIn("/", marca.nombre)
                
                # Verificar que el contenido peligroso fue removido
                self.assertNotIn('<script>', marca.nombre)
                self.assertNotIn('alert(', marca.nombre)