"""Crea una cuenta administrativa inicial de forma interactiva.

Ejecutar tras inicializar la base de datos:
    python crear_superadmin.py
"""

from getpass import getpass

from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from models import db, RolAplicacion, Usuario
from utils.security import password_valida

def crear_admin():
    app = create_app()
    with app.app_context():
        print('\n--- CREACIÓN DE ADMINISTRADOR INICIAL ---\n')

        rol_admin = RolAplicacion.query.filter_by(nombre='Admin').first()
        if rol_admin is None:
            print('Error: no existe el rol Admin. Ejecuta primero inicializar_bd.py.')
            return 1

        nombre = input('Nombre completo: ').strip()
        if not nombre or len(nombre) > 255:
            print('Error: el nombre debe tener entre 1 y 255 caracteres.')
            return 1

        email = input('Correo electrónico: ').strip().lower()
        # Validación práctica básica; no sustituye comprobaciones del servidor de correo.
        from email_validator import EmailNotValidError, validate_email
        try:
            email = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError:
            print('Error: ingresa un correo electrónico válido.')
            return 1
        if len(email) > 255:
            print('Error: el correo es demasiado largo.')
            return 1

        if Usuario.query.filter_by(email=email).first():
            print('Error: ya existe una cuenta registrada con ese correo.')
            return 1

        clave = getpass('Contraseña (mínimo 8 caracteres, mayúscula y número): ')
        confirmar = getpass('Confirmar contraseña: ')
        if not password_valida(clave, confirmar):
            print('Error: las contraseñas deben coincidir y cumplir los requisitos.')
            return 1

        usuario = Usuario(
            nombre_completo=nombre,
            email=email,
            rol_id=rol_admin.id,
            activo=True,
            activacion_pendiente=False,
            cambio_clave_requerido=False,
        )
        usuario.set_password(clave)
        try:
            db.session.add(usuario)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception('Error al crear el administrador inicial')
            print('Error: no fue posible guardar la cuenta. Revisa los registros del servidor.')
            return 1

        print('\nAdministrador creado correctamente. Inicia Flask y accede a /login.')
        return 0

if __name__ == '__main__':
    raise SystemExit(crear_admin())