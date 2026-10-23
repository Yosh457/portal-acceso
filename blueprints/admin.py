# blueprints/admin.py
import re
import unicodedata
from urllib.parse import urlsplit
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_

# Modelos adaptados al Portal de Acceso
from models import (
    db, Usuario, RolAplicacion, LogSistema,
    CategoriaAplicacion, TipoAplicacion, Aplicacion
)

# Utilidades 
from utils import registrar_log_sistema, admin_required, enviar_activacion_usuario
from utils.security import generar_token, ACTIVACION_HORAS
from utils.rate_limit import validar_limite

# Instanciamos el blueprint
admin_bp = Blueprint('admin', __name__, template_folder='../templates', url_prefix='/admin')

# Helper para normalizar slugs en el backend
def normalizar_slug(texto):
    """
    Convierte el texto a snake_case seguro para usar como slug.
    Ej: 'Sistema Inventario TICs' -> 'sistema_inventario_tics'
    """
    # Eliminar acentos
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    # Convertir a minúsculas
    texto = texto.lower()
    # Dejar solo alfanuméricos, espacios y guiones bajos
    texto = re.sub(r'[^a-z0-9\s_]', '', texto)
    # Reemplazar uno o más espacios/guiones bajos por un solo guion bajo
    texto = re.sub(r'[\s_]+', '_', texto).strip('_')
    return texto

# --- PROTECCIÓN GLOBAL DEL BLUEPRINT ---
@admin_bp.before_request
@login_required
@admin_required
def before_request():
    """
    Se ejecuta antes de cada petición a /admin/*.
    Garantiza que nadie sin sesión o sin rol de Admin pueda acceder a estas rutas.
    """
    pass

# --- ADMINISTRACIÓN DE CUENTAS TICs ---

def obtener_rol_admin():
    """El rol Admin se obtiene por nombre, sin asumir un ID fijo."""
    return RolAplicacion.query.filter_by(nombre='Admin').first()

def obtener_administrador_o_404(usuario_id):
    """Impide administrar cuentas que no pertenezcan al rol Admin."""
    return Usuario.query.join(RolAplicacion).filter(
        Usuario.id == usuario_id,
        RolAplicacion.nombre == 'Admin'
    ).first_or_404()

@admin_bp.route('/panel')
def panel():
    """Muestra únicamente cuentas administrativas y estadísticas del portal."""
    page = request.args.get('page', 1, type=int)
    busqueda = request.args.get('busqueda', '').strip()

    query = Usuario.query.join(RolAplicacion).filter(RolAplicacion.nombre == 'Admin')
    if busqueda:
        query = query.filter(or_(
            Usuario.nombre_completo.ilike(f'%{busqueda}%'),
            Usuario.email.ilike(f'%{busqueda}%')
        ))

    pagination = query.order_by(Usuario.id).paginate(
        page=page, per_page=10, error_out=False
    )
    stats = {
        'total_administradores': Usuario.query.join(RolAplicacion).filter(
            RolAplicacion.nombre == 'Admin'
        ).count(),
        'aplicaciones_activas': Aplicacion.query.filter_by(activo=True).count(),
        'categorias_activas': CategoriaAplicacion.query.filter_by(activo=True).count()
    }

    return render_template(
        'admin/panel.html', pagination=pagination,
        busqueda=busqueda, stats=stats
    )

@admin_bp.route('/crear_usuario', methods=['GET', 'POST'])
def crear_usuario():
    """Crea exclusivamente administradores, con activación por correo."""
    rol_admin = obtener_rol_admin()
    if rol_admin is None:
        flash('No existe el rol Admin. Revisa los roles de la base de datos.', 'danger')
        return redirect(url_for('admin.panel'))

    if request.method == 'POST':
        nombre = request.form.get('nombre_completo', '').strip()
        email = request.form.get('email', '').strip().lower()

        if not nombre or not email:
            flash('Nombre y correo electrónico son obligatorios.', 'danger')
        elif len(nombre) > 255 or len(email) > 255:
            flash('El nombre o correo supera la longitud permitida.', 'danger')
        elif Usuario.query.filter_by(email=email).first():
            flash('El correo electrónico ya se encuentra registrado.', 'danger')
        else:
            try:
                token, digest, expiracion = generar_token(ACTIVACION_HORAS)
                nuevo_usuario = Usuario(
                    nombre_completo=nombre,
                    email=email,
                    rol_id=rol_admin.id,
                    cambio_clave_requerido=False,
                    activo=True,
                    activacion_pendiente=True,
                    activacion_token_hash=digest,
                    activacion_token_expiracion=expiracion,
                    password_hash=None
                )
                db.session.add(nuevo_usuario)
                db.session.flush()
                registrar_log_sistema(
                    'Creación Administrador',
                    f'Se creó la cuenta administrativa de {nombre} ({email}).',
                    usuario=current_user, commit=False)
                db.session.commit()
                if enviar_activacion_usuario(nuevo_usuario, token):
                    flash('Administrador creado. Se envió el enlace de activación.', 'success')
                else:
                    flash('Administrador creado, pero no se pudo enviar el correo. Reenvía la activación.', 'warning')
                return redirect(url_for('admin.panel'))
            except Exception:
                db.session.rollback()
                current_app.logger.exception('Error al crear administrador')
                flash('No fue posible crear el administrador. Inténtalo nuevamente.', 'danger')

    return render_template('admin/crear_usuario.html', datos_previos=request.form)

@admin_bp.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    """Modifica los datos de una cuenta Admin; no altera permisos de aplicaciones."""
    usuario = obtener_administrador_o_404(id)

    if request.method == 'POST':
        email_nuevo = request.form.get('email', '').strip().lower()
        nombre_nuevo = request.form.get('nombre_completo', '').strip()
        forzar_cambio = request.form.get('forzar_cambio_clave') == '1'

        if not nombre_nuevo or not email_nuevo:
            flash('Nombre y correo electrónico son obligatorios.', 'danger')
        elif len(nombre_nuevo) > 255 or len(email_nuevo) > 255:
            flash('El nombre o correo supera la longitud permitida.', 'danger')
        elif Usuario.query.filter(
            Usuario.email == email_nuevo, Usuario.id != id
        ).first():
            flash('El correo electrónico ya pertenece a otra cuenta.', 'danger')
        else:
            try:
                usuario.nombre_completo = nombre_nuevo
                usuario.email = email_nuevo
                usuario.cambio_clave_requerido = (
                    forzar_cambio if not usuario.activacion_pendiente else False
                )
                # El rol y las relaciones con aplicaciones permanecen intactos.
                registrar_log_sistema(
                    'Edición Administrador',
                    f'Se actualizó la cuenta administrativa ID {usuario.id}.',
                    usuario=current_user, commit=False)
                db.session.commit()
                flash('Administrador actualizado correctamente.', 'success')
                return redirect(url_for('admin.panel'))
            except Exception:
                db.session.rollback()
                current_app.logger.exception('Error al editar administrador ID %s', id)
                flash('No se pudo actualizar el administrador.', 'danger')

    return render_template('admin/editar_usuario.html', usuario=usuario)

@admin_bp.route('/toggle_activo/<int:id>', methods=['POST'])
def toggle_activo(id):
    """Activa o bloquea cuentas Admin, excepto la cuenta propia."""
    usuario = obtener_administrador_o_404(id)
    if usuario.id == current_user.id:
        flash('No puedes cambiar el estado de tu propia cuenta.', 'danger')
        return redirect(url_for('admin.panel'))

    try:
        usuario.activo = not usuario.activo
        # La protección de sesiones ya verifica el estado de la cuenta.
        db.session.commit()
        estado = 'activado' if usuario.activo else 'desactivado'
        registrar_log_sistema(
            'Cambio Estado Administrador',
            f'Administrador ID {usuario.id} {estado}.', usuario=current_user, commit=False)
        db.session.commit()
        flash(f'Administrador {usuario.nombre_completo} {estado} correctamente.', 'success')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al cambiar estado de administrador ID %s', id)
        flash('Ocurrió un error al cambiar el estado del administrador.', 'danger')

    return redirect(url_for('admin.panel'))

# --- VISTAS DE AUDITORÍA ---

@admin_bp.route('/ver_logs')
def ver_logs():
    """Historial de auditoría administrativa y de sistema."""
    page = request.args.get('page', 1, type=int)
    usuario_filtro = request.args.get('usuario_id')
    accion_filtro = request.args.get('accion')

    query = LogSistema.query.order_by(LogSistema.timestamp.desc())

    if usuario_filtro and usuario_filtro.isdigit():
        query = query.filter(LogSistema.usuario_id == int(usuario_filtro))
    if accion_filtro:
        query = query.filter(LogSistema.accion == accion_filtro)

    pagination = query.paginate(page=page, per_page=15, error_out=False)
    todos_los_usuarios = Usuario.query.order_by(Usuario.nombre_completo).all()
    acciones_unicas = [r[0] for r in db.session.query(LogSistema.accion).distinct().all()]

    return render_template('admin/ver_logs.html', 
                           pagination=pagination,
                           todos_los_usuarios=todos_los_usuarios,
                           acciones_posibles=acciones_unicas,
                           filtros={'usuario_id': usuario_filtro, 'accion': accion_filtro})

# --- VALIDACIONES COMPARTIDAS DEL CATÁLOGO ---

MAX_ORDEN = 2_147_483_647  # INT positivo de MySQL

def validar_orden(valor):
    """Devuelve un entero positivo válido o None; nunca aplica un valor oculto."""
    texto = (valor or '').strip()
    if not texto.isascii() or not texto.isdecimal():
        return None
    numero = int(texto)
    return numero if 1 <= numero <= MAX_ORDEN else None

def validar_url_destino(valor):
    """Acepta HTTP/HTTPS con host; permite dominios e IP internas."""
    if not valor or len(valor) > 500 or any(ord(c) < 32 or ord(c) == 127 for c in valor):
        return False
    try:
        url = urlsplit(valor)
        return (
            url.scheme in ('http', 'https')
            and bool(url.hostname)
            and not url.username
            and not url.password
            and url.port != 0
        )
    except ValueError:
        return False

def validar_campos_aplicacion(nombre, url, descripcion, version, orden):
    if not nombre or not url:
        return 'El nombre y la URL de destino son obligatorios.'
    if len(nombre) > 150 or len(descripcion) > 255 or len(version) > 50:
        return 'Uno de los campos excede la longitud permitida.'
    if not validar_url_destino(url):
        return 'Ingresa una URL HTTP o HTTPS válida con un destino definido (máximo 500 caracteres).'
    if orden is None:
        return 'El orden debe ser un entero positivo válido.'
    return None

def obtener_categoria_destino(valor, actual_id=None):
    """Permite conservar la categoría inactiva actual, pero no seleccionar otra inactiva."""
    if not valor or not valor.isascii() or not valor.isdecimal():
        return None
    categoria = db.session.get(CategoriaAplicacion, int(valor))
    if categoria and (categoria.activo or categoria.id == actual_id):
        return categoria
    return None

def obtener_tipo_destino(valor, actual_id=None):
    if not valor or not valor.isascii() or not valor.isdecimal():
        return None
    tipo = db.session.get(TipoAplicacion, int(valor))
    if tipo and (tipo.activo or tipo.id == actual_id):
        return tipo
    return None

# --- GESTIÓN DE CATEGORÍAS ---

