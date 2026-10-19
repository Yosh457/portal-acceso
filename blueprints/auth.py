# blueprints/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from utils.security import generar_token, hash_token, ahora_utc, password_valida, ACTIVACION_HORAS, RECUPERACION_HORAS

from models import db, Usuario
from utils import registrar_log_sistema, enviar_correo_reseteo

# Definimos el Blueprint
auth_bp = Blueprint('auth', __name__, template_folder='../templates')

def obtener_ruta_redireccion(usuario):
    """
    Define el destino tras login basado en la tabla roles_aplicacion.
    Mantiene la arquitectura base separando las interfaces según el rol.
    """
    if not usuario.rol:
        return url_for('auth.login')
    
    if usuario.rol.nombre == 'Admin':
        return url_for('admin.panel')
    
    if usuario.rol.nombre == 'Funcionario':
        return url_for('portal.index')
    
    return url_for('auth.login')

# --- RUTAS DE AUTENTICACIÓN ---

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Validación básica
        if not email or not password:
            flash('Debes ingresar correo y contraseña.', 'danger')
            return render_template('auth/login.html')
        
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario:
            if not usuario.is_active:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'danger')
                return redirect(url_for('auth.login'))
            
            if usuario.check_password(password):
                login_user(usuario)
                registrar_log_sistema("Inicio de Sesión", f"Acceso exitoso al sistema. Rol: {usuario.rol.nombre}")

                # Bloqueo forzoso si requiere cambio de clave
                if usuario.cambio_clave_requerido:
                    flash('Por seguridad, debes cambiar tu contraseña inicial.', 'warning')
                    return redirect(url_for('auth.cambiar_clave'))
                
                flash(f'Bienvenido, {usuario.nombre_completo}', 'success')
                return redirect(obtener_ruta_redireccion(usuario))
            else:
                registrar_log_sistema("Login Fallido", f"Contraseña incorrecta para: {email}")
        else:
            registrar_log_sistema("Login Fallido", f"Email no registrado: {email}")
        
        flash('Correo o contraseña incorrectos.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    reason = request.args.get('reason')

    if reason == 'timeout':
        registrar_log_sistema(
            "Cierre de Sesión Automático",
            "Sesión cerrada por inactividad del usuario."
        )
        mensaje = 'Su sesión ha expirado por inactividad. Por favor, ingrese nuevamente.'
        categoria = 'warning'
    else:
        registrar_log_sistema(
            "Cierre de Sesión",
            "Usuario salió del sistema manualmente."
        )
        mensaje = 'Has cerrado sesión correctamente.'
        categoria = 'success'

    logout_user()
    flash(mensaje, categoria)

    return redirect(url_for('auth.login'))

@auth_bp.route('/cambiar_clave', methods=['GET', 'POST'])
@login_required
def cambiar_clave():
    # Si el usuario ya la cambió, no debería estar aquí, lo sacamos
    if not current_user.cambio_clave_requerido:
        return redirect(obtener_ruta_redireccion(current_user))
        
    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password')
        confirmar = request.form.get('confirmar_password')

        if not password_valida(nueva_password, confirmar):
            flash('Error: La contraseña debe tener 8 caracteres, una mayúscula y un número.', 'danger')
        else:
            current_user.set_password(nueva_password)
            current_user.cambio_clave_requerido = False
            db.session.commit()
            
            registrar_log_sistema("Cambio de Clave", "Usuario actualizó su contraseña obligatoria.")
            logout_user()
            flash('Contraseña actualizada correctamente. Ingresa nuevamente.', 'success')
            return redirect(url_for('auth.login'))
            
    return render_template('auth/cambiar_clave.html')

@auth_bp.route('/activar-cuenta/<token>', methods=['GET', 'POST'])
def activar_cuenta(token):
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))
    usuario = Usuario.query.filter_by(activacion_token_hash=hash_token(token)).first()
    if (not usuario or not usuario.activo or not usuario.activacion_pendiente
            or not usuario.activacion_token_expiracion
            or usuario.activacion_token_expiracion <= ahora_utc()):
        flash('El enlace de activación es inválido o ha expirado. Solicita uno nuevo al administrador.', 'warning')
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        password = request.form.get('nueva_password')
        confirmar = request.form.get('confirmar_password')
        if not password_valida(password, confirmar):
            flash('Verifica la contraseña, su confirmación y los requisitos indicados.', 'danger')
        else:
            try:
                usuario.set_password(password)
                usuario.activacion_pendiente = False
                usuario.activacion_token_hash = None
                usuario.activacion_token_expiracion = None
                usuario.cambio_clave_requerido = False
                db.session.commit()
                registrar_log_sistema('Activación Cuenta', f'Cuenta activada: {usuario.id}')
                flash('Cuenta activada. Ya puedes iniciar sesión.', 'success')
                return redirect(url_for('auth.login'))
            except SQLAlchemyError:
                db.session.rollback()
                flash('No fue posible activar la cuenta. Intenta nuevamente.', 'danger')
    return render_template('auth/activar_cuenta.html')


@auth_bp.route('/solicitar-reseteo', methods=['GET', 'POST'])
def solicitar_reseteo():
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        usuario = Usuario.query.filter_by(email=email).first()
        if (
            usuario
            and usuario.is_active
            and not usuario.activacion_pendiente
            and usuario.password_hash is not None
        ):
            token, digest, expiracion = generar_token(RECUPERACION_HORAS)
            try:
                usuario.reset_token = digest
                usuario.reset_token_expiracion = expiracion
                db.session.commit()
                if not enviar_correo_reseteo(usuario, token):
                    registrar_log_sistema('Error Correo Reseteo', f'Fallo al enviar recuperación para ID {usuario.id}')
                else:
                    registrar_log_sistema('Solicitud Reseteo', f'Solicitud recibida para ID {usuario.id}')
            except SQLAlchemyError:
                db.session.rollback()
        # Misma respuesta para cuentas existentes, inexistentes, inactivas o pendientes.
        flash('Si la cuenta existe y está habilitada, recibirás un enlace de recuperación.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/solicitar_reseteo.html')


@auth_bp.route('/resetear-clave/<token>', methods=['GET', 'POST'])
def resetear_clave(token):
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))
    usuario = Usuario.query.filter_by(reset_token=hash_token(token)).first()
    if (
        not usuario
        or not usuario.is_active
        or usuario.activacion_pendiente
        or usuario.password_hash is None
        or not usuario.reset_token_expiracion
        or usuario.reset_token_expiracion <= ahora_utc()
    ):
        flash('El enlace es inválido o ha expirado.', 'danger')
        return redirect(url_for('auth.solicitar_reseteo'))
    if request.method == 'POST':
        password = request.form.get('nueva_password')
        confirmar = request.form.get('confirmar_password')
        if not password_valida(password, confirmar):
            flash('Verifica la contraseña, su confirmación y los requisitos indicados.', 'danger')
        else:
            try:
                usuario.set_password(password)
                usuario.reset_token = None
                usuario.reset_token_expiracion = None
                usuario.cambio_clave_requerido = False
                db.session.commit()
                registrar_log_sistema('Recuperación Clave', f'Clave recuperada para ID {usuario.id}')
                flash('Contraseña restablecida. Inicia sesión nuevamente.', 'success')
                return redirect(url_for('auth.login'))
            except SQLAlchemyError:
                db.session.rollback()
                flash('No fue posible completar la operación.', 'danger')
    return render_template('auth/resetear_clave.html')
