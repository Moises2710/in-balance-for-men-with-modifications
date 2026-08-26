from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django import forms
from .models import CustomUser, Producto, Venta, DetalleVenta, Color, Cliente, Pago, MetodoPago, GastoAdministrativo
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.contrib.auth.forms import AuthenticationForm
from captcha.fields import CaptchaField
from django.contrib.auth.models import Group
from django.contrib.auth import authenticate
from django.utils import timezone

class CustomUserCreationForm(UserCreationForm):
    group = forms.ModelChoiceField(  
        queryset=Group.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Grupo de usuario"
    )

    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'telefono',
            'imagen',
            'group',  # Agregar el campo group a los fields
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Agregar atributo required a los campos obligatorios
        self.fields['username'].widget.attrs.update({'required': 'required', 'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'required': 'required'})
        self.fields['password2'].widget.attrs.update({'required': 'required'})
        self.fields['group'].widget.attrs.update({'required': 'required'})
        
        # Agregar clases CSS a otros campos
        for field_name, field in self.fields.items():
            if field_name not in ['username', 'password1', 'password2', 'group']:
                field.widget.attrs.update({'class': 'form-control'})
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        
        # Asegurar que el usuario se cree activo por defecto
        user.is_active = True
    
        if commit:
            user.save()
            group = self.cleaned_data['group']  
            user.groups.clear()
            user.groups.add(group)
        return user
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Este correo ya está en uso. Intenta con otro.")
        return email

class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'telefono', 'imagen'] 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        user_id = self.instance.pk
        if CustomUser.objects.exclude(pk=user_id).filter(email=email).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return email

class SimpleCaptchaLoginForm(AuthenticationForm):
    # Campo oculto para el token de reCAPTCHA v3
    recaptcha_token = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label=''
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # No agregar captcha por defecto, solo cuando sea necesario
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        recaptcha_token = self.cleaned_data.get('recaptcha_token')
        
        # Debug: Imprimir datos recibidos
        print(f"DEBUG FORM: username='{username}', password={'*' * len(password) if password else 'None'}, recaptcha_token={'*' * 20 if recaptcha_token else 'None'}")
        
        # Validar reCAPTCHA v3 si está disponible
        if recaptcha_token:
            try:
                from .recaptcha_service import RecaptchaV3Service
                recaptcha_service = RecaptchaV3Service()
                
                if recaptcha_service.is_configured():
                    validation_result = recaptcha_service.validate_token(recaptcha_token, 'login')
                    
                    if not validation_result['valid']:
                        # Si reCAPTCHA v3 falla, agregar captcha tradicional
                        if 'captcha' not in self.fields:
                            self.fields['captcha'] = CaptchaField(
                                label='Verificación',
                                error_messages={
                                    'invalid': 'El texto introducido no coincide con la imagen.',
                                    'required': '¡Por favor, completa la verificación!'
                                }
                            )
                        self.add_error('captcha', 'Verificación de seguridad fallida. Por favor, completa el captcha.')
                        return self.cleaned_data
                    else:
                        # reCAPTCHA v3 exitoso, limpiar errores de captcha si los hay
                        if 'captcha' in self.errors:
                            del self.errors['captcha']
                else:
                    # Si reCAPTCHA v3 no está configurado, agregar captcha tradicional
                    if 'captcha' not in self.fields:
                        self.fields['captcha'] = CaptchaField(
                            label='Verificación',
                            error_messages={
                                'invalid': 'El texto introducido no coincide con la imagen.',
                                'required': '¡Por favor, completa la verificación!'
                            }
                        )
                    self.add_error('captcha', 'reCAPTCHA v3 no configurado. Por favor, completa el captcha.')
                    return self.cleaned_data
            except Exception as e:
                # Si hay error con reCAPTCHA v3, agregar captcha tradicional
                if 'captcha' not in self.fields:
                    self.fields['captcha'] = CaptchaField(
                        label='Verificación',
                        error_messages={
                            'invalid': 'El texto introducido no coincide con la imagen.',
                            'required': '¡Por favor, completa la verificación!'
                        }
                    )
                self.add_error('captcha', 'Error en verificación de seguridad. Por favor, completa el captcha.')
                return self.cleaned_data
        else:
            # Si no hay token de reCAPTCHA v3, agregar captcha tradicional
            if 'captcha' not in self.fields:
                self.fields['captcha'] = CaptchaField(
                    label='Verificación',
                    error_messages={
                        'invalid': 'El texto introducido no coincide con la imagen.',
                        'required': '¡Por favor, completa la verificación!'
                    }
                )
            self.add_error('captcha', 'Por favor, completa la verificación.')
            return self.cleaned_data
        
        if username and password:
            try:
                # Obtener la versión más reciente del usuario para evitar problemas de caché
                user = CustomUser.objects.get(username=username)
                
                # Verificar si el usuario está bloqueado (esto también limpia automáticamente si expiró)
                if user.is_locked():
                    remaining_time = user.get_remaining_lockout_time()
                    if remaining_time > 0:
                        if remaining_time >= 60:
                            hours = remaining_time // 60
                            minutes = remaining_time % 60
                            if minutes > 0:
                                time_str = f"{hours} hora{'s' if hours != 1 else ''} y {minutes} minuto{'s' if minutes != 1 else ''}"
                            else:
                                time_str = f"{hours} hora{'s' if hours != 1 else ''}"
                        else:
                            time_str = f"{remaining_time} minuto{'s' if remaining_time != 1 else ''}"
                        
                        raise ValidationError(
                            f'Tu cuenta está bloqueada temporalmente. Intenta nuevamente en {time_str}.'
                        )
                
                # Intentar autenticar
                self.user_cache = authenticate(self.request, username=username, password=password)
                
                if self.user_cache is None:
                    # Login fallido
                    user.record_failed_login()
                    
                    # Registrar intento fallido por IP
                    self._record_ip_failed_attempt()
                    
                    # Verificar si ahora está bloqueado
                    if user.is_locked():
                        remaining_time = user.get_remaining_lockout_time()
                        if remaining_time >= 60:
                            hours = remaining_time // 60
                            minutes = remaining_time % 60
                            if minutes > 0:
                                time_str = f"{hours} hora{'s' if hours != 1 else ''} y {minutes} minuto{'s' if minutes != 1 else ''}"
                            else:
                                time_str = f"{remaining_time} hora{'s' if remaining_time != 1 else ''}"
                        else:
                            time_str = f"{remaining_time} minuto{'s' if remaining_time != 1 else ''}"
                        
                        raise ValidationError(
                            f'Demasiados intentos fallidos. Tu cuenta ha sido bloqueada por {time_str}.'
                        )
                    else:
                        attempts_left = 3 - user.failed_login_attempts
                        if attempts_left > 0:
                            raise ValidationError(
                                f'Credenciales incorrectas. Te quedan {attempts_left} intento{"s" if attempts_left != 1 else ""} antes del bloqueo.'
                            )
                        else:
                            raise ValidationError('Credenciales incorrectas.')
                else:
                    # Login exitoso
                    user.record_successful_login()
                    
                    # Registrar intento exitoso por IP
                    self._record_ip_successful_attempt()
                    
            except CustomUser.DoesNotExist:
                raise ValidationError('Credenciales incorrectas.')
        
        return self.cleaned_data
    
    def _record_ip_failed_attempt(self):
        """Registra un intento fallido por IP"""
        try:
            from inventario.middleware import IPBlockingMiddleware
            ip = self._get_client_ip()
            middleware = IPBlockingMiddleware(None)
            middleware.record_failed_attempt(ip)
        except Exception as e:
            # Si hay error, no fallar el login por esto
            pass
    
    def _record_ip_successful_attempt(self):
        """Registra un intento exitoso por IP"""
        try:
            from inventario.middleware import IPBlockingMiddleware
            ip = self._get_client_ip()
            middleware = IPBlockingMiddleware(None)
            middleware.record_successful_attempt(ip)
        except Exception as e:
            # Si hay error, no fallar el login por esto
            pass
    
    def _get_client_ip(self):
        """Obtiene la IP del cliente desde el request"""
        if hasattr(self, 'request') and self.request:
            x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = self.request.META.get('REMOTE_ADDR')
            return ip
        return 'unknown'

class ProductoForm(forms.ModelForm):
    precio_venta = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'inputmode': 'decimal',
            'class': 'form-control'
        })
    )
    precio_compra = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'inputmode': 'decimal',
            'class': 'form-control'
        })
    )
    stock = forms.IntegerField(
        validators=[MinValueValidator(0)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = Producto
        fields = [
            'descripcion', 'codigo', 'precio_venta', 'precio_compra', 
            'stock', 'imagen', 'tipo', 'marca', 'fit', 'color', 'talla'
        ]
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.Select(attrs={'class': 'form-select'}),
            'fit': forms.Select(attrs={'class': 'form-select'}),
            'color': forms.Select(attrs={'class': 'form-select'}),
            'talla': forms.Select(attrs={'class': 'form-select'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        if codigo:
            codigo = codigo.upper()
        return codigo

class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ['nombre', 'is_active'] 
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'nombre', 'apellido', 'identificacion', 'email', 'telefono',
            'tallas'
        ]
        exclude = ['saldo', 'status']  # Excluir saldo y status del formulario
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'identificacion': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'tallas': forms.SelectMultiple(attrs={'class': 'form-select'})
        }
        labels = {
            'nombre': 'Nombre',
            'apellido': 'Apellido',
            'identificacion': 'Identificación',
            'email': 'Correo Electrónico',
            'telefono': 'Teléfono',
            'tallas': 'Tallas'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar el widget de tallas para usar Select2
        self.fields['tallas'].widget.attrs.update({
            'class': 'form-select select2-multiple',
            'multiple': 'multiple',
            'data-placeholder': 'Selecciona las tallas...'
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Verificar si el email ya existe en otro cliente
            if self.instance.pk:
                # Si es una actualización, excluir el cliente actual
                if Cliente.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
                    raise ValidationError("Este correo electrónico ya está registrado.")
            else:
                # Si es una creación nueva
                if Cliente.objects.filter(email=email).exists():
                    raise ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean_identificacion(self):
        identificacion = self.cleaned_data.get('identificacion')
        if identificacion:
            # Verificar si la identificación ya existe en otro cliente
            if self.instance.pk:
                # Si es una actualización, excluir el cliente actual
                if Cliente.objects.exclude(pk=self.instance.pk).filter(identificacion=identificacion).exists():
                    raise ValidationError("Esta identificación ya está registrada.")
            else:
                # Si es una creación nueva
                if Cliente.objects.filter(identificacion=identificacion).exists():
                    raise ValidationError("Esta identificación ya está registrada.")
        return identificacion

class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Formulario personalizado para cambiar contraseña con validaciones dinámicas
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalizar widgets y atributos
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingresa tu contraseña actual',
            'required': 'required'
        })
        self.fields['old_password'].label = 'Contraseña actual'
        
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingresa tu nueva contraseña',
            'required': 'required'
        })
        self.fields['new_password1'].label = 'Nueva contraseña'
        
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirma tu nueva contraseña',
            'required': 'required'
        })
        self.fields['new_password2'].label = 'Confirmar nueva contraseña'
        
        # Sin mensajes de ayuda visuales
        self.fields['new_password1'].help_text = ""
        self.fields['new_password2'].help_text = ""
    
    def clean_old_password(self):
        """
        Verificar que la contraseña actual sea correcta
        """
        old_password = self.cleaned_data.get('old_password')
        if old_password and not self.user.check_password(old_password):
            raise ValidationError('La contraseña actual es incorrecta.')
        return old_password
    
    def clean_new_password1(self):
        """
        Validaciones adicionales para la nueva contraseña
        """
        password = self.cleaned_data.get('new_password1')
        
        # Verificar que no sea igual a la contraseña actual
        if self.user.check_password(password):
            raise ValidationError('La nueva contraseña no puede ser igual a la actual.')
        
        return password


class MermaForm(forms.Form):
    """Formulario para crear mermas desde productos"""
    cantidad = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cantidad a mermar'
        }),
        label='Cantidad'
    )
    
    motivo = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe el motivo de la merma...'
        }),
        label='Motivo'
    )
    
    def __init__(self, *args, **kwargs):
        self.producto = kwargs.pop('producto', None)
        super().__init__(*args, **kwargs)
        
        if self.producto:
            # Establecer el máximo de cantidad basado en el stock disponible
            self.fields['cantidad'].widget.attrs['max'] = self.producto.stock
    
    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        
        if self.producto and cantidad:
            if cantidad > self.producto.stock:
                raise ValidationError(f'La cantidad no puede ser mayor al stock disponible ({self.producto.stock} unidades).')
            
            if cantidad <= 0:
                raise ValidationError('La cantidad debe ser mayor a 0.')
        
        return cantidad


class GastoAdministrativoForm(forms.ModelForm):
    class Meta:
        model = GastoAdministrativo
        fields = ['nombre', 'monto', 'fecha']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre del gasto administrativo'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
        labels = {
            'nombre': 'Nombre del Gasto',
            'monto': 'Monto',
            'fecha': 'Fecha'
        }