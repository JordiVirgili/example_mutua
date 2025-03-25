import os
import logging
import hashlib
import csv
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt

from models import Base, User, Paciente, Tratamiento, Autorizacion, Factura, DetalleFactura, ServicioUtilizado, \
    ServicioClinica

# Configuración
PG_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/mutua_db")
SQLITE_DATABASE_URL = "sqlite:///./mutua.db"
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
TST_USER = os.getenv("TST_USER", "admin")
TST_PASSWORD = os.getenv("TST_PASSWORD", "password")

# Inicialización de la conexión a base de datos
# Intenta conectar con PostgreSQL, si falla usa SQLite
try:
    logging.info("Intentando conectar a PostgreSQL...")
    engine = create_engine(PG_DATABASE_URL)
    # Probar la conexión
    with engine.connect() as conn:
        pass
    logging.info("Conexión a PostgreSQL exitosa")
except Exception as e:
    logging.warning(f"No se pudo conectar a PostgreSQL: {e}")
    logging.info("Usando SQLite como alternativa")
    engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False}  # Necesario para SQLite
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Creación de tablas
Base.metadata.create_all(bind=engine)


# Función para crear la conexión a la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Funciones de seguridad y autenticación simplificadas (sin bcrypt)
def get_simple_hash(password):
    """Función de hash simple usando sha256 - SOLO PARA DESARROLLO"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password, hashed_password):
    """Verificación de contraseña simple - SOLO PARA DESARROLLO"""
    # Si el hash empieza con "simple:", usar nuestro método simple
    if hashed_password.startswith("simple:"):
        actual_hash = hashed_password[7:]  # Quitar el prefijo "simple:"
        return get_simple_hash(plain_password) == actual_hash
    # Para compatibilidad hacia atrás o si decides usar bcrypt en el futuro
    return False


def get_password_hash(password):
    """Genera un hash simple - SOLO PARA DESARROLLO"""
    return f"simple:{get_simple_hash(password)}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Funciones para inicializar datos de prueba
def init_db(db: Session):
    # Crear usuario admin si no existe
    user = db.query(User).filter(User.username == TST_USER).first()
    if not user:
        db_user = User(username=TST_USER, hashed_password=get_password_hash(TST_PASSWORD), is_active=True)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    # Inicializar pacientes de prueba
    if db.query(Paciente).count() == 0:
        pacientes = [
            Paciente(nombre="Juan", apellido="Pérez", fecha_nacimiento=date(1980, 5, 15), numero_afiliado="A12345",
                pertenece_mutua=True),
            Paciente(nombre="María", apellido="González", fecha_nacimiento=date(1975, 10, 22), numero_afiliado="A67890",
                pertenece_mutua=True),
            Paciente(nombre="Pedro", apellido="Martínez", fecha_nacimiento=date(1990, 3, 8), numero_afiliado="B12345",
                pertenece_mutua=False  # Este paciente no pertenece a la mutua
            )]
        db.add_all(pacientes)
        db.commit()

    # Inicializar tratamientos de prueba
    if db.query(Tratamiento).count() == 0:
        tratamientos = [Tratamiento(descripcion="Consulta médica general", costo=50.0, requiere_autorizacion=False),
            Tratamiento(descripcion="Resonancia magnética", costo=500.0, requiere_autorizacion=True),
            Tratamiento(descripcion="Cirugía ambulatoria", costo=1200.0, requiere_autorizacion=True)]
        db.add_all(tratamientos)
        db.commit()

    # Inicializar catálogo de servicios de la clínica
    if db.query(ServicioClinica).count() == 0:
        # Cargar datos del CSV de servicios
        servicios_data = [
            {"nombre": "Consulta médica general", "descripcion": "Evaluación general de la salud del paciente.",
             "tipo_servicio": "Consulta General", "precio": 50.0, "incluido_mutua": True, "duracion_minutos": 30},
            {"nombre": "Consulta de especialidad (Cardiología)",
             "descripcion": "Valoración especializada del sistema cardiovascular.",
             "tipo_servicio": "Consulta Especializada", "precio": 80.0, "incluido_mutua": True, "duracion_minutos": 40},
            {"nombre": "Consulta de especialidad (Dermatología)",
             "descripcion": "Diagnóstico y tratamiento de enfermedades de la piel.",
             "tipo_servicio": "Consulta Especializada", "precio": 75.0, "incluido_mutua": True, "duracion_minutos": 30},
            {"nombre": "Consulta de especialidad (Neurología)",
             "descripcion": "Evaluación y diagnóstico de trastornos neurológicos.",
             "tipo_servicio": "Consulta Especializada", "precio": 90.0, "incluido_mutua": False,
             "duracion_minutos": 45},
            {"nombre": "Análisis de sangre completo", "descripcion": "Examen general de componentes sanguíneos.",
             "tipo_servicio": "Prueba Diagnóstica", "precio": 40.0, "incluido_mutua": True, "duracion_minutos": 15},
            {"nombre": "Electrocardiograma (ECG)", "descripcion": "Registro de la actividad eléctrica del corazón.",
             "tipo_servicio": "Prueba Diagnóstica", "precio": 35.0, "incluido_mutua": True, "duracion_minutos": 20},
            {"nombre": "Ecografía abdominal", "descripcion": "Exploración por ultrasonido de órganos abdominales.",
             "tipo_servicio": "Prueba Diagnóstica", "precio": 90.0, "incluido_mutua": False, "duracion_minutos": 30},
            {"nombre": "Resonancia Magnética (RMN)",
             "descripcion": "Exploración por imágenes de alta resolución del cuerpo.",
             "tipo_servicio": "Prueba Diagnóstica", "precio": 250.0, "incluido_mutua": False, "duracion_minutos": 60},
            {"nombre": "Radiografía de tórax", "descripcion": "Imagen del tórax para evaluar pulmones y corazón.",
             "tipo_servicio": "Prueba Diagnóstica", "precio": 50.0, "incluido_mutua": True, "duracion_minutos": 20},
            {"nombre": "Colonoscopia", "descripcion": "Exploración del colon mediante endoscopio.",
             "tipo_servicio": "Prueba Diagnóstica", "precio": 300.0, "incluido_mutua": False, "duracion_minutos": 45},
            {"nombre": "Fisioterapia rehabilitadora", "descripcion": "Terapia física para recuperación de lesiones.",
             "tipo_servicio": "Terapia", "precio": 60.0, "incluido_mutua": True, "duracion_minutos": 45},
            {"nombre": "Sesión de psicología clínica", "descripcion": "Evaluación y tratamiento psicológico.",
             "tipo_servicio": "Terapia", "precio": 70.0, "incluido_mutua": False, "duracion_minutos": 50},
            {"nombre": "Consulta de ginecología", "descripcion": "Revisión ginecológica y prevención de enfermedades.",
             "tipo_servicio": "Consulta Especializada", "precio": 80.0, "incluido_mutua": True, "duracion_minutos": 40},
            {"nombre": "Consulta de pediatría", "descripcion": "Valoración de la salud infantil.",
             "tipo_servicio": "Consulta Especializada", "precio": 60.0, "incluido_mutua": True, "duracion_minutos": 30},
            {"nombre": "Extracción de lunar", "descripcion": "Procedimiento quirúrgico menor para eliminar lunares.",
             "tipo_servicio": "Cirugía Menor", "precio": 120.0, "incluido_mutua": False, "duracion_minutos": 30},
            {"nombre": "Vacunación antigripal", "descripcion": "Administración de vacuna contra la gripe.",
             "tipo_servicio": "Prevención", "precio": 25.0, "incluido_mutua": True, "duracion_minutos": 15},
            {"nombre": "Ergometría (Prueba de esfuerzo)",
             "descripcion": "Evaluación del rendimiento cardíaco bajo esfuerzo.", "tipo_servicio": "Prueba Diagnóstica",
             "precio": 110.0, "incluido_mutua": False, "duracion_minutos": 45},
            {"nombre": "Holter de presión arterial", "descripcion": "Monitoreo continuo de la presión arterial.",
             "tipo_servicio": "Prueba Diagnóstica", "precio": 90.0, "incluido_mutua": True, "duracion_minutos": 30}]

        servicios = []
        for servicio_data in servicios_data:
            servicios.append(ServicioClinica(nombre=servicio_data["nombre"], descripcion=servicio_data["descripcion"],
                tipo_servicio=servicio_data["tipo_servicio"], precio=servicio_data["precio"],
                incluido_mutua=servicio_data["incluido_mutua"], duracion_minutos=servicio_data["duracion_minutos"]))

        db.add_all(servicios)
        db.commit()

    # Obtener pacientes y tratamientos para crear registros relacionados
    pacientes = db.query(Paciente).all()
    tratamientos = db.query(Tratamiento).all()

    # Inicializar autorizaciones de prueba
    if db.query(Autorizacion).count() == 0 and pacientes and tratamientos:
        autorizaciones = [Autorizacion(id_paciente=pacientes[0].id, id_tratamiento=tratamientos[1].id,
            fecha_solicitud=date(2023, 1, 15), estado="aprobada",
            comentarios="Autorización aprobada sin observaciones"),
            Autorizacion(id_paciente=pacientes[1].id, id_tratamiento=tratamientos[2].id,
                fecha_solicitud=date(2023, 2, 10), estado="rechazada",
                comentarios="Falta documentación médica de respaldo")]
        db.add_all(autorizaciones)
        db.commit()

    # Inicializar facturas de prueba
    if db.query(Factura).count() == 0 and pacientes:
        # Factura para el primer paciente
        factura1 = Factura(id_paciente=pacientes[0].id, fecha_emision=date(2023, 1, 20), monto_total=550.0,
            estado="pagada")
        db.add(factura1)
        db.commit()
        db.refresh(factura1)

        # Detalles de la factura 1
        detalles1 = [DetalleFactura(id_factura=factura1.id, concepto="Consulta médica", monto=50.0),
            DetalleFactura(id_factura=factura1.id, concepto="Resonancia magnética", monto=500.0)]
        db.add_all(detalles1)

        # Factura para el segundo paciente
        factura2 = Factura(id_paciente=pacientes[1].id, fecha_emision=date(2023, 2, 15), monto_total=50.0,
            estado="pendiente")
        db.add(factura2)
        db.commit()
        db.refresh(factura2)

        # Detalle de la factura 2
        detalle2 = DetalleFactura(id_factura=factura2.id, concepto="Consulta médica", monto=50.0)
        db.add(detalle2)
        db.commit()

    # Inicializar servicios utilizados de prueba
    if db.query(ServicioUtilizado).count() == 0 and pacientes:
        servicios = [ServicioUtilizado(id_paciente=pacientes[0].id, descripcion="Consulta médica general",
            fecha=date(2023, 1, 15), costo=50.0),
            ServicioUtilizado(id_paciente=pacientes[0].id, descripcion="Resonancia magnética", fecha=date(2023, 1, 16),
                costo=500.0), ServicioUtilizado(id_paciente=pacientes[1].id, descripcion="Consulta médica general",
                fecha=date(2023, 2, 10), costo=50.0)]
        db.add_all(servicios)
        db.commit()