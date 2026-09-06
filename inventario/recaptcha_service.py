"""
Servicio para validar reCAPTCHA v3 Enterprise
"""
import os
from django.conf import settings
from google.cloud import recaptchaenterprise_v1
from google.cloud.recaptchaenterprise_v1 import Assessment
import logging

logger = logging.getLogger(__name__)

class RecaptchaV3Service:
    """Servicio para validar tokens de reCAPTCHA v3 Enterprise"""
    
    def __init__(self):
        # self.project_id = settings.calve_entorno_recaptcha_v3_CLOUD_PROJECT_ID
        # self.site_key = settings.clave_entorno_recaptcha_v3
        # self.secret_key = settings.clave_entorno_recaptcha_v3
        # self.score_threshold = settings.clave_entorno_recapCHA_V3_SCORE_THRESHOLD
        # 👇 CORREGIDO: Usar los nombres correctos de las variables
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT_ID', '')  # ⬅️ El ID de tu proyecto en Google Cloud
        self.site_key = settings.RECAPTCHA_V3_SITE_KEY  # ⬅️ Tu Site Key
        self.secret_key = settings.RECAPTCHA_V3_SECRET_KEY  # ⬅️ Tu Secret Key
        self.score_threshold = getattr(settings, 'RECAPTCHA_V3_SCORE_THRESHOLD', 0.5)
        
        # Debug: Imprimir configuración
        print(f"DEBUG RECAPTCHA SERVICE:")
        print(f"  Project ID: {self.project_id}")
        # print(f"  Site Key: {self.site_key}")
        print(f"  Site Key: {self.site_key[:20]}..." if self.site_key else "  Site Key: None")
        print(f"  Secret Key: {'*' * 20 if self.secret_key else 'None'}")
        print(f"  Score Threshold: {self.score_threshold}")
        print(f"  Is Configured: {self.is_configured()}")
        
    def validate_token(self, token: str, action: str = 'login') -> dict:
        """
        Valida un token de reCAPTCHA v3
        
        Args:
            token: Token generado por el cliente
            action: Acción esperada (por defecto 'login')
            
        Returns:
            dict: {
                'valid': bool,
                'score': float,
                'error': str (opcional),
                'reasons': list (opcional)
            }
        """
        # if not self.project_id or not self.secret_key:
        if not self.project_id or not self.secret_key or not self.site_key:
            logger.warning("reCAPTCHA v3 no configurado correctamente")
            return {
                'valid': False,
                'score': 0.0,
                'error': 'reCAPTCHA v3 no configurado'
            }
            
        try:
            client = recaptchaenterprise_v1.RecaptchaEnterpriseServiceClient()
            
            # Configurar el evento
            event = recaptchaenterprise_v1.Event()
            event.site_key = self.site_key
            event.token = token
            
            # Crear la evaluación
            assessment = recaptchaenterprise_v1.Assessment()
            assessment.event = event
            
            project_name = f"projects/{self.project_id}"
            
            # Construir la solicitud
            request = recaptchaenterprise_v1.CreateAssessmentRequest()
            request.assessment = assessment
            request.parent = project_name
            
            # Ejecutar la evaluación
            response = client.create_assessment(request)
            
            # Verificar si el token es válido
            if not response.token_properties.valid:
                invalid_reasons = []
                # Manejar el caso donde invalid_reason puede ser un solo objeto o una lista
                if hasattr(response.token_properties, 'invalid_reason'):
                    if isinstance(response.token_properties.invalid_reason, list):
                        for reason in response.token_properties.invalid_reason:
                            invalid_reasons.append(str(reason))
                    else:
                        invalid_reasons.append(str(response.token_properties.invalid_reason))
                
                return {
                    'valid': False,
                    'score': 0.0,
                    'error': f'Token inválido: {", ".join(invalid_reasons) if invalid_reasons else "Razón desconocida"}'
                }
            
            # Verificar la acción
            if response.token_properties.action != action:
                return {
                    'valid': False,
                    'score': 0.0,
                    'error': f'Acción no coincide. Esperada: {action}, Recibida: {response.token_properties.action}'
                }
            
            # Obtener el score y razones
            score = response.risk_analysis.score
            reasons = []
            if hasattr(response.risk_analysis, 'reasons'):
                for reason in response.risk_analysis.reasons:
                    reasons.append(str(reason))
            
            # Verificar si el score es aceptable
            is_valid = score >= self.score_threshold
            
            logger.info(f"reCAPTCHA v3 - Score: {score}, Threshold: {self.score_threshold}, Valid: {is_valid}")
            
            return {
                'valid': is_valid,
                'score': score,
                'reasons': reasons,
                'error': None if is_valid else f'Score demasiado bajo: {score} < {self.score_threshold}'
            }
            
        except Exception as e:
            logger.error(f"Error validando reCAPTCHA v3: {str(e)}")
            return {
                'valid': False,
                'score': 0.0,
                'error': f'Error interno: {str(e)}'
            }
    
    def is_configured(self) -> bool:
        """Verifica si reCAPTCHA v3 está configurado correctamente"""
        return bool(self.project_id and self.secret_key and self.site_key)
