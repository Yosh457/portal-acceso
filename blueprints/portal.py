# blueprints/portal.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import CategoriaAplicacion, Aplicacion

portal_bp = Blueprint('portal', __name__)

# Diccionario centralizado de iconos (SVGs de Heroicons u otros) asociados al slug.
# Si agregas una app nueva con un slug diferente, solo debes mapear su ícono aquí.
ICONOS = {
    'fichas_clinicas': '<svg class="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>',
    'salud_mental': '<svg class="w-8 h-8 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path></svg>',
    'inventario_tics': '<svg class="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>',
    'sigges': '<svg class="w-8 h-8 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
    'default': '<svg class="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"></path></svg>'
}

@portal_bp.route('/')
@login_required
def index():
    # 1. Obtener todas las categorías activas, ordenadas (secundario por nombre)
    categorias_activas = CategoriaAplicacion.query.filter_by(activo=True)\
        .order_by(CategoriaAplicacion.orden.asc(), CategoriaAplicacion.nombre.asc())
    
    dashboard_data = []
    
    for categoria in categorias_activas:
        # 2. Filtrar aplicaciones permitidas, activas, y ordenarlas (secundario por nombre)
        aplicaciones = Aplicacion.query.filter(
            Aplicacion.categoria_id == categoria.id,
            Aplicacion.activo == True,
            Aplicacion.usuarios_permitidos.any(id=current_user.id)
        ).order_by(Aplicacion.orden.asc(), Aplicacion.nombre.asc()).all()
        
        # 3. Solo agregar la categoría al dashboard si tiene aplicaciones
        if aplicaciones:
            dashboard_data.append({
                'categoria': categoria,
                'aplicaciones': aplicaciones
            })
            
    return render_template('portal/index.html', dashboard_data=dashboard_data, ICONOS=ICONOS)