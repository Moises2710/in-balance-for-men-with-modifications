# 🔐 Configuración de Permisos del Sistema

Este directorio contiene scripts para configurar los permisos de los grupos de usuarios en el sistema de inventario.

## 📁 Archivos Disponibles

### 1. `inventario/management/commands/configurar_permisos.py` 🐍 **COMANDO DJANGO - PRODUCCIÓN**
- **Comando oficial de Django**
- **Funciona con PostgreSQL/Supabase**
- **Ejecutar con:** `python manage.py configurar_permisos`
- **Recomendado para producción**

### 2. `configurar_permisos_postgresql.py` 🔧 **SCRIPT INDEPENDIENTE**
- **Funciona sin Django**
- **Conecta directamente a PostgreSQL/Supabase**
- **Ejecutar con:** `python configurar_permisos_postgresql.py`
- **Para casos donde Django no esté disponible**

## 🎯 Configuración Actual

### 👑 **Administrador**
- **Permisos:** TODOS los permisos de la app inventario
- **Puede:** Ver, crear, editar, eliminar todo

### 👤 **Vendedor**
- **Permisos:** Solo `view` y `add` para:
  - `producto` - Ver y crear productos
  - `cliente` - Ver y crear clientes
  - `venta` - Ver y crear ventas
  - `detalleventa` - Ver y crear detalles de venta
  - `pago` - Ver y crear pagos
  - `devolucion` - Ver y crear devoluciones
  - `detalledevolucion` - Ver y crear detalles de devolución
  - `metodopago` - Ver y crear métodos de pago

## ✏️ Cómo Personalizar los Permisos

### Para el Vendedor:

1. **Abrir el archivo:** `configurar_permisos_editable.py`

2. **Buscar la sección:** `# PERMISOS DEL VENDEDOR - EDITAR AQUÍ`

3. **Modificar los tipos de permisos:**
   ```python
   # Solo ver y añadir
   tipos_permisos = ['view', 'add']
   
   # Ver, añadir y editar
   tipos_permisos = ['view', 'add', 'change']
   
   # Todos los permisos
   tipos_permisos = ['view', 'add', 'change', 'delete']
   ```

4. **Agregar o quitar modelos:**
   ```python
   modelos_vendedor = [
       'producto', 'cliente', 'venta', 'detalleventa', 
       'pago', 'devolucion', 'detalledevolucion', 'metodopago'
       # Agregar más modelos aquí
   ]
   ```

### Para Agregar Nuevos Grupos:

1. **Abrir el archivo:** `configurar_permisos_editable.py`

2. **Buscar la sección:** `# CONFIGURACIÓN ADICIONAL - EDITAR AQUÍ`

3. **Agregar el nuevo grupo:**
   ```python
   # Crear grupo adicional
   otro_grupo_id = crear_o_obtener_grupo(cursor, 'NombreDelGrupo')
   configurar_otro_grupo(cursor, 'NombreDelGrupo')
   ```

4. **Implementar la función `configurar_otro_grupo`** con los permisos específicos

## 🚀 Ejecución

### Opción 1: Comando Django (Recomendado para Producción)
```bash
python manage.py configurar_permisos
```

### Opción 2: Script Independiente PostgreSQL
```bash
python configurar_permisos_postgresql.py
```

### Opciones adicionales del comando Django:
```bash
# Resetear permisos antes de configurar
python manage.py configurar_permisos --reset

# Configurar solo un grupo específico
python manage.py configurar_permisos --grupo vendedor
python manage.py configurar_permisos --grupo administrador
```

### Variables de entorno requeridas (Script PostgreSQL):
```bash
# Para el script independiente, asegúrate de tener configurada:
export DATABASE_URL="postgresql://usuario:password@host:puerto/database"
```

## 📊 Resultado Esperado

Después de ejecutar el script, deberías ver:

```
🔧 Configurando permisos del sistema...

👥 Creando grupos...
✅ Grupo Administrador ya existe
✅ Grupo Vendedor ya existe

🧹 Limpiando permisos existentes...

📋 Obteniendo permisos de inventario...
✅ Encontrados 85 permisos de inventario

👑 Configurando Administrador...
✅ 85 permisos asignados a Administrador

👤 Configurando Vendedor...
   ✅ producto: view, add
   ✅ cliente: view, add
   ✅ venta: view, add
   ✅ detalleventa: view, add
   ✅ pago: view, add
   ✅ devolucion: view, add
   ✅ detalledevolucion: view, add
   ✅ metodopago: view, add
✅ 16 permisos asignados a Vendedor

🎉 ¡Permisos configurados exitosamente!

📊 Resumen de permisos:
👑 Administrador: 85 permisos
👤 Vendedor: 16 permisos
```

## 🔧 Solución de Problemas

### Error: "No module named 'dj_database_url'" (Local)
- **Solución:** Usar `configurar_permisos_postgresql.py` en lugar del comando Django

### Error: "No se encontró DATABASE_URL"
- **Solución:** Asegúrate de tener configurada la variable de entorno DATABASE_URL

### Error de conexión a PostgreSQL
- **Solución:** Verificar que la URL de la base de datos sea correcta y que el servidor esté accesible

### Los permisos no se aplican
- **Solución:** Verificar que los usuarios estén asignados a los grupos correctos en el admin de Django

## 📝 Notas Importantes

- Los scripts **NO afectan** los usuarios existentes, solo configuran los grupos
- Para aplicar los permisos, los usuarios deben ser asignados a los grupos correspondientes
- Los permisos se aplican inmediatamente después de ejecutar el script
- Es seguro ejecutar el script múltiples veces (no duplica permisos)
