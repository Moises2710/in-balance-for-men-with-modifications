from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from PIL import Image
from io import BytesIO
import tempfile
import os
import shutil

from inventario.forms import CustomUserCreationForm, CustomUserChangeForm

# Configuración para usar un directorio temporal para MEDIA_ROOT durante las pruebas
TEST_MEDIA_ROOT = tempfile.mkdtemp()

def create_test_image():
    """Crea una imagen de prueba para los tests"""
    image = Image.new('RGB', (100, 100), color='green')
    image_file = BytesIO()
    image.save(image_file, 'JPEG')
    image_file.seek(0)
    return SimpleUploadedFile('test.jpg', image_file.getvalue(), content_type='image/jpeg')

class CustomUserCreationFormTest(TestCase):
    """Pruebas para el formulario de creación de usuarios"""
    
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

    def test_user_creation_form_valid_data(self):
        """Test que verifica que el formulario acepta datos válidos"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!',
            'first_name': 'Nuevo',
            'last_name': 'Usuario'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_user_creation_form_required_fields(self):
        """Test que verifica los campos requeridos"""
        # Formulario sin campos requeridos
        form = CustomUserCreationForm(data={})
        self.assertFalse(form.is_valid())
        
        # Verificar que los campos requeridos están en los errores
        self.assertIn('username', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('password1', form.errors)
        self.assertIn('password2', form.errors)

    def test_user_creation_form_optional_fields(self):
        """Test que verifica que los campos opcionales funcionan"""
        form_data = {
            'username': 'optionaluser',
            'email': 'optional@test.com',
            'password1': 'OptionalPass123!',
            'password2': 'OptionalPass123!'
            # Sin first_name, last_name
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_user_creation_form_username_unique(self):
        """Test que verifica que el username debe ser único"""
        form_data = {
            'username': 'testuser',  # Ya existe
            'email': 'new@test.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_user_creation_form_email_unique(self):
        """Test que verifica que el email debe ser único"""
        form_data = {
            'username': 'newuser',
            'email': 'test@test.com',  # Ya existe
            'password1': 'TestPass123!',
            'password2': 'TestPass123!'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_user_creation_form_email_validation(self):
        """Test que verifica la validación del email"""
        # Email válido
        form_data = {
            'username': 'emailuser',
            'email': 'email@test.com',
            'password1': 'EmailPass123!',
            'password2': 'EmailPass123!'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Email inválido
        form_data['email'] = 'email_invalido'
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_user_creation_form_password_validation(self):
        """Test que verifica la validación de contraseñas"""
        # Contraseña válida
        form_data = {
            'username': 'passuser',
            'email': 'pass@test.com',
            'password1': 'ValidPass123!',
            'password2': 'ValidPass123!'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Contraseñas no coinciden
        form_data['password2'] = 'DifferentPass123!'
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_user_creation_form_password_too_short(self):
        """Test que verifica que la contraseña no sea muy corta"""
        form_data = {
            'username': 'shortpassuser',
            'email': 'shortpass@test.com',
            'password1': '123',
            'password2': '123'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_user_creation_form_password_too_common(self):
        """Test que verifica que la contraseña no sea muy común"""
        form_data = {
            'username': 'commonpassuser',
            'email': 'commonpass@test.com',
            'password1': 'password',
            'password2': 'password'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_user_creation_form_password_numeric(self):
        """Test que verifica que la contraseña no sea solo numérica"""
        form_data = {
            'username': 'numericpassuser',
            'email': 'numericpass@test.com',
            'password1': '123456789',
            'password2': '123456789'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_user_creation_form_save_method(self):
        """Test que verifica el método save del formulario"""
        form_data = {
            'username': 'saveuser',
            'email': 'save@test.com',
            'password1': 'SavePass123!',
            'password2': 'SavePass123!',
            'first_name': 'Save',
            'last_name': 'User'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        user = form.save()
        self.assertEqual(user.username, 'saveuser')
        self.assertEqual(user.email, 'save@test.com')
        self.assertEqual(user.first_name, 'Save')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('SavePass123!'))

    def test_user_creation_form_save_commit_false(self):
        """Test que verifica el método save con commit=False"""
        form_data = {
            'username': 'commituser',
            'email': 'commit@test.com',
            'password1': 'CommitPass123!',
            'password2': 'CommitPass123!'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        user = form.save(commit=False)
        self.assertEqual(user.username, 'commituser')
        self.assertEqual(user.email, 'commit@test.com')
        # El usuario no debe estar guardado en la base de datos
        self.assertIsNone(user.pk)

    def test_user_creation_form_field_labels(self):
        """Test que verifica las etiquetas de los campos"""
        form = CustomUserCreationForm()
        
        self.assertEqual(form.fields['username'].label, 'Username')
        self.assertEqual(form.fields['email'].label, 'Email address')
        self.assertEqual(form.fields['password1'].label, 'Password')
        self.assertEqual(form.fields['password2'].label, 'Password confirmation')
        self.assertEqual(form.fields['first_name'].label, 'First name')
        self.assertEqual(form.fields['last_name'].label, 'Last name')

    def test_user_creation_form_field_help_text(self):
        """Test que verifica los textos de ayuda de los campos"""
        form = CustomUserCreationForm()
        
        # Verificar que algunos campos tienen texto de ayuda
        self.assertIsNotNone(form.fields['username'].help_text)
        self.assertIsNotNone(form.fields['password1'].help_text)
        self.assertIsNotNone(form.fields['password2'].help_text)

    def test_user_creation_form_field_widgets(self):
        """Test que verifica los widgets de los campos"""
        form = CustomUserCreationForm()
        
        # Verificar tipos de widgets
        self.assertEqual(form.fields['username'].widget.__class__.__name__, 'TextInput')
        self.assertEqual(form.fields['email'].widget.__class__.__name__, 'EmailInput')
        self.assertEqual(form.fields['password1'].widget.__class__.__name__, 'PasswordInput')
        self.assertEqual(form.fields['password2'].widget.__class__.__name__, 'PasswordInput')
        self.assertEqual(form.fields['first_name'].widget.__class__.__name__, 'TextInput')
        self.assertEqual(form.fields['last_name'].widget.__class__.__name__, 'TextInput')

    def test_user_creation_form_username_max_length(self):
        """Test que verifica la longitud máxima del username"""
        # Username muy largo
        long_username = 'a' * 151  # Más del límite
        form_data = {
            'username': long_username,
            'email': 'long@test.com',
            'password1': 'LongPass123!',
            'password2': 'LongPass123!'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_user_creation_form_email_max_length(self):
        """Test que verifica la longitud máxima del email"""
        # Email muy largo
        long_email = 'a' * 245 + '@test.com'  # Más del límite
        form_data = {
            'username': 'longemailuser',
            'email': long_email,
            'password1': 'LongEmailPass123!',
            'password2': 'LongEmailPass123!'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

class CustomUserChangeFormTest(TestCase):
    """Pruebas para el formulario de cambio de usuarios"""
    
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

    def test_user_change_form_valid_data(self):
        """Test que verifica que el formulario acepta datos válidos"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'first_name': 'Juan Carlos',
            'last_name': 'Pérez López'
        }
        
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_user_change_form_required_fields(self):
        """Test que verifica los campos requeridos"""
        # Formulario sin campos requeridos
        form = CustomUserChangeForm(data={}, instance=self.user)
        self.assertFalse(form.is_valid())
        
        # Verificar que los campos requeridos están en los errores
        self.assertIn('username', form.errors)
        self.assertIn('email', form.errors)

    def test_user_change_form_optional_fields(self):
        """Test que verifica que los campos opcionales funcionan"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com'
            # Sin first_name, last_name
        }
        
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_user_change_form_username_unique(self):
        """Test que verifica que el username debe ser único"""
        # Crear otro usuario
        User = get_user_model()
        otro_user = User.objects.create_user(
            username='otrouser',
            email='otro@test.com',
            password='testpass123'
        )
        
        # Intentar usar el username del otro usuario
        form_data = {
            'username': 'otrouser',  # Username del otro usuario
            'email': 'test@test.com'
        }
        
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_user_change_form_email_unique(self):
        """Test que verifica que el email debe ser único"""
        # Crear otro usuario
        User = get_user_model()
        otro_user = User.objects.create_user(
            username='otrouser',
            email='otro@test.com',
            password='testpass123'
        )
        
        # Intentar usar el email del otro usuario
        form_data = {
            'username': 'testuser',
            'email': 'otro@test.com'  # Email del otro usuario
        }
        
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_user_change_form_email_validation(self):
        """Test que verifica la validación del email"""
        # Email válido
        form_data = {
            'username': 'testuser',
            'email': 'valid@test.com'
        }
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())
        
        # Email inválido
        form_data['email'] = 'email_invalido'
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_user_change_form_with_image(self):
        """Test que verifica el formulario con imagen"""
        image_file = create_test_image()
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com'
        }
        files = {
            'imagen': image_file
        }
        
        form = CustomUserChangeForm(data=form_data, files=files, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_user_change_form_image_validation(self):
        """Test que verifica la validación de imágenes"""
        # Crear archivo de texto (no imagen)
        text_file = SimpleUploadedFile('test.txt', b'not an image', content_type='text/plain')
        
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com'
        }
        files = {
            'imagen': text_file
        }
        
        form = CustomUserChangeForm(data=form_data, files=files, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('imagen', form.errors)

    def test_user_change_form_save_method(self):
        """Test que verifica el método save del formulario"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'first_name': 'Juan Actualizado',
            'last_name': 'Pérez Actualizado'
        }
        
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())
        
        user = form.save()
        self.assertEqual(user.first_name, 'Juan Actualizado')
        self.assertEqual(user.last_name, 'Pérez Actualizado')

    def test_user_change_form_save_commit_false(self):
        """Test que verifica el método save con commit=False"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'first_name': 'Juan Sin Guardar',
            'last_name': 'Pérez Sin Guardar'
        }
        
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())
        
        user = form.save(commit=False)
        self.assertEqual(user.first_name, 'Juan Sin Guardar')
        self.assertEqual(user.last_name, 'Pérez Sin Guardar')
        
        # Los cambios no deben estar guardados en la base de datos
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Juan')  # Valor original

    def test_user_change_form_field_labels(self):
        """Test que verifica las etiquetas de los campos"""
        form = CustomUserChangeForm(instance=self.user)
        
        self.assertEqual(form.fields['username'].label, 'Username')
        self.assertEqual(form.fields['email'].label, 'Email address')
        self.assertEqual(form.fields['first_name'].label, 'First name')
        self.assertEqual(form.fields['last_name'].label, 'Last name')
        self.assertEqual(form.fields['imagen'].label, 'Imagen')

    def test_user_change_form_field_widgets(self):
        """Test que verifica los widgets de los campos"""
        form = CustomUserChangeForm(instance=self.user)
        
        # Verificar tipos de widgets
        self.assertEqual(form.fields['username'].widget.__class__.__name__, 'TextInput')
        self.assertEqual(form.fields['email'].widget.__class__.__name__, 'EmailInput')
        self.assertEqual(form.fields['first_name'].widget.__class__.__name__, 'TextInput')
        self.assertEqual(form.fields['last_name'].widget.__class__.__name__, 'TextInput')
        self.assertEqual(form.fields['imagen'].widget.__class__.__name__, 'ClearableFileInput')

    def test_user_change_form_initial_data(self):
        """Test que verifica los datos iniciales del formulario"""
        form = CustomUserChangeForm(instance=self.user)
        
        # Verificar que los datos iniciales coinciden con la instancia
        self.assertEqual(form.initial['username'], 'testuser')
        self.assertEqual(form.initial['email'], 'test@test.com')
        self.assertEqual(form.initial['first_name'], 'Juan')
        self.assertEqual(form.initial['last_name'], 'Pérez')

    def test_user_change_form_max_length_validation(self):
        """Test que verifica la validación de longitud máxima"""
        # Username muy largo
        long_username = 'a' * 151  # Más del límite
        form_data = {
            'username': long_username,
            'email': 'test@test.com'
        }
        
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_user_change_form_blank_fields(self):
        """Test que verifica el comportamiento con campos en blanco"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'first_name': '',  # Campo opcional en blanco
            'last_name': ''    # Campo opcional en blanco
        }
        
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_user_change_form_error_messages(self):
        """Test que verifica los mensajes de error personalizados"""
        form_data = {
            'username': '',
            'email': ''
        }
        
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        
        # Verificar que hay mensajes de error
        self.assertIn('username', form.errors)
        self.assertIn('email', form.errors) 