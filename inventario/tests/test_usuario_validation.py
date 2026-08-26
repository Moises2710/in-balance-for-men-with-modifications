from django.test import TestCase, Client
from django.contrib.auth.models import Group
from django.urls import reverse
from inventario.forms import CustomUserCreationForm
from inventario.models import CustomUser


class UsuarioValidationTestCase(TestCase):
    """Test case para verificar la validación de campos obligatorios antes de la validación de contraseña"""
    
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.client = Client()
        self.group = Group.objects.create(name='Test Group')
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '123456789',
            'group': self.group.id,
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
        }
    
    def test_form_required_fields_validation(self):
        """Prueba que los campos obligatorios se validen correctamente"""
        print("\n🧪 PROBANDO VALIDACIÓN DE CAMPOS OBLIGATORIOS")
        
        # Caso 1: Formulario completamente vacío
        empty_data = {
            'username': '',
            'email': '',
            'first_name': '',
            'last_name': '',
            'telefono': '',
            'group': '',
            'password1': '',
            'password2': '',
        }
        
        form = CustomUserCreationForm(data=empty_data)
        self.assertFalse(form.is_valid())
        
        # Verificar que se muestren errores para campos obligatorios
        required_fields = ['username', 'password1', 'password2', 'group']
        for field in required_fields:
            self.assertIn(field, form.errors)
            self.assertIn('Este campo es obligatorio', str(form.errors[field]))
        
        print("✅ Caso 1: Formulario vacío - Errores de campos obligatorios detectados")
    
    def test_form_partial_validation(self):
        """Prueba validación con campos parcialmente completos"""
        print("\n🧪 PROBANDO VALIDACIÓN PARCIAL")
        
        # Caso 2: Solo username completado
        partial_data = {
            'username': 'testuser',
            'email': '',
            'first_name': '',
            'last_name': '',
            'telefono': '',
            'group': '',
            'password1': '',
            'password2': '',
        }
        
        form = CustomUserCreationForm(data=partial_data)
        self.assertFalse(form.is_valid())
        
        # Verificar que aún faltan campos obligatorios
        missing_required = ['password1', 'password2', 'group']
        for field in missing_required:
            self.assertIn(field, form.errors)
        
        print("✅ Caso 2: Solo username - Errores de campos faltantes detectados")
    
    def test_form_password_validation_order(self):
        """Prueba que la validación de contraseña solo ocurra después de campos obligatorios"""
        print("\n🧪 PROBANDO ORDEN DE VALIDACIÓN")
        
        # Caso 3: Campos obligatorios completos pero contraseña débil
        weak_password_data = self.user_data.copy()
        weak_password_data['password1'] = 'weak'
        weak_password_data['password2'] = 'weak'
        
        form = CustomUserCreationForm(data=weak_password_data)
        self.assertFalse(form.is_valid())
        
        # Verificar que el error sea de contraseña, no de campos obligatorios
        self.assertIn('password2', form.errors)
        self.assertNotIn('username', form.errors)
        self.assertNotIn('group', form.errors)
        
        print("✅ Caso 3: Contraseña débil - Error de contraseña detectado (no de campos obligatorios)")
    
    def test_form_complete_validation(self):
        """Prueba formulario completamente válido"""
        print("\n🧪 PROBANDO FORMULARIO COMPLETO")
        
        form = CustomUserCreationForm(data=self.user_data)
        self.assertTrue(form.is_valid())
        
        print("✅ Caso 4: Formulario completo - Validación exitosa")
    
    def test_form_widget_attributes(self):
        """Prueba que los widgets tengan los atributos correctos"""
        print("\n🧪 PROBANDO ATRIBUTOS DE WIDGETS")
        
        form = CustomUserCreationForm()
        
        # Verificar atributos required
        required_fields = ['username', 'password1', 'password2', 'group']
        for field_name in required_fields:
            self.assertIn(field_name, form.fields)
            field = form.fields[field_name]
            self.assertEqual(field.widget.attrs.get('required'), 'required')
        
        # Verificar clases CSS
        css_fields = ['username', 'email', 'first_name', 'last_name', 'telefono']
        for field_name in css_fields:
            self.assertIn(field_name, form.fields)
            field = form.fields[field_name]
            self.assertIn('form-control', field.widget.attrs.get('class', ''))
        
        print("✅ Widgets: Atributos required y CSS aplicados correctamente")
    
    def test_form_view_rendering(self):
        """Prueba que la vista del formulario se renderice correctamente"""
        print("\n🧪 PROBANDO RENDERIZADO DE VISTA")
        
        # Crear un superusuario para acceder a la vista
        admin_user = CustomUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123!'
        )
        self.client.force_login(admin_user)
        
        # Acceder a la vista de crear usuario
        response = self.client.get(reverse('usuario_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventario/usuarios/usuario_form.html')
        
        # Verificar que el formulario esté en el contexto
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertIsInstance(form, CustomUserCreationForm)
        
        print("✅ Vista: Formulario renderizado correctamente")
    
    def test_form_submission_validation(self):
        """Prueba el envío del formulario con diferentes escenarios"""
        print("\n🧪 PROBANDO ENVÍO DE FORMULARIO")
        
        # Crear un superusuario para acceder a la vista
        admin_user = CustomUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123!'
        )
        self.client.force_login(admin_user)
        
        # Caso 1: Envío con campos vacíos
        empty_response = self.client.post(reverse('usuario_create'), {})
        self.assertEqual(empty_response.status_code, 200)  # No redirige, muestra errores
        
        # Caso 2: Envío con datos válidos
        valid_response = self.client.post(reverse('usuario_create'), self.user_data)
        self.assertEqual(valid_response.status_code, 302)  # Redirige al éxito
        
        print("✅ Envío: Validación de envío funcionando correctamente")
    
    def tearDown(self):
        """Limpieza después de las pruebas"""
        # Limpiar usuarios creados durante las pruebas
        CustomUser.objects.filter(username__in=['testuser', 'admin']).delete()
        Group.objects.filter(name='Test Group').delete()


if __name__ == '__main__':
    # Ejecutar las pruebas
    import django
    from django.test.utils import get_runner
    from django.conf import settings
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['inventario.tests.test_usuario_validation'])
    
    if failures:
        print(f"\n❌ {failures} pruebas fallaron")
    else:
        print("\n✅ Todas las pruebas pasaron exitosamente") 