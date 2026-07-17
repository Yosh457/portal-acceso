# blueprints/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_

# Modelos adaptados al Portal de Acceso
from models import (
    db, Usuario, RolAplicacion, LogSistema,
    CategoriaAplicacion, TipoAplicacion, Aplicacion
)

# Utilidades 
from utils import registrar_log_sistema, admin_required, enviar_credenciales_nuevo_usuario

# Instanciamos el blueprint
admin_bp = Blueprint('admin', __name__, template_folder='../templates', url_prefix='/admin')

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

# --- RUTAS PRINCIPALES ---

@admin_bp.route('/panel')
def panel():
    """
    Vista principal del Panel de Administración.
    Muestra estadísticas rápidas del portal y tabla de usuarios.
    """
    page = request.args.get('page', 1, type=int)
    busqueda = request.args.get('busqueda', '')
    rol_filtro = request.args.get('rol_filtro', '')
    
    query = Usuario.query

    # Filtro por texto (Nombre o Email)
    if busqueda:
        query = query.filter(
            or_(Usuario.nombre_completo.ilike(f'%{busqueda}%'),
                Usuario.email.ilike(f'%{busqueda}%'))
        )
    
    # Filtro por Rol de Aplicación
    if rol_filtro:
        query = query.filter(Usuario.rol_id == rol_filtro)
    
    # Paginación de usuarios
    pagination = query.order_by(Usuario.id).paginate(page=page, per_page=10, error_out=False)
    roles_para_filtro = RolAplicacion.query.order_by(RolAplicacion.nombre).all()
    
    # Estadísticas
    stats = {
        'total_usuarios': Usuario.query.count(),
        'aplicaciones_activas': Aplicacion.query.filter_by(activo=True).count(),
        'categorias_activas': CategoriaAplicacion.query.filter_by(activo=True).count()
    }

    return render_template('admin/panel.html', 
                           pagination=pagination,
                           roles_para_filtro=roles_para_filtro,
                           busqueda=busqueda,
                           rol_filtro=rol_filtro,
                           stats=stats)

# --- GESTIÓN DE USUARIOS ---

