# 🚀 Guía de Despliegue en Render con Supabase

## 📋 Configuración Lista

Tu proyecto está configurado para usar tu base de datos PostgreSQL de Supabase en producción. Los siguientes archivos han sido creados/modificados:

### ✅ Archivos de Configuración Creados:
- `build.sh` - Script de construcción para Render
- `runtime.txt` - Versión de Python (3.11.7)
- `render.yaml` - Configuración automática de Render (sin base de datos)

### ✅ Configuración de Settings:
- Configuración híbrida que funciona tanto en desarrollo como en producción
- Base de datos SQLite en desarrollo, PostgreSQL de Supabase en producción
- WhiteNoise solo se activa en producción
- Variables de entorno configuradas

## 🔧 Pasos para Desplegar en Render:

### 1. **Subir Código a GitHub**
```bash
git add .
git commit -m "Configuración para despliegue en Render con Supabase"
git push origin main
```

### 2. **Configurar en Render**

#### Opción A: Usando render.yaml (Recomendado)
1. Ve a [render.com](https://render.com)
2. Conecta tu repositorio de GitHub
3. Render detectará automáticamente el archivo `render.yaml`
4. Se creará automáticamente:
   - Servicio web
   - Variables de entorno (SIN base de datos)

#### Opción B: Configuración Manual
1. **Crear Servicio Web:**
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn in_balance.wsgi:application`
   - **Environment:** Python 3.11.7

2. **Variables de Entorno:**
   ```
   SECRET_KEY: [Generar automáticamente]
   DEBUG: False
   ALLOWED_HOSTS: .onrender.com
   DATABASE_URL: [Tu URL de conexión de Supabase]
   ```

### 3. **Configurar DATABASE_URL de Supabase**
1. Ve a tu proyecto en Supabase
2. Ve a Settings > Database
3. Copia la "Connection string" (URI)
4. En Render, agrega la variable `DATABASE_URL` con tu string de conexión de Supabase

### 4. **Verificar Despliegue**
- El build script ejecutará automáticamente:
  - `pip install -r requirements.txt`
  - `python manage.py collectstatic --no-input`
  - `python manage.py migrate`
  - `python manage.py cargar_datos_iniciales`


## 📁 Estructura de Archivos:
```
in_balance/
├── build.sh              # Script de construcción
├── runtime.txt           # Versión de Python
├── render.yaml           # Configuración de Render
├── requirements.txt      # Dependencias
├── in_balance/
│   ├── settings.py       # Configuración híbrida
│   └── urls.py           # URLs configuradas
└── inventario/
    └── management/
        └── commands/
            └── cargar_datos_iniciales.py  # Datos iniciales
```

## ⚠️ Notas Importantes:

### 🔒 Seguridad:
- Las claves de captcha están configuradas
- La configuración de seguridad se activa automáticamente en producción
- HTTPS se fuerza en producción

### 📊 Base de Datos:
- En desarrollo: SQLite
- En producción: PostgreSQL (automático)
- Los datos se migran automáticamente

### 🎨 Archivos Estáticos:
- En desarrollo: servidos por Django
- En producción: servidos por WhiteNoise (optimizado)

### 📧 Email:
- Configurado para Gmail SMTP
- Funciona tanto en desarrollo como en producción

## 🚀 ¡Listo para Desplegar!

Tu proyecto está completamente configurado para Render. Solo necesitas:

1. **Subir el código a GitHub**
2. **Conectar el repositorio en Render**
3. **¡Disfrutar de tu aplicación en línea!**

---

**¿Problemas?** Revisa los logs de Render para diagnosticar cualquier error durante el despliegue. 