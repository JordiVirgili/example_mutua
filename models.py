from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, Date, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session

# Base de SQLAlchemy para los modelos ORM
Base = declarative_base()


# Modelos SQLAlchemy (ORM) para la base de datos
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)


class Paciente(Base):
    __tablename__ = "pacientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    apellido = Column(String, index=True)
    fecha_nacimiento = Column(Date)
    numero_afiliado = Column(String, unique=True, index=True)
    pertenece_mutua = Column(Boolean, default=True)  # Indica si el paciente pertenece a la mutua

    # Relaciones
    autorizaciones = relationship("Autorizacion", back_populates="paciente")
    facturas = relationship("Factura", back_populates="paciente")
    servicios = relationship("ServicioUtilizado", back_populates="paciente")


class Tratamiento(Base):
    __tablename__ = "tratamientos"

    id = Column(Integer, primary_key=True, index=True)
    servicio = Column(String, index=True)
    descripcion = Column(String)
    tipo_servicio = Column(String, index=True)
    precio = Column(Float)
    incluido_mutua = Column(Boolean, default=False)
    duracion_minutos = Column(Integer)
    requiere_autorizacion = Column(Boolean, default=False)

    # Relaciones
    autorizaciones = relationship("Autorizacion", back_populates="tratamiento")


class Autorizacion(Base):
    __tablename__ = "autorizaciones"

    id = Column(Integer, primary_key=True, index=True)
    id_paciente = Column(Integer, ForeignKey("pacientes.id"))
    id_tratamiento = Column(Integer, ForeignKey("tratamientos.id"))
    fecha_solicitud = Column(Date)
    estado = Column(String)  # "pendiente", "aprobada", "rechazada"
    comentarios = Column(String, nullable=True)

    # Relaciones
    paciente = relationship("Paciente", back_populates="autorizaciones")
    tratamiento = relationship("Tratamiento", back_populates="autorizaciones")


class Factura(Base):
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, index=True)
    id_paciente = Column(Integer, ForeignKey("pacientes.id"))
    fecha_emision = Column(Date)
    monto_total = Column(Float)
    estado = Column(String)  # "pendiente", "pagada", "vencida"

    # Relaciones
    paciente = relationship("Paciente", back_populates="facturas")
    detalles = relationship("DetalleFactura", back_populates="factura")


class DetalleFactura(Base):
    __tablename__ = "detalles_factura"

    id = Column(Integer, primary_key=True, index=True)
    id_factura = Column(Integer, ForeignKey("facturas.id"))
    concepto = Column(String)
    monto = Column(Float)

    # Relaciones
    factura = relationship("Factura", back_populates="detalles")


class ServicioClinica(Base):
    __tablename__ = "servicios_clinica"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    descripcion = Column(String)
    tipo_servicio = Column(String)
    precio = Column(Float)
    incluido_mutua = Column(Boolean, default=False)
    duracion_minutos = Column(Integer)


class ServicioUtilizado(Base):
    __tablename__ = "servicios_utilizados"

    id = Column(Integer, primary_key=True, index=True)
    id_paciente = Column(Integer, ForeignKey("pacientes.id"))
    descripcion = Column(String)
    fecha = Column(Date)
    costo = Column(Float)

    # Relaciones
    paciente = relationship("Paciente", back_populates="servicios")


# Modelos Pydantic para la API (esquemas)
class TokenBase(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserInDB(UserBase):
    id: int
    hashed_password: str
    is_active: bool

    class Config:
        from_attributes = True


class PacienteBase(BaseModel):
    nombre: str
    apellido: str
    fecha_nacimiento: date
    numero_afiliado: str
    pertenece_mutua: bool = True


class PacienteCreate(PacienteBase):
    pass


class PacienteInDB(PacienteBase):
    id: int

    class Config:
        from_attributes = True


class TratamientoBase(BaseModel):
    servicio: str
    descripcion: str
    tipo_servicio: str
    precio: float
    incluido_mutua: bool
    duracion_minutos: int
    requiere_autorizacion: bool


class TratamientoCreate(TratamientoBase):
    pass


class TratamientoInDB(TratamientoBase):
    id: int

    class Config:
        from_attributes = True


class AutorizacionBase(BaseModel):
    id_paciente: int
    id_tratamiento: int
    estado: str
    comentarios: Optional[str] = None


class AutorizacionCreate(AutorizacionBase):
    pass


class AutorizacionInDB(AutorizacionBase):
    id: int
    fecha_solicitud: date

    class Config:
        from_attributes = True


class AutorizacionWithDetails(AutorizacionInDB):
    paciente: PacienteInDB
    tratamiento: TratamientoInDB

    class Config:
        from_attributes = True


class DetalleFacturaBase(BaseModel):
    concepto: str
    monto: float


class DetalleFacturaCreate(DetalleFacturaBase):
    pass


class DetalleFacturaInDB(DetalleFacturaBase):
    id: int
    id_factura: int

    class Config:
        from_attributes = True


class FacturaBase(BaseModel):
    id_paciente: int
    fecha_emision: date
    monto_total: float
    estado: str


class FacturaCreate(FacturaBase):
    detalles: List[DetalleFacturaCreate]


class FacturaInDB(FacturaBase):
    id: int
    detalles: List[DetalleFacturaInDB] = []

    class Config:
        from_attributes = True


class ServicioClinicaBase(BaseModel):
    nombre: str
    descripcion: str
    tipo_servicio: str
    precio: float
    incluido_mutua: bool
    duracion_minutos: int


class ServicioClinicaCreate(ServicioClinicaBase):
    pass


class ServicioClinicaInDB(ServicioClinicaBase):
    id: int

    class Config:
        from_attributes = True


class ServicioUtilizadoBase(BaseModel):
    id_paciente: int
    descripcion: str
    fecha: date
    costo: float


class ServicioUtilizadoCreate(ServicioUtilizadoBase):
    pass


class ServicioUtilizadoInDB(ServicioUtilizadoBase):
    id: int

    class Config:
        from_attributes = True


class InformeServicios(BaseModel):
    paciente: str
    numero_afiliado: str
    periodo: Dict[str, Any]
    servicios: List[ServicioUtilizadoInDB]
    total: float