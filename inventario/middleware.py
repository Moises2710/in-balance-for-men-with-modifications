from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.conf import settings
import time
import logging
import threading

logger = logging.getLogger('security')

# Thread-local storage para almacenar el usuario actual
_thread_locals = threading.local()

class IPBlockingMiddleware:
    """
    Middleware para bloquear IPs que realizan demasiados intentos fallidos de login.
    Protege contra ataques de fuerza bruta a nivel de red.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Configuración de seguridad
        self.max_attempts = getattr(settings, 'IP_MAX_ATTEMPTS', 10)  # Máximo 10 intentos por IP
        self.block_duration = getattr(settings, 'IP_BLOCK_DURATION', 3600)  # Bloquear por 1 hora
        self.window_duration = getattr(settings, 'IP_WINDOW_DURATION', 300)  # Ventana de 5 minutos
    
    def __call__(self, request):
        # Solo aplicar en vistas de login y recuperación de contraseña
        if self._should_apply_security(request):
            ip = self.get_client_ip(request)
            
            if self.is_ip_blocked(ip):
                remaining_time = self.get_remaining_block_time(ip)
                logger.warning(f"IP {ip} bloqueada intentando acceder a {request.path}")
                
                return HttpResponseForbidden(
                    f"Tu IP ha sido bloqueada por múltiples intentos fallidos. "
                    f"Intenta nuevamente en {remaining_time} minutos."
                )
        
        response = self.get_response(request)
        return response
    
    def _should_apply_security(self, request):
        """Determina si se debe aplicar seguridad basado en la URL y método"""
        secure_paths = ['/', '/recuperar_contraseña/', '/recuperar-contraseña_confirmar/']
        return (
            request.method == 'POST' and 
            any(request.path.startswith(path) for path in secure_paths)
        )
    
    def get_client_ip(self, request):
        """Obtiene la IP real del cliente considerando proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_ip_blocked(self, ip):
        """Verifica si una IP está bloqueada"""
        cache_key = f'ip_blocked_{ip}'
        return cache.get(cache_key) is not None
    
    def get_remaining_block_time(self, ip):
        """Calcula el tiempo restante de bloqueo en minutos"""
        cache_key = f'ip_blocked_{ip}'
        block_until = cache.get(cache_key)
        if block_until:
            remaining = (block_until - timezone.now()).total_seconds() / 60
            return max(0, int(remaining))
        return 0
    
    def record_failed_attempt(self, ip):
        """Registra un intento fallido por IP"""
        cache_key = f'ip_attempts_{ip}'
        attempts = cache.get(cache_key, 0) + 1
        
        # Guardar intentos por 5 minutos
        cache.set(cache_key, attempts, self.window_duration)
        
        logger.info(f"IP {ip}: intento fallido {attempts}/{self.max_attempts}")
        
        if attempts >= self.max_attempts:
            # Bloquear IP
            block_until = timezone.now() + timezone.timedelta(seconds=self.block_duration)
            cache.set(f'ip_blocked_{ip}', block_until, self.block_duration)
            cache.delete(cache_key)  # Limpiar contador
            
            logger.warning(
                f"IP {ip} bloqueada por {self.block_duration} segundos "
                f"después de {attempts} intentos fallidos"
            )
    
    def record_successful_attempt(self, ip):
        """Registra un intento exitoso y limpia contadores"""
        cache_key = f'ip_attempts_{ip}'
        cache.delete(cache_key)
        logger.info(f"IP {ip}: intento exitoso, contadores limpiados")
    
    def unblock_ip(self, ip):
        """Desbloquea una IP manualmente (para administradores)"""
        cache.delete(f'ip_blocked_{ip}')
        cache.delete(f'ip_attempts_{ip}')
        logger.info(f"IP {ip} desbloqueada manualmente")


class SecurityLoggingMiddleware:
    """
    Middleware para logging de eventos de seguridad
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.security_logger = logging.getLogger('security')
    
    def __call__(self, request):
        # Log de acceso a rutas sensibles
        if self._is_sensitive_route(request):
            ip = self.get_client_ip(request)
            self.security_logger.info(
                f"Acceso a ruta sensible: {request.path} desde IP {ip} "
                f"usuario: {getattr(request.user, 'username', 'anónimo')}"
            )
        
        response = self.get_response(request)
        
        # Log de respuestas de error
        if response.status_code >= 400:
            ip = self.get_client_ip(request)
            self.security_logger.warning(
                f"Respuesta de error {response.status_code} para {request.path} "
                f"desde IP {ip}"
            )
        
        return response
    
    def _is_sensitive_route(self, request):
        """Determina si una ruta es sensible para logging"""
        sensitive_paths = [
            '/admin/', '/usuarios/', '/clientes/', '/productos/',
            '/venta/', '/reportes/', '/gastos-administrativos/'
        ]
        return any(request.path.startswith(path) for path in sensitive_paths)
    
    def get_client_ip(self, request):
        """Obtiene la IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CurrentUserMiddleware:
    """
    Middleware para almacenar el usuario actual en thread-local storage
    para poder acceder a él desde los signals de la bitácora
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Almacenar el usuario actual en thread-local storage
        _thread_locals.user = getattr(request, 'user', None)
        
        response = self.get_response(request)
        
        # Limpiar thread-local storage
        _thread_locals.user = None
        
        return response


def get_current_user():
    """
    Función helper para obtener el usuario actual desde thread-local storage
    """
    return getattr(_thread_locals, 'user', None)
