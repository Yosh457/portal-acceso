"""Inicialización de una base de datos VACÍA de PortalAcceso.

No ejecuta migraciones destructivas ni elimina registros existentes.
Uso: python inicializar_bd.py
"""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from models import db, RolAplicacion, TipoAplicacion

SQL_LIMITES = """
CREATE TABLE IF NOT EXISTS limites_solicitudes (
    clave CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    ventana BIGINT UNSIGNED NOT NULL,
    intentos INT UNSIGNED NOT NULL DEFAULT 0,
    expira_en DATETIME NOT NULL,
    PRIMARY KEY (clave, ventana),
    INDEX idx_limites_expira (expira_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

def inicializar():
    app = create_app()
    with app.app_context():
        try:
            # Crea únicamente tablas faltantes definidas en models.py.
            db.create_all()
            db.session.execute(text(SQL_LIMITES))

            if RolAplicacion.query.filter_by(nombre='Admin').first() is None:
                db.session.add(RolAplicacion(nombre='Admin'))

            # Catálogo de los tipos previstos por PortalAcceso.
            for nombre in ('Interno', 'Externo', 'IFRAME'):
                if TipoAplicacion.query.filter_by(nombre=nombre).first() is None:
                    db.session.add(TipoAplicacion(nombre=nombre, activo=True))

            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception('Error al inicializar la base de datos')
            print('Error de inicialización. Revisa la configuración MySQL y los registros.')
            return 1

        print('Tablas y catálogos mínimos comprobados correctamente.')
        print('Siguiente paso: python crear_superadmin.py')
        return 0

if __name__ == '__main__':
    raise SystemExit(inicializar())