@admin_bp.route('/crear_usuario', methods=['GET', 'POST'])
def crear_usuario():
    """Formulario para registrar nuevos usuarios."""
    roles = RolAplicacion.query.order_by(RolAplicacion.nombre).all()
    # Necesitamos las categorías con sus apps para el formulario
    categorias = CategoriaAplicacion.query.filter_by(activo=True).order_by(CategoriaAplicacion.orden).all()

    if request.method == 'POST':
        nombre = request.form.get('nombre_completo', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        rol_id = request.form.get('rol_id')
        forzar_cambio = request.form.get('forzar_cambio_clave') == '1'
        aplicaciones_ids = request.form.getlist('aplicaciones') # IDs de las apps seleccionadas
        
        # 🔴 Validaciones backend
        if not nombre or not email or not password or not rol_id:
            flash('Todos los campos obligatorios deben completarse.', 'danger')
            return render_template('admin/crear_usuario.html', roles=roles, datos_previos=request.form)
        
        # Validación de email duplicado
        if Usuario.query.filter_by(email=email).first():
            flash('Error: El correo electrónico ya se encuentra registrado.', 'danger')
            return render_template('admin/crear_usuario.html', roles=roles, datos_previos=request.form)

        try:
            nuevo_usuario = Usuario(
                nombre_completo=nombre,
                email=email,
                rol_id=int(rol_id),
                cambio_clave_requerido=forzar_cambio,
                activo=True
            )
            nuevo_usuario.set_password(password)
            
            # Asignar aplicaciones
            if aplicaciones_ids:
                apps_seleccionadas = Aplicacion.query.filter(Aplicacion.id.in_(aplicaciones_ids)).all()
                nuevo_usuario.aplicaciones_permitidas.extend(apps_seleccionadas)

            db.session.add(nuevo_usuario)
            db.session.commit()

            registrar_log_sistema("Creación Usuario", f"Admin creó a {nombre} ({email}).", usuario=current_user)

            if enviar_credenciales_nuevo_usuario(nuevo_usuario, password):
                flash(f'Usuario creado con éxito. Credenciales enviadas a {email}.', 'success')
            else:
                flash(f'Usuario creado, pero FALLÓ el envío del correo. Entregar clave manual: {password}', 'warning')

            return redirect(url_for('admin.panel'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error de base de datos: {str(e)}', 'danger')

    return render_template('admin/crear_usuario.html', roles=roles, categorias=categorias, datos_previos=request.form)

@admin_bp.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    """Permite modificar los datos básicos, perfil y permisos granulares de un usuario."""
    usuario = Usuario.query.get_or_404(id)
    roles = RolAplicacion.query.order_by(RolAplicacion.nombre).all()
    categorias = CategoriaAplicacion.query.filter_by(activo=True).order_by(CategoriaAplicacion.orden).all()

    if request.method == 'POST':
        email_nuevo = request.form.get('email', '').strip().lower()
        nombre_nuevo = request.form.get('nombre_completo', '').strip()
        rol_id = request.form.get('rol_id')
        forzar_cambio = request.form.get('forzar_cambio_clave') == '1'
        password = request.form.get('password', '').strip()
        aplicaciones_ids = request.form.getlist('aplicaciones')
        
        # Validación de duplicidad de email
        usuario_existente = Usuario.query.filter_by(email=email_nuevo).first()
        if usuario_existente and usuario_existente.id != id:
            flash('Error: Ese correo ya pertenece a otro usuario en el sistema.', 'danger')
            return render_template('admin/editar_usuario.html', usuario=usuario, roles=roles, categorias=categorias)

        usuario.nombre_completo = nombre_nuevo
        usuario.email = email_nuevo
        usuario.rol_id = int(rol_id)
        usuario.cambio_clave_requerido = forzar_cambio

        if password:
            usuario.set_password(password)
            flash('Contraseña actualizada correctamente.', 'info')
            
        # Actualizar permisos de aplicaciones
        if aplicaciones_ids:
            apps_seleccionadas = Aplicacion.query.filter(Aplicacion.id.in_(aplicaciones_ids)).all()
            usuario.aplicaciones_permitidas = apps_seleccionadas
        else:
            usuario.aplicaciones_permitidas = []

        try:
            db.session.commit()
            registrar_log_sistema("Edición Usuario", f"Admin editó perfil de {usuario.nombre_completo}.", usuario=current_user)
            flash('Usuario actualizado con éxito.', 'success')
            return redirect(url_for('admin.panel'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la base de datos: {str(e)}', 'danger')

    return render_template('admin/editar_usuario.html', usuario=usuario, roles=roles, categorias=categorias)

@admin_bp.route('/toggle_activo/<int:id>', methods=['POST'])
def toggle_activo(id):
    """
    Habilita o deshabilita a un usuario. 
    Protege al usuario actual de desactivarse a sí mismo.
    """
    usuario = Usuario.query.get_or_404(id)

    if usuario.id == current_user.id:
        flash('Medida de seguridad: No puedes desactivar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.panel'))

    try:
        usuario.activo = not usuario.activo
        db.session.commit()

        estado = "activado" if usuario.activo else "desactivado"
        registrar_log_sistema("Cambio Estado Usuario", f"Usuario {usuario.nombre_completo} fue {estado}.", usuario=current_user)
        flash(f'Usuario {usuario.nombre_completo} {estado} correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        registrar_log_sistema("Error Cambio Estado", f"Error al cambiar estado de {usuario.nombre_completo}: {str(e)}", usuario=current_user)
        flash('Ocurrió un error al cambiar el estado del usuario.', 'danger')

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
    categorias = CategoriaAplicacion.query.order_by(CategoriaAplicacion.orden.asc(), CategoriaAplicacion.nombre.asc()).all()
    tipos = TipoAplicacion.query.filter_by(activo=True).all()
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        slug = request.form.get('slug', '').strip().lower()
        url_destino = request.form.get('url_destino', '').strip()
        cat_id = request.form.get('categoria_id')
        tipo_id = request.form.get('tipo_aplicacion_id')
        
        if not all([nombre, slug, url_destino, cat_id, tipo_id]):
            flash('Faltan campos obligatorios.', 'danger')
            return redirect(url_for('admin.aplicaciones'))
            
        # Validación Backend: Evitar nombres o slugs duplicados
        if Aplicacion.query.filter_by(nombre=nombre).first():
            flash(f'Ya existe una aplicación registrada con el nombre "{nombre}".', 'danger')
            return redirect(url_for('admin.aplicaciones'))

        if Aplicacion.query.filter_by(slug=slug).first():
            flash('El slug especificado ya existe en otra aplicación.', 'danger')
            return redirect(url_for('admin.aplicaciones'))

        try:
            nueva_app = Aplicacion(
                nombre=nombre,
                slug=slug,
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
                           categorias=categorias,
                           tipos=tipos,
                           cat_filtro=cat_filtro,
                           busqueda=busqueda)
    
@admin_bp.route('/editar_aplicacion/<int:id>', methods=['POST'])
def editar_aplicacion(id):
    app_obj = Aplicacion.query.get_or_404(id)
    
    nombre = request.form.get('nombre', '').strip()
    slug = request.form.get('slug', '').strip().lower()
    url_destino = request.form.get('url_destino', '').strip()
    cat_id = request.form.get('categoria_id')
    tipo_id = request.form.get('tipo_aplicacion_id')

    if not all([nombre, slug, url_destino, cat_id, tipo_id]):
        flash('Faltan campos obligatorios.', 'danger')
        return redirect(url_for('admin.aplicaciones'))

    # Validación Backend: Evitar nombres duplicados excluyendo la actual
    existe_nombre = Aplicacion.query.filter(Aplicacion.nombre == nombre, Aplicacion.id != id).first()
    if existe_nombre:
        flash(f'Ya existe otra aplicación con el nombre "{nombre}".', 'warning')
        return redirect(url_for('admin.aplicaciones'))

    # Validación Backend: Evitar slugs duplicados excluyendo la actual
    existe_slug = Aplicacion.query.filter(Aplicacion.slug == slug, Aplicacion.id != id).first()
    if existe_slug:
        flash('El slug especificado ya pertenece a otra aplicación.', 'warning')
        return redirect(url_for('admin.aplicaciones'))

    try:
        app_obj.nombre = nombre
        app_obj.slug = slug
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