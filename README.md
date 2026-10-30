# 🏥 Portal de Acceso Institucional - Red de Salud APS Alto Hospicio

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)
![Database](https://img.shields.io/badge/Database-MySQL-blue.svg)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v3-38B2AC.svg)

Plataforma web institucional desarrollada para la **Red de Atención Primaria de Salud Municipal de Alto Hospicio**. Centraliza el acceso a los sistemas y herramientas digitales utilizados por establecimientos y unidades de salud.

El **Portal de Acceso** funciona como un **catálogo público de aplicaciones institucionales**: los visitantes pueden visualizar las aplicaciones activas sin iniciar sesión. Su **panel de administración es privado**, reservado a cuentas con rol `Admin` autorizadas para gestionar administradores, categorías, aplicaciones y auditoría.

> **Importante:** el portal muestra enlaces a otros sistemas; **no reemplaza sus mecanismos de autenticación**. Cada aplicación enlazada mantiene sus propias credenciales y permisos cuando corresponda.

---

## 🚀 Características principales

### 🖥️ Catálogo público de aplicaciones

- **Acceso sin iniciar sesión:** consulta de aplicaciones institucionales activas desde `/portal/inicio`.
- **Organización por categorías:** tarjetas agrupadas según categoría y orden de visualización.
- **Enlaces a sistemas internos y externos:** desde un único punto de acceso.
- **Identidad visual institucional:** logos, iconografía y estilos propios; identificadores únicos (*slugs*) para las aplicaciones.
- **Diseño responsivo:** vistas adaptadas a computadores y dispositivos móviles.

### 👥 Administración centralizada

- Gestión de cuentas **administrativas**, con acceso restringido al rol `Admin`.
- Registro, edición, activación y desactivación de categorías y aplicaciones.
- Búsqueda, filtrado y paginación en módulos administrativos.
- Formularios y modales con mejoras de navegación por teclado y accesibilidad.
- Consulta de registros históricos de operaciones administrativas.

### 🔒 Seguridad institucional

- Autenticación y sesiones mediante **Flask-Login**.
- Protección de contraseñas mediante funciones de hash de **Werkzeug**.
- Protección **CSRF** en las operaciones correspondientes mediante **Flask-WTF**.
- Autorización del backend para proteger los módulos de administración.
- Activación de cuentas y recuperación de contraseñas mediante enlaces temporales.
- Limitación persistente de solicitudes de autenticación en MySQL.
- Control de inactividad, renovación e invalidación de sesiones.
- Políticas diferenciadas de caché HTTP para catálogo, recursos estáticos y contenido privado.

### 📊 Auditoría y trazabilidad

El módulo de auditoría permite consultar eventos almacenados en `log_sistema`. Según el evento, se registran usuario, fecha y hora, acción, detalles e IP de origen.

### 🎨 Interfaz y rendimiento

- **Tailwind CSS 3 compilado localmente**, sin el CDN de desarrollo en producción.
- CSS institucional complementario en `static/css/style.css`.
- JavaScript nativo para formularios, mensajes, modales y sesiones.
- Versionado de recursos CSS y JavaScript a partir de su fecha de modificación.

---

## 🛠️ Tecnologías utilizadas

| Componente | Tecnología |
| --- | --- |
| Lenguaje | Python 3.10 (entorno probado; verificar compatibilidad antes de cambiar de versión) |
| Framework | Flask 3.x |
| Arquitectura | Application Factory (`create_app`) y Blueprints |
| Persistencia | MySQL, Flask-SQLAlchemy, SQLAlchemy y PyMySQL |
| Plantillas | HTML5 y Jinja2 |
| Estilos | Tailwind CSS 3 compilado y CSS institucional |
| Interactividad | JavaScript nativo |
| Autenticación | Flask-Login |
| Formularios y CSRF | Flask-WTF |
| Contraseñas | Werkzeug Security |
| Compilación CSS | Node.js y npm |
| Ejecución WSGI | Passenger/cPanel o Waitress, según el entorno |
| Versionamiento | Git y GitHub |

La instalación exacta de dependencias Python se rige por `requirements.txt`; la de frontend, por `package.json` y `package-lock.json`.

---

## 📂 Estructura del proyecto

```text
PortalAcceso/
├── blueprints/                     # Rutas y controladores Flask
│   ├── admin.py                    # Administradores, categorías, aplicaciones y logs
│   ├── auth.py                     # Inicio de sesión, activación, recuperación y sesiones
│   └── portal.py                   # Catálogo público de aplicaciones
├── frontend/                       # Archivos fuente de compilación frontend
│   └── tailwind-input.css          # Entrada para generar Tailwind CSS
├── sql/                            # Scripts históricos y de referencia; no son migraciones automáticas
│   ├── 01_fase2_mysql.sql
│   ├── 02_limites_solicitudes_mysql.sql
│   └── 03_sesion_version_mysql.sql
├── static/                         # Recursos servidos públicamente por Flask
│   ├── css/
│   │   ├── style.css               # Estilos institucionales y componentes propios
│   │   └── tailwind.css            # Hoja compilada incluida en el repositorio
│   ├── docs/                       # Recursos públicos, nunca documentación interna sensible
│   ├── img/
│   │   ├── favicon.ico             # Ícono del sitio
│   │   ├── Logo_Red_APS_2.png      # Logo de la Red APS
│   │   └── logoMaho.png            # Logo municipal
│   └── js/
│       ├── flash_messages.js       # Mensajes de confirmación y alerta
│       ├── form_submit.js          # Comportamiento de envío de formularios
│       ├── modal_handler.js        # Apertura, cierre y accesibilidad de modales
│       ├── session_timeout.js      # Advertencias y control de inactividad
│       └── validation.js           # Validaciones de interfaz
├── templates/                      # Plantillas HTML/Jinja2
│   ├── admin/
│   │   ├── aplicaciones.html       # Gestión de aplicaciones
│   │   ├── categorias.html         # Gestión de categorías
│   │   ├── crear_usuario.html      # Alta de administrador
│   │   ├── editar_usuario.html     # Edición de administrador
│   │   ├── panel.html              # Panel administrativo
│   │   └── ver_logs.html           # Auditoría y filtros
│   ├── auth/
│   │   ├── activar_cuenta.html     # Activación inicial de cuenta
│   │   ├── cambiar_clave.html      # Cambio de contraseña
│   │   ├── login.html              # Acceso de administradores
│   │   ├── resetear_clave.html     # Restablecimiento de contraseña
│   │   └── solicitar_reseteo.html  # Solicitud de recuperación
│   ├── errors/
│   │   ├── 403.html                # Acceso denegado
│   │   ├── 404.html                # Recurso inexistente
│   │   ├── 429.html                # Límite de solicitudes alcanzado
│   │   └── 500.html                # Error interno
│   ├── portal/
│   │   └── index.html              # Catálogo público
│   ├── _macros.html                # Componentes reutilizables, incluido paginador
│   └── base.html                   # Layout institucional compartido
├── tests/                          # Pruebas automatizadas
│   ├── test_auditoria.py           # Pruebas de auditoría y transacciones
│   └── test_rate_limit.py          # Pruebas del limitador de solicitudes
├── utils/                          # Servicios y utilidades transversales
│   ├── __init__.py                 # Inicialización de utilidades
│   ├── decorators.py               # Controles de permisos y sesión
│   ├── email.py                    # Envío de mensajes de correo
│   ├── helpers.py                  # Funciones auxiliares y auditoría
│   ├── rate_limit.py               # Limitación de solicitudes
│   └── security.py                 # Tokens y verificaciones de seguridad
├── .env.example                    # Ejemplo de variables de entorno (versionado)
├── .gitignore                      # Exclusiones de Git
├── app.py                          # Configuración Flask y Application Factory
├── crear_superadmin.py             # Alta interactiva del primer administrador
├── extensions.py                   # Extensiones compartidas
├── inicializar_bd.py               # Inicialización de tablas y catálogos mínimos
├── models.py                       # Modelos y tablas SQLAlchemy
├── package-lock.json               # Dependencias npm fijadas
├── package.json                    # Dependencias y comandos de compilación
├── passenger_wsgi.py               # Punto de entrada Passenger/cPanel
├── README.md                       # Esta documentación
├── requirements.txt                # Dependencias Python
└── tailwind.config.js               # Configuración de Tailwind
```

En desarrollo se crean también `.env`, `venv/`, `node_modules/` y `__pycache__/`. **No deben publicarse en Git**. En particular, `.env` contiene secretos.

---

## ⚙️ Requisitos previos

- Python 3.10 para reproducir el entorno local probado; otras versiones requieren validar sus dependencias.
- MySQL compatible con el esquema y la configuración del proyecto.
- Git y una terminal (los ejemplos utilizan **PowerShell en Windows**).
- Credenciales SMTP para activar las funcionalidades de correo.
- Node.js y npm **solo si se necesita recompilar Tailwind**; el CSS compilado está incluido en el repositorio.

> Para un despliegue con cPanel, confirmar primero la versión de Python disponible, compatibilidad de dependencias y configuración de Passenger.

## 💻 Instalación local desde cero

Estos pasos describen una **instalación nueva sobre una base MySQL vacía**. No son instrucciones para migrar una instalación existente.

### 1. Clonar el repositorio

```powershell
git clone https://github.com/Yosh457/portal-acceso.git
cd portal-acceso
```

### 2. Preparar Python

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

Si PowerShell impide activar el entorno por su política de ejecución, consultar la política aplicable al equipo antes de modificarla.

### 3. Configurar `.env`

```powershell
Copy-Item .env.example .env
```

Editar `.env` y reemplazar todos los valores de ejemplo por los del entorno. Las variables contemplan `SECRET_KEY`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`, `FLASK_DEBUG`, `EMAIL_USUARIO`, `EMAIL_CONTRASENA`, `WAITRESS_PORT` y `PORTAL_BASE_URL`.

Para generar una clave aleatoria:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Mantener `FLASK_DEBUG=0` fuera del desarrollo local. No subir `.env` ni reutilizar secretos entre instalaciones. Los valores numéricos pueden escribirse sin comillas, por ejemplo `MYSQL_PORT=3306`.

### 4. Crear la base MySQL

Ingresar con una cuenta MySQL autorizada (Workbench, consola o administrador del hosting) y ejecutar:

```sql
CREATE DATABASE portal_acceso_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Crear un usuario **dedicado** con permisos adecuados para la instalación y configurar ese usuario en `.env`. Evitar utilizar `root` en la ejecución habitual. Tras instalar, revisar y reducir los permisos de creación de tablas si ya no son necesarios.

> `inicializar_bd.py` **no crea la base de datos**; esta debe existir antes de ejecutarlo.

### 5. Crear tablas y catálogos mínimos

```powershell
python inicializar_bd.py
```

El script:

1. Ejecuta `db.create_all()`, que crea **solo las tablas faltantes declaradas en `models.py`**, incluidas las tablas de asociación que este define.
2. Crea `limites_solicitudes` mediante `CREATE TABLE IF NOT EXISTS`, porque está gestionada por SQL explícito.
3. Inserta el rol `Admin` si falta.
4. Inserta los tipos `Interno`, `Externo` e `IFRAME` si faltan.

**No crea administradores, categorías ni aplicaciones**, no elimina información y no actualiza columnas de tablas existentes. Por ello debe usarse como inicialización de una instalación nueva, **no como sistema de migraciones**.

En el esquema actual existe una tabla de asociación `aplicaciones_usuarios`; `aplicaciones_roles` es una estructura histórica del volcado de desarrollo y **no está definida en el modelo actual**: no se crea en una instalación nueva mediante `db.create_all()`.

### 6. Crear el primer administrador

```powershell
python crear_superadmin.py
```

El asistente solicita nombre, correo y contraseña, oculta la contraseña durante la captura y realiza validaciones antes de almacenar la cuenta. Se requiere que exista el rol `Admin`, creado durante la inicialización.

### 7. Iniciar Flask en desarrollo

```powershell
python app.py
```

- **Portal público:** http://127.0.0.1:5000/portal/inicio
- **Inicio de sesión administrativo:** http://127.0.0.1:5000/login
- **Panel administrativo:** http://127.0.0.1:5000/admin/panel (requiere autenticación)

La aplicación local escucha en `127.0.0.1` por defecto. **No exponer el servidor de desarrollo a Internet ni utilizarlo como servicio de producción**.

Una instalación nueva puede mostrar el catálogo vacío hasta que un administrador registre categorías y aplicaciones.

---

## 🎨 Compilación local de Tailwind CSS

El proyecto utiliza **Tailwind CSS 3 compilado**, en lugar de `cdn.tailwindcss.com`.

```powershell
npm ci
npm run css:build
```

- `frontend/tailwind-input.css`: punto de entrada.
- `tailwind.config.js`: configuración y rutas de contenido para detectar clases.
- `static/css/tailwind.css`: resultado compilado que Flask sirve al navegador.
- `static/css/style.css`: estilos institucionales adicionales.

Cuando cambien las clases Tailwind en plantillas o scripts, recompilar y comprobar visualmente las páginas en escritorio y móvil. `node_modules/` se excluye de Git; el CSS ya generado sí se mantiene versionado para que ejecutar Flask no exija Node.js.

---

## 🛡️ Matriz de permisos

| Funcionalidad | Visitante sin sesión | Admin autenticado |
| --- | :---: | :---: |
| Consultar catálogo público | ✅ | ✅ |
| Ver categorías y aplicaciones activas | ✅ | ✅ |
| Abrir enlaces a sistemas enlazados | ✅ | ✅ |
| Acceder al panel administrativo | ❌ | ✅ |
| Gestionar cuentas administrativas | ❌ | ✅ |
| Gestionar categorías y aplicaciones | ❌ | ✅ |
| Consultar auditoría | ❌ | ✅ |

La disponibilidad de un enlace en el catálogo **no implica** autorización dentro del sistema de destino. El acceso administrativo se comprueba en el backend, no solo mediante la interfaz.

---

## 🔐 Seguridad, caché y sesiones

- **Usuarios:** cuentas administrativas con rol `Admin`; activación y recuperación de credenciales mediante enlaces temporales.
- **Sesiones:** expiración por inactividad e invalidación según eventos de seguridad.
- **Solicitudes:** límites persistidos en la tabla MySQL `limites_solicitudes` para operaciones protegidas.
- **Auditoría:** operaciones sensibles registradas en `log_sistema`.
- **HTML privado y autenticación:** respuestas con políticas que impiden almacenarlas en caché.
- **Catálogo público:** revalidación para reflejar cambios en categorías y aplicaciones.
- **CSS y JS:** almacenamiento temporal y URL versionada según la modificación de cada recurso.

En producción utilizar HTTPS, una `SECRET_KEY` propia, credenciales dedicadas, respaldos y control de acceso adecuados al entorno. Nunca almacenar contraseñas o respaldos sensibles en `static/`.

---

## 🧪 Pruebas y verificaciones

```powershell
python -m pip check
python -m compileall -q app.py blueprints utils models.py extensions.py crear_superadmin.py inicializar_bd.py passenger_wsgi.py
python -m unittest discover -s tests -v
flask --app app:create_app routes
```

Las pruebas existentes cubren aspectos de auditoría y limitación de solicitudes. La prueba que **simula un fallo de MySQL** puede escribir un traceback esperado en la consola y aun así terminar en `ok`. El resultado global `OK` significa que las aserciones de la suite pasaron; **no sustituye una prueba funcional completa ni una instalación desde cero en una base desechable**.

Antes de publicar cambios, comprobar además el portal público, inicio/cierre de sesión, filtros, formularios, modales, paginación y navegación desde móvil y escritorio.

---

## 🚀 Despliegue WSGI

### cPanel y Passenger

`passenger_wsgi.py` expone `application = create_app()` como punto de entrada WSGI. Al configurar la aplicación Python en cPanel, verificar la ruta raíz del proyecto, el archivo de arranque esperado por Passenger, el entorno virtual, variables `.env`, acceso MySQL, SMTP y recursos estáticos compilados. El comportamiento preciso depende del proveedor de hosting.

### Waitress

`requirements.txt` incluye Waitress como alternativa de servidor WSGI, útil en entornos Windows. El valor `WAITRESS_PORT` de `.env.example` es un parámetro previsto para su configuración; **`python app.py` no usa automáticamente ese puerto**.

No confundir los servidores WSGI con el servidor de desarrollo de Flask. En producción deben configurarse HTTPS, proxy inverso cuando corresponda, permisos, respaldos y registros.

---

## 🗄️ Base de datos y scripts históricos

`models.py` es la referencia de los modelos ORM actuales, pero `db.create_all()` **no actualiza estructuras existentes**. La carpeta `sql/` conserva scripts utilizados durante el desarrollo de mejoras previas (seguridad, solicitudes y sesiones). Son **históricos y de referencia**, no un procedimiento secuencial de instalación ni migraciones automáticas.

El volcado `Estructura_Portal_Acceso_DB.sql` facilitado para revisión contiene sentencias `DROP TABLE IF EXISTS`; no forma parte del instalador ni debe ejecutarse sobre bases con información. Antes de cualquier cambio real de esquema, realizar respaldo, revisar diferencias y aplicar una migración controlada.

---

## 📌 Mantenimiento y buenas prácticas

- Mantener la estructura modular con Blueprints y Application Factory.
- Centralizar configuración y extensiones compartidas; no introducir claves en el código.
- Respetar las comprobaciones de rol, CSRF, autenticación y auditoría existentes.
- Usar una cuenta MySQL dedicada y limitar sus privilegios.
- Recompilar Tailwind tras cambios que introduzcan nuevas clases.
- Ejecutar pruebas y revisar `git diff --check` antes de confirmar cambios.
- Utilizar **Conventional Commits**, por ejemplo `feat(admin): ...`, `fix(auth): ...`, `refactor(frontend): ...`, `perf(cache): ...` y `docs(readme): ...`.
- Actualizar este README cuando cambie la instalación o la arquitectura.

> `static/docs/` solo debe contener materiales destinados a acceso público. Los procedimientos internos y secretos de infraestructura deben mantenerse fuera del directorio estático y, según su sensibilidad, fuera del repositorio público.

---

## 👨‍💻 Desarrollo y mantenimiento

**Desarrollado por Josting Silva**  
Analista Programador — Unidad de TICs  
Departamento de Salud, Municipalidad de Alto Hospicio

*Portal de Acceso Institucional — Centralizando el acceso a los sistemas y herramientas digitales de la Red APS Alto Hospicio.*
