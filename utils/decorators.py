# utils/decorators.py
from functools import wraps
from flask import abort, redirect, url_for, flash, request
from flask_login import current_user, logout_user

def verificar_restricciones_sesion():
    """Protege todas las rutas con un único control de sesión.

    Se registra mediante app.before_request en la fábrica Flask.
    Devuelve una respuesta para bloquear la solicitud, o None si puede continuar.
    """
    # Los archivos estáticos no necesitan esta comprobación.
    if request.endpoint == 'static':
        return None

    if not current_user.is_authenticated:
        return None

    # Una cuenta desactivada pierde acceso en su siguiente solicitud.
    if not current_user.is_active:
        logout_user()
        flash('Tu cuenta ha sido desactivada. Contacta al administrador.', 'warning')
        return redirect(url_for('auth.login'))

    # Permitir únicamente actualizar la clave o cerrar sesión durante
    # el cambio inicial obligatorio; aplica tanto a Admin como Funcionario.
    if current_user.cambio_clave_requerido:
        if request.endpoint not in ('auth.cambiar_clave', 'auth.logout'):
            return redirect(url_for('auth.cambiar_clave'))

    return None


def check_password_change(f):
    """Verifica si el usuario debe cambiar su contraseña obligatoriamente."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.cambio_clave_requerido:
            if request.endpoint not in ['auth.cambiar_clave', 'auth.logout']:
                flash('Debes cambiar tu contraseña para continuar.', 'warning')
                return redirect(url_for('auth.cambiar_clave'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Solo permite acceso al Rol 'Admin'."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_active or not current_user.rol or current_user.rol.nombre != 'Admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def funcionario_required(f):
    """Solo permite acceso al Rol 'Funcionario'."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_active or not current_user.rol or current_user.rol.nombre != 'Funcionario':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*roles_permitidos):
    """Permite acceso a uno o más roles específicos."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_active or not current_user.rol:
                abort(403)
            if current_user.rol.nombre not in roles_permitidos:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator