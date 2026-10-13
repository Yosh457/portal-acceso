# 🏥 Portal de Acceso Institucional - Red de Salud APS Alto Hospicio

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)
![Database](https://img.shields.io/badge/Database-MySQL-blue.svg)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v3-38B2AC.svg)

Plataforma web centralizada (Intranet) desarrollada para la **Red de Atención Primaria de Salud Municipal de Alto Hospicio**. Su objetivo es actuar como el *hub* principal desde el cual los funcionarios pueden acceder de manera unificada y segura a todo el ecosistema de sistemas satélites municipales (Inventario TICs, Repositorio Documental, Fichas Clínicas, SIGGES, etc.), optimizando el flujo de trabajo y centralizando la administración de accesos.

---

## 🚀 Características Principales

### 🖥️ Dashboard Dinámico
- **Grid de Aplicaciones:** Renderizado de tarjetas agrupadas por categorías.
- **Acceso Inteligente:** Redirección automática a plataformas internas o externas (apertura en nueva pestaña).
- **Identidad Visual:** Asignación de íconos representativos mediante un sistema de identificadores únicos (*slugs*).

### 👥 Gestión Granular de Permisos
- **Asignación Directa:** Los accesos a las aplicaciones se asignan usuario por usuario, brindando máxima flexibilidad y evitando el exceso de privilegios.
- **Roles Diferenciados:** Acceso al panel de control exclusivo para perfiles *Admin*, y acceso al *Hub* operativo para *Funcionarios*.

### 🔒 Seguridad Institucional
- Protección CSRF nativa en todos los formularios.
- Cambio de contraseña obligatorio al primer inicio de sesión.
- Cierre automático de sesión inactiva con modal de advertencia visual.
- Normalización estricta en el backend para datos sensibles (ej. *slugs* inmutables).

### 📊 Trazabilidad Completa
- Registro histórico de eventos en el módulo de auditoría (`log_sistema`).
- Captura de IP, fecha, hora, usuario y detalle de cada acción (creación de usuarios, edición de aplicaciones, cambios de estado, etc.).

---

## 🛠️ Tecnologías Utilizadas

- **Arquitectura:** Application Factory Pattern (`create_app`) + Blueprints
- **Backend:** Python 3 + Flask
- **Base de Datos:** MySQL + SQLAlchemy (ORM)
- **Frontend:** HTML5, Jinja2, TailwindCSS (CDN), JavaScript (Vanilla)
- **Seguridad:** Flask-Login, Werkzeug Security, Flask-WTF

---

## 📂 Estructura del Proyecto

El proyecto sigue una arquitectura modular y limpia, diseñada para ser escalable y de fácil mantenimiento:
```text
PortalAcceso/
├── blueprints/          # Lógica de rutas y controladores
│   ├── admin.py         # CRUD de Usuarios, Categorías, Aplicaciones y Logs
│   ├── auth.py          # Autenticación, recuperación y reseteo de claves
│   └── portal.py        # Controlador del Hub principal de aplicaciones
├── static/              # Archivos estáticos
│   ├── css/             # Estilos personalizados (style.css)
│   ├── docs/            # Documentación del Proyecto
│   ├── img/             # Assets gráficos (logos institucionales, favicon)
│   └── js/              # Scripts utilitarios (validaciones, timeouts, modales)
├── templates/           # Vistas HTML (Jinja2)
│   ├── admin/           # Formularios y listados de administración
│   ├── auth/            # Vistas de acceso y seguridad
│   ├── errors/          # Páginas de error personalizadas (403, 404, 500)
│   ├── portal/          # Vista principal (index.html) del Grid
│   ├── _macros.html     # Componentes reutilizables (Paginador)
│   └── base.html        # Layout maestro del sistema
├── utils/               # Módulos transversales y utilidades
│   ├── __init__.py      # Exportador de utilidades
│   ├── decorators.py    # Decoradores de protección de rutas y roles
│   ├── email.py         # Lógica de notificaciones SMTP
│   └── helpers.py       # Funciones auxiliares (fechas, captura de IP, logs)
├── venv/                # Entorno virtual
├── .env                 # Variables de Entorno (Credenciales)
├── .gitignore           # Archivos ignorados por Git
├── app.py               # Punto de entrada de la aplicación (Factory Pattern)
├── crear_superadmin.py  # Script inicializador del Usuario Admin
├── extensions.py        # Inicialización de extensiones globales
├── models.py            # Modelos de Base de Datos (SQLAlchemy)
└── requirements.txt     # Dependencias del proyecto
```
---

## ⚙️ Instalación y Despliegue Local

1. Clonar el repositorio:

```bash
git clone https://github.com/Yosh457/portal-acceso
cd portal-acceso
```
2. Crear entorno virtual:

```bash
python -m venv venv
# En Windows:
venv\Scripts\activate
# En Mac/Linux:
source venv/bin/activate
```
3. Instalar dependencias:

```bash
pip install -r requirements.txt
```
4. Configurar variables de entorno (.env):

```env
SECRET_KEY=tu_clave_secreta_super_segura
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=tu_password_de_base_de_datos
MYSQL_DB=portal_acceso_db
FLASK_DEBUG=1
EMAIL_USUARIO=tu_correo@institucional.cl
EMAIL_CONTRASENA=tu_contraseña_de_aplicacion
```
5. Inicializar Base de Datos (Primera vez):

**Paso A: Crear la base de datos en MySQL.**

Ingresa a tu cliente MySQL (Workbench o consola) y ejecuta:

```sql
CREATE DATABASE portal_acceso_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
**Paso B: Crear las tablas.**

```bash
flask shell
```
Dentro de la shell interactiva de Flask ejecuta línea por línea lo siguiente:

```python
from models import db
db.create_all()
exit()
```
**Paso C: Crear usuario administrador inicial.**

```bash
python crear_superadmin.py
```
6. Ejecutar la aplicación:

```bash
python app.py
```

Accede en tu navegador a: http://localhost:5000

## 🛡️ Matriz de Permisos (Resumen)

| **Funcionalidad / Módulo**  | **Rol: Admin**   | **Rol: Funcionario**      |
|-----------------------------|------------------|---------------------------|
| **Visualizar Portal (Hub)** | ❌ (Irrelevante) | ✅ (Filtrado por permisos) |
| **Gestión de Usuarios**     | ✅                | ❌                         |
| **Gestión de Categorías**   | ✅                | ❌                         |
| **Gestión de Aplicaciones** | ✅                | ❌                         |
| **Asignar Apps a Usuarios** | ✅                | ❌                         |
| **Ver Logs de Auditoría**   | ✅                | ❌                         |
---
Desarrollado por **Josting Silva**  
Analista Programador – Unidad de TICs  
Departamento de Salud, Municipalidad de Alto Hospicio
