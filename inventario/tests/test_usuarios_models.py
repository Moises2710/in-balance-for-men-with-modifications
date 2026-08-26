
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
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

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CustomUserModelTest(TestCase):
    """Pruebas para el modelo CustomUser"""
    
    @classmethod
    def setUpTestData(cls):
        """Configuración inicial para todos los tests"""
        User = get_user_model()
        
        # Usuario de prueba
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            first_name='Juan',
            last_name='Pérez'
        )

    @classmethod
    def tearDownClass(cls):
        """Limpieza después de todas las pruebas"""
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_user_creation(self):
        """Test que verifica la creación básica de un usuario"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@test.com')
        self.assertEqual(self.user.first_name, 'Juan')
        self.assertEqual(self.user.last_name, 'Pérez')
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertIsNone(self.user.imagen)

    def test_user_str_method(self):
        """Test que verifica el método __str__ del usuario"""
        # Usuario con nombre completo
        self.assertEqual(str(self.user), 'Juan Pérez')
        
        # Usuario sin nombre
        user_sin_nombre = get_user_model().objects.create_user(
            username='sinombre',
            email='sinombre@test.com',
            password='testpass123'
        )
        self.assertEqual(str(user_sin_nombre), 'sinombre')

    def test_username_unique_constraint(self):
        """Test que verifica que el username debe ser único"""
        with self.assertRaises(IntegrityError):
            get_user_model().objects.create_user(
                username='testuser',  # Mismo username
                email='otro@test.com',
                password='testpass123'
            )

    def test_email_unique_constraint(self):
        """Test que verifica que el email debe ser único"""
        with self.assertRaises(IntegrityError):
            get_user_model().objects.create_user(
                username='otrouser',
                email='test@test.com',  # Mismo email
                password='testpass123'
            )

    def test_password_validation(self):
        """Test que verifica la validación de contraseñas"""
        # Contraseña válida
        user_valido = get_user_model().objects.create_user(
            username='validuser',
            email='valid@test.com',
            password='ValidPass123!'
        )
        self.assertTrue(user_valido.check_password('ValidPass123!'))
        
        # Contraseña muy corta
        with self.assertRaises(ValidationError):
            user_invalido = get_user_model()(
                username='invaliduser',
                email='invalid@test.com'
            )
            user_invalido.set_password('123')  # Muy corta
            user_invalido.full_clean()

    def test_email_validation(self):
        """Test que verifica la validación del email"""
        # Email válido
        user_valido = get_user_model()(
            username='test',
            email='test@test.com'
        )
        user_valido.full_clean()  # No debe lanzar error
        
        # Email inválido
        with self.assertRaises(ValidationError):
            user_invalido = get_user_model()(
                username='test',
                email='email_invalido'
            )
            user_invalido.full_clean()

    def test_is_active_default_value(self):
        """Test que verifica el valor por defecto de is_active"""
        user = get_user_model().objects.create_user(
            username='newuser',
            email='new@test.com',
            password='testpass123'
        )
        self.assertTrue(user.is_active)  # Por defecto True

    def test_is_staff_default_value(self):
        """Test que verifica el valor por defecto de is_staff"""
        user = get_user_model().objects.create_user(
            username='staffuser',
            email='staff@test.com',
            password='testpass123'
        )
        self.assertFalse(user.is_staff)  # Por defecto False

    def test_is_superuser_default_value(self):
        """Test que verifica el valor por defecto de is_superuser"""
        user = get_user_model().objects.create_user(
            username='superuser',
            email='super@test.com',
            password='testpass123'
        )
        self.assertFalse(user.is_superuser)  # Por defecto False

    def test_imagen_upload(self):
        """Test que verifica la subida de imágenes"""
        image_file = create_test_image()
        user = get_user_model().objects.create_user(
            username='imagenuser',
            email='imagen@test.com',
            password='testpass123',
            imagen=image_file
        )
        
        self.assertIsNotNone(user.imagen)
        self.assertTrue(os.path.exists(user.imagen.path))

    def test_imagen_validation(self):
        """Test que verifica la validación de imágenes"""
        # Crear archivo de texto (no imagen)
        text_file = SimpleUploadedFile('test.txt', b'not an image', content_type='text/plain')
        
        with self.assertRaises(ValidationError):
            user = get_user_model()(
                username='test',
                email='test@test.com',
                imagen=text_file
            )
            user.full_clean()

    def test_sanitization(self):
        """Test que verifica la sanitización de datos"""
        user = get_user_model().objects.create_user(
            username='sanitizeuser',
            email='sanitize@test.com',
            password='testpass123',
            first_name='<script>alert("xss")</script>Juan',
            last_name='<script>alert("xss")</script>Pérez'
        )
        
        # Los datos deben estar sanitizados
        self.assertNotIn('<script>', user.first_name)
        self.assertNotIn('<script>', user.last_name)

    def test_optional_fields(self):
        """Test que verifica que los campos opcionales funcionan correctamente"""
        user = get_user_model().objects.create_user(
            username='optionaluser',
            email='optional@test.com',
            password='testpass123'
            # Sin first_name, last_name, imagen
        )
        
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
        self.assertIsNone(user.imagen)

    def test_user_authentication(self):
        """Test que verifica la autenticación del usuario"""
        # Verificar que la contraseña funciona
        self.assertTrue(self.user.check_password('testpass123'))
        self.assertFalse(self.user.check_password('wrongpass'))

    def test_user_permissions(self):
        """Test que verifica los permisos del usuario"""
        # Usuario normal no tiene permisos especiales
        self.assertFalse(self.user.has_perm('auth.add_user'))
        self.assertFalse(self.user.has_perm('auth.change_user'))
        
        # Usuario staff tiene algunos permisos
        self.user.is_staff = True
        self.user.save()
        self.assertTrue(self.user.has_perm('auth.add_user'))

    def test_superuser_creation(self):
        """Test que verifica la creación de superusuarios"""
        superuser = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123'
        )
        
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_active)

    def test_user_deactivation(self):
        """Test que verifica la desactivación de usuarios"""
        self.assertTrue(self.user.is_active)
        
        # Desactivar usuario
        self.user.is_active = False
        self.user.save()
        self.assertFalse(self.user.is_active)
        
        # Reactivar usuario
        self.user.is_active = True
        self.user.save()
        self.assertTrue(self.user.is_active)

    def test_password_change(self):
        """Test que verifica el cambio de contraseña"""
        old_password = 'testpass123'
        new_password = 'newpass456'
        
        # Verificar contraseña antigua
        self.assertTrue(self.user.check_password(old_password))
        
        # Cambiar contraseña
        self.user.set_password(new_password)
        self.user.save()
        
        # Verificar nueva contraseña
        self.assertFalse(self.user.check_password(old_password))
        self.assertTrue(self.user.check_password(new_password))

    def test_user_groups(self):
        """Test que verifica la funcionalidad de grupos"""
        from django.contrib.auth.models import Group
        
        # Crear grupo
        group = Group.objects.create(name='Test Group')
        
        # Agregar usuario al grupo
        self.user.groups.add(group)
        
        # Verificar que está en el grupo
        self.assertIn(group, self.user.groups.all())
        self.assertTrue(self.user.groups.filter(name='Test Group').exists())

    def test_user_permissions_direct(self):
        """Test que verifica permisos directos del usuario"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        # Obtener permiso
        content_type = ContentType.objects.get_for_model(get_user_model())
        permission = Permission.objects.get(
            content_type=content_type,
            codename='add_customuser'
        )
        
        # Agregar permiso al usuario
        self.user.user_permissions.add(permission)
        
        # Verificar permiso
        self.assertTrue(self.user.has_perm('inventario.add_customuser'))

    def test_user_creation_without_password(self):
        """Test que verifica la creación de usuario sin contraseña"""
        user = get_user_model().objects.create_user(
            username='nopassuser',
            email='nopass@test.com'
        )
        
        self.assertFalse(user.has_usable_password())

    def test_user_creation_with_blank_password(self):
        """Test que verifica la creación de usuario con contraseña en blanco"""
        user = get_user_model().objects.create_user(
            username='blankpassuser',
            email='blankpass@test.com',
            password=''
        )
        
        self.assertFalse(user.has_usable_password())

    def test_user_get_full_name(self):
        """Test que verifica el método get_full_name"""
        # Usuario con nombre completo
        self.assertEqual(self.user.get_full_name(), 'Juan Pérez')
        
        # Usuario sin nombre
        user_sin_nombre = get_user_model().objects.create_user(
            username='sinombre',
            email='sinombre@test.com',
            password='testpass123'
        )
        self.assertEqual(user_sin_nombre.get_full_name(), '')

    def test_user_get_short_name(self):
        """Test que verifica el método get_short_name"""
        # Usuario con nombre
        self.assertEqual(self.user.get_short_name(), 'Juan')
        
        # Usuario sin nombre
        user_sin_nombre = get_user_model().objects.create_user(
            username='sinombre',
            email='sinombre@test.com',
            password='testpass123'
        )
        self.assertEqual(user_sin_nombre.get_short_name(), '')

    def test_user_natural_key(self):
        """Test que verifica la clave natural del usuario"""
        self.assertEqual(self.user.natural_key(), ('testuser',))

    def test_user_required_fields(self):
        """Test que verifica los campos requeridos"""
        # Usuario con campos mínimos requeridos
        user = get_user_model().objects.create_user(
            username='minimaluser',
            email='minimal@test.com',
            password='testpass123'
        )
        
        self.assertIsNotNone(user.pk)
        self.assertTrue(user.is_active)

    def test_user_username_max_length(self):
        """Test que verifica la longitud máxima del username"""
        # Username válido
        user_valido = get_user_model()(
            username='validusername',
            email='valid@test.com'
        )
        user_valido.full_clean()  # No debe lanzar error
        
        # Username muy largo
        long_username = 'a' * 151  # Más del límite
        with self.assertRaises(ValidationError):
            user_invalido = get_user_model()(
                username=long_username,
                email='invalid@test.com'
            )
            user_invalido.full_clean()

    def test_user_email_max_length(self):
        """Test que verifica la longitud máxima del email"""
        # Email válido
        user_valido = get_user_model()(
            username='test',
            email='test@test.com'
        )
        user_valido.full_clean()  # No debe lanzar error
        
        # Email muy largo
        long_email = 'a' * 245 + '@test.com'  # Más del límite
        with self.assertRaises(ValidationError):
            user_invalido = get_user_model()(
                username='test',
                email=long_email
            )
            user_invalido.full_clean()

    def test_user_date_joined(self):
        """Test que verifica el campo date_joined"""
        from django.utils import timezone
        
        user = get_user_model().objects.create_user(
            username='dateuser',
            email='date@test.com',
            password='testpass123'
        )
        
        # date_joined debe estar cerca del tiempo actual
        time_diff = abs((timezone.now() - user.date_joined).total_seconds())
        self.assertLess(time_diff, 10)  # Diferencia menor a 10 segundos

    def test_user_last_login(self):
        """Test que verifica el campo last_login"""
        # Inicialmente debe ser None
        self.assertIsNone(self.user.last_login)
        
        # Simular login
        from django.utils import timezone
        self.user.last_login = timezone.now()
        self.user.save()
        
        self.assertIsNotNone(self.user.last_login) 