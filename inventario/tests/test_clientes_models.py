from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
import decimal

from inventario.models import Cliente, Talla, Etiqueta, Categoria

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ClienteModelTest(TestCase):
    """Pruebas para el modelo Cliente"""
    
    @classmethod
    def setUpTestData(cls):
        """Configuración inicial para todos los tests"""
        # Crear datos de prueba
        cls.categoria = Categoria.objects.create(nombre='Ropa')
        cls.talla = Talla.objects.create(nombre='M')
        cls.etiqueta = Etiqueta.objects.create(nombre='VIP')
        
        # Cliente de prueba
        cls.cliente = Cliente.objects.create(
            nombre='Juan',
            apellido='Pérez',
            identificacion='12345678',
            email='juan.perez@test.com',
            telefono='3001234567',
            saldo=decimal.Decimal('150.50'),
            status=True
        )
        cls.cliente.tallas.add(cls.talla)
        cls.cliente.etiqueta.add(cls.etiqueta)

    @classmethod
    def tearDownClass(cls):
        """Limpieza después de todas las pruebas"""
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_cliente_creation(self):
        """Test que verifica la creación básica de un cliente"""
        self.assertEqual(self.cliente.nombre, 'Juan')
        self.assertEqual(self.cliente.apellido, 'Pérez')
        self.assertEqual(self.cliente.identificacion, '12345678')
        self.assertEqual(self.cliente.email, 'juan.perez@test.com')
        self.assertEqual(self.cliente.telefono, '3001234567')
        self.assertEqual(self.cliente.saldo, decimal.Decimal('150.50'))
        self.assertTrue(self.cliente.status)
        self.assertFalse(self.cliente.imagen)  # Cambiado de assertIsNone a assertFalse

    def test_cliente_str_method(self):
        """Test que verifica el método __str__ del cliente"""
        # Cliente con apellido
        self.assertEqual(str(self.cliente), 'Juan Pérez')
        
        # Cliente sin apellido
        cliente_sin_apellido = Cliente.objects.create(
            nombre='María',
            identificacion='87654321',
            email='maria@test.com'
        )
        self.assertEqual(str(cliente_sin_apellido), 'María')

    def test_identificacion_unique_constraint(self):
        """Test que verifica que la identificación debe ser única"""
        with self.assertRaises(IntegrityError):
            Cliente.objects.create(
                nombre='Otro Juan',
                apellido='García',
                identificacion='12345678',  # Misma identificación
                email='otro@test.com'
            )





    def test_telefono_validation(self):
        """Test que verifica la validación del teléfono"""
        # Teléfono válido
        cliente_valido = Cliente(
            nombre='Test',
            identificacion='11111111',
            email='test@test.com',
            telefono='3001234567'
        )
        cliente_valido.full_clean()  # No debe lanzar error
        
        # Teléfono inválido (muy corto)
        with self.assertRaises(ValidationError):
            cliente_invalido = Cliente(
                nombre='Test',
                identificacion='87654321',
                email='test2@test.com',
                telefono='123'  # Muy corto
            )
            cliente_invalido.full_clean()

    def test_email_validation(self):
        """Test que verifica la validación del email"""
        # Email válido
        cliente_valido = Cliente(
            nombre='Test',
            identificacion='22222222',
            email='test@test.com'
        )
        cliente_valido.full_clean()  # No debe lanzar error
        
        # Email inválido
        with self.assertRaises(ValidationError):
            cliente_invalido = Cliente(
                nombre='Test',
                identificacion='87654321',
                email='email_invalido'
            )
            cliente_invalido.full_clean()

    def test_saldo_default_value(self):
        """Test que verifica el valor por defecto del saldo"""
        cliente = Cliente.objects.create(
            nombre='Test',
            identificacion='11111111',
            email='test@test.com'
        )
        self.assertEqual(cliente.saldo, decimal.Decimal('0.00'))

    def test_status_default_value(self):
        """Test que verifica el valor por defecto del status"""
        cliente = Cliente.objects.create(
            nombre='Test',
            identificacion='22222222',
            email='test2@test.com'
        )
        self.assertTrue(cliente.status)  # Por defecto True

    def test_tallas_relationship(self):
        """Test que verifica la relación ManyToMany con Talla"""
        nueva_talla = Talla.objects.create(nombre='L')
        self.cliente.tallas.add(nueva_talla)
        
        self.assertIn(nueva_talla, self.cliente.tallas.all())
        self.assertEqual(self.cliente.tallas.count(), 2)

    def test_etiqueta_relationship(self):
        """Test que verifica la relación ManyToMany con Etiqueta"""
        nueva_etiqueta = Etiqueta.objects.create(nombre='Premium')
        self.cliente.etiqueta.add(nueva_etiqueta)
        
        self.assertIn(nueva_etiqueta, self.cliente.etiqueta.all())
        self.assertEqual(self.cliente.etiqueta.count(), 2)



    def test_sanitization(self):
        """Test que verifica la sanitización de datos"""
        cliente = Cliente.objects.create(
            nombre='<script>alert("xss")</script>Juan',
            apellido='<script>alert("xss")</script>Pérez',
            identificacion='55555555',
            email='test@test.com',
            telefono='<script>alert("xss")</script>3001234567'
        )
        
        # Los datos deben estar sanitizados
        self.assertNotIn('<script>', cliente.nombre)
        self.assertNotIn('<script>', cliente.apellido)
        self.assertNotIn('<script>', cliente.telefono)

    def test_optional_fields(self):
        """Test que verifica que los campos opcionales funcionan correctamente"""
        cliente = Cliente.objects.create(
            nombre='Solo Nombre',
            identificacion='66666666',
            email='solo@test.com'
            # Sin apellido, teléfono, tallas, etiquetas, imagen
        )
        
        self.assertIsNone(cliente.apellido)
        self.assertIsNone(cliente.telefono)
        self.assertEqual(cliente.tallas.count(), 0)
        self.assertEqual(cliente.etiqueta.count(), 0)
        self.assertFalse(cliente.imagen)

    def test_saldo_decimal_precision(self):
        """Test que verifica la precisión decimal del saldo"""
        cliente = Cliente.objects.create(
            nombre='Test Saldo',
            identificacion='77777777',
            email='saldo@test.com',
            saldo=decimal.Decimal('123.456789')
        )
        
        # Debe mantener la precisión original
        self.assertEqual(cliente.saldo, decimal.Decimal('123.456789'))

    def test_toggle_status(self):
        """Test que verifica el cambio de status"""
        self.assertTrue(self.cliente.status)
        
        # Cambiar a inactivo
        self.cliente.status = False
        self.cliente.save()
        self.assertFalse(self.cliente.status)
        
        # Cambiar a activo
        self.cliente.status = True
        self.cliente.save()
        self.assertTrue(self.cliente.status)

    def test_venta_relationship(self):
        """Test que verifica la relación con ventas (si existe)"""
        # Este test verifica que se puede acceder a las ventas del cliente
        # Asumiendo que existe una relación venta_set
        self.assertEqual(self.cliente.venta_set.count(), 0)

    def test_apellido_optional(self):
        """Test que verifica que el apellido es opcional"""
        cliente = Cliente.objects.create(
            nombre='Sin Apellido',
            identificacion='88888888',
            email='sinapellido@test.com'
        )
        
        self.assertIsNone(cliente.apellido)
        self.assertEqual(str(cliente), 'Sin Apellido')

    def test_apellido_with_special_characters(self):
        """Test que verifica el manejo de caracteres especiales en apellido"""
        cliente = Cliente.objects.create(
            nombre='María',
            apellido='García-López',
            identificacion='99999999',
            email='maria@test.com'
        )
        
        self.assertEqual(cliente.apellido, 'García-López')
        self.assertEqual(str(cliente), 'María García-López')

    def test_identificacion_numeric_only(self):
        """Test que verifica que la identificación solo acepta números"""
        # Identificación válida (solo números)
        cliente_valido = Cliente(
            nombre='Test',
            identificacion='33333333',
            email='test@test.com'
        )
        cliente_valido.full_clean()  # No debe lanzar error
        
        # Identificación inválida (con letras)
        with self.assertRaises(ValidationError):
            cliente_invalido = Cliente(
                nombre='Test',
                identificacion='12345ABC',
                email='test2@test.com'
            )
            cliente_invalido.full_clean()

    def test_telefono_numeric_only(self):
        """Test que verifica que el teléfono solo acepta números"""
        # Teléfono válido (solo números)
        cliente_valido = Cliente(
            nombre='Test',
            identificacion='44444444',
            email='test@test.com',
            telefono='3001234567'
        )
        cliente_valido.full_clean()  # No debe lanzar error
        
        # Teléfono inválido (con letras)
        with self.assertRaises(ValidationError):
            cliente_invalido = Cliente(
                nombre='Test',
                identificacion='87654321',
                email='test2@test.com',
                telefono='300ABC4567'
            )
            cliente_invalido.full_clean() 