@admin_bp.route('/categorias', methods=['GET', 'POST'])
def categorias():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        orden = validar_orden(request.form.get('orden'))
        
        if not nombre or len(nombre) > 100 or orden is None:
            flash('Ingresa un nombre de hasta 100 caracteres y un orden entero positivo.', 'danger')
            return redirect(url_for('admin.categorias'))
            
        # Validación Backend: Evitar nombres duplicados
        if CategoriaAplicacion.query.filter_by(nombre=nombre).first():
            flash(f'Ya existe la categoría "{nombre}".', 'warning')
            return redirect(url_for('admin.categorias'))
            
        try:
            nueva_cat = CategoriaAplicacion(nombre=nombre, orden=orden, activo=True)
            db.session.add(nueva_cat)
            db.session.flush()
            registrar_log_sistema('Creación Categoría', f'Categoría ID {nueva_cat.id} creada.', usuario=current_user, commit=False)
            db.session.commit()
            flash('Categoría creada exitosamente.', 'success')
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Error al crear categoría')
            registrar_log_sistema('Error Creación Categoría', "Fallo al ejecutar la operación; revisar el registro técnico.", usuario=current_user)
            flash('Error al crear la categoría.', 'danger')
            
        return redirect(url_for('admin.categorias'))

    # Paginación y Listado (Ordenamiento Secundario)
    page = request.args.get('page', 1, type=int)
    busqueda = request.args.get('busqueda', '').strip()
    
    query = CategoriaAplicacion.query
    if busqueda:
        query = query.filter(CategoriaAplicacion.nombre.ilike(f'%{busqueda}%'))
        
    pagination = query.order_by(CategoriaAplicacion.orden.asc(), CategoriaAplicacion.nombre.asc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('admin/categorias.html', pagination=pagination, busqueda=busqueda)

@admin_bp.route('/editar_categoria/<int:id>', methods=['POST'])
def editar_categoria(id):
    categoria = db.get_or_404(CategoriaAplicacion, id)
    nombre = request.form.get('nombre', '').strip()
    orden = validar_orden(request.form.get('orden'))

    if not nombre or len(nombre) > 100 or orden is None:
        flash('Ingresa un nombre de hasta 100 caracteres y un orden entero positivo.', 'danger')
        return redirect(url_for('admin.categorias'))

    # Validación Backend: Evitar nombres duplicados excluyendo la actual
    existe = CategoriaAplicacion.query.filter(
        CategoriaAplicacion.nombre == nombre, CategoriaAplicacion.id != id
    ).first()
    if existe:
        flash(f'Ya existe otra categoría llamada "{nombre}".', 'warning')
        return redirect(url_for('admin.categorias'))

    try:
        categoria.nombre = nombre
        categoria.orden = orden
        registrar_log_sistema('Edición Categoría', f'Categoría ID {id} actualizada.', usuario=current_user, commit=False)
        db.session.commit()
        flash('Categoría actualizada correctamente.', 'success')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al editar categoría ID %s', id)
        registrar_log_sistema('Error Edición Categoría', "Fallo al ejecutar la operación; revisar el registro técnico.", usuario=current_user)
        flash('Error al actualizar la categoría.', 'danger')

    return redirect(url_for('admin.categorias'))

@admin_bp.route('/toggle_categoria/<int:id>', methods=['POST'])
def toggle_categoria(id):
    categoria = db.get_or_404(CategoriaAplicacion, id)
    try:
        categoria.activo = not categoria.activo
        estado = 'activada' if categoria.activo else 'desactivada'
        registrar_log_sistema('Cambio Estado Categoría', f'Categoría ID {id} {estado}.', usuario=current_user, commit=False)
        db.session.commit()
        flash(f'Categoría "{categoria.nombre}" {estado}.', 'success')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al cambiar estado de categoría ID %s', id)
        registrar_log_sistema('Error Cambio Estado Categoría', "Fallo al ejecutar la operación; revisar el registro técnico.", usuario=current_user)
        flash('Error al cambiar el estado.', 'danger')

    return redirect(url_for('admin.categorias'))

# --- GESTIÓN DE APLICACIONES ---

@admin_bp.route('/aplicaciones', methods=['GET', 'POST'])
def aplicaciones():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        # Normalización Backend a snake_case
        slug = normalizar_slug(request.form.get('slug', '').strip())
        url = request.form.get('url_destino', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        version = request.form.get('version', '').strip()
        orden = validar_orden(request.form.get('orden'))
        cat_id = request.form.get('categoria_id', '').strip()
        tipo_id = request.form.get('tipo_aplicacion_id', '').strip()

        error = validar_campos_aplicacion(nombre, url, descripcion, version, orden)
        if error:
            flash(error, 'danger')
            return redirect(url_for('admin.aplicaciones'))
        
        if not slug or len(slug) > 50:
            flash('El slug debe contener caracteres válidos y tener hasta 50 caracteres.', 'danger')
            return redirect(url_for('admin.aplicaciones'))
        
        # Validar que la categoría y tipo de destino están activos
        categoria = obtener_categoria_destino(cat_id)
        tipo = obtener_tipo_destino(tipo_id)
        if not categoria or not tipo:
            flash('Selecciona una categoría y un tipo de aplicación activos.', 'danger')
            return redirect(url_for('admin.aplicaciones'))
            
        # Validación Backend: Evitar nombres o slugs duplicados
        if Aplicacion.query.filter_by(nombre=nombre).first():
            flash(f'Ya existe una aplicación registrada con el nombre "{nombre}".', 'danger')
            return redirect(url_for('admin.aplicaciones'))

        if Aplicacion.query.filter_by(slug=slug).first():
            flash(f'El slug "{slug}" ya existe en otra aplicación.', 'danger')
            return redirect(url_for('admin.aplicaciones'))

        try:
            nueva_app = Aplicacion(
                nombre=nombre, slug=slug, descripcion=descripcion, version=version,
                url_destino=url, categoria_id=categoria.id, tipo_aplicacion_id=tipo.id,
                orden=orden, activo=True
            )
            db.session.add(nueva_app)
            db.session.flush()
            registrar_log_sistema('Creación Aplicación', f'Aplicación ID {nueva_app.id} registrada.', usuario=current_user, commit=False)
            db.session.commit()
            flash('Aplicación registrada exitosamente.', 'success')
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Error al registrar aplicación')
            registrar_log_sistema('Error Creación Aplicación', "Fallo al ejecutar la operación; revisar el registro técnico.", usuario=current_user)
            flash('Error al crear la aplicación.', 'danger')
            
        return redirect(url_for('admin.aplicaciones'))

    # Solo mostrar categorías activas para crear nuevas apps (Para los selects de creación/edición)
    categorias_activas = CategoriaAplicacion.query.filter_by(activo=True).order_by(
        CategoriaAplicacion.orden.asc(), CategoriaAplicacion.nombre.asc()
    ).all()
    tipos = TipoAplicacion.query.filter_by(activo=True).all()

    # Para el filtro general
    todas_categorias = CategoriaAplicacion.query.order_by(
        CategoriaAplicacion.orden.asc(), CategoriaAplicacion.nombre.asc()
    ).all()
    todos_tipos = TipoAplicacion.query.order_by(TipoAplicacion.nombre.asc()).all()

    # Paginación y Listado (Ordenamiento Secundario)
    page = request.args.get('page', 1, type=int)
    cat_filtro = request.args.get('categoria_id', '').strip()
    busqueda = request.args.get('busqueda', '').strip()

    query = Aplicacion.query
    if cat_filtro.isascii() and cat_filtro.isdecimal():
        query = query.filter_by(categoria_id=int(cat_filtro))
    if busqueda:
        query = query.filter(or_(Aplicacion.nombre.ilike(f'%{busqueda}%'), Aplicacion.slug.ilike(f'%{busqueda}%')))
        
    pagination = query.order_by(Aplicacion.categoria_id, Aplicacion.orden.asc(), Aplicacion.nombre.asc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template(
        'admin/aplicaciones.html', pagination=pagination,
        categorias=categorias_activas, todas_categorias=todas_categorias,
        tipos=tipos, todos_tipos=todos_tipos, cat_filtro=cat_filtro, busqueda=busqueda
    )


@admin_bp.route('/editar_aplicacion/<int:id>', methods=['POST'])
def editar_aplicacion(id):
    app_obj = db.get_or_404(Aplicacion, id)
    
    nombre = request.form.get('nombre', '').strip()
    # El slug NO se recibe del POST porque es de solo lectura (inmutable)
    url = request.form.get('url_destino', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    version = request.form.get('version', '').strip()
    orden = validar_orden(request.form.get('orden'))
    cat_id = request.form.get('categoria_id', '').strip()
    tipo_id = request.form.get('tipo_aplicacion_id', '').strip()
    
    error = validar_campos_aplicacion(nombre, url, descripcion, version, orden)
    if error:
        flash(error, 'danger')
        return redirect(url_for('admin.aplicaciones'))
    
    categoria = obtener_categoria_destino(cat_id, app_obj.categoria_id)
    tipo = obtener_tipo_destino(tipo_id, app_obj.tipo_aplicacion_id)
    if not categoria or not tipo:
        flash('Selecciona una categoría y un tipo válidos. No se permite trasladar a elementos inactivos.', 'danger')
        return redirect(url_for('admin.aplicaciones'))

    # Validación Backend: Evitar nombres duplicados excluyendo la actual
    existe = Aplicacion.query.filter(Aplicacion.nombre == nombre, Aplicacion.id != id).first()
    if existe:
        flash(f'Ya existe otra aplicación con el nombre "{nombre}".', 'warning')
        return redirect(url_for('admin.aplicaciones'))

    try:
        app_obj.nombre = nombre
        # El slug y las relaciones de usuarios/roles no se modifican.
        app_obj.descripcion = descripcion
        app_obj.version = version
        app_obj.url_destino = url
        app_obj.categoria_id = categoria.id
        app_obj.tipo_aplicacion_id = tipo.id
        app_obj.orden = orden
        registrar_log_sistema('Edición Aplicación', f'Aplicación ID {id} actualizada.', usuario=current_user, commit=False)
        db.session.commit()
        flash('Aplicación actualizada correctamente.', 'success')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al editar aplicación ID %s', id)
        registrar_log_sistema('Error Edición Aplicación', "Fallo al ejecutar la operación; revisar el registro técnico.", usuario=current_user)
        flash('Error al actualizar la aplicación.', 'danger')

    return redirect(url_for('admin.aplicaciones'))


@admin_bp.route('/toggle_aplicacion/<int:id>', methods=['POST'])
def toggle_aplicacion(id):
    app_obj = db.get_or_404(Aplicacion, id)
    try:
        app_obj.activo = not app_obj.activo
        estado = 'activada' if app_obj.activo else 'desactivada'
        registrar_log_sistema('Cambio Estado Aplicación', f'Aplicación ID {id} {estado}.', usuario=current_user, commit=False)
        db.session.commit()
        flash(f'Aplicación "{app_obj.nombre}" {estado}.', 'success')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al cambiar estado de aplicación ID %s', id)
        registrar_log_sistema('Error Cambio Estado Aplicación', "Fallo al ejecutar la operación; revisar el registro técnico.", usuario=current_user)
        flash('Error al cambiar el estado.', 'danger')

    return redirect(url_for('admin.aplicaciones'))


@admin_bp.route('/reenviar_activacion/<int:id>', methods=['POST'])
def reenviar_activacion(id):
    usuario = obtener_administrador_o_404(id)
    if not usuario.activo or not usuario.activacion_pendiente:
        flash('La cuenta no requiere activación o está bloqueada.', 'warning')
        return redirect(url_for('admin.panel'))

    # Cuenta destinataria: 3 reenvíos por hora desde cualquier administrador.
    validar_limite('reenviar_activacion_cuenta', str(usuario.id), 3, 60 * 60)
    token, digest, expiracion = generar_token(ACTIVACION_HORAS)
    try:
        usuario.activacion_token_hash = digest
        usuario.activacion_token_expiracion = expiracion
        registrar_log_sistema('Reenvío Activación', f'Nuevo enlace para ID {usuario.id}', usuario=current_user, commit=False)
        db.session.commit()
        if enviar_activacion_usuario(usuario, token):
            flash('Se envió un nuevo enlace de activación.', 'success')
        else:
            flash('No se pudo enviar el correo. Puedes intentar reenviarlo más tarde.', 'warning')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al reenviar activación ID %s', id)
        flash('No se pudo renovar el enlace.', 'danger')

    return redirect(url_for('admin.panel'))