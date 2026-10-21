# blueprints/admin.py
import re
import unicodedata
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
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
                db.session.commit()
                registrar_log_sistema(
                    'Creación Administrador',
                    f'Se creó la cuenta administrativa de {nombre} ({email}).',
                    usuario=current_user
                )
                if enviar_activacion_usuario(nuevo_usuario, token):
                    flash('Administrador creado. Se envió el enlace de activación.', 'success')
                else:
                    flash('Administrador creado, pero no se pudo enviar el correo. Reenvía la activación.', 'warning')
                return redirect(url_for('admin.panel'))
            except Exception:
                db.session.rollback()
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
                db.session.commit()
                registrar_log_sistema(
                    'Edición Administrador',
                    f'Se actualizó la cuenta administrativa ID {usuario.id}.',
                    usuario=current_user
                )
                flash('Administrador actualizado correctamente.', 'success')
                return redirect(url_for('admin.panel'))
            except Exception:
                db.session.rollback()
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
            f'Administrador ID {usuario.id} {estado}.', usuario=current_user
        )
        flash(f'Administrador {usuario.nombre_completo} {estado} correctamente.', 'success')
    except Exception:
        db.session.rollback()
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

# --- GESTIÓN DE CATEGORÍAS ---

@admin_bp.route('/categorias', methods=['GET', 'POST'])
def categorias():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        orden = request.form.get('orden', '1').strip()
        
        if not nombre:
            flash('El nombre de la categoría es obligatorio.', 'danger')
            return redirect(url_for('admin.categorias'))
            
        # Validación Backend: Evitar nombres duplicados
        if CategoriaAplicacion.query.filter_by(nombre=nombre).first():
            flash(f'Ya existe la categoría "{nombre}".', 'warning')
            return redirect(url_for('admin.categorias'))
            
        try:
            nueva_cat = CategoriaAplicacion(
                nombre=nombre,
                orden=int(orden) if orden.isdigit() else 1,
                activo=True
            )
            db.session.add(nueva_cat)
            db.session.commit()
            registrar_log_sistema("Creación Categoría", f"Categoría '{nombre}' creada.", usuario=current_user)
            flash('Categoría creada exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            registrar_log_sistema("Error Creación Categoría", f"Error al crear la categoría '{nombre}': {str(e)}", usuario=current_user)
            flash('Error al crear la categoría.', 'danger')
            
        return redirect(url_for('admin.categorias'))

    # Paginación y Listado (Ordenamiento Secundario)
    page = request.args.get('page', 1, type=int)
    busqueda = request.args.get('busqueda', '')
    
    query = CategoriaAplicacion.query
    if busqueda:
        query = query.filter(CategoriaAplicacion.nombre.ilike(f'%{busqueda}%'))
        
    pagination = query.order_by(CategoriaAplicacion.orden.asc(), CategoriaAplicacion.nombre.asc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/categorias.html', pagination=pagination, busqueda=busqueda)

@admin_bp.route('/editar_categoria/<int:id>', methods=['POST'])
def editar_categoria(id):
    categoria = CategoriaAplicacion.query.get_or_404(id)
    nombre = request.form.get('nombre', '').strip()
    orden = request.form.get('orden', '1').strip()

    if not nombre:
        flash('El nombre es obligatorio.', 'danger')
        return redirect(url_for('admin.categorias'))

    # Validación Backend: Evitar nombres duplicados excluyendo la actual
    existe = CategoriaAplicacion.query.filter(CategoriaAplicacion.nombre == nombre, CategoriaAplicacion.id != id).first()
    if existe:
        flash(f'Ya existe otra categoría llamada "{nombre}".', 'warning')
        return redirect(url_for('admin.categorias'))

    try:
        categoria.nombre = nombre
        categoria.orden = int(orden) if orden.isdigit() else 1
        db.session.commit()
        registrar_log_sistema("Edición Categoría", f"Categoría ID {categoria.id} actualizada.", usuario=current_user)
        flash('Categoría actualizada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        registrar_log_sistema("Error Edición Categoría", f"Error: {str(e)}", usuario=current_user)
        flash('Error al actualizar la categoría.', 'danger')

    return redirect(url_for('admin.categorias'))

@admin_bp.route('/toggle_categoria/<int:id>', methods=['POST'])
def toggle_categoria(id):
    categoria = CategoriaAplicacion.query.get_or_404(id)
    try:
        categoria.activo = not categoria.activo
        db.session.commit()
        estado = "activada" if categoria.activo else "desactivada"
        registrar_log_sistema("Cambio Estado Categoría", f"La categoría '{categoria.nombre}' fue {estado}.", usuario=current_user)
        flash(f"Categoría '{categoria.nombre}' {estado}.", 'success')
    except Exception as e:
        db.session.rollback()
        registrar_log_sistema("Error Cambio Estado Categoría", f"Error: {str(e)}", usuario=current_user)
        flash("Error al cambiar el estado.", 'danger')
    return redirect(url_for('admin.categorias'))

# --- GESTIÓN DE APLICACIONES ---

@admin_bp.route('/aplicaciones', methods=['GET', 'POST'])
def aplicaciones():
    # Solo mostrar categorías activas para crear nuevas apps
    categorias_activas = CategoriaAplicacion.query.filter_by(activo=True).order_by(CategoriaAplicacion.orden.asc(), CategoriaAplicacion.nombre.asc()).all()
    tipos = TipoAplicacion.query.filter_by(activo=True).all()
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        slug_raw = request.form.get('slug', '').strip()
        url_destino = request.form.get('url_destino', '').strip()
        cat_id = request.form.get('categoria_id')
        tipo_id = request.form.get('tipo_aplicacion_id')
        
        if not all([nombre, slug_raw, url_destino, cat_id, tipo_id]):
            flash('Faltan campos obligatorios.', 'danger')
            return redirect(url_for('admin.aplicaciones'))
        
        # Validación de URL simple: obligatorio http:// o https://
        if not url_destino.startswith(('http://', 'https://')):
            flash('La URL de destino debe comenzar con http:// o https://', 'danger')
            return redirect(url_for('admin.aplicaciones'))
        
        # Validar que la categoría de destino está activa
        cat_obj = CategoriaAplicacion.query.get(cat_id)
        if not cat_obj or not cat_obj.activo:
            flash('No puedes registrar una aplicación en una categoría inactiva o inexistente.', 'danger')
            return redirect(url_for('admin.aplicaciones'))
        
        # Normalización Backend a snake_case
        slug = normalizar_slug(slug_raw)
            
        # Validación Backend: Evitar nombres o slugs duplicados
        if Aplicacion.query.filter_by(nombre=nombre).first():
            flash(f'Ya existe una aplicación registrada con el nombre "{nombre}".', 'danger')
            return redirect(url_for('admin.aplicaciones'))

        if Aplicacion.query.filter_by(slug=slug).first():
            flash(f'El slug "{slug}" ya existe en otra aplicación.', 'danger')
            return redirect(url_for('admin.aplicaciones'))

        try:
            nueva_app = Aplicacion(
                nombre=nombre,
                slug=slug, # Se guarda el normalizado
                descripcion=request.form.get('descripcion', '').strip(),
                version=request.form.get('version', '').strip(),
                url_destino=url_destino,
                categoria_id=int(cat_id),
                tipo_aplicacion_id=int(tipo_id),
                orden=int(request.form.get('orden', '1'))
            )
            db.session.add(nueva_app)
            db.session.commit()
            registrar_log_sistema("Creación Aplicación", f"App '{nombre}' registrada.", usuario=current_user)
            flash('Aplicación registrada exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            registrar_log_sistema("Error Creación Aplicación", f"Error al crear la app '{nombre}': {str(e)}", usuario=current_user)
            flash('Error al crear la aplicación.', 'danger')
            
        return redirect(url_for('admin.aplicaciones'))

    # Paginación y Listado (Ordenamiento Secundario)
    todas_categorias = CategoriaAplicacion.query.order_by(CategoriaAplicacion.orden.asc(), CategoriaAplicacion.nombre.asc()).all()
    page = request.args.get('page', 1, type=int)
    cat_filtro = request.args.get('categoria_id', '')
    busqueda = request.args.get('busqueda', '')

    query = Aplicacion.query
    if cat_filtro and cat_filtro.isdigit():
        query = query.filter_by(categoria_id=int(cat_filtro))
    if busqueda:
        query = query.filter(or_(Aplicacion.nombre.ilike(f'%{busqueda}%'), Aplicacion.slug.ilike(f'%{busqueda}%')))
        
    pagination = query.order_by(Aplicacion.categoria_id, Aplicacion.orden.asc(), Aplicacion.nombre.asc()).paginate(page=page, per_page=10, error_out=False)

    return render_template('admin/aplicaciones.html', 
                           pagination=pagination, 
                           categorias=categorias_activas, # Para los selects de creación/edición
                           todas_categorias=todas_categorias, # Para el filtro general
                           tipos=tipos,
                           cat_filtro=cat_filtro,
                           busqueda=busqueda)
    
@admin_bp.route('/editar_aplicacion/<int:id>', methods=['POST'])
def editar_aplicacion(id):
    app_obj = Aplicacion.query.get_or_404(id)
    
    nombre = request.form.get('nombre', '').strip()
    # El slug NO se recibe del POST porque es de solo lectura (inmutable)
    url_destino = request.form.get('url_destino', '').strip()
    cat_id = request.form.get('categoria_id')
    tipo_id = request.form.get('tipo_aplicacion_id')

    if not all([nombre, url_destino, cat_id, tipo_id]):
        flash('Faltan campos obligatorios.', 'danger')
        return redirect(url_for('admin.aplicaciones'))
    
    if not url_destino.startswith(('http://', 'https://')):
        flash('La URL de destino debe comenzar obligatoriamente con http:// o https://', 'danger')
        return redirect(url_for('admin.aplicaciones'))
    
    cat_obj = CategoriaAplicacion.query.get(cat_id)
    if not cat_obj or not cat_obj.activo:
        flash('No se puede mover la aplicación a una categoría inactiva o inexistente.', 'danger')
        return redirect(url_for('admin.aplicaciones'))

    # Validación Backend: Evitar nombres duplicados excluyendo la actual
    existe_nombre = Aplicacion.query.filter(Aplicacion.nombre == nombre, Aplicacion.id != id).first()
    if existe_nombre:
        flash(f'Ya existe otra aplicación con el nombre "{nombre}".', 'warning')
        return redirect(url_for('admin.aplicaciones'))

    try:
        app_obj.nombre = nombre
        # app_obj.slug queda intacto
        app_obj.descripcion = request.form.get('descripcion', '').strip()
        app_obj.version = request.form.get('version', '').strip()
        app_obj.url_destino = url_destino
        app_obj.categoria_id = int(cat_id)
        app_obj.tipo_aplicacion_id = int(tipo_id)
        app_obj.orden = int(request.form.get('orden', '1'))
        
        db.session.commit()
        registrar_log_sistema("Edición Aplicación", f"App ID {app_obj.id} actualizada.", usuario=current_user)
        flash('Aplicación actualizada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        registrar_log_sistema("Error Edición Aplicación", f"Error: {str(e)}", usuario=current_user)
        flash('Error al actualizar la aplicación.', 'danger')

    return redirect(url_for('admin.aplicaciones'))

@admin_bp.route('/toggle_aplicacion/<int:id>', methods=['POST'])
def toggle_aplicacion(id):
    app_obj = Aplicacion.query.get_or_404(id)
    try:
        app_obj.activo = not app_obj.activo
        db.session.commit()
        estado = "activada" if app_obj.activo else "desactivada"
        registrar_log_sistema("Cambio Estado Aplicación", f"La app '{app_obj.nombre}' fue {estado}.", usuario=current_user)
        flash(f"Aplicación '{app_obj.nombre}' {estado}.", 'success')
    except Exception as e:
        db.session.rollback()
        registrar_log_sistema("Error Cambio Estado Aplicación", f"Error: {str(e)}", usuario=current_user)
        flash("Error al cambiar el estado.", 'danger')
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
        db.session.commit()
        registrar_log_sistema('Reenvío Activación', f'Nuevo enlace para ID {usuario.id}', usuario=current_user)
        if enviar_activacion_usuario(usuario, token):
            flash('Se envió un nuevo enlace de activación.', 'success')
        else:
            flash('No se pudo enviar el correo. Puedes intentar reenviarlo más tarde.', 'warning')
    except Exception:
        db.session.rollback()
        flash('No se pudo renovar el enlace.', 'danger')
    return redirect(url_for('admin.panel'))
