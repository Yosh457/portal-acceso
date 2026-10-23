# utils/helpers.py
from datetime import datetime

import pytz
from flask import current_app, has_request_context, request
from flask_login import current_user

def obtener_hora_chile():
    """Retorna la hora local de Santiago, sin modificar los modelos existentes."""
    return datetime.now(pytz.timezone('America/Santiago'))

def obtener_ip_cliente():
    """Usa la IP de Flask; no confía en cabeceras remitidas por el cliente.

    Si en producción se configura un proxy confiable, su tratamiento debe
    ajustarse explícitamente en el servidor/WSGI antes de esta función.
    """
    return request.remote_addr if has_request_context() else None

def registrar_log_sistema(accion, detalles, usuario=None, commit=True):
    """Registra un evento de auditoría.

    commit=True: evento independiente compatible con llamadas existentes;
    ante error registra diagnóstico y no altera el flujo de autenticación.
    commit=False: agrega el evento a la transacción del llamador, sin confirmar;
    propaga excepciones para que el llamador haga rollback de toda la operación.

    En modo transaccional, invocar ANTES de db.session.commit().
    """
    from models import db, LogSistema

    try:
        usuario_actual = usuario
        if usuario_actual is None and has_request_context() and current_user.is_authenticated:
            usuario_actual = current_user

        nuevo_log = LogSistema(
            usuario_id=usuario_actual.id if usuario_actual is not None else None,
            usuario_nombre=(usuario_actual.nombre_completo if usuario_actual is not None
                            else 'Sistema/Anónimo'),
            accion=accion,
            detalles=detalles,
            ip_origen=obtener_ip_cliente(),
            timestamp=obtener_hora_chile(),
        )
        db.session.add(nuevo_log)
        if commit:
            db.session.commit()
        return True
    except Exception:
        if not commit:
            raise
        db.session.rollback()
        current_app.logger.exception('No fue posible registrar el evento de auditoría: %s', accion)
        return False