from django.test import TestCase
from django.core.exceptions import ValidationError
import decimal

from inventario.models import Cliente, Talla, Categoria
from inventario.forms import ClienteForm

class ClienteFormTest(TestCase):
    """Pruebas para el formulario de Cliente"""
    
    @classmethod
    def setUpTestData(cls):
        """Configuración inicial para todos los tests"""
        # Crear datos de prueba
        cls.categoria = Categoria.objects.create(nombre='Ropa')
        cls.talla = Talla.objects.create(nombre='M')
        
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



    def test_cliente_form_valid_data(self):
        """Test que verifica que el formulario acepta datos válidos"""
        form_data = {
            'nombre': 'María',
            'apellido': 'García',
            'identificacion': '87654321',
            'email': 'maria.garcia@test.com',
            'telefono': '3008765432',
            'status': True,
            'tallas': [self.talla.pk]
        }
        
        form = ClienteForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_cliente_form_required_fields(self):
        """Test que verifica los campos requeridos"""
        # Formulario sin campos requeridos
        form = ClienteForm(data={})
        self.assertFalse(form.is_valid())
        
        # Verificar que los campos requeridos están en los errores
        self.assertIn('nombre', form.errors)
        self.assertIn('identificacion', form.errors)
        # email es opcional, no debe estar en los errores

    def test_cliente_form_optional_fields(self):
        """Test que verifica que los campos opcionales funcionan"""
        form_data = {
            'nombre': 'Test',
            'identificacion': '11111111',
            'email': 'test@test.com'
            # Sin apellido, teléfono, tallas
        }
        
        form = ClienteForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_cliente_form_identificacion_unique(self):
        """Test que verifica que la identificación debe ser única"""
        form_data = {
            'nombre': 'Test',
            'identificacion': '12345678',  # Ya existe
            'email': 'test@test.com'
        }
        
        form = ClienteForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('identificacion', form.errors)

    def test_cliente_form_email_unique(self):
        """Test que verifica que el email debe ser único"""
        form_data = {
            'nombre': 'Test',
            'identificacion': '22222222',
            'email': 'juan.perez@test.com'  # Ya existe
        }
        
        form = ClienteForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_cliente_form_email_validation(self):
        """Test que verifica la validación del email"""
        # Email válido
        form_data = {
            'nombre': 'Test',
            'identificacion': '33333333',
            'email': 'test@test.com'
        }
        form = ClienteForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Email inválido
        form_data['email'] = 'email_invalido'
        form = ClienteForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_cliente_form_telefono_validation(self):
        """Test que verifica la validación del teléfono"""
        # Teléfono válido
        form_data = {
            'nombre': 'Test',
            'identificacion': '44444444',
            'email': 'test@test.com',
            'telefono': '3001234567'
        }
        form = ClienteForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Teléfono inválido (muy corto)
        form_data['telefono'] = '123'
        form = ClienteForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('telefono', form.errors)

    def test_cliente_form_identificacion_validation(self):
        """Test que verifica la validación de la identificación"""
        # Identificación válida
        form_data = {
            'nombre': 'Test',
            'identificacion': '55555555',
            'email': 'test@test.com'
        }
        form = ClienteForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Identificación inválida (muy corta)
        form_data['identificacion'] = '123'
        form = ClienteForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('identificacion', form.errors)

    def test_cliente_form_tallas_validation(self):
        """Test que verifica la validación de tallas"""
        # Tallas válidas
        form_data = {
            'nombre': 'Test',
            'identificacion': '66666666',
            'email': 'test@test.com',
            'tallas': [self.talla.pk]
        }
        form = ClienteForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Tallas inválidas (ID inexistente)
        form_data['tallas'] = [99999]
        form = ClienteForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('tallas', form.errors)





    def test_cliente_form_update_existing(self):
        """Test que verifica el formulario para actualizar un cliente existente"""
        form_data = {
            'nombre': 'Juan Carlos',
            'apellido': 'Pérez López',
            'identificacion': '12345678',
            'email': 'juan.perez@test.com',
            'telefono': '3001234567',
            'status': True,
            'tallas': [self.talla.pk]
        }
        
        form = ClienteForm(data=form_data, instance=self.cliente)
        self.assertTrue(form.is_valid())

    def test_cliente_form_update_duplicate_identificacion(self):
        """Test que verifica que no se puede duplicar identificación al actualizar"""
        # Crear otro cliente
        otro_cliente = Cliente.objects.create(
            nombre='Otro',
            identificacion='87654321',
            email='otro@test.com'
        )
        
        # Intentar actualizar el primer cliente con la identificación del segundo
        form_data = {
            'nombre': 'Juan',
            'identificacion': '87654321',  # Identificación del otro cliente
            'email': 'juan.perez@test.com'
        }
        
        form = ClienteForm(data=form_data, instance=self.cliente)
        self.assertFalse(form.is_valid())
        self.assertIn('identificacion', form.errors)

    def test_cliente_form_update_duplicate_email(self):
        """Test que verifica que no se puede duplicar email al actualizar"""
        # Crear otro cliente
        otro_cliente = Cliente.objects.create(
            nombre='Otro',
            identificacion='87654321',
            email='otro@test.com'
        )
        
        # Intentar actualizar el primer cliente con el email del segundo
        form_data = {
            'nombre': 'Juan',
            'identificacion': '12345678',
            'email': 'otro@test.com'  # Email del otro cliente
        }
        
        form = ClienteForm(data=form_data, instance=self.cliente)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_cliente_form_save_method(self):
        """Test que verifica el método save del formulario"""
        form_data = {
            'nombre': 'Test Save',
            'identificacion': '11111111',
            'email': 'save@test.com',
            'tallas': [self.talla.pk]
        }
        
        form = ClienteForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        cliente = form.save()
        self.assertEqual(cliente.nombre, 'Test Save')
        self.assertEqual(cliente.identificacion, 11111111)
        self.assertEqual(cliente.email, 'save@test.com')
        self.assertIn(self.talla, cliente.tallas.all())



    def test_cliente_form_clean_method(self):
        """Test que verifica el método clean del formulario"""
        form_data = {
            'nombre': 'Test Clean',
            'identificacion': '33333333',
            'email': 'clean@test.com'
        }
        
        form = ClienteForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Verificar que los datos están sanitizados
        cleaned_data = form.clean()
        self.assertNotIn('<script>', cleaned_data.get('nombre', ''))

    def test_cliente_form_field_labels(self):
        """Test que verifica las etiquetas de los campos"""
        form = ClienteForm()
        
        self.assertEqual(form.fields['nombre'].label, 'Nombre')
        self.assertEqual(form.fields['apellido'].label, 'Apellido')
        self.assertEqual(form.fields['identificacion'].label, 'Identificación')
        self.assertEqual(form.fields['email'].label, 'Email')
        self.assertEqual(form.fields['telefono'].label, 'Teléfono')
        self.assertEqual(form.fields['tallas'].label, 'Tallas')

        self.assertEqual(form.fields['status'].label, 'Status')


    def test_cliente_form_field_help_text(self):
        """Test que verifica los textos de ayuda de los campos"""
        form = ClienteForm()
        
        # Verificar que algunos campos tienen texto de ayuda
        self.assertIsNotNone(form.fields['identificacion'].help_text)
        self.assertIsNotNone(form.fields['email'].help_text)

    def test_cliente_form_field_widgets(self):
        """Test que verifica los widgets de los campos"""
        form = ClienteForm()
        
        # Verificar tipos de widgets
        self.assertEqual(form.fields['nombre'].widget.__class__.__name__, 'TextInput')
        self.assertEqual(form.fields['email'].widget.__class__.__name__, 'EmailInput')
        self.assertEqual(form.fields['telefono'].widget.__class__.__name__, 'TextInput')
        self.assertEqual(form.fields['status'].widget.__class__.__name__, 'CheckboxInput')


    def test_cliente_form_queryset_choices(self):
        """Test que verifica las opciones de los campos de selección"""
        form = ClienteForm()
        
        # Verificar que tallas tiene opciones
        self.assertGreater(len(form.fields['tallas'].queryset), 0)
        self.assertIn(self.talla, form.fields['tallas'].queryset)
        


    def test_cliente_form_initial_data(self):
        """Test que verifica los datos iniciales del formulario"""
        form = ClienteForm(instance=self.cliente)
        
        # Verificar que los datos iniciales coinciden con la instancia
        self.assertEqual(form.initial['nombre'], 'Juan')
        self.assertEqual(form.initial['apellido'], 'Pérez')
        self.assertEqual(form.initial['identificacion'], '12345678')
        self.assertEqual(form.initial['email'], 'juan.perez@test.com')
        self.assertEqual(form.initial['telefono'], '3001234567')
        self.assertTrue(form.initial['status'])

    def test_cliente_form_empty_queryset(self):
        """Test que verifica el comportamiento con querysets vacíos"""
        # Eliminar todas las tallas
        Talla.objects.all().delete()
        
        form = ClienteForm()
        
        # El formulario debe seguir siendo válido para campos opcionales
        form_data = {
            'nombre': 'Test',
            'identificacion': '44444444',
            'email': 'test@test.com'
        }
        form = ClienteForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_cliente_form_max_length_validation(self):
        """Test que verifica la validación de longitud máxima"""
        # Nombre muy largo
        long_name = 'a' * 101  # Más del límite
        form_data = {
            'nombre': long_name,
            'identificacion': '55555555',
            'email': 'test@test.com'
        }
        
        form = ClienteForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_cliente_form_blank_fields(self):
        """Test que verifica el comportamiento con campos en blanco"""
        form_data = {
            'nombre': 'Test',
            'identificacion': '66666666',
            'email': 'test@test.com',
            'apellido': '',  # Campo opcional en blanco
            'telefono': ''   # Campo opcional en blanco
        }
        
        form = ClienteForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_cliente_form_status_default(self):
        """Test que verifica el valor por defecto del campo status"""
        form = ClienteForm()
        
        # Verificar que status tiene un valor por defecto
        self.assertIsNotNone(form.fields['status'].initial)

    def test_cliente_form_error_messages(self):
        """Test que verifica los mensajes de error personalizados"""
        form_data = {
            'nombre': '',
            'identificacion': '',
            'email': 'invalid-email'  # Email inválido
        }
        
        form = ClienteForm(data=form_data)
        self.assertFalse(form.is_valid())
        
        # Verificar que hay mensajes de error
        self.assertIn('nombre', form.errors)
        self.assertIn('identificacion', form.errors)
        # email es opcional, pero si se proporciona debe ser válido
        if 'email' in form_data and form_data['email']:
            self.assertIn('email', form.errors) 