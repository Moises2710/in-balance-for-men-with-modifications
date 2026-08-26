from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages
from PIL import Image
from io import BytesIO
import tempfile
import os
import shutil
import decimal

from inventario.models import Cliente, Talla, Etiqueta, Categoria

# Configuración para usar un directorio temporal para MEDIA_ROOT durante las pruebas
TEST_MEDIA_ROOT = tempfile.mkdtemp()

def create_test_image():
    """Crea una imagen de prueba para los tests"""
    image = Image.new('RGB', (100, 100), color='blue')
    image_file = BytesIO()
    image.save(image_file, 'JPEG')
    image_file.seek(0)
    return SimpleUploadedFile('test.jpg', image_file.getvalue(), content_type='image/jpeg')

class ClienteViewsTest(TestCase):
    """Pruebas para las vistas de Cliente"""
    
    @classmethod
    def setUpTestData(cls):
        """Configuración inicial para todos los tests"""
        User = get_user_model()
        
        # Crear usuario con permisos
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        # Crear superusuario
        cls.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123'
        )
        
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

    def setUp(self):
        """Configuración antes de cada test"""
        self.client = Client()

    def test_cliente_list_view_requires_login(self):
        """Test que verifica que la vista de lista requiere login"""
        response = self.client.get(reverse('cliente_list'))
        self.assertEqual(response.status_code, 302)  # Redirección a login
        self.assertIn('login', response.url)

    def test_cliente_list_view_with_login(self):
        """Test que verifica la vista de lista con usuario autenticado"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('cliente_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventario/clientes/cliente_list.html')
        self.assertIn('clientes', response.context)
        self.assertIn(self.cliente, response.context['clientes'])

    def test_cliente_list_view_search(self):
        """Test que verifica la funcionalidad de búsqueda en la lista"""
        self.client.login(username='testuser', password='testpass123')
        
        # Búsqueda por nombre
        response = self.client.get(reverse('cliente_list'), {'search': 'Juan'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.cliente, response.context['clientes'])
        
        # Búsqueda por email
        response = self.client.get(reverse('cliente_list'), {'search': 'juan.perez@test.com'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.cliente, response.context['clientes'])
        
        # Búsqueda sin resultados
        response = self.client.get(reverse('cliente_list'), {'search': 'NoExiste'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.cliente, response.context['clientes'])

    def test_cliente_detail_view_requires_login(self):
        """Test que verifica que la vista de detalle requiere login"""
        response = self.client.get(reverse('cliente_detail', kwargs={'pk': self.cliente.pk}))
        self.assertEqual(response.status_code, 302)  # Redirección a login

    def test_cliente_detail_view_with_login(self):
        """Test que verifica la vista de detalle con usuario autenticado"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('cliente_detail', kwargs={'pk': self.cliente.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventario/clientes/cliente_detail.html')
        self.assertEqual(response.context['cliente'], self.cliente)

    def test_cliente_detail_view_not_found(self):
        """Test que verifica la vista de detalle con cliente inexistente"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('cliente_detail', kwargs={'pk': 99999}))
        
        self.assertEqual(response.status_code, 404)

    def test_cliente_create_view_requires_login(self):
        """Test que verifica que la vista de creación requiere login"""
        response = self.client.get(reverse('cliente_create'))
        self.assertEqual(response.status_code, 302)  # Redirección a login

    def test_cliente_create_view_with_login(self):
        """Test que verifica la vista de creación con usuario autenticado"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('cliente_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventario/clientes/cliente_form.html')
        self.assertIn('form', response.context)

    def test_cliente_create_view_post_valid(self):
        """Test que verifica la creación exitosa de un cliente"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'nombre': 'María',
            'apellido': 'García',
            'identificacion': '87654321',
            'email': 'maria.garcia@test.com',
            'telefono': '3008765432',
            'status': True,
            'tallas': [self.talla.pk],
            'etiqueta': [self.etiqueta.pk]
        }
        
        response = self.client.post(reverse('cliente_create'), data)
        
        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cliente_list'))
        
        # Verificar que el cliente fue creado
        cliente_creado = Cliente.objects.get(identificacion='87654321')
        self.assertEqual(cliente_creado.nombre, 'María')
        self.assertEqual(cliente_creado.apellido, 'García')
        self.assertEqual(cliente_creado.email, 'maria.garcia@test.com')

    def test_cliente_create_view_post_invalid(self):
        """Test que verifica la creación fallida de un cliente"""
        self.client.login(username='testuser', password='testpass123')
        
        # Datos inválidos (identificación duplicada)
        data = {
            'nombre': 'Test',
            'identificacion': '12345678',  # Ya existe
            'email': 'test@test.com'
        }
        
        response = self.client.post(reverse('cliente_create'), data)
        
        # Debe mostrar el formulario con errores
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)

    def test_cliente_update_view_requires_login(self):
        """Test que verifica que la vista de actualización requiere login"""
        response = self.client.get(reverse('cliente_update', kwargs={'pk': self.cliente.pk}))
        self.assertEqual(response.status_code, 302)  # Redirección a login

    def test_cliente_update_view_with_login(self):
        """Test que verifica la vista de actualización con usuario autenticado"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('cliente_update', kwargs={'pk': self.cliente.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventario/clientes/cliente_form.html')
        self.assertIn('form', response.context)
        self.assertEqual(response.context['form'].instance, self.cliente)

    def test_cliente_update_view_post_valid(self):
        """Test que verifica la actualización exitosa de un cliente"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'nombre': 'Juan Carlos',
            'apellido': 'Pérez López',
            'identificacion': '12345678',
            'email': 'juan.perez@test.com',
            'telefono': '3001234567',
            'status': True,
            'tallas': [self.talla.pk],
            'etiqueta': [self.etiqueta.pk]
        }
        
        response = self.client.post(reverse('cliente_update', kwargs={'pk': self.cliente.pk}), data)
        
        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cliente_list'))
        
        # Verificar que el cliente fue actualizado
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.nombre, 'Juan Carlos')
        self.assertEqual(self.cliente.apellido, 'Pérez López')

    def test_cliente_update_view_post_invalid(self):
        """Test que verifica la actualización fallida de un cliente"""
        self.client.login(username='testuser', password='testpass123')
        
        # Crear otro cliente para probar duplicación
        otro_cliente = Cliente.objects.create(
            nombre='Otro',
            identificacion='87654321',
            email='otro@test.com'
        )
        
        # Intentar usar la identificación del otro cliente
        data = {
            'nombre': 'Test',
            'identificacion': '87654321',  # Identificación del otro cliente
            'email': 'test@test.com'
        }
        
        response = self.client.post(reverse('cliente_update', kwargs={'pk': self.cliente.pk}), data)
        
        # Debe mostrar el formulario con errores
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)

    def test_cliente_update_view_not_found(self):
        """Test que verifica la vista de actualización con cliente inexistente"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('cliente_update', kwargs={'pk': 99999}))
        
        self.assertEqual(response.status_code, 404)

    def test_cliente_toggle_view_requires_login(self):
        """Test que verifica que la vista de toggle requiere login"""
        response = self.client.post(reverse('cliente_toggle', kwargs={'pk': self.cliente.pk}))
        self.assertEqual(response.status_code, 302)  # Redirección a login

    def test_cliente_toggle_view_with_login(self):
        """Test que verifica la funcionalidad de toggle con usuario autenticado"""
        self.client.login(username='testuser', password='testpass123')
        
        # Estado inicial
        self.assertTrue(self.cliente.status)
        
        # Toggle a inactivo
        response = self.client.post(reverse('cliente_toggle', kwargs={'pk': self.cliente.pk}))
        
        self.assertEqual(response.status_code, 200)  # JSON response
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.status)
        
        # Toggle a activo
        response = self.client.post(reverse('cliente_toggle', kwargs={'pk': self.cliente.pk}))
        
        self.assertEqual(response.status_code, 200)  # JSON response
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.status)

    def test_cliente_toggle_view_not_found(self):
        """Test que verifica la vista de toggle con cliente inexistente"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('cliente_toggle', kwargs={'pk': 99999}))
        
        # La vista devuelve JSON con status 404
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_cliente_toggle_view_get_method(self):
        """Test que verifica que la vista de toggle solo acepta POST"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('cliente_toggle', kwargs={'pk': self.cliente.pk}))
        
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_cliente_form_with_image(self):
        """Test que verifica el formulario con imagen"""
        self.client.login(username='testuser', password='testpass123')
        
        image_file = create_test_image()
        data = {
            'nombre': 'Test Imagen',
            'identificacion': '11111111',
            'email': 'imagen@test.com',
            'status': True,
            'tallas': [self.talla.pk],
            'etiqueta': [self.etiqueta.pk]
        }
        files = {
            'imagen': image_file
        }
        
        response = self.client.post(reverse('cliente_create'), data, files=files)
        
        self.assertEqual(response.status_code, 302)  # Redirección exitosa
        
        # Verificar que el cliente fue creado con imagen
        cliente_creado = Cliente.objects.get(identificacion='11111111')
        self.assertIsNotNone(cliente_creado.imagen)

    def test_cliente_form_action_save_and_add_new(self):
        """Test que verifica la acción 'save_and_add_new'"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'nombre': 'Test Action',
            'identificacion': '22222222',
            'email': 'action@test.com',
            'status': True,
            'action': 'save_and_add_new',
            'tallas': [self.talla.pk],
            'etiqueta': [self.etiqueta.pk]
        }
        
        response = self.client.post(reverse('cliente_create'), data)
        
        # Debe redirigir al formulario de creación
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cliente_create'))

    def test_cliente_form_action_save_and_continue(self):
        """Test que verifica la acción 'save_and_continue'"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'nombre': 'Test Continue',
            'identificacion': '33333333',
            'email': 'continue@test.com',
            'status': True,
            'action': 'save_and_continue',
            'tallas': [self.talla.pk],
            'etiqueta': [self.etiqueta.pk]
        }
        
        response = self.client.post(reverse('cliente_create'), data)
        
        # Debe redirigir al formulario de edición
        cliente_creado = Cliente.objects.get(identificacion='33333333')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cliente_update', kwargs={'pk': cliente_creado.pk}))

    def test_cliente_list_view_ordering(self):
        """Test que verifica el ordenamiento de la lista de clientes"""
        self.client.login(username='testuser', password='testpass123')
        
        # Crear clientes adicionales
        Cliente.objects.create(
            nombre='Ana',
            identificacion='44444444',
            email='ana@test.com'
        )
        Cliente.objects.create(
            nombre='Carlos',
            identificacion='55555555',
            email='carlos@test.com'
        )
        
        response = self.client.get(reverse('cliente_list'))
        
        self.assertEqual(response.status_code, 200)
        clientes = response.context['clientes']
        
        # Verificar que están ordenados por nombre
        nombres = [cliente.nombre for cliente in clientes]
        self.assertEqual(nombres, sorted(nombres))

    def test_cliente_context_data(self):
        """Test que verifica los datos de contexto en las vistas"""
        self.client.login(username='testuser', password='testpass123')
        
        # Vista de lista
        response = self.client.get(reverse('cliente_list'))
        self.assertIn('clientes', response.context)
        
        # Vista de detalle
        response = self.client.get(reverse('cliente_detail', kwargs={'pk': self.cliente.pk}))
        self.assertIn('cliente', response.context)
        
        # Vista de creación
        response = self.client.get(reverse('cliente_create'))
        self.assertIn('form', response.context)
        
        # Vista de actualización
        response = self.client.get(reverse('cliente_update', kwargs={'pk': self.cliente.pk}))
        self.assertIn('form', response.context)

    def test_cliente_messages(self):
        """Test que verifica los mensajes de éxito"""
        self.client.login(username='testuser', password='testpass123')
        
        # Crear cliente
        data = {
            'nombre': 'Test Mensaje',
            'identificacion': '66666666',
            'email': 'mensaje@test.com',
            'status': True,
            'tallas': [self.talla.pk],
            'etiqueta': [self.etiqueta.pk]
        }
        
        response = self.client.post(reverse('cliente_create'), data, follow=True)
        
        # Verificar mensaje de éxito
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('creado exitosamente' in str(message) for message in messages))
        
        # Actualizar cliente
        update_data = {
            'nombre': 'Test Mensaje Actualizado',
            'apellido': 'Pérez',
            'identificacion': '12345678',
            'email': 'juan.perez@test.com',
            'telefono': '3001234567',
            'status': True,
            'tallas': [self.talla.pk],
            'etiqueta': [self.etiqueta.pk]
        }
        response = self.client.post(reverse('cliente_update', kwargs={'pk': self.cliente.pk}), update_data, follow=True)
        
        # Verificar mensaje de éxito
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('actualizado exitosamente' in str(message) for message in messages))

    def test_cliente_permissions(self):
        """Test que verifica los permisos en las vistas"""
        # Usuario sin permisos específicos
        self.client.login(username='testuser', password='testpass123')
        
        # Debe poder acceder a las vistas básicas
        response = self.client.get(reverse('cliente_list'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('cliente_detail', kwargs={'pk': self.cliente.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Debe poder crear y actualizar (permisos por defecto)
        response = self.client.get(reverse('cliente_create'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('cliente_update', kwargs={'pk': self.cliente.pk}))
        self.assertEqual(response.status_code, 200) 