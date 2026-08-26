"""
Vistas para mostrar la bitácora de acciones del sistema
"""
import os
import re
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator

User = get_user_model()

class BitacoraView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista principal para mostrar la bitácora de acciones"""
    template_name = 'inventario/bitacora/bitacora_list.html'
    
    def test_func(self):
        """Solo superuser, staff o administradores pueden ver la bitácora"""
        user = self.request.user
        return (user.is_superuser or 
                user.is_staff or 
                user.groups.filter(name='Administrador').exists())
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Bitácora de Acciones'
        
        # Obtener parámetros de filtro
        usuario_filtro = self.request.GET.get('usuario', '')
        tipo_accion_filtro = self.request.GET.get('tipo_accion', '')
        entidad_filtro = self.request.GET.get('entidad', '')
        fecha_desde = self.request.GET.get('fecha_desde', '')
        fecha_hasta = self.request.GET.get('fecha_hasta', '')
        
        # Leer y filtrar logs
        logs = self._leer_logs_bitacora()
        logs_filtrados = self._filtrar_logs(logs, usuario_filtro, tipo_accion_filtro, 
                                          entidad_filtro, fecha_desde, fecha_hasta)
        
        # Paginación
        paginator = Paginator(logs_filtrados, 50)  # 50 registros por página
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context.update({
            'page_obj': page_obj,
            'usuario_filtro': usuario_filtro,
            'tipo_accion_filtro': tipo_accion_filtro,
            'entidad_filtro': entidad_filtro,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'total_registros': len(logs_filtrados),
            'tipos_accion': self._obtener_tipos_accion(),
            'entidades': self._obtener_entidades(),
        })
        
        return context
    
    def _leer_logs_bitacora(self):
        """Lee los logs de bitácora desde el archivo con manejo robusto de codificación"""
        logs = []
        log_file = os.path.join(settings.BASE_DIR, 'logs', 'bitacora_new.log')
        
        try:
            if os.path.exists(log_file):
                # Intentar diferentes codificaciones en orden de preferencia
                encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
                lines = []
                
                for encoding in encodings:
                    try:
                        with open(log_file, 'r', encoding=encoding) as f:
                            lines = f.readlines()
                        print(f"Logs leídos exitosamente con codificación: {encoding}")
                        break  # Si funciona, salir del bucle
                    except UnicodeDecodeError as e:
                        print(f"Error con codificación {encoding}: {e}")
                        continue
                
                # Si ninguna codificación funciona, usar 'utf-8' con errores ignorados
                if not lines:
                    print("Usando UTF-8 con errores ignorados")
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                for line in lines:
                    # Limpiar la línea de caracteres problemáticos
                    line = line.strip()
                    if line:  # Solo procesar líneas no vacías
                        log_entry = self._parsear_linea_log(line)
                        if log_entry:
                            logs.append(log_entry)
                        
        except Exception as e:
            print(f"Error leyendo logs de bitácora: {e}")
            
        return logs
    
    def _parsear_linea_log(self, line):
        """Parsea una línea del log de bitácora"""
        try:
            # Formato: timestamp | level | usuario | tipo_accion | entidad | entidad_id | descripcion
            parts = line.split(' | ')
            if len(parts) >= 7:
                return {
                    'timestamp': parts[0],
                    'level': parts[1],
                    'usuario': parts[2],
                    'tipo_accion': parts[3],
                    'entidad': parts[4],
                    'entidad_id': parts[5],
                    'descripcion': ' | '.join(parts[6:]),  # En caso de que la descripción contenga |
                }
        except Exception:
            pass
        return None
    
    def _filtrar_logs(self, logs, usuario, tipo_accion, entidad, fecha_desde, fecha_hasta):
        """Filtra los logs según los parámetros"""
        filtered_logs = logs
        
        if usuario:
            filtered_logs = [log for log in filtered_logs 
                           if usuario.lower() in log['usuario'].lower()]
        
        if tipo_accion:
            filtered_logs = [log for log in filtered_logs 
                           if log['tipo_accion'] == tipo_accion]
        
        if entidad:
            filtered_logs = [log for log in filtered_logs 
                           if log['entidad'] == entidad]
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
                filtered_logs = [log for log in filtered_logs 
                               if self._parsear_fecha_log(log['timestamp']) >= fecha_desde_dt]
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d') + timedelta(days=1)
                filtered_logs = [log for log in filtered_logs 
                               if self._parsear_fecha_log(log['timestamp']) < fecha_hasta_dt]
            except ValueError:
                pass
        
        return filtered_logs
    
    def _parsear_fecha_log(self, timestamp_str):
        """Parsea el timestamp del log a datetime"""
        try:
            # Formato: 2025-01-22 15:30:45,123
            return datetime.strptime(timestamp_str.split(',')[0], '%Y-%m-%d %H:%M:%S')
        except:
            return datetime.min
    
    def _obtener_tipos_accion(self):
        """Obtiene lista de tipos de acción únicos"""
        return [
            'crear', 'editar', 'eliminar', 'activar', 'desactivar', 'suspender',
            'cambiar_password', 'login', 'logout', 'marcar_pagado', 'marcar_pendiente',
            'aprobar', 'rechazar'
        ]
    
    def _obtener_entidades(self):
        """Obtiene lista de entidades únicas"""
        return [
            'usuario', 'cliente', 'producto', 'venta', 'pago', 'devolucion',
            'gasto_administrativo', 'comision', 'sistema'
        ]


class BitacoraAjaxView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista AJAX para obtener datos de bitácora con DataTables"""
    
    def test_func(self):
        """Solo superuser, staff o administradores pueden ver la bitácora"""
        user = self.request.user
        return (user.is_superuser or 
                user.is_staff or 
                user.groups.filter(name='Administrador').exists())
    
    def get(self, request, *args, **kwargs):
        """Retorna datos de bitácora en formato JSON para DataTables"""
        try:
            # Parámetros básicos de DataTables
            draw = int(request.GET.get('draw', 1))
            start = int(request.GET.get('start', 0))
            length = int(request.GET.get('length', 10))
            search_value = request.GET.get('search[value]', '')
            order_column_index = request.GET.get('order[0][column]', 0)
            order_direction = request.GET.get('order[0][dir]', 'desc')
            
            # Obtener parámetros de filtro
            usuario_filtro = request.GET.get('usuario', '')
            tipo_accion_filtro = request.GET.get('tipo_accion', '')
            entidad_filtro = request.GET.get('entidad', '')
            fecha_desde = request.GET.get('fecha_desde', '')
            fecha_hasta = request.GET.get('fecha_hasta', '')
            
            # Leer logs
            logs = self._leer_logs_bitacora()
            logs_filtrados = self._filtrar_logs(logs, usuario_filtro, tipo_accion_filtro, 
                                              entidad_filtro, fecha_desde, fecha_hasta)
            
            # Aplicar búsqueda global
            if search_value:
                logs_filtrados = [log for log in logs_filtrados 
                                if search_value.lower() in ' '.join([
                                    log['timestamp'], log['usuario'], log['tipo_accion'], 
                                    log['entidad'], log['descripcion']
                                ]).lower()]
            
            # Ordenamiento
            try:
                order_col = int(order_column_index)
                reverse = order_direction == 'desc'
                
                if order_col == 0:  # Timestamp
                    logs_filtrados.sort(key=lambda x: self._parsear_fecha_log(x['timestamp']), reverse=reverse)
                elif order_col == 1:  # Usuario
                    logs_filtrados.sort(key=lambda x: x['usuario'], reverse=reverse)
                elif order_col == 2:  # Tipo de acción
                    logs_filtrados.sort(key=lambda x: x['tipo_accion'], reverse=reverse)
                elif order_col == 3:  # Entidad
                    logs_filtrados.sort(key=lambda x: x['entidad'], reverse=reverse)
                elif order_col == 4:  # Descripción
                    logs_filtrados.sort(key=lambda x: x['descripcion'], reverse=reverse)
                else:
                    # Ordenamiento por defecto por timestamp descendente
                    logs_filtrados.sort(key=lambda x: self._parsear_fecha_log(x['timestamp']), reverse=True)
            except (ValueError, TypeError):
                # Si hay error en el ordenamiento, usar ordenamiento por defecto
                logs_filtrados.sort(key=lambda x: self._parsear_fecha_log(x['timestamp']), reverse=True)
            
            # Paginación
            total_records = len(logs)
            filtered_records = len(logs_filtrados)
            paginated_logs = logs_filtrados[start:start + length]
            
            # Preparar datos para DataTables
            data = []
            for log in paginated_logs:
                data.append({
                    'timestamp': log['timestamp'],
                    'usuario': log['usuario'],
                    'tipo_accion': log['tipo_accion'],
                    'entidad': log['entidad'],
                    'descripcion': log['descripcion'],
                })
            
            return JsonResponse({
                'draw': draw,
                'recordsTotal': total_records,
                'recordsFiltered': filtered_records,
                'data': data,
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def _leer_logs_bitacora(self):
        """Lee los logs de bitácora desde el archivo con manejo robusto de codificación"""
        logs = []
        log_file = os.path.join(settings.BASE_DIR, 'logs', 'bitacora_new.log')
        
        try:
            if os.path.exists(log_file):
                # Intentar diferentes codificaciones en orden de preferencia
                encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
                lines = []
                
                for encoding in encodings:
                    try:
                        with open(log_file, 'r', encoding=encoding) as f:
                            lines = f.readlines()
                        print(f"Logs leídos exitosamente con codificación: {encoding}")
                        break  # Si funciona, salir del bucle
                    except UnicodeDecodeError as e:
                        print(f"Error con codificación {encoding}: {e}")
                        continue
                
                # Si ninguna codificación funciona, usar 'utf-8' con errores ignorados
                if not lines:
                    print("Usando UTF-8 con errores ignorados")
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                for line in lines:
                    # Limpiar la línea de caracteres problemáticos
                    line = line.strip()
                    if line:  # Solo procesar líneas no vacías
                        log_entry = self._parsear_linea_log(line)
                        if log_entry:
                            logs.append(log_entry)
                        
        except Exception as e:
            print(f"Error leyendo logs de bitácora: {e}")
            
        return logs
    
    def _parsear_linea_log(self, line):
        """Parsea una línea del log de bitácora"""
        try:
            parts = line.split(' | ')
            if len(parts) >= 7:
                return {
                    'timestamp': parts[0],
                    'level': parts[1],
                    'usuario': parts[2],
                    'tipo_accion': parts[3],
                    'entidad': parts[4],
                    'entidad_id': parts[5],
                    'descripcion': ' | '.join(parts[6:]),
                }
        except Exception:
            pass
        return None
    
    def _filtrar_logs(self, logs, usuario, tipo_accion, entidad, fecha_desde, fecha_hasta):
        """Filtra los logs según los parámetros"""
        filtered_logs = logs
        
        if usuario:
            filtered_logs = [log for log in filtered_logs 
                           if usuario.lower() in log['usuario'].lower()]
        
        if tipo_accion:
            filtered_logs = [log for log in filtered_logs 
                           if log['tipo_accion'] == tipo_accion]
        
        if entidad:
            filtered_logs = [log for log in filtered_logs 
                           if log['entidad'] == entidad]
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
                filtered_logs = [log for log in filtered_logs 
                               if self._parsear_fecha_log(log['timestamp']) >= fecha_desde_dt]
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d') + timedelta(days=1)
                filtered_logs = [log for log in filtered_logs 
                               if self._parsear_fecha_log(log['timestamp']) < fecha_hasta_dt]
            except ValueError:
                pass
        
        return filtered_logs
    
    def _parsear_fecha_log(self, timestamp_str):
        """Parsea el timestamp del log a datetime"""
        try:
            return datetime.strptime(timestamp_str.split(',')[0], '%Y-%m-%d %H:%M:%S')
        except:
            return datetime.min

