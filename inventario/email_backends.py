"""
Backend personalizado de email para Supabase + Resend
"""
import logging
import requests
import json
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)

class SupabaseEmailBackend(BaseEmailBackend):
    """
    Backend de email personalizado que usa Supabase Edge Functions con Resend.
    """
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.supabase_url = getattr(settings, 'SUPABASE_URL', None)
        self.supabase_key = getattr(settings, 'SUPABASE_KEY', None)
        self.resend_api_key = getattr(settings, 'RESEND_API_KEY', None)
        self.default_from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        
        if not self.supabase_url or not self.supabase_key:
            logger.warning("SUPABASE_URL o SUPABASE_KEY no están configurados. SupabaseEmailBackend funcionará en modo de simulación.")
        
        if not self.resend_api_key:
            logger.warning("RESEND_API_KEY no está configurado. Se usará el servicio de email de Supabase.")

    def send_messages(self, email_messages):
        """
        Envía uno o más objetos EmailMessage a través de Supabase Edge Functions.
        """
        if not self.supabase_url or not self.supabase_key:
            logger.info("Modo de simulación de Supabase: No se enviaron emails reales.")
            for message in email_messages:
                logger.info(f"Simulando envío de email a: {message.to}, Asunto: {message.subject}")
                logger.info(f"Contenido (HTML): {message.alternatives[0][0] if message.alternatives else message.body}")
            return len(email_messages)  # Simular éxito

        sent_count = 0
        
        for email_message in email_messages:
            try:
                # Preparar datos del email
                email_data = {
                    'to': email_message.to,
                    'subject': email_message.subject,
                    'from': email_message.from_email or self.default_from_email,
                    'html': email_message.alternatives[0][0] if email_message.alternatives else email_message.body,
                    'text': email_message.body if not email_message.alternatives else None
                }
                
                # Opción 1: Usar Supabase Edge Function (recomendado)
                if self._send_via_supabase_edge_function(email_data):
                    logger.info(f"Email enviado exitosamente via Supabase Edge Function a: {email_message.to}")
                    sent_count += 1
                    continue
                
                # Opción 2: Usar Resend directamente como fallback
                if self.resend_api_key and self._send_via_resend_direct(email_data):
                    logger.info(f"Email enviado exitosamente via Resend directo a: {email_message.to}")
                    sent_count += 1
                    continue
                
                # Si ambos fallan
                logger.error(f"No se pudo enviar email a {email_message.to} via Supabase ni Resend")
                if not self.fail_silently:
                    raise Exception("No se pudo enviar email via Supabase ni Resend")
                    
            except Exception as e:
                logger.error(f"Excepción al enviar email via Supabase a {email_message.to}: {e}")
                if not self.fail_silently:
                    raise
        
        return sent_count

    def _send_via_supabase_edge_function(self, email_data):
        """
        Envía email usando Supabase Edge Function.
        """
        try:
            # URL de la Edge Function (debes crear esta función en Supabase)
            edge_function_url = f"{self.supabase_url}/functions/v1/send-email"
            
            headers = {
                'Authorization': f'Bearer {self.supabase_key}',
                'Content-Type': 'application/json',
            }
            
            # Datos para enviar a la Edge Function
            payload = {
                'email_data': email_data,
                'resend_api_key': self.resend_api_key  # Pasar la clave de Resend
            }
            
            response = requests.post(
                edge_function_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Supabase Edge Function respondió exitosamente: {response.json()}")
                return True
            else:
                logger.error(f"Error en Supabase Edge Function: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error enviando via Supabase Edge Function: {e}")
            return False

    def _send_via_resend_direct(self, email_data):
        """
        Envía email usando Resend directamente como fallback.
        """
        try:
            import resend
            
            resend.api_key = self.resend_api_key
            
            # Preparar datos para Resend
            resend_data = {
                "from": email_data['from'],
                "to": email_data['to'],
                "subject": email_data['subject'],
                "html": email_data['html']
            }
            
            if email_data['text']:
                resend_data["text"] = email_data['text']
            
            response = resend.Emails.send(resend_data)
            
            if response and 'id' in response:
                logger.info(f"Resend directo exitoso: {response['id']}")
                return True
            else:
                logger.error(f"Error en Resend directo: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error enviando via Resend directo: {e}")
            return False
