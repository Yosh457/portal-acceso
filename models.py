# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

db = SQLAlchemy()

def obtener_hora_chile():
    cl_tz = pytz.timezone('America/Santiago')
    return datetime.now(cl_tz)

# ==============================================================================
# TABLA INTERMEDIA (MUCHOS A MUCHOS)
# ==============================================================================
aplicaciones_roles = db.Table('aplicaciones_roles',
    db.Column('rol_id', db.Integer, db.ForeignKey('roles_aplicacion.id', ondelete='CASCADE'), primary_key=True),
    db.Column('aplicacion_id', db.Integer, db.ForeignKey('aplicaciones.id', ondelete='CASCADE'), primary_key=True)
)

# ==============================================================================
# CATÁLOGOS BASE Y ORGANIZACIÓN
# ==============================================================================
class RolAplicacion(db.Model):
    __tablename__ = 'roles_aplicacion'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    usuarios = db.relationship('Usuario', back_populates='rol')
    aplicaciones_permitidas = db.relationship(
        'Aplicacion', 
        secondary=aplicaciones_roles, 
        back_populates='roles_permitidos'
    )

# ==============================================================================
# USUARIOS
# ==============================================================================
class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=obtener_hora_chile, nullable=False)
    cambio_clave_requerido = db.Column(db.Boolean, default=False, nullable=False)
    reset_token = db.Column(db.String(32), unique=True, nullable=True)
    reset_token_expiracion = db.Column(db.DateTime, nullable=True)

    rol_id = db.Column(db.Integer, db.ForeignKey('roles_aplicacion.id'), nullable=False, index=True)

    rol = db.relationship('RolAplicacion', back_populates='usuarios')
    logs = db.relationship('LogSistema', back_populates='usuario')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ==============================================================================
# LOGS DEL SISTEMA (Auditoría)
# ==============================================================================
class LogSistema(db.Model):
    __tablename__ = 'log_sistema'
    id = db.Column(db.BigInteger, primary_key=True)
    timestamp = db.Column(db.DateTime, default=obtener_hora_chile, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True, index=True)
    usuario_nombre = db.Column(db.String(255), nullable=True)
    accion = db.Column(db.String(255), nullable=False)
    detalles = db.Column(db.Text, nullable=True)
    ip_origen = db.Column(db.String(50), nullable=True)

    usuario = db.relationship('Usuario', back_populates='logs')

# ==============================================================================
# SISTEMAS DEL PORTAL
# ==============================================================================
class CategoriaAplicacion(db.Model):
    __tablename__ = 'categorias_aplicacion'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    orden = db.Column(db.Integer, default=1, nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    aplicaciones = db.relationship('Aplicacion', back_populates='categoria', cascade='all, delete-orphan')

class TipoAplicacion(db.Model):
    __tablename__ = 'tipos_aplicacion'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    aplicaciones = db.relationship('Aplicacion', back_populates='tipo_aplicacion')

class Aplicacion(db.Model):
    __tablename__ = 'aplicaciones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    version = db.Column(db.String(50), nullable=True)
    url_destino = db.Column(db.String(500), nullable=False)
    
    tipo_aplicacion_id = db.Column(db.Integer, db.ForeignKey('tipos_aplicacion.id'), nullable=False, index=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias_aplicacion.id'), nullable=False, index=True)
    
    orden = db.Column(db.Integer, default=1, nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    categoria = db.relationship('CategoriaAplicacion', back_populates='aplicaciones')
    tipo_aplicacion = db.relationship('TipoAplicacion', back_populates='aplicaciones')
    
    roles_permitidos = db.relationship(
        'RolAplicacion', 
        secondary=aplicaciones_roles, 
        back_populates='aplicaciones_permitidas'
    )

    __table_args__ = (
        db.Index('idx_aplicaciones_activo_orden', 'activo', 'orden'),
    )