"""Pruebas aisladas con SQLite: no utilizan MySQL ni alteran datos reales.

Ejecutar desde la raíz del proyecto:
    python -m unittest discover -s tests -v
"""
import unittest

from flask import Flask
from flask_login import LoginManager
from sqlalchemy import BigInteger, event
from sqlalchemy.ext.compiler import compiles

# SQLite solo autogenera PK si el tipo SQL se llama INTEGER.
# Esta adaptación se limita al proceso de pruebas y no altera models.py
# ni el tipo BIGINT AUTO_INCREMENT utilizado por MySQL.
@compiles(BigInteger, 'sqlite')
def compilar_bigint_para_sqlite(element, compiler, **kw):
    return 'INTEGER'

from models import db, CategoriaAplicacion, LogSistema
from utils.helpers import obtener_ip_cliente, registrar_log_sistema

class TestAuditoria(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SECRET_KEY='clave-solo-para-pruebas',
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(self.app)
        # En las pruebas no hay usuarios autenticados ni sesiones reales.
        login_manager = LoginManager()
        login_manager.user_loader(lambda user_id: None)
        login_manager.init_app(self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_ip_no_confia_en_cabeceras(self):
        with self.app.test_request_context(
            '/', environ_base={'REMOTE_ADDR': '192.0.2.10'},
            headers={'X-Forwarded-For': '203.0.113.200',
                     'X-Real-IP': '203.0.113.201'}
        ):
            self.assertEqual(obtener_ip_cliente(), '192.0.2.10')

    def test_auditoria_independiente(self):
        with self.app.test_request_context('/'):
            self.assertTrue(registrar_log_sistema('Prueba', 'Registro independiente'))
        self.assertEqual(LogSistema.query.count(), 1)

    def test_cambio_y_auditoria_transaccional(self):
        with self.app.test_request_context('/'):
            db.session.add(CategoriaAplicacion(nombre='Prueba', orden=1))
            self.assertTrue(registrar_log_sistema('Creación Categoría', 'Prueba', commit=False))
            # Todavía no se ha confirmado nada: commit=False solo agrega a la sesión.
            self.assertEqual(len([obj for obj in db.session.new if isinstance(obj, LogSistema)]), 1)
            db.session.commit()
        self.assertEqual(CategoriaAplicacion.query.count(), 1)
        self.assertEqual(LogSistema.query.count(), 1)

    def test_falla_auditoria_retrocede_cambio(self):
        def falla_insercion(mapper, connection, target):
            raise RuntimeError('Fallo simulado de auditoría')

        event.listen(LogSistema, 'before_insert', falla_insercion)
        try:
            with self.app.test_request_context('/'):
                db.session.add(CategoriaAplicacion(nombre='No Persistir', orden=1))
                registrar_log_sistema('Creación Categoría', 'Prueba', commit=False)
                with self.assertRaises(RuntimeError):
                    db.session.commit()
                db.session.rollback()
            self.assertEqual(CategoriaAplicacion.query.count(), 0)
            self.assertEqual(LogSistema.query.count(), 0)
        finally:
            event.remove(LogSistema, 'before_insert', falla_insercion)

if __name__ == '__main__':
    unittest.main()