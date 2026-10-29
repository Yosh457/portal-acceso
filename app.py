# app.py
import os
from dotenv import load_dotenv
from flask import Flask, redirect, url_for, flash, render_template, request, session
from flask_wtf.csrf import CSRFError

# Importamos extensiones y modelos
from extensions import login_manager, csrf
from models import db, Usuario

# Función de fábrica para crear la aplicación Flask
def create_app():
    # Inicializa Flask
    app = Flask(__name__)
    # Habilitar extensión 'do' para Jinja2
    app.jinja_env.add_extension('jinja2.ext.do')
    # Cargar variables de entorno
    load_dotenv()
    
    # -------------------------------------------------------------------------
    # CONFIGURACIÓN DE SEGURIDAD
    # -------------------------------------------------------------------------
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        raise RuntimeError("Error crítico: No se ha configurado SECRET_KEY en el archivo .env")

    # Duración máxima de inactividad de una sesión autenticada.
    app.config['SESION_INACTIVIDAD_SEGUNDOS'] = 10 * 60

    # -------------------------------------------------------------------------
    # CONFIGURACIÓN DE BASE DE DATOS
    # -------------------------------------------------------------------------
    db_host = os.getenv('MYSQL_HOST')
    db_port = os.getenv('MYSQL_PORT')
    db_user = os.getenv('MYSQL_USER')
    db_pass = os.getenv('MYSQL_PASSWORD')
    db_name = os.getenv('MYSQL_DB')

    if not all([db_host, db_port, db_user, db_pass, db_name]):
        raise RuntimeError("Error crítico: Configuración de base de datos incompleta en el archivo .env")

    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024 # Límite de 32MB

    # Configuración de Pool para estabilidad
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 280
    }

    # -------------------------------------------------------------------------
    # INICIALIZACIÓN DE EXTENSIONES
    # -------------------------------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # -------------------------------------------------------------------------
    # CONFIGURACIÓN DE LOGIN MANAGER
    # -------------------------------------------------------------------------
    login_manager.session_protection = 'strong'
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión como administrador para acceder a esta sección.'
    login_manager.login_message_category = 'warning'

    # -------------------------------------------------------------------------
    # REGISTRO DE BLUEPRINTS
    # -------------------------------------------------------------------------
    from blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)

    from blueprints.admin import admin_bp
    app.register_blueprint(admin_bp)

    from blueprints.portal import portal_bp
    app.register_blueprint(portal_bp)

    # Versiona los recursos estáticos usando su fecha de modificación.
    # De este modo, el navegador solicita la versión nueva cuando cambia un archivo.
    def static_versionado(filename):
        ruta = os.path.join(app.static_folder, filename)
        try:
            version = os.stat(ruta).st_mtime_ns
        except OSError:
            # Flask seguirá devolviendo 404 si el archivo no existe.
            return url_for('static', filename=filename)
        return url_for('static', filename=filename, v=version)

    app.jinja_env.globals['static_versionado'] = static_versionado

    # -------------------------------------------------------------------------
    # RESTRICCIONES TRANSVERSALES DE SESIÓN
    # -------------------------------------------------------------------------
    from utils.decorators import verificar_restricciones_sesion
    app.before_request(verificar_restricciones_sesion)

    from utils.rate_limit import limitar_autenticacion
    app.before_request(limitar_autenticacion)

    # -------------------------------------------------------------------------
    # RUTA RAÍZ
    # -------------------------------------------------------------------------
    @app.route('/')
    def index():
        return redirect(url_for('portal.index'))

    # -------------------------------------------------------------------------
    # ERRORES Y CACHÉ
    # -------------------------------------------------------------------------
    @app.errorhandler(429)
    def muchas_solicitudes(error):
        from flask import make_response
        espera = getattr(error, 'retry_after', None) or 60
        respuesta = make_response(render_template('errors/429.html'), 429)
        respuesta.headers['Retry-After'] = str(int(espera))
        return respuesta

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        app.logger.warning('Solicitud rechazada por CSRF: %s %s', request.method, request.path)
        flash('La solicitud no se pudo validar. Actualice la página y vuelva a intentarlo.', 'warning')
        return redirect(url_for('auth.login'))

    @app.after_request
    def add_header(response):
        """Distingue archivos públicos, catálogo y respuestas sensibles."""
        response.headers['Referrer-Policy'] = 'no-referrer'

        # Los errores no deben quedar almacenados, especialmente las
        # respuestas de autenticación, rate limiting o fallos del servidor.
        if response.status_code >= 400:
            response.headers['Cache-Control'] = 'no-store'
        elif request.endpoint == 'static':
            # Conserva ETag y Last-Modified generados por Flask.
            # El versionado de URL evita reutilizar CSS/JS obsoletos.
            response.headers['Cache-Control'] = 'public, max-age=3600'
        elif request.endpoint == 'portal.index' and not session.get('_user_id'):
            # La página pública puede almacenarse, pero debe revalidarse
            # antes de mostrar cambios en categorías o aplicaciones.
            response.headers['Cache-Control'] = 'private, no-cache, max-age=0, must-revalidate'
        else:
            # Administración, autenticación, redirecciones y API de sesión.
            response.headers['Cache-Control'] = 'private, no-store'

        response.headers.pop('Pragma', None)
        response.headers.pop('Expires', None)
        return response

    # MANEJO DE ERRORES PERSONALIZADOS
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def access_denied(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        app.logger.error('Error interno no controlado: %s', type(e).__name__)
        return render_template('errors/500.html'), 500

    return app

# Loader de usuario para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(Usuario, int(user_id))
    except (TypeError, ValueError):
        return None

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        try:
            db.create_all()
            print("✅ Portal de Acceso inicializado. Tablas verificadas en MySQL.")
        except Exception as e:
            print(f"❌ Error al conectar con BD: {e}")

    app.run(
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
        host="0.0.0.0",
        port=5000
    )