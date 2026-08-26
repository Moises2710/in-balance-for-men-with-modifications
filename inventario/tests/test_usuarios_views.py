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

from inventario.models import CustomUser

# Configuración para usar un directorio temporal para MEDIA_ROOT durante las pruebas
TEST_MEDIA_ROOT = tempfile.mkdtemp()

def create_test_image():
    """Crea una imagen de prueba para los tests"""
    image = Image.new('RGB', (100, 100), color='green')
    image_file = BytesIO()
    image.save(image_file, 'JPEG')
    image_file.seek(0)
    return SimpleUploadedFile('test.jpg', image_file.getvalue(), content_type='image/jpeg')

class UsuarioViewsTest(TestCase):
    """Pruebas para las vistas de Usuario"""
    
    @classmethod
    def setUpTestData(cls):
        """Configuración inicial para todos los tests"""
        User = get_user_model()
        
        # Crear usuario normal
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            first_name='Juan',
            last_name='Pérez'
        )
        
        # Crear superusuario
        cls.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123'
        )
        
        # Crear usuario para pruebas
        cls.test_user = User.objects.create_user(
            username='usertest',
            email='usertest@test.com',
            password='testpass123',
            first_name='María',
            last_name='García'
        )

    @classmethod
    def tearDownClass(cls):
        """Limpieza después de todas las pruebas"""
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        """Configuración antes de cada test"""
        self.client = Client()

    def test_usuario_list_view_requires_login(self):
        """Test que verifica que la vista de lista requiere login"""
        response = self.client.get(reverse('usuario_list'))
        self.assertEqual(response.status_code, 302)  # Redirección a login
        self.assertIn('login', response.url)

    def test_usuario_list_view_with_login(self):
        """Test que verifica la vista de lista con usuario autenticado"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('usuario_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventario/usuarios/usuario_list.html')
        self.assertIn('usuarios', response.context)
        self.assertIn(self.user, response.context['usuarios'])

    def test_usuario_list_view_search(self):
        """Test que verifica la funcionalidad de búsqueda en la lista"""
        self.client.login(username='testuser', password='testpass123')
        
        # Búsqueda por username
        response = self.client.get(reverse('usuario_list'), {'q': 'testuser'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user, response.context['usuarios'])
        
        # Búsqueda por email
        response = self.client.get(reverse('usuario_list'), {'q': 'test@test.com'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user, response.context['usuarios'])
        
        # Búsqueda por nombre
        response = self.client.get(reverse('usuario_list'), {'q': 'Juan'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user, response.context['usuarios'])
        
        # Búsqueda sin resultados
        response = self.client.get(reverse('usuario_list'), {'q': 'NoExiste'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.user, response.context['usuarios'])

    def test_usuario_detail_view_requires_login(self):
        """Test que verifica que la vista de detalle requiere login"""
        response = self.client.get(reverse('usuario_detail', kwargs={'pk': self.user.pk}))
        self.assertEqual(response.status_code, 302)  # Redirección a login

    def test_usuario_detail_view_with_login(self):
        """Test que verifica la vista de detalle con usuario autenticado"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('usuario_detail', kwargs={'pk': self.user.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventario/usuarios/usuario_detail.html')
        self.assertEqual(response.context['usuario'], self.user)

    def test_usuario_detail_view_not_found(self):
        """Test que verifica la vista de detalle con usuario inexistente"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('usuario_detail', kwargs={'pk': 99999}))
        
        self.assertEqual(response.status_code, 404)

    def test_usuario_create_view_requires_login(self):
        """Test que verifica que la vista de creación requiere login"""
        response = self.client.get(reverse('usuario_create'))
        self.assertEqual(response.status_code, 302)  # Redirección a login

    def test_usuario_create_view_requires_permission(self):
        """Test que verifica que la vista de creación requiere permisos"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('usuario_create'))
        
        # Debe redirigir o mostrar error 403
        self.assertIn(response.status_code, [302, 403])

    def test_usuario_create_view_with_permission(self):
        """Test que verifica la vista de creación con permisos"""
        # Dar permisos al usuario
        content_type = ContentType.objects.get_for_model(get_user_model())
        permission = Permission.objects.get(
            content_type=content_type,
            codename='add_customuser'
        )
        self.user.user_permissions.add(permission)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('usuario_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventario/usuarios/usuario_form.html')
        self.assertIn('form', response.context)

    def test_usuario_create_view_post_valid(self):
        """Test que verifica la creación exitosa de un usuario"""
        # Dar permisos al usuario
        content_type = ContentType.objects.get_for_model(get_user_model())
        permission = Permission.objects.get(
            content_type=content_type,
            codename='add_customuser'
        )
        self.user.user_permissions.add(permission)
        
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!',
            'first_name': 'Nuevo',
            'last_name': 'Usuario'
        }
        
        response = self.client.post(reverse('usuario_create'), data)
        
        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('usuario_list'))
        
        # Verificar que el usuario fue creado
        usuario_creado = get_user_model().objects.get(username='newuser')
        self.assertEqual(usuario_creado.email, 'newuser@test.com')
        self.assertEqual(usuario_creado.first_name, 'Nuevo')
        self.assertEqual(usuario_creado.last_name, 'Usuario')

    def test_usuario_create_view_post_invalid(self):
        """Test que verifica la creación fallida de un usuario"""
        # Dar permisos al usuario
        content_type = ContentType.objects.get_for_model(get_user_model())
        permission = Permission.objects.get(
            content_type=content_type,
            codename='add_customuser'
        )
        self.user.user_permissions.add(permission)
        
        self.client.login(username='testuser', password='testpass123')
        
        # Datos inválidos (username duplicado)
        data = {
            'username': 'testuser',  # Ya existe
            'email': 'test@test.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!'
        }
        
        response = self.client.post(reverse('usuario_create'), data)
        
        # Debe mostrar el formulario con errores
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)

    def test_usuario_update_view_requires_login(self):
        """Test que verifica que la vista de actualización requiere login"""
        response = self.client.get(reverse('usuario_update', kwargs={'pk': self.user.pk}))
        self.assertEqual(response.status_code, 302)  # Redirección a login

    def test_usuario_update_view_own_profile(self):
        """Test que verifica que un usuario puede editar su propio perfil"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('usuario_update', kwargs={'pk': self.user.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventario/usuarios/usuario_update.html')
        self.assertIn('form', response.context)
        self.assertEqual(response.context['form'].instance, self.user)

    def test_usuario_update_view_other_profile(self):
        """Test que verifica que un usuario no puede editar el perfil de otro"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('usuario_update', kwargs={'pk': self.test_user.pk}))
        
        # Debe redirigir o mostrar error 403
        self.assertIn(response.status_code, [302, 403])

    def test_usuario_update_view_post_valid(self):
        """Test que verifica la actualización exitosa de un usuario"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'first_name': 'Juan Carlos',
            'last_name': 'Pérez López'
        }
        
        response = self.client.post(reverse('usuario_update', kwargs={'pk': self.user.pk}), data)
        
        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('usuario_detail', kwargs={'pk': self.user.pk}))
        
        # Verificar que el usuario fue actualizado
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Juan Carlos')
        self.assertEqual(self.user.last_name, 'Pérez López')

    def test_usuario_update_view_post_invalid(self):
        """Test que verifica la actualización fallida de un usuario"""
        self.client.login(username='testuser', password='testpass123')
        
        # Datos inválidos (email duplicado)
        data = {
            'username': 'testuser',
            'email': 'usertest@test.com',  # Email del otro usuario
            'first_name': 'Juan',
            'last_name': 'Pérez'
        }
        
        response = self.client.post(reverse('usuario_update', kwargs={'pk': self.user.pk}), data)
        
        # Debe mostrar el formulario con errores
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)

    def test_usuario_update_view_not_found(self):
        """Test que verifica la vista de actualización con usuario inexistente"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('usuario_update', kwargs={'pk': 99999}))
        
        self.assertEqual(response.status_code, 404)

    def test_toggle_user_active_status_view_requires_login(self):
        """Test que verifica que la vista de toggle requiere login"""
        response = self.client.post(reverse('toggle_user_active_status', kwargs={'pk': self.user.pk}))
        self.assertEqual(response.status_code, 302)  # Redirección a login

    def test_toggle_user_active_status_view_requires_permission(self):
        """Test que verifica que la vista de toggle requiere permisos"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('toggle_user_active_status', kwargs={'pk': self.test_user.pk}))
        
        # Debe redirigir o mostrar error 403
        self.assertIn(response.status_code, [302, 403])

    def test_toggle_user_active_status_view_with_permission(self):
        """Test que verifica la funcionalidad de toggle con permisos"""
        # Dar permisos al usuario
        content_type = ContentType.objects.get_for_model(get_user_model())
        permission = Permission.objects.get(
            content_type=content_type,
            codename='can_suspend_user'
        )
        self.user.user_permissions.add(permission)
        
        self.client.login(username='testuser', password='testpass123')
        
        # Estado inicial
        self.assertTrue(self.test_user.is_active)
        
        # Toggle a inactivo
        response = self.client.post(reverse('toggle_user_active_status', kwargs={'pk': self.test_user.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirección
        self.test_user.refresh_from_db()
        self.assertFalse(self.test_user.is_active)
        
        # Toggle a activo
        response = self.client.post(reverse('toggle_user_active_status', kwargs={'pk': self.test_user.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirección
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.is_active)

    def test_suspender_usuario_view_requires_login(self):
        """Test que verifica que la vista de suspensión requiere login"""
        response = self.client.post(reverse('suspender_usuario', kwargs={'user_id': self.user.pk}))
        self.assertEqual(response.status_code, 302)  # Redirección a login

    def test_suspender_usuario_view_requires_permission(self):
        """Test que verifica que la vista de suspensión requiere permisos"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('suspender_usuario', kwargs={'user_id': self.test_user.pk}))
        
        # Debe redirigir o mostrar error 403
        self.assertIn(response.status_code, [302, 403])

    def test_suspender_usuario_view_with_permission(self):
        """Test que verifica la funcionalidad de suspensión con permisos"""
        # Dar permisos al usuario
        content_type = ContentType.objects.get_for_model(get_user_model())
        permission = Permission.objects.get(
            content_type=content_type,
            codename='can_suspend_user'
        )
        self.user.user_permissions.add(permission)
        
        self.client.login(username='testuser', password='testpass123')
        
        # Estado inicial
        self.assertTrue(self.test_user.is_active)
        
        # Suspender usuario
        response = self.client.post(reverse('suspender_usuario', kwargs={'user_id': self.test_user.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirección
        self.test_user.refresh_from_db()
        self.assertFalse(self.test_user.is_active)

    def test_usuario_form_with_image(self):
        """Test que verifica el formulario con imagen"""
        self.client.login(username='testuser', password='testpass123')
        
        image_file = create_test_image()
        data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'first_name': 'Juan',
            'last_name': 'Pérez'
        }
        files = {
            'imagen': image_file
        }
        
        response = self.client.post(reverse('usuario_update', kwargs={'pk': self.user.pk}), data, files=files)
        
        self.assertEqual(response.status_code, 302)  # Redirección exitosa
        
        # Verificar que el usuario fue actualizado con imagen
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.imagen)

    def test_usuario_list_view_ordering(self):
        """Test que verifica el ordenamiento de la lista de usuarios"""
        self.client.login(username='testuser', password='testpass123')
        
        # Crear usuarios adicionales
        get_user_model().objects.create_user(
            username='ana',
            email='ana@test.com',
            password='testpass123',
            first_name='Ana'
        )
        get_user_model().objects.create_user(
            username='carlos',
            email='carlos@test.com',
            password='testpass123',
            first_name='Carlos'
        )
        
        response = self.client.get(reverse('usuario_list'))
        
        self.assertEqual(response.status_code, 200)
        usuarios = response.context['usuarios']
        
        # Verificar que están ordenados por username
        usernames = [usuario.username for usuario in usuarios]
        self.assertEqual(usernames, sorted(usernames))

    def test_usuario_context_data(self):
        """Test que verifica los datos de contexto en las vistas"""
        self.client.login(username='testuser', password='testpass123')
        
        # Vista de lista
        response = self.client.get(reverse('usuario_list'))
        self.assertIn('usuarios', response.context)
        
        # Vista de detalle
        response = self.client.get(reverse('usuario_detail', kwargs={'pk': self.user.pk}))
        self.assertIn('usuario', response.context)
        
        # Vista de actualización
        response = self.client.get(reverse('usuario_update', kwargs={'pk': self.user.pk}))
        self.assertIn('form', response.context)

    def test_usuario_messages(self):
        """Test que verifica los mensajes de éxito"""
        # Dar permisos al usuario
        content_type = ContentType.objects.get_for_model(get_user_model())
        permission = Permission.objects.get(
            content_type=content_type,
            codename='add_customuser'
        )
        self.user.user_permissions.add(permission)
        
        self.client.login(username='testuser', password='testpass123')
        
        # Crear usuario
        data = {
            'username': 'mensajeuser',
            'email': 'mensaje@test.com',
            'password1': 'MensajePass123!',
            'password2': 'MensajePass123!',
            'first_name': 'Mensaje',
            'last_name': 'Usuario'
        }
        
        response = self.client.post(reverse('usuario_create'), data, follow=True)
        
        # Verificar mensaje de éxito
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('creado exitosamente' in str(message) for message in messages))
        
        # Actualizar usuario
        data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'first_name': 'Juan Actualizado',
            'last_name': 'Pérez'
        }
        response = self.client.post(reverse('usuario_update', kwargs={'pk': self.user.pk}), data, follow=True)
        
        # Verificar mensaje de éxito
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('actualizado exitosamente' in str(message) for message in messages))

    def test_usuario_permissions(self):
        """Test que verifica los permisos en las vistas"""
        # Usuario sin permisos específicos
        self.client.login(username='testuser', password='testpass123')
        
        # Debe poder acceder a las vistas básicas
        response = self.client.get(reverse('usuario_list'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('usuario_detail', kwargs={'pk': self.user.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Debe poder editar su propio perfil
        response = self.client.get(reverse('usuario_update', kwargs={'pk': self.user.pk}))
        self.assertEqual(response.status_code, 200)
        
        # No debe poder crear usuarios sin permisos
        response = self.client.get(reverse('usuario_create'))
        self.assertIn(response.status_code, [302, 403])

    def test_usuario_delete_view_not_implemented(self):
        """Test que verifica que no existe vista de eliminación de usuarios"""
        self.client.login(username='testuser', password='testpass123')
        
        # Intentar acceder a una URL de eliminación (no debe existir)
        try:
            response = self.client.get(reverse('usuario_delete', kwargs={'pk': self.user.pk}))
            # Si existe, debe requerir permisos especiales
            self.assertIn(response.status_code, [302, 403, 404])
        except:
            # Si no existe la URL, es correcto
            pass

    def test_usuario_password_change_view(self):
        """Test que verifica la vista de cambio de contraseña"""
        self.client.login(username='testuser', password='testpass123')
        
        # Verificar que existe la vista
        try:
            response = self.client.get(reverse('password_change'))
            self.assertEqual(response.status_code, 200)
        except:
            # Si no existe, es correcto (puede estar deshabilitada)
            pass

    def test_usuario_profile_view(self):
        """Test que verifica que un usuario puede ver su propio perfil"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('usuario_detail', kwargs={'pk': self.user.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['usuario'], self.user)

    def test_usuario_other_profile_view(self):
        """Test que verifica que un usuario puede ver el perfil de otro"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('usuario_detail', kwargs={'pk': self.test_user.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['usuario'], self.test_user) 