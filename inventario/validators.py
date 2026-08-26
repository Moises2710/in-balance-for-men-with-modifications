from django.core.exceptions import PermissionDenied, ValidationError
import re

class SecurePasswordValidator:
    def validate(self, password, user=None):
        if len(password) < 16:
            raise ValidationError('La contraseña debe tener al menos 16 caracteres.')
        if not re.search(r'[A-Z]', password):
            raise ValidationError('La contraseña debe contener al menos una letra mayúscula.')
        if not re.search(r'\d', password):
            raise ValidationError('La contraseña debe contener al menos un número.')
        if not re.search(r'[^\w\s]', password):
            raise ValidationError('La contraseña debe contener al menos un símbolo.')

    def get_help_text(self):
        return "Tu contraseña debe tener al menos 16 caracteres, incluir mayúsculas, minúsculas, números y símbolos."

"""
import os
from django.core.exceptions import ValidationError

def validate_image_format(file):
    valid_extensions = ['.jpg', '.jpeg', '.png', '.heic']
    ext = os.path.splitext(file.name)[1].lower()
    
    if ext not in valid_extensions:
        raise ValidationError('Formato de archivo no soportado. Use JPG, JPEG, PNG o HEIC.')
    

import os
from io import BytesIO
from django.core.exceptions import ValidationError
from PIL import Image

def validate_image_format(file):
    # Validación de extensión
    valid_extensions = ['.jpg', '.jpeg', '.png', '.heic']
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError('Extensión no permitida.')
    
    # Validación de contenido real
    try:
        # Para HEIC necesitamos manejo especial
        if ext == '.heic':
            import pillow_heif
            heif_file = pillow_heif.open_heif(file)
            heif_file.load()  # Intenta decodificar el HEIC
        else:
            # Usa Pillow para verificar el contenido
            image = Image.open(file)
            image.verify()  # Verifica integridad sin cargar en memoria
            
            # Verifica que el tipo MIME coincida con la extensión
            image = Image.open(file)
            image.format = image.format.upper()
            if (ext == '.jpg' or ext == '.jpeg') and image.format != 'JPEG':
                raise ValidationError('El contenido no es JPEG válido.')
            elif ext == '.png' and image.format != 'PNG':
                raise ValidationError('El contenido no es PNG válido.')
                
    except Exception as e:
        raise ValidationError(f'Archivo inválido o corrupto: {str(e)}') 
"""