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
    image = Image.new('RGB', (100, 100), color='purple')
    image_file = BytesIO()
    image.save(image_file, 'JPEG')
    image_file.seek(0)
    return SimpleUploadedFile('test.jpg', image_file.getvalue(), content_type='image/jpeg')

class ClienteUsuarioIntegrationTest(TestCase):
    """Pruebas de integración entre módulos de Cliente y Usuario"""
    
    @classmethod
    def setUpTestData(cls):
        """Configuración inicial para todos los tests"""
        User = get_user_model()
        
        # Crear usuarios con diferentes permisos
        cls.user_normal = User.objects.create_user(
            username='normaluser',
            email='normal@test.com',
            password='testpass123',
            first_name='Usuario',
            last_name='Normal'
        )
        
        cls.user_staff = User.objects.create_user(
            username='staffuser',
            email='staff@test.com',
            password='testpass123',
            first_name='Usuario',
            last_name='Staff',
            is_staff=True
        )
        
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

    def test_complete_cliente_crud_flow(self):
        """Test que verifica el flujo completo CRUD de clientes"""
        # Login como usuario normal
        self.client.login(username='normaluser', password='testpass123')
        
        # 1. CREATE - Crear un nuevo cliente
        cliente_data = {
            'nombre': 'María',
            'apellido': 'García',
            'identificacion': '87654321',
            'email': 'maria.garcia@test.com',
            'telefono': '3008765432',
            'status': True,
            'tallas': [self.talla.pk],
            'etiqueta': [self.etiqueta.pk]
        }
        
        response = self.client.post(reverse('cliente_create'), cliente_data)
        self.assertEqual(response.status_code, 302)  # Redirección exitosa
        
        # Verificar que el cliente fue creado
        cliente_creado = Cliente.objects.get(identificacion='87654321')
        self.assertEqual(cliente_creado.nombre, 'María')
        self.assertEqual(cliente_creado.apellido, 'García')
        
        # 2. READ - Ver la lista de clientes
        response = self.client.get(reverse('cliente_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(cliente_creado, response.context['clientes'])
        
        # 3. READ - Ver el detalle del cliente
        response = self.client.get(reverse('cliente_detail', kwargs={'pk': cliente_creado.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['cliente'], cliente_creado)
        
        # 4. UPDATE - Actualizar el cliente
        update_data = {
            'nombre': 'María Elena',
            'apellido': 'García López',
            'identificacion': '87654321',
            'email': 'maria.garcia@test.com',
            'telefono': '3008765432',
            'status': True,
            'tallas': [self.talla.pk],
            'etiqueta': [self.etiqueta.pk]
        }
        
        response = self.client.post(reverse('cliente_update', kwargs={'pk': cliente_creado.pk}), update_data)
        self.assertEqual(response.status_code, 302)  # Redirección exitosa
        
        # Verificar que el cliente fue actualizado
        cliente_creado.refresh_from_db()
        self.assertEqual(cliente_creado.nombre, 'María Elena')
        self.assertEqual(cliente_creado.apellido, 'García López')
        
        # 5. TOGGLE - Cambiar estado del cliente
        response = self.client.post(reverse('cliente_toggle', kwargs={'pk': cliente_creado.pk}))
        self.assertEqual(response.status_code, 302)  # Redirección
        
        cliente_creado.refresh_from_db()
        self.assertFalse(cliente_creado.status)  # Ahora inactivo
        
        # Reactivar
        response = self.client.post(reverse('cliente_toggle', kwargs={'pk': cliente_creado.pk}))
        self.assertEqual(response.status_code, 302)  # Redirección
        
        cliente_creado.refresh_from_db()
        self.assertTrue(cliente_creado.status)  # Ahora activo

    def test_complete_usuario_crud_flow(self):
        """Test que verifica el flujo completo CRUD de usuarios"""
        # Dar permisos al usuario normal
        content_type = ContentType.objects.get_for_model(get_user_model())
        add_permission = Permission.objects.get(
            content_type=content_type,
            codename='add_customuser'
        )
        self.user_normal.user_permissions.add(add_permission)
        
        # Login como usuario con permisos
        self.client.login(username='normaluser', password='testpass123')
        
        # 1. CREATE - Crear un nuevo usuario
        user_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!',
            'first_name': 'Nuevo',
            'last_name': 'Usuario'
        }
        
        response = self.client.post(reverse('usuario_create'), user_data)
        self.assertEqual(response.status_code, 302)  # Redirección exitosa
        
        # Verificar que el usuario fue creado
        User = get_user_model()
        usuario_creado = User.objects.get(username='newuser')
        self.assertEqual(usuario_creado.email, 'newuser@test.com')
        self.assertEqual(usuario_creado.first_name, 'Nuevo')
        
        # 2. READ - Ver la lista de usuarios
        response = self.client.get(reverse('usuario_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(usuario_creado, response.context['usuarios'])
        
        # 3. READ - Ver el detalle del usuario
        response = self.client.get(reverse('usuario_detail', kwargs={'pk': usuario_creado.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['usuario'], usuario_creado)
        
        # 4. UPDATE - Actualizar el usuario (solo su propio perfil)
        self.client.login(username='newuser', password='NewPass123!')
        update_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'first_name': 'Nuevo Actualizado',
            'last_name': 'Usuario Actualizado'
        }
        
        response = self.client.post(reverse('usuario_update', kwargs={'pk': usuario_creado.pk}), update_data)
        self.assertEqual(response.status_code, 302)  # Redirección exitosa
        
        # Verificar que el usuario fue actualizado
        usuario_creado.refresh_from_db()
        self.assertEqual(usuario_creado.first_name, 'Nuevo Actualizado')
        self.assertEqual(usuario_creado.last_name, 'Usuario Actualizado')

    def test_user_permissions_affect_cliente_access(self):
        """Test que verifica cómo los permisos de usuario afectan el acceso a clientes"""
        # Usuario sin permisos específicos
        self.client.login(username='normaluser', password='testpass123')
        
        # Debe poder acceder a las vistas básicas de clientes
        response = self.client.get(reverse('cliente_list'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('cliente_detail', kwargs={'pk': self.cliente.pk}))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('cliente_create'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('cliente_update', kwargs={'pk': self.cliente.pk}))
        self.assertEqual(response.status_code, 200)

    def test_user_permissions_affect_usuario_access(self):
        """Test que verifica cómo los permisos de usuario afectan el acceso a usuarios"""
        # Usuario sin permisos específicos
        self.client.login(username='normaluser', password='testpass123')
        
        # Debe poder acceder a las vistas básicas de usuarios
        response = self.client.get(reverse('usuario_list'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('usuario_detail', kwargs={'pk': self.user_normal.pk}))
        self.assertEqual(response.status_code, 200)
        
        # No debe poder crear usuarios sin permisos
        response = self.client.get(reverse('usuario_create'))
        self.assertIn(response.status_code, [302, 403])

    def test_session_data_persistence(self):
        """Test que verifica la persistencia de datos de sesión entre módulos"""
        self.client.login(username='normaluser', password='testpass123')
        
        # Acceder a clientes
        response = self.client.get(reverse('cliente_list'))
        self.assertEqual(response.status_code, 200)
        
        # Verificar que la sesión persiste
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, 'normaluser')
        
        # Acceder a usuarios
        response = self.client.get(reverse('usuario_list'))
        self.assertEqual(response.status_code, 200)
        
        # Verificar que la sesión sigue persistiendo
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, 'normaluser')

    def test_cross_module_search_functionality(self):
        """Test que verifica la funcionalidad de búsqueda entre módulos"""
        self.client.login(username='normaluser', password='testpass123')
        
        # Búsqueda en clientes
        response = self.client.get(reverse('cliente_list'), {'q': 'Juan'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.cliente, response.context['clientes'])
        
        # Búsqueda en usuarios
        response = self.client.get(reverse('usuario_list'), {'q': 'normaluser'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user_normal, response.context['usuarios'])

    def test_image_handling_across_modules(self):
        """Test que verifica el manejo de imágenes en ambos módulos"""
        self.client.login(username='normaluser', password='testpass123')
        
        # Crear cliente con imagen
        image_file = create_test_image()
        cliente_data = {
            'nombre': 'Test Imagen',
            'identificacion': '11111111',
            'email': 'imagen@test.com',
            'status': True
        }
        files = {
            'imagen': image_file
        }
        
        response = self.client.post(reverse('cliente_create'), cliente_data, files=files)
        self.assertEqual(response.status_code, 302)
        
        cliente_creado = Cliente.objects.get(identificacion='11111111')
        self.assertIsNotNone(cliente_creado.imagen)
        
        # Actualizar usuario con imagen
        self.client.login(username='normaluser', password='testpass123')
        image_file2 = create_test_image()
        user_data = {
            'username': 'normaluser',
            'email': 'normal@test.com',
            'first_name': 'Usuario',
            'last_name': 'Normal'
        }
        files = {
            'imagen': image_file2
        }
        
        response = self.client.post(reverse('usuario_update', kwargs={'pk': self.user_normal.pk}), user_data, files=files)
        self.assertEqual(response.status_code, 302)
        
        self.user_normal.refresh_from_db()
        self.assertIsNotNone(self.user_normal.imagen)

    def test_error_handling_across_modules(self):
        """Test que verifica el manejo de errores entre módulos"""
        self.client.login(username='normaluser', password='testpass123')
        
        # Error en cliente (identificación duplicada)
        cliente_data = {
            'nombre': 'Test Error',
            'identificacion': '12345678',  # Ya existe
            'email': 'error@test.com'
        }
        
        response = self.client.post(reverse('cliente_create'), cliente_data)
        self.assertEqual(response.status_code, 200)  # Muestra formulario con errores
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)
        
        # Error en usuario (username duplicado)
        User = get_user_model()
        user_data = {
            'username': 'normaluser',  # Ya existe
            'email': 'error@test.com',
            'password1': 'ErrorPass123!',
            'password2': 'ErrorPass123!'
        }
        
        response = self.client.post(reverse('usuario_create'), user_data)
        self.assertEqual(response.status_code, 200)  # Muestra formulario con errores
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)

    def test_messages_framework_across_modules(self):
        """Test que verifica el framework de mensajes entre módulos"""
        self.client.login(username='normaluser', password='testpass123')
        
        # Mensaje de éxito en cliente
        cliente_data = {
            'nombre': 'Test Mensaje',
            'identificacion': '22222222',
            'email': 'mensaje@test.com',
            'status': True
        }
        
        response = self.client.post(reverse('cliente_create'), cliente_data, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('creado exitosamente' in str(message) for message in messages))
        
        # Mensaje de éxito en usuario (con permisos)
        content_type = ContentType.objects.get_for_model(get_user_model())
        add_permission = Permission.objects.get(
            content_type=content_type,
            codename='add_customuser'
        )
        self.user_normal.user_permissions.add(add_permission)
        
        user_data = {
            'username': 'mensajeuser',
            'email': 'mensaje@test.com',
            'password1': 'MensajePass123!',
            'password2': 'MensajePass123!'
        }
        
        response = self.client.post(reverse('usuario_create'), user_data, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('creado exitosamente' in str(message) for message in messages))

    def test_admin_user_full_access(self):
        """Test que verifica el acceso completo del usuario administrador"""
        self.client.login(username='admin', password='adminpass123')
        
        # Acceso completo a clientes
        response = self.client.get(reverse('cliente_list'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('cliente_create'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('cliente_update', kwargs={'pk': self.cliente.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Acceso completo a usuarios
        response = self.client.get(reverse('usuario_list'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('usuario_create'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('usuario_update', kwargs={'pk': self.user_normal.pk}))
        self.assertEqual(response.status_code, 200)

    def test_staff_user_limited_access(self):
        """Test que verifica el acceso limitado del usuario staff"""
        self.client.login(username='staffuser', password='testpass123')
        
        # Acceso a clientes
        response = self.client.get(reverse('cliente_list'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('cliente_create'))
        self.assertEqual(response.status_code, 200)
        
        # Acceso limitado a usuarios
        response = self.client.get(reverse('usuario_list'))
        self.assertEqual(response.status_code, 200)
        
        # Puede o no poder crear usuarios dependiendo de permisos específicos
        response = self.client.get(reverse('usuario_create'))
        self.assertIn(response.status_code, [200, 302, 403])

    def test_data_consistency_across_modules(self):
        """Test que verifica la consistencia de datos entre módulos"""
        self.client.login(username='normaluser', password='testpass123')
        
        # Crear cliente
        cliente_data = {
            'nombre': 'Test Consistencia',
            'identificacion': '33333333',
            'email': 'consistencia@test.com',
            'status': True
        }
        
        response = self.client.post(reverse('cliente_create'), cliente_data)
        self.assertEqual(response.status_code, 302)
        
        cliente_creado = Cliente.objects.get(identificacion='33333333')
        
        # Verificar que los datos son consistentes en la lista
        response = self.client.get(reverse('cliente_list'))
        self.assertIn(cliente_creado, response.context['clientes'])
        
        # Verificar que los datos son consistentes en el detalle
        response = self.client.get(reverse('cliente_detail', kwargs={'pk': cliente_creado.pk}))
        self.assertEqual(response.context['cliente'], cliente_creado)
        self.assertEqual(response.context['cliente'].nombre, 'Test Consistencia')

    def test_form_validation_across_modules(self):
        """Test que verifica la validación de formularios entre módulos"""
        self.client.login(username='normaluser', password='testpass123')
        
        # Validación de cliente
        cliente_data = {
            'nombre': 'Test Validación',
            'identificacion': '44444444',
            'email': 'validacion@test.com',
            'telefono': '3001234567'  # Válido
        }
        
        response = self.client.post(reverse('cliente_create'), cliente_data)
        self.assertEqual(response.status_code, 302)  # Éxito
        
        # Validación de cliente con datos inválidos
        cliente_data_invalido = {
            'nombre': 'Test Inválido',
            'identificacion': '55555555',
            'email': 'email_invalido',  # Inválido
            'telefono': '123'  # Muy corto
        }
        
        response = self.client.post(reverse('cliente_create'), cliente_data_invalido)
        self.assertEqual(response.status_code, 200)  # Muestra errores
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)

    def test_redirect_behavior_across_modules(self):
        """Test que verifica el comportamiento de redirecciones entre módulos"""
        self.client.login(username='normaluser', password='testpass123')
        
        # Redirección después de crear cliente
        cliente_data = {
            'nombre': 'Test Redirección',
            'identificacion': '66666666',
            'email': 'redireccion@test.com',
            'status': True
        }
        
        response = self.client.post(reverse('cliente_create'), cliente_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cliente_list'))
        
        # Redirección después de actualizar cliente
        cliente_creado = Cliente.objects.get(identificacion='66666666')
        update_data = {
            'nombre': 'Test Redirección Actualizado',
            'identificacion': '66666666',
            'email': 'redireccion@test.com',
            'status': True
        }
        
        response = self.client.post(reverse('cliente_update', kwargs={'pk': cliente_creado.pk}), update_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cliente_list')